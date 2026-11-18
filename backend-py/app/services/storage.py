"""画像の保存先（SeaweedFS など S3 と同じ使い方ができるストレージ）。"""

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app import config

s3 = boto3.client(
    "s3",
    endpoint_url=config.S3_ENDPOINT,
    aws_access_key_id=config.S3_ACCESS_KEY,
    aws_secret_access_key=config.S3_SECRET_KEY,
    region_name="us-east-1",  # S3 互換ストレージでは何でもよい
    config=Config(s3={"addressing_style": "path"}),
)


def create_bucket() -> None:
    try:
        s3.create_bucket(Bucket=config.S3_BUCKET)
    except ClientError as err:
        if err.response["Error"]["Code"] not in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
            raise


def save_image(key: str, data: bytes, content_type: str) -> None:
    s3.put_object(Bucket=config.S3_BUCKET, Key=key, Body=data, ContentType=content_type)


def load_image(key: str) -> tuple[bytes, str]:
    obj = s3.get_object(Bucket=config.S3_BUCKET, Key=key)
    return obj["Body"].read(), obj.get("ContentType", "image/jpeg")


def delete_image(key: str) -> None:
    s3.delete_object(Bucket=config.S3_BUCKET, Key=key)
