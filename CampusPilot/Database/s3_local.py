import os
import json
import pandas as pd
from dotenv import load_dotenv

try:
    import boto3
    from botocore.exceptions import NoCredentialsError, ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False

class S3Manager:
    """Manages interactions with an AWS S3 bucket."""

    def __init__(self, bucket_name, region_name="eu-central-1"):
        if not BOTO3_AVAILABLE:
            raise ImportError("boto3 is not installed. S3Manager cannot function.")
        
        self.bucket_name = bucket_name
        self.region_name = region_name
        try:
            self.s3_client = boto3.client('s3', region_name=self.region_name)
            self.s3_resource = boto3.resource('s3', region_name=self.region_name)
            print(f"✅ Connected to S3 in region '{self.region_name}'.")
        except NoCredentialsError:
            raise Exception("AWS credentials not found. Please run 'aws configure'.")

    def check_or_create_bucket(self):
        """Checks if the bucket exists and creates it if it doesn't."""
        try:
            existing_buckets = [bucket.name for bucket in self.s3_resource.buckets.all()]
            if self.bucket_name not in existing_buckets:
                print(f"Bucket '{self.bucket_name}' not found. Creating it...")
                self.s3_client.create_bucket(
                    Bucket=self.bucket_name,
                    CreateBucketConfiguration={'LocationConstraint': self.region_name}
                )
                print(f"✅ Created new bucket: {self.bucket_name}")
            else:
                print(f"✅ Bucket '{self.bucket_name}' already exists.")
        except ClientError as e:
            raise Exception(f"An AWS client error occurred: {e}")

    def upload_json(self, s3_key, data_dict):
        """
        Converts a Python dictionary to a JSON string and uploads it to S3.

        :param s3_key: The full key (path) for the object in S3.
        :param data_dict: The Python dictionary to upload.
        """
        try:
            json_string = json.dumps(data_dict, indent=4)
            # Upload the string data using put_object
            self.s3_client.put_object(Bucket=self.bucket_name, Key=s3_key, Body=json_string)
            print(f"✅ Successfully uploaded JSON to s3://{self.bucket_name}/{s3_key}")
        except ClientError as e:
            raise Exception(f"Failed to upload JSON to S3: {e}")

    def download_json(self, s3_key):
        """
        Downloads a JSON file from S3 and returns it as a Python dictionary.

        :param s3_key: The full key (path) of the object in S3.
        :return: A Python dictionary with the JSON content.
        """
        try:
            s3_object = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
            json_string = s3_object['Body'].read().decode('utf-8')
            data_dict = json.loads(json_string)
            print(f"✅ Successfully downloaded JSON from s3://{self.bucket_name}/{s3_key}")
            return data_dict
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                raise FileNotFoundError(f"The key '{s3_key}' does not exist in bucket '{self.bucket_name}'.")
            else:
                raise Exception(f"Failed to download JSON from S3: {e}")

def test_json_methods():
    """Tests the upload_json and download_json methods."""
    print("\n--- Starting JSON Upload/Download Test ---")
    load_dotenv()
    
    bucket_name = "metadaten-tum-hackathon-reply-top90"
    
    try:
        s3_manager = S3Manager(bucket_name=bucket_name)
        s3_manager.check_or_create_bucket()

        # 1. Prepare test data and S3 key
        user_profile = {
            "userId": "user_12345",
            "firstName": "Max",
            "studyProgram": "Informatik",
            "semester": 5,
            "interests": ["AI", "Data Science", "Quantum Computing"]
        }
        s3_key = f"user_profiles/{user_profile['userId']}.json"

        # 2. Upload the JSON data
        s3_manager.upload_json(s3_key, user_profile)

        # 3. Download the JSON data
        downloaded_profile = s3_manager.download_json(s3_key)

        # 4. Verify the data
        if user_profile == downloaded_profile:
            print("✅ Verification successful: Downloaded data matches original data.")
        else:
            print("❌ Verification failed: Data mismatch.")
            print("Original:", user_profile)
            print("Downloaded:", downloaded_profile)
        
        print("\n--- JSON Test Completed Successfully ---")

    except Exception as e:
        print(f"\n❌ [ERROR] An error occurred during the JSON test: {e}")

if __name__ == "__main__":
    test_json_methods()
