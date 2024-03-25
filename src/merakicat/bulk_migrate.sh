#!/bin/bash
#
# This is an example of a bulk migration using an input file of hostnames
# or IP addresses (one per line).  The example spawns and maintains 20
# simultaneous switch migrations until the input file is exhausted.
#
# bulk_migrate.sh <input_file> <meraki_network_name>
#

echo "File Name: $1"
echo "Meraki Network: $2"
< $1 xargs -I% -P20 python3.11 merakicat.py migrate host % to $2
