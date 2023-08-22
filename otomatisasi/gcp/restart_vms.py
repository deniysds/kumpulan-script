from google.cloud import compute_v1
import os
import time

PROJECT_ID = 'omics-training'
ZONE = 'asia-southeast2'

compute_client = compute_v1.InstancesClient()

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] =  "omics-training-12e59ce0a89f.json"

def stop_instance(project_id,zone,instance_name):
    stop_instance_request=  compute_client.stop(
        project=project_id,
        zone=zone,
        instance=instance_name
    )
    time.sleep(5)
    stop_instance_request.result()
    print(f'Stoped VM instance: {instance_name}')

def start_instance(project_id,zone,instance_name):
    start_instance_request = compute_client.start(
        project=project_id,
        zone=zone,
        instance=instance_name
    )
    time.sleep(5)
    start_instance_request.result()
    print(f'Start VM instance: {instance_name}')
  