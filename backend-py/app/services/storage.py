"""画像の保存先（SeaweedFS）。S3 と同じ使い方ができる。"""

import os

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

BUCKET = os.environ.get("S3_BUCKET", "screenshots")

s3 = boto3.client(
    "s3",
    endpoint_url=os.environ.get("S3_ENDPOINT"),  # 例：http://storage:8333
    aws_access_key_id=os.environ.get("S3_ACCESS_KEY", "app"),
    aws_secret_access_key=os.environ.get("S3_SECRET_KEY", "app"),
    region_name="us-east-1",  # S3 互換ストレージでは何でもよい
    config=Config(s3={"addressing_style": "path"}),
)


def create_bucket() -> None:
    """画像を入れるバケットを作る（もうあればそのまま）。"""
    try:
        s3.create_bucket(Bucket=BUCKET)
    except ClientError as err:
        if err.response["Error"]["Code"] not in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
            raise


def save_image(key: str, data: bytes, content_type: str) -> None:
    s3.put_object(Bucket=BUCKET, Key=key, Body=data, ContentType=content_type)


def load_image(key: str) -> bytes:
    return s3.get_object(Bucket=BUCKET, Key=key)["Body"].read()
