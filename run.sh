#!/bin/bash

set -x
set -e

data_folder="data"
output_folder="ground_truth"

mkdir -p $output_folder

./crop_boxes.py $data_folder $output_folder
