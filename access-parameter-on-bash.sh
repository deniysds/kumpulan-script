#!/bin/bash

# Check if at least one parameter is provided
if [ $# -lt 1 ]; then
    echo "Usage: $0 <param1> [param2] [param3]"
    exit 1
fi

# Access the parameters
param1=$1
param2=$2
param3=$3

# Perform some actions using the parameters
echo "Parameter 1: $param1"
echo "Parameter 2: $param2"
echo "Parameter 3: $param3"