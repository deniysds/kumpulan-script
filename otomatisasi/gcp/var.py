#Add variable values as per your requirements
project = 'omics-training'
region = 'asia-southeast2'
zone = 'asia-southeast2-a'
instance_name = 'oto-instance'

ubuntu_image = 'projects/ubuntu-os-cloud/global/images/family/ubuntu-2204-lts'

vm_configs = [
    {'name': 'oto-instance', 'zone':'asia-southeast2-a','subnet_name':'asia-subnet','machine_type': 'e2-micro', 'vm_image': ubuntu_image}
]




















