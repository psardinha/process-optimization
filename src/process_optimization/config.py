import os

data_bucket = os.getenv("DATA_BUCKET")
subfolder = os.getenv("S3_PREFIX")
dataset = os.getenv("DATASET")
role = os.getenv("SAGEMAKER_EXECUTION_ROLE_ARN")
model_name = os.getenv("MODEL_NAME", "order-approval-model")
endpoint_name = os.getenv("ENDPOINT_NAME", "order-approval")
endpoint_config_name = os.getenv("MODEL_CONFIG_NAME", f"{model_name}-config")
region = os.getenv("AWS_REGION", "ue-central-1")