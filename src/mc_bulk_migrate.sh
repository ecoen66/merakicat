#!/bin/bash
echo "File Name: $1"
echo "Meraki Network: $2"
< $1 xargs -I% -P20 python3.11 merakicat.py migrate host % to $2
