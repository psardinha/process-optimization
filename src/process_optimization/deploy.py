import os
import time
import boto3
from process_optimization import deploy
from process_optimization.config import region, role, endpoint_name, model_name, endpoint_config_name


def deploy():
    # Delete an eventual previous deployed endpoint
    sm = boto3.client("sagemaker", region_name=region)
    try:
        sm.delete_endpoint(EndpointName=endpoint_name)
        print("Existing endpoint deleted.")
        time.sleep(30)
    except sm.exceptions.ClientError as e:
        if "Could not find endpoint" in str(e):
            pass
        else:
            raise

    model_artifact = os.getenv("MODEL_ARTIFACT")

    # Delete an eventual previous deployed model
    try:
        sm.delete_model(ModelName=model_name)
        print("Existing model deleted.")
        time.sleep(10)
    except sm.exceptions.ClientError as e:
        if f'Could not find model "{model_name}"' in str(e):
            pass
        else:
            raise

    container = os.environ.get("CONTAINER")
    response = sm.create_model(ModelName=model_name,
                            ExecutionRoleArn=role,
                            PrimaryContainer={"Image": container,
                                                "ModelDataUrl": model_artifact})
    print("Created model:", response["ModelArn"])

    # Delete an eventual previous deployed endpoint config
    try:
        sm.delete_endpoint_config(EndpointConfigName=endpoint_config_name)
        print("Existing endpoint configuration deleted.")
        time.sleep(10)
    except sm.exceptions.ClientError as e:
        if f'Could not find endpoint configuration "{endpoint_config_name}"' in str(e):
            pass
        else:
            raise

    sm.create_endpoint_config(EndpointConfigName=endpoint_config_name,
                            ProductionVariants=[{"VariantName": "AllTraffic",
                                                "ModelName": model_name,
                                                "InitialInstanceCount": 1,
                                                "InstanceType": "ml.m4.xlarge",
                                                "InitialVariantWeight": 1.0}])

    response = sm.create_endpoint(EndpointName=endpoint_name, EndpointConfigName=endpoint_config_name)
    print("Endpoint creation requested:", endpoint_name)


if __name__ == "__main__":
    deploy()