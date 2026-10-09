import pandas as pd
import boto3
from sklearn.model_selection import train_test_split
from process_optimization.config import region, data_bucket, subfolder, dataset

def prepare_data():
    # Load new dataset from S3
    sm = boto3.client("sagemaker", region_name=region)
    s3 = boto3.client("s3", region_name=region)
    df = pd.read_csv(s3.get_object(Bucket=data_bucket, Key=f"{subfolder}/incoming/{dataset}")["Body"])
    print("First rows of new dataset:\n", df.head(3))
    print(f'Number of rows in new dataset: {df.shape[0]}\n')
    print("Distribution of target variable:\n", df[df.columns[0]].value_counts())

    # Pre-processing
    encoded_data = pd.get_dummies(df)
    print("First rows of encoded data:\n", encoded_data.head(3))
    corrs = encoded_data.corr()['tech_approval_required'].abs()
    columns = corrs[corrs > .1].index
    corrs = corrs.filter(columns)
    print("Correlations with target variable (only abs(correlation) > 0.1):\n", corrs)
    encoded_data = encoded_data[columns]
    print("First rows of encoded data (filtered for columns with abs(correlation) with target variabl> 0.1):\n", 
        encoded_data.head(3))


    # Create train, validation and test datasets
    train_df, val_and_test_data = train_test_split(encoded_data, test_size=0.3, random_state=0)
    val_df, test_df = train_test_split(val_and_test_data, test_size=0.3, random_state=0)

    s3.put_object(Bucket=data_bucket, Key=f"{subfolder}/processed/train.csv", Body=train_df.to_csv(index=False, header=False))
    s3.put_object(Bucket=data_bucket, Key=f"{subfolder}/processed/val.csv", Body=val_df.to_csv(index=False, header=False))
    s3.put_object(Bucket=data_bucket, Key=f"{subfolder}/processed/test.csv", Body=test_df.to_csv(index=False, header=True))


if __name__ == "__main__":
    prepare_data()