# list_s3_contents.py
import boto3
from botocore.exceptions import ClientError
import sys

def list_bucket_contents(bucket_name):
    """
    Lists all objects in a given S3 bucket.

    :param bucket_name: The name of the S3 bucket.
    """
    print(f"--- Listing contents of S3 bucket: '{bucket_name}' ---")
    try:
        s3_client = boto3.client('s3')
        paginator = s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=bucket_name)


        object_count = 0
        for page in pages:
            if "Contents" in page:
                for obj in page['Contents']:
                    print(f"- {obj['Key']}  (Size: {obj['Size']} bytes)")
                    object_count += 1
            
        if object_count == 0:
            print("Bucket is empty or contains no objects.")
        else:
            print(f"\nFound {object_count} object(s).")

    except ClientError as e:
        print(f"❌ An error occurred: {e}")

if __name__ == "__main__":
    # Replace with your bucket name
    BUCKET_TO_LIST = "metadaten-tum-hackathon-reply-top90"
    list_bucket_contents(BUCKET_TO_LIST)