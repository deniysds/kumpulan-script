#!/bin/bash

# Check if at least one parameter is provided
if [ $# -lt 1 ]; then
	    echo "Usage: $0 <param1> [param2] [param3]"
	        exit 1
fi

# Access the parameters
param1=$1
param2=$2

# Run Fasterq Dump SRA to Fastq
/opt/sratoolkit/bin/fasterq-dump /home/sra_to_sam/$param1.sra -O /home/sra_to_sam/

# Run Fastq to Sam
/bin/bwa mem -t 4 /opt/ref/GCA_000001405.15_GRCh38_full_analysis_set.fna /home/sra_to_sam/$param1.fastq > /home/sra_to_sam/output/$param1.sam

# Compress to Zip
/bin/zip /home/sra_to_sam/output/$param1.zip /home/sra_to_sam/output/$param1.sam
echo "Alignment $param1 SRA to SAM Success"
