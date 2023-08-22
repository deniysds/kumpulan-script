from googleapiclient.discovery import build
import os
from gcp.var import *
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "omics-training-12e59ce0a89f.json"

compute_service = build('compute', 'v1')
#Fetch existing VPC List
def get_vpc_list(project):
    vpcs_request = compute_service.networks().list(project=project)
    vpcs_list = vpcs_request.execute()
    return vpcs_list

#Fetch existing VM list
def get_vm_instance_list(project,zone):
    instance_request = compute_service.instances().list(project=project,zone=zone)
    instance_list = instance_request.execute()
    return instance_list

#Fetch existing VM list
def get_vm_instance(project,zone,instance_name):
    return compute_service.instances().get(project=project,zone=zone, instance=instance_name)