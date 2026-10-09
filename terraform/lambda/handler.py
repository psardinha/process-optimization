
import json
import logging
import os
import urllib.error
import urllib.request

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

secrets_client = boto3.client("secretsmanager")

GITHUB_OWNER = os.environ["GITHUB_OWNER"]
GITHUB_REPO = os.environ["GITHUB_REPO"]
GITHUB_EVENT_TYPE = os.environ["GITHUB_EVENT_TYPE"]
DATA_BUCKET = os.environ["DATA_BUCKET"]
DATA_PREFIX = os.environ["DATA_PREFIX"]
REGION = os.environ["REGION"]
SECRET_NAME = os.environ["SECRET_NAME"]

def get_token_secret():
    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(service_name='secretsmanager', region_name=REGION)

    try:
        get_secret_value_response = client.get_secret_value(SecretId=SECRET_NAME)
        return json.loads(get_secret_value_response['SecretString'])["token"]
    except ClientError as e:
        # For a list of exceptions thrown, see
        # https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
        raise e


def lambda_handler(event, context):
    logger.info("Received event:")
    logger.info(json.dumps(event, indent=2))

    detail = event.get("detail", {})
    bucket = detail.get("bucket", {}).get("name", "unknown")
    key = detail.get("object", {}).get("key", "unknown")

    print(f"Bucket: {bucket}")
    print(f"Changed file: {key}")

    # Ignore unrelated buckets, folders and file types.
    if bucket != DATA_BUCKET:
        logger.info("Ignoring event from unrelated bucket")
        return {"statusCode": 200, "body": "Ignored bucket"}

    if not key.startswith(DATA_PREFIX) or not key.lower().endswith(".csv"):
        logger.info("Ignoring unrelated object")
        return {"statusCode": 200, "body": "Ignored object"}

    token = get_token_secret()
    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/dispatches"
    payload = {"event_type": GITHUB_EVENT_TYPE,
               "client_payload": {"bucket": bucket,
                                  "dataset_key": key,
                                  "s3_event_id": event.get("id", "")}}
    request = urllib.request.Request(url,
                                     data=json.dumps(payload).encode("utf-8"),
                                     headers={"Accept": "application/vnd.github+json",
                                              "Authorization": f"Bearer {token}",
                                              "X-GitHub-Api-Version": "2022-11-28",
                                              "Content-Type": "application/json"},
                                     method="POST")
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            if response.status != 204:
                raise RuntimeError(f"Unexpected GitHub response: {response.status}")

        logger.info("GitHub dispatch accepted for s3://%s/%s", bucket, key)
        return {"statusCode": 200,
                "body": "GitHub training workflow dispatched"}
    except urllib.error.HTTPError as exc:
        logger.error("GitHub API returned HTTP %s", exc.code)
        raise
