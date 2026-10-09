import os
import boto3
from botocore.exceptions import ClientError
from sklearn.metrics import accuracy_score, precision_score, recall_score, roc_auc_score
from process_optimization.config import region, model_name, role, data_bucket, subfolder
import numpy as np
import pandas as pd
import uuid


def evaluate():
    sm = boto3.client("sagemaker", region_name=region)
    s3 = boto3.client("s3", region_name=region)
    try:
        sm.delete_model(ModelName=model_name)
    except Exception as e:
        pass

    model_artifact = os.getenv("MODEL_ARTIFACT")
    container = os.getenv("CONTAINER")
    sm.create_model(ModelName=model_name,
                    ExecutionRoleArn=role,
                    PrimaryContainer={"Image": container,
                                      "ModelDataUrl": model_artifact})
    print(f"Created evaluation model: {model_name}")

    test_df = pd.read_csv(f's3://{data_bucket}/{subfolder}/processed/test.csv')
    y_true = test_df.iloc[:, 0].astype(int).to_numpy() 
    # Keep existing logic: features start at column 1.
    features_df = test_df.iloc[:, 1:].copy()
    # Convert Boolean values to numeric values.
    for column in features_df.columns:
        features_df[column] = features_df[column].map(lambda value: int(value) if isinstance(value, (bool, np.bool_)) else value)
    eval_key = f"{subfolder}/evaluation/eval.csv"
    eval_file = f"s3://{data_bucket}/{eval_key}"   
    s3.put_object(Bucket=data_bucket, Key=eval_key, Body=features_df.to_csv(index=False, header=False))

    # Delete the evaluation output file if it exists
    eval_output_key = f"{subfolder}/evaluation/eval.csv.out"
    eval_output_file = f"{data_bucket}/{eval_output_key}"
    s3.delete_object(Bucket=data_bucket, Key=eval_output_key)  

    output_uri = f"s3://{data_bucket}/{subfolder}/evaluation"
    transform_job_name = f"order-approval-evaluation-{uuid.uuid4().hex[:8]}"
    sm.create_transform_job(TransformJobName=transform_job_name,
                            ModelName=model_name,
                            TransformInput={"DataSource": {"S3DataSource": {"S3DataType": "S3Prefix",
                                                                            "S3Uri": eval_file}},
                                            "ContentType": "text/csv",
                                            "SplitType": "Line"},
                            TransformOutput={
                                "S3OutputPath": output_uri,
                                "Accept": "text/csv",
                                "AssembleWith": "Line"},
                            TransformResources={
                                "InstanceType": "ml.m5.large",
                                "InstanceCount": 1})
    print(f"Started transform job: {transform_job_name}")

    waiter = sm.get_waiter("transform_job_completed_or_stopped")
    waiter.wait(TransformJobName=transform_job_name,  WaiterConfig={"Delay": 20, "MaxAttempts": 180})
    job = sm.describe_transform_job(TransformJobName=transform_job_name)
    if job["TransformJobStatus"] != "Completed":
        raise RuntimeError(f"Batch Transform failed: {job.get('FailureReason')}")
    print(f"Transform job: {transform_job_name} completed successfully.")

    # XGBoost binary:logistic returns probability scores.
    df = pd.read_csv(s3.get_object(Bucket=data_bucket, Key=eval_output_key)["Body"], header=None)
    s3.delete_object(Bucket=data_bucket, Key=eval_output_key) 
    scores = df.iloc[:, 0].astype(float).to_numpy()    
    if len(scores) != len(y_true):
        raise RuntimeError(f"Label/prediction count mismatch: {len(y_true)} labels and {len(scores)} predictions")
    y_pred = (scores >= 0.5).astype(int)

    auc = roc_auc_score(y_true, scores)
    accuracy = accuracy_score(y_true, y_pred)
    precision = precision_score(y_true, y_pred, zero_division=0)
    recall = recall_score(y_true, y_pred, zero_division=0)

    print("\nEvaluation metrics")
    print(f"ROC AUC:   {auc:.4f}")
    print(f"Accuracy:  {accuracy:.4f}")
    print(f"Precision: {precision:.4f}")
    print(f"Recall:    {recall:.4f}")

    # Remove the temporary SageMaker model resource
    sm.delete_model(ModelName=model_name)


if __name__ == "__main__":
    evaluate()