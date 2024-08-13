#!/bin/bash

fn=reimu_mugen_test.`date '+%Y%m%d-%H%M%S'`.log
echo Write log to $fn

python3 ./reimu_mugen_test.py 2>&1 | tee $fn
