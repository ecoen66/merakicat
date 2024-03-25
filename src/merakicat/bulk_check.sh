#!/bin/bash
#
# This is an example of a bulk check using an input file of hostnames
# or IP addresses (one per line).  The example spawns and maintains 20
# simultaneous switch config checks until the input file is exhausted.
#
# bulk_check.sh <input_file>
#

echo "File Name: $1"
< $1 xargs -I% -P20 python3.11 merakicat.py check host %
