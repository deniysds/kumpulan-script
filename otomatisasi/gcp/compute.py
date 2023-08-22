#First install required library using below pip command
#pip install google-api-python-client

import os
import time
from gcp.metadata import *
from gcp.var import *
from gcp.restart_vms import *

from google.oauth2 import service_account
from googleapiclient.discovery import build
from google.cloud import compute_v1

# Create Service account , download keys and add your key file path below 
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "omics-training-12e59ce0a89f.json"

# I am creating function to create VM instance and this function is being called from main.py
def create_gce_instance(vm_name, zone, machine_type, vm_image):
    vm_instance_list = get_vm_instance_list(project, zone)
    vm_exists = False
    for instance in vm_instance_list.get('items', []):
        if instance['name'] == vm_name:
            vm_exists = True
            break

    if not vm_exists:
        compute_service = build('compute', 'v1')
        config = {
            'name': vm_name,
            'machineType': 'zones/{}/machineTypes/{}'.format(zone, machine_type),
            'disks': [{
                'boot': True,
                'autoDelete': True,
                'initializeParams': {
                    'sourceImage': vm_image,
                    'diskSizeGb' : '50'
                }
            }],
            'networkInterfaces': [{
                'accessConfigs': [{
                    'type': 'ONE_TO_ONE_NAT',
                    'name': 'External NAT'
                }]
            }]
        }

        request = compute_service.instances().insert(
            project=project, zone=zone, body=config)
        response = request.execute()

        print('VM instance created:', response['selfLink'])
    else:
        print(f'VM instance {vm_name} already exist')

def update_instance_machine_type(project_id, zone, instance_name, machine_type):
    # Get the current instance configuration
    compute_client = build('compute', 'v1')
    stop_instance(project_id,zone,instance_name)
    time.sleep(5)
            
    # Get the current instance configuration
    vm_instance_list = get_vm_instance_list(project_id, zone)
    for instance in vm_instance_list.get('items', []):
        if instance['name'] == instance_name:
            #print(instance)
            # Update the machine type
        
            instance['machineType'] = f"zones/{zone}/machineTypes/{machine_type}"
            # Apply the update to the instance
            operation = compute_client.instances().update(project=project_id, zone=zone, instance=instance_name, body=instance)
            # Wait for the operation to complete
            operation.execute()
            time.sleep(10)
            print(f"Instance {instance_name} updated successfully to machine type {machine_type}.")
            time.sleep(5)
            start_instance(project_id,zone,instance_name)
            break

