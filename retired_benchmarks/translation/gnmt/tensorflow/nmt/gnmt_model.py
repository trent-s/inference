# Copyright 2017 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================

"""GNMT attention sequence-to-sequence model with dynamic RNN support."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import tensorflow as tf

from . import attention_model
from . import model_helper
from .utils import misc_utils as utils
from .utils import vocab_utils

__all__ = ["GNMTModel"]


class GNMTModel(attention_model.AttentionModel):
    """Sequence-to-sequence dynamic model with GNMT attention architecture."""

    def __init__(
        self,
        hparams,
        mode,
        iterator,
        source_vocab_table,
        target_vocab_table,
        reverse_target_vocab_table=None,
        scope=None,
        extra_args=None,
    ):
        self.is_gnmt_attention = hparams.attention_architecture in [
            "gnmt", "gnmt_v2"]

        super(GNMTModel, self).__init__(
            hparams=hparams,
            mode=mode,
            iterator=iterator,
            source_vocab_table=source_vocab_table,
            target_vocab_table=target_vocab_table,
            reverse_target_vocab_table=reverse_target_vocab_table,
            scope=scope,
            extra_args=extra_args,
        )

    def _build_encoder(self, hparams):
        """Build a GNMT encoder."""
        if hparams.encoder_type == "uni" or hparams.encoder_type == "bi":
            return super(GNMTModel, self)._build_encoder(hparams)

        if hparams.encoder_type != "gnmt":
            raise ValueError("Unknown encoder_type %s" % hparams.encoder_type)

        # Build GNMT encoder.
        num_bi_layers = 1
        num_uni_layers = self.num_encoder_layers - num_bi_layers
        utils.print_out("# Build a GNMT encoder")
        utils.print_out("  num_bi_layers = %d" % num_bi_layers)
        utils.print_out("  num_uni_layers = %d" % num_uni_layers)

        iterator = self.iterator
        source = iterator.source
        if self.time_major:
            source = tf.transpose(source)

        with tf.variable_scope("encoder") as scope:
            dtype = scope.dtype

            self.encoder_emb_inp = self.encoder_emb_lookup_fn(
                self.embedding_encoder, source
            )

            # Execute _build_bidirectional_rnn from Model class
            bi_encoder_outputs, bi_encoder_state = self._build_bidirectional_rnn(
                inputs=self.encoder_emb_inp,
                sequence_length=iterator.source_sequence_length,
                dtype=dtype,
                hparams=hparams,
                num_bi_layers=num_bi_layers,
                num_bi_residual_layers=0,  # no residual connection
            )

            # Build unidirectional layers
            if self.extract_encoder_layers:
                encoder_state, encoder_outputs = self._build_individual_encoder_layers(
                    bi_encoder_outputs, num_uni_layers, dtype, hparams
                )
            else:
                encoder_state, encoder_outputs = self._build_all_encoder_layers(
                    bi_encoder_outputs, num_uni_layers, dtype, hparams
                )

            # Pass all encoder states to the decoder
            #   except the first bi-directional layer
            encoder_state = (bi_encoder_state[1],) + (
                (encoder_state,) if num_uni_layers == 1 else encoder_state
            )

        return encoder_outputs, encoder_state

    def _build_all_encoder_layers(
        self, bi_encoder_outputs, num_uni_layers, dtype, hparams
    ):
        """Build encoder layers all at once."""
        uni_cell = model_helper.create_rnn_cell(
            unit_type=hparams.unit_type,
            num_units=hparams.num_units,
            num_layers=num_uni_layers,
            num_residual_layers=self.num_encoder_residual_layers,
            forget_bias=hparams.forget_bias,
            dropout=hparams.dropout,
            num_gpus=self.num_gpus,
            base_gpu=1,
            mode=self.mode,
            single_cell_fn=self.single_cell_fn,
        )
        encoder_outputs, encoder_state = tf.nn.dynamic_rnn(
            uni_cell,
            bi_encoder_outputs,
            dtype=dtype,
            sequence_length=self.iterator.source_sequence_length,
            time_major=self.time_major,
        )

        # Use the top layer for now
        self.encoder_state_list = [encoder_outputs]

        return encoder_state, encoder_outputs

    def _build_individual_encoder_layers(
        self, bi_encoder_outputs, num_uni_layers, dtype, hparams
    ):
        """Run each of the encoder layer separately, not used in general seq2seq."""
        uni_cell_lists = model_helper._cell_list(
            unit_type=hparams.unit_type,
            num_units=hparams.num_units,
            num_layers=num_uni_layers,
            num_residual_layers=self.num_encoder_residual_layers,
            forget_bias=hparams.forget_bias,
            dropout=hparams.dropout,
            num_gpus=self.num_gpus,
            base_gpu=1,
            mode=self.mode,
            single_cell_fn=self.single_cell_fn,
        )

        encoder_inp = bi_encoder_outputs
        encoder_states = []
        self.encoder_state_list = [
            bi_encoder_outputs[:, :, : hparams.num_units],
            bi_encoder_outputs[:, :, hparams.num_units:],
        ]
        with tf.variable_scope("rnn/multi_rnn_cell"):
            for i, cell in enumerate(uni_cell_lists):
                with tf.variable_scope("cell_%d" % i) as scope:
                    encoder_inp, encoder_state = tf.nn.dynamic_rnn(
                        cell,
                        encoder_inp,
                        dtype=dtype,
                        sequence_length=self.iterator.source_sequence_length,
                        time_major=self.time_major,
                        scope=scope,
                    )
                    encoder_states.append(encoder_state)
                    self.encoder_state_list.append(encoder_inp)

        encoder_state = tuple(encoder_states)
        encoder_outputs = self.encoder_state_list[-1]
        return encoder_state, encoder_outputs

    def _build_decoder_cell(
        self, hparams, encoder_outputs, encoder_state, source_sequence_length
    ):
        """Build a RNN cell with GNMT attention architecture."""
        # Standard attention
        if not self.is_gnmt_attention:
            return super(GNMTModel, self)._build_decoder_cell(
                hparams, encoder_outputs, encoder_state, source_sequence_length
            )

        # GNMT attention
        attention_option = hparams.attention
        attention_architecture = hparams.attention_architecture
        num_units = hparams.num_units
        infer_mode = hparams.infer_mode

        dtype = tf.float32

        if self.time_major:
            memory = tf.transpose(encoder_outputs, [1, 0, 2])
        else:
            memory = encoder_outputs

        if self.mode == tf.contrib.learn.ModeKeys.INFER and infer_mode == "beam_search":
            memory, source_sequence_length, encoder_state, batch_size = (
                self._prepare_beam_search_decoder_inputs(
                    hparams.beam_width, memory, source_sequence_length, encoder_state
                )
            )
        else:
            batch_size = self.batch_size

        attention_mechanism = self.attention_mechanism_fn(
            attention_option, num_units, memory, source_sequence_length, self.mode
        )

        cell_list = model_helper._cell_list(  # pylint: disable=protected-access
            unit_type=hparams.unit_type,
            num_units=num_units,
            num_layers=self.num_decoder_layers,
            num_residual_layers=self.num_decoder_residual_layers,
            forget_bias=hparams.forget_bias,
            dropout=hparams.dropout,
            num_gpus=self.num_gpus,
            mode=self.mode,
            single_cell_fn=self.single_cell_fn,
            residual_fn=gnmt_residual_fn,
        )

        # Only wrap the bottom layer with the attention mechanism.
        attention_cell = cell_list.pop(0)

        # Only generate alignment in greedy INFER mode.
        alignment_history = (
            self.mode == tf.contrib.learn.ModeKeys.INFER and infer_mode != "beam_search"
        )
        attention_cell = tf.contrib.seq2seq.AttentionWrapper(
            attention_cell,
            attention_mechanism,
            attention_layer_size=None,  # don't use attention layer.
            output_attention=False,
            alignment_history=alignment_history,
            name="attention",
        )

        if attention_architecture == "gnmt":
            cell = GNMTAttentionMultiCell(attention_cell, cell_list)
        elif attention_architecture == "gnmt_v2":
            cell = GNMTAttentionMultiCell(
                attention_cell, cell_list, use_new_attention=True
            )
        else:
            raise ValueError(
                "Unknown attention_architecture %s" % attention_architecture
            )

        if hparams.pass_hidden_state:
            decoder_initial_state = tuple(
                (
                    zs.clone(cell_state=es)
                    if isinstance(zs, tf.contrib.seq2seq.AttentionWrapperState)
                    else es
                )
                for zs, es in zip(cell.zero_state(batch_size, dtype), encoder_state)
            )
        else:
            decoder_initial_state = cell.zero_state(batch_size, dtype)

        return cell, decoder_initial_state

    def _get_infer_summary(self, hparams):
        if hparams.infer_mode == "beam_search":
            return tf.no_op()
        elif self.is_gnmt_attention:
            return attention_model._create_attention_images_summary(
                self.final_context_state[0]
            )
        else:
            return super(GNMTModel, self)._get_infer_summary(hparams)


class GNMTAttentionMultiCell(tf.nn.rnn_cell.MultiRNNCell):
    """A MultiCell with GNMT attention style."""

    def __init__(self, attention_cell, cells, use_new_attention=False):
        """Creates a GNMTAttentionMultiCell.

        Args:
          attention_cell: An instance of AttentionWrapper.
          cells: A list of RNNCell wrapped with AttentionInputWrapper.
          use_new_attention: Whether to use the attention generated from current
            step bottom layer's output. Default is False.
        """
        cells = [attention_cell] + cells
        self.use_new_attention = use_new_attention
        super(
            GNMTAttentionMultiCell,
            self).__init__(
            cells,
            state_is_tuple=True)

    def __call__(self, inputs, state, scope=None):
        """Run the cell with bottom layer's attention copied to all upper layers."""
        if not tf.contrib.framework.nest.is_sequence(state):
            raise ValueError(
                "Expected state to be a tuple of length %d, but received: %s"
                % (len(self.state_size), state)
            )

        with tf.variable_scope(scope or "multi_rnn_cell"):
            new_states = []

            with tf.variable_scope("cell_0_attention"):
                attention_cell = self._cells[0]
                attention_state = state[0]
                cur_inp, new_attention_state = attention_cell(
                    inputs, attention_state)
                new_states.append(new_attention_state)

            for i in range(1, len(self._cells)):
                with tf.variable_scope("cell_%d" % i):

                    cell = self._cells[i]
                    cur_state = state[i]

                    if self.use_new_attention:
                        cur_inp = tf.concat(
                            [cur_inp, new_attention_state.attention], -1
                        )
                    else:
                        cur_inp = tf.concat(
                            [cur_inp, attention_state.attention], -1)

                    cur_inp, new_state = cell(cur_inp, cur_state)
                    new_states.append(new_state)

        return cur_inp, tuple(new_states)


def gnmt_residual_fn(inputs, outputs):
    """Residual function that handles different inputs and outputs inner dims.

    Args:
      inputs: cell inputs, this is actual inputs concatenated with the attention
        vector.
      outputs: cell outputs

    Returns:
      outputs + actual inputs
    """

    def split_input(inp, out):
        out_dim = out.get_shape().as_list()[-1]
        inp_dim = inp.get_shape().as_list()[-1]
        return tf.split(inp, [out_dim, inp_dim - out_dim], axis=-1)

    actual_inputs, _ = tf.contrib.framework.nest.map_structure(
        split_input, inputs, outputs
    )

    def assert_shape_match(inp, out):
        inp.get_shape().assert_is_compatible_with(out.get_shape())

    tf.contrib.framework.nest.assert_same_structure(actual_inputs, outputs)
    tf.contrib.framework.nest.map_structure(
        assert_shape_match, actual_inputs, outputs)
    return tf.contrib.framework.nest.map_structure(
        lambda inp, out: inp + out, actual_inputs, outputs
    )
