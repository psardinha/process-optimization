import os
import boto3
from sagemaker.train.configs import InputData
from sagemaker.train.configs import InputData, Compute, OutputDataConfig, StoppingCondition
from sagemaker.core import image_uris
from sagemaker.train import ModelTrainer
from process_optimization.config import region, data_bucket, subfolder, role


def prepare_data():
    # Train the model
    train_input = InputData(channel_name="train",
                            data_source=f"s3://{data_bucket}/{subfolder}/processed/train.csv",
                            content_type="text/csv")

    val_input = InputData(channel_name="validation",
                        data_source=f"s3://{data_bucket}/{subfolder}/processed/val.csv",
                        content_type="text/csv") 


    # XGBoost container
    container = image_uris.retrieve(framework="xgboost", region=region, version="1.7-1", instance_type="ml.m4.xlarge")
    with open(os.environ["GITHUB_OUTPUT"], "a") as f:
        f.write(f"container={container}\n")

    # Compute
    compute = Compute(instance_type="ml.m4.xlarge", instance_count=1, enable_managed_spot_training=True)

    # Trainer
    stopping_condition = StoppingCondition(max_runtime_in_seconds=1200, max_wait_time_in_seconds=2000)
    model_trainer = ModelTrainer(training_image=container,
                                role=role,
                                compute=compute,
                                stopping_condition=stopping_condition,
                                output_data_config=OutputDataConfig(s3_output_path=f"s3://{data_bucket}/{subfolder}/output"),
                                hyperparameters={"max_depth": "5",
                                                "subsample": "0.7",
                                                "objective": "binary:logistic",
                                                "eval_metric": "auc",
                                                "num_round": "70",
                                                "early_stopping_rounds": "10"})

    # Start training
    model_trainer.train(input_data_config=[train_input, val_input])

    # Find the most recent training job with this prefix
    sm = boto3.client("sagemaker", region_name=region)
    response = sm.list_training_jobs(SortBy="CreationTime", SortOrder="Descending", MaxResults=100)
    matching_jobs = [job for job in response["TrainingJobSummaries"]
                    if job["TrainingJobName"].startswith(model_trainer.base_job_name)]

    if not matching_jobs:
        raise RuntimeError("No matching SageMaker training jobs found.")

    training_job_name = matching_jobs[0]["TrainingJobName"]
    with open(os.environ["GITHUB_OUTPUT"], "a") as f:
        f.write(f"training_job_name={training_job_name}\n") #??

    # Retrieve the training results
    job = sm.describe_training_job(TrainingJobName=training_job_name)
    with open(os.environ["GITHUB_OUTPUT"], "a") as f:
        f.write(f'model_artifact={job.get("ModelArtifacts", {}).get("S3ModelArtifacts")}\n')

    print("Job:", training_job_name)
    print("Status:", job["TrainingJobStatus"])
    print("Training time:", job.get("TrainingTimeInSeconds"), "seconds")
    print("Billable time:", job.get("BillableTimeInSeconds"), "seconds")
    print("\nFinal metrics:")
    for metric in job.get("FinalMetricDataList", []):
        print(f'{metric["MetricName"]}: {metric["Value"]}')
    print("\nModel artifact:")
    print(job.get("ModelArtifacts", {}).get("S3ModelArtifacts"))


if __name__ == "__main__":
    prepare_data()