#!/bin/bash

set -x
set -e

data_folder="/run/user/kevin/gvfs/sftp:host=shell4.doc.ic.ac.uk,user=kpk09/vol/biomedic/users/kpk09/BRAINS/KEVIN-TAKEHOME/data"
output_folder="ground_truth"

mkdir -p $output_folder

./crop_boxes.py $data_folder $output_folder
