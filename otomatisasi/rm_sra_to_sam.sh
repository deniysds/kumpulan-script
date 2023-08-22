#!/bin/bash

# Check if at least one parameter is provided
if [ $# -lt 1 ]; then
	    echo "Usage: $0 <param1> [param2] [param3]"
	        exit 1
fi

# Access the parameters
param1=$1

rm -rf /home/sra_to_sam/$param1.*
rm -rf /home/sra_to_sam/output/$param1.*

