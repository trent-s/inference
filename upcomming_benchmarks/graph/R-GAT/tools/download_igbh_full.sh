#!/bin/bash
# This script was taken from: https://github.com/IllinoisGraphBenchmark/IGB-Datasets/blob/main/igb/download_igbh600m.sh
# Copy of licence for this ONLY this script
# MIT License

# Copyright (c) 2022 IMPACT Research Group and IllinoisGraphBenchmark

# This license is applicable for all software codebases provided in the repository.

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

echo "IGBH600M download starting"
mkdir -p $1/full/processed
cd $1/full/processed

# paper
mkdir paper
cd paper
wget -c https://igb-public.s3.us-east-2.amazonaws.com/IGBH/processed/paper/node_feat.npy
wget -c https://igb-public.s3.us-east-2.amazonaws.com/IGBH/processed/paper/node_label_19.npy
wget -c https://igb-public.s3.us-east-2.amazonaws.com/IGBH/processed/paper/node_label_2K.npy
wget -c https://igb-public.s3.us-east-2.amazonaws.com/IGBH/processed/paper/paper_id_index_mapping.npy
cd ..

# paper__cites__paper
mkdir paper__cites__paper
cd paper__cites__paper
wget -c https://igb-public.s3.us-east-2.amazonaws.com/IGBH/processed/paper__cites__paper/edge_index.npy
cd ..

# author
mkdir author
cd author
wget -c https://igb-public.s3.us-east-2.amazonaws.com/IGBH/processed/author/author_id_index_mapping.npy
wget -c https://igb-public.s3.us-east-2.amazonaws.com/IGBH/processed/author/node_feat.npy
cd ..

# conference
mkdir conference
cd conference
wget -c https://igb-public.s3.us-east-2.amazonaws.com/IGBH/processed/conference/conference_id_index_mapping.npy
wget -c https://igb-public.s3.us-east-2.amazonaws.com/IGBH/processed/conference/node_feat.npy
cd ..

# institute
mkdir institute
cd institute
wget -c https://igb-public.s3.us-east-2.amazonaws.com/IGBH/processed/institute/institute_id_index_mapping.npy
wget -c https://igb-public.s3.us-east-2.amazonaws.com/IGBH/processed/institute/node_feat.npy
cd ..

# journal
mkdir journal
cd journal
wget -c https://igb-public.s3.us-east-2.amazonaws.com/IGBH/processed/journal/journal_id_index_mapping.npy
wget -c https://igb-public.s3.us-east-2.amazonaws.com/IGBH/processed/journal/node_feat.npy
cd ..

# fos
mkdir fos
cd fos
wget -c https://igb-public.s3.us-east-2.amazonaws.com/IGBH/processed/fos/fos_id_index_mapping.npy
wget -c https://igb-public.s3.us-east-2.amazonaws.com/IGBH/processed/fos/node_feat.npy
cd ..

# author__affiliated_to__institute
mkdir author__affiliated_to__institute
cd author__affiliated_to__institute
wget -c https://igb-public.s3.us-east-2.amazonaws.com/IGBH/processed/author__affiliated_to__institute/edge_index.npy
cd ..

# paper__published__journal
mkdir paper__published__journal
cd paper__published__journal
wget -c https://igb-public.s3.us-east-2.amazonaws.com/IGBH/processed/paper__published__journal/edge_index.npy
cd ..

# paper__topic__fos
mkdir paper__topic__fos
cd paper__topic__fos
wget -c https://igb-public.s3.us-east-2.amazonaws.com/IGBH/processed/paper__topic__fos/edge_index.npy
cd ..

# paper__venue__conference
mkdir paper__venue__conference
cd paper__venue__conference
wget -c https://igb-public.s3.us-east-2.amazonaws.com/IGBH/processed/paper__venue__conference/edge_index.npy
cd ..

# paper__written_by__author
mkdir paper__written_by__author
cd paper__written_by__author
wget -c https://igb-public.s3.us-east-2.amazonaws.com/IGBH/processed/paper__written_by__author/edge_index.npy
cd ..

echo "IGBH-IGBH download complete"