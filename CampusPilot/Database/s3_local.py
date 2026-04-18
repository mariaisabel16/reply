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
        """
        try:
            json_string = json.dumps(data_dict, indent=4)
            self.s3_client.put_object(Bucket=self.bucket_name, Key=s3_key, Body=json_string)
            print(f"✅ Successfully uploaded JSON to s3://{self.bucket_name}/{s3_key}")
        except ClientError as e:
            raise Exception(f"Failed to upload JSON to S3: {e}")

    def download_json(self, s3_key):
        """
        Downloads a JSON file from S3 and returns it as a Python dictionary.
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

def loadScrapedDataInBucket(s3_manager, local_folder_path):
    """
    Loads all JSON files from a local folder into the S3 bucket under the 'users/' prefix.
    """
    print(f"\n--- Starting to load data from '{local_folder_path}' to S3 ---")
    
    if not os.path.isdir(local_folder_path):
        print(f"❌ Error: Local directory not found at '{local_folder_path}'")
        return

    files_to_upload = [f for f in os.listdir(local_folder_path) if f.endswith('.json')]
    
    if not files_to_upload:
        print("No JSON files found in the directory to upload.")
        return

    for file_name in files_to_upload:
        try:
            local_file_path = os.path.join(local_folder_path, file_name)
            with open(local_file_path, 'r') as f:
                user_data = json.load(f)

            # Assuming the filename is the user ID (e.g., "tum_12345.json")
            s3_key = f"users/{file_name}"

            s3_manager.upload_json(s3_key, user_data)
            
        except json.JSONDecodeError:
            print(f"⚠️ Warning: Could not parse JSON from '{file_name}'. Skipping.")
        except Exception as e:
            print(f"❌ Error processing file '{file_name}': {e}")
            
    print("\n--- Finished loading scraped data ---")

    def key_exists(self, s3_key):
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            else:
                raise e



if __name__ == "__main__":
    load_dotenv()
    
    BUCKET_NAME = "metadaten-tum-hackathon-reply-top90"
    
    try:
        # Initialize the S3 Manager
        s3_manager = S3Manager(bucket_name=BUCKET_NAME)
        s3_manager.check_or_create_bucket()

        # Define the path to the local folder with user data.
        # This assumes the script is run from the 'Database' directory.
        # We construct a path to the sibling folder 'TemporaryUserInfoFiles'.
        base_dir = os.path.dirname(os.path.abspath(__file__)) # /path/to/CampusPilot/Database
        parent_dir = os.path.dirname(base_dir) # /path/to/CampusPilot
        local_user_data_folder = os.path.join(parent_dir, "TemporaryUserInfoFiles")

        # Run the function to load the data
        loadScrapedDataInBucket(s3_manager, local_user_data_folder)

    except Exception as e:
        print(f"\n❌ [FATAL ERROR] An error occurred in the main process: {e}")
