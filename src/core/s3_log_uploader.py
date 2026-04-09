import os
import boto3
from datetime import datetime, timezone

s3_client = boto3.client("s3")


def upload_log_file_to_s3(
    bucket_name: str,
    local_file_path: str,
    prefix: str = "backend-logs"
) -> str:
    if not os.path.exists(local_file_path):
        return ""

    timestamp = datetime.now(timezone.utc).strftime("%Y/%m/%d/%H%M%S")
    object_key = f"{prefix}/{timestamp}-app.log"

    s3_client.upload_file(local_file_path, bucket_name, object_key)
    return object_key