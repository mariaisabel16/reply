# workflow.py
import json
import os
import sys

# Add the project root to the Python path to enable modular imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

from Agent.bedrock_agent import BedrockAgent
from Agent.prompts import SYSTEM_PROMPT_AGENT_INTRODUCTION, SYSTEM_PROMPT_FILTER_STATIC_USER_DATA
from Database.s3_local import S3Manager

def get_agent_introduction(agent):
    """Generates the agent's introduction using a pre-initialized agent."""
    print("Requesting introduction from LLM...")
    user_prompt = "Stell dich bitte vor."
    return agent.invoke(prompt=user_prompt, system_prompt=SYSTEM_PROMPT_AGENT_INTRODUCTION)

def load_and_structure_data_into_bucket(s3_manager, agent, local_folder_path):
    """
    Intelligently processes local JSON files, extracts structured static user data
    using an LLM, and uploads it to the correct S3 path.
    """
    print(f"\n--- Starting intelligent data structuring and upload from '{local_folder_path}' ---")

    if not os.path.isdir(local_folder_path):
        print(f"❌ Error: Local directory not found at '{local_folder_path}'")
        return

    files_to_process = sorted([f for f in os.listdir(local_folder_path) if f.endswith('.json')])
    if not files_to_process:
        print("ℹ️ No JSON files found to process.")
        return

    print(f"Found {len(files_to_process)} JSON files to process.")
    successful_uploads = 0

    for file_name in files_to_process:
        try:
            local_file_path = os.path.join(local_folder_path, file_name)
            with open(local_file_path, 'r', encoding='utf-8') as f:
                try:
                    raw_data = json.load(f)
                except json.JSONDecodeError as e:
                    print(f"❌ Error for '{file_name}': Source file contains invalid JSON. Skipping. Details: {e}")
                    continue

            print(f"Processing '{file_name}': Asking agent to extract static data...")
            prompt = f"Please extract the static user profile from the following JSON data:\n\n{json.dumps(raw_data)}"

            structured_data_str = agent.invoke(
                prompt=prompt,
                system_prompt=SYSTEM_PROMPT_FILTER_STATIC_USER_DATA
            )

            if not structured_data_str or "Bedrock invocation failed" in structured_data_str:
                print(f"❌ Error for '{file_name}': Agent failed to process data. Response: {structured_data_str}")
                continue
            
            try:
                structured_data = json.loads(structured_data_str)
            except json.JSONDecodeError:
                print(f"❌ Error for '{file_name}': Agent returned a non-JSON string. Skipping.")
                print(f"   Agent's raw response: {structured_data_str[:500]}...")
                continue

            user_id = structured_data.get('userId')
            if not user_id:
                print(f"⚠️ Warning for '{file_name}': 'userId' not found in agent's response. Skipping file.")
                continue

            s3_key = f"users/{user_id}.json"

            s3_manager.upload_json(s3_key, structured_data)
            successful_uploads += 1

        except Exception as e:
            print(f"❌ Unexpected error processing '{file_name}': {e}")

    print(f"\n--- Intelligent upload finished. Successfully processed and uploaded {successful_uploads}/{len(files_to_process)} files. ---")


if __name__ == "__main__":
    print("--- Starting CampusPilot Workflow ---")

    # Initialize core components once
    try:
        bedrock_agent = BedrockAgent()
        if not bedrock_agent.available:
            raise Exception(f"Bedrock Agent is not available: {bedrock_agent.init_error}")
        
        s3_manager = S3Manager(bucket_name="metadaten-tum-hackathon-reply-top90")
        s3_manager.check_or_create_bucket()
    except Exception as e:
        print(f"❌ [FATAL ERROR] Failed to initialize core components: {e}")
        sys.exit(1)

    # Step 1: Agent Introduction
    print("\nInitializing CampusPilot Agent for introduction...")
    intro_response = get_agent_introduction(bedrock_agent)
    print("\n" + "="*50)
    print("CampusPilot Agent Response:")
    print("="*50)
    print(intro_response or "Agent introduction failed.")
    print("="*50)

    # Step 2: Intelligent Data Structuring and Loading into S3
    # Correctly define path to the data folder at the project root
    local_user_data_folder = os.path.join(project_root, "TemporaryUserInfoFiles")
    load_and_structure_data_into_bucket(s3_manager, bedrock_agent, local_user_data_folder)

    print("\n--- CampusPilot Workflow Finished ---")
