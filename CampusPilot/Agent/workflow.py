# workflow.py
import json
import os
import sys
from collections import defaultdict

# Add the project root to the Python path to enable modular imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

from Agent.bedrock_agent import BedrockAgent
from Agent.prompts import (
    SYSTEM_PROMPT_AGENT_INTRODUCTION,
    SYSTEM_PROMPT_FILTER_STATIC_USER_DATA,
    SYSTEM_PROMPT_FILTER_STATIC_USER_DATA_FROM_TEXT,
)
from Database.s3_local import S3Manager

def get_agent_introduction(agent):
    """Generates the agent's introduction using a pre-initialized agent."""
    print("Requesting introduction from LLM...")
    user_prompt = "Stell dich bitte vor."
    return agent.invoke(prompt=user_prompt, system_prompt=SYSTEM_PROMPT_AGENT_INTRODUCTION)

def deep_merge_dicts(d1, d2):
    """
    Merges d2 into d1 recursively. For lists, it combines and removes duplicates,
    preferring items from d2 in case of conflicts in simple lists.
    For lists of dictionaries, it attempts to deduplicate based on content.
    """
    for k, v in d2.items():
        if k in d1 and isinstance(d1[k], dict) and isinstance(v, dict):
            d1[k] = deep_merge_dicts(d1[k], v)
        elif k in d1 and isinstance(d1[k], list) and isinstance(v, list):
            # Simple list deduplication
            # For aggregation, extending the list is often more robust and predictable
            # than complex deduplication logic.
            d1[k].extend(v)
        else:
            # If key exists in d1 but types are different, d2 wins.
            d1[k] = v
    return d1

def load_and_structure_data_into_bucket(s3_manager, agent, base_folder_path):
    """
    Scans for session subdirectories, processes all .json and .txt files within them,
    aggregates the data using an LLM, and uploads one structured profile per user to S3.
    """
    print(f"\n--- Starting intelligent data structuring and upload from '{base_folder_path}' ---")

    if not os.path.isdir(base_folder_path):
        print(f"❌ Error: Base directory not found at '{base_folder_path}'")
        return

    session_folders = [d for d in os.listdir(base_folder_path) if os.path.isdir(os.path.join(base_folder_path, d)) and d.startswith('session_')]
    if not session_folders:
        print("ℹ️ No session log folders found to process in the base directory.")
        return

    print(f"Found {len(session_folders)} session folders to process.")

    for session_folder in session_folders:
        session_path = os.path.join(base_folder_path, session_folder)
        print(f"\n--- Processing Session Folder: {session_folder} ---")
        
        aggregated_data = {}
        files_to_process = sorted([f for f in os.listdir(session_path) if f.endswith(('.json', '.txt'))])

        for file_name in files_to_process:
            local_file_path = os.path.join(session_path, file_name)
            print(f"  - Processing file: {file_name}")
            
            try:
                if file_name.endswith('.json'):
                    with open(local_file_path, 'r', encoding='utf-8') as f:
                        try:
                            raw_data = json.load(f)
                        except json.JSONDecodeError as e:
                            print(f"    ❌ Error: Source file '{file_name}' contains invalid JSON. Skipping. Details: {e}")
                            continue
                    prompt = f"Extract static user profile from this JSON:\n\n{json.dumps(raw_data)}"
                    system_prompt = SYSTEM_PROMPT_FILTER_STATIC_USER_DATA
                elif file_name.endswith('.txt'):
                    with open(local_file_path, 'r', encoding='utf-8') as f:
                        raw_data = f.read()
                    prompt = f"Extract static user profile from this text:\n\n{raw_data}"
                    system_prompt = SYSTEM_PROMPT_FILTER_STATIC_USER_DATA_FROM_TEXT
                
                structured_data_str = agent.invoke(prompt=prompt, system_prompt=system_prompt)
                if not structured_data_str or "Bedrock invocation failed" in structured_data_str:
                    print(f"    ❌ Agent failed to process '{file_name}'. Response: {structured_data_str}")
                    continue

                # This is the most critical part: parsing the agent's response.
                try:
                    structured_data = json.loads(structured_data_str)
                except json.JSONDecodeError:
                    print(f"    ❌ Error: Agent returned a non-JSON string for '{file_name}'. Skipping.")
                    # Log the problematic response for debugging!
                    print(f"      -> Agent's raw response (first 200 chars): {structured_data_str[:200]}...")
                    continue

                aggregated_data = deep_merge_dicts(aggregated_data, structured_data)
                print(f"    ✅ Aggregated data from {file_name}.")

            except Exception as e:
                print(f"    ❌ Unexpected error processing '{file_name}': {e}")

        if aggregated_data:
            user_id = aggregated_data.get('userId')
            if not user_id:
                print("    ❌ Could not determine userId from aggregated data. Cannot upload profile.")
                continue
            
            s3_key = f"users/{user_id}.json"
            print(f"  - Uploading aggregated profile for userId '{user_id}' to S3...")
            s3_manager.upload_json(s3_key, aggregated_data)
        else:
            print("    ℹ️ No data could be aggregated from this session folder.")


if __name__ == "__main__":
    print("--- Starting CampusPilot Workflow ---")

    try:
        bedrock_agent = BedrockAgent()
        if not bedrock_agent.available:
            raise Exception(f"Bedrock Agent is not available: {bedrock_agent.init_error}")
        
        s3_manager = S3Manager(bucket_name="metadaten-tum-hackathon-reply-top90")
        s3_manager.check_or_create_bucket()
    except Exception as e:
        print(f"❌ [FATAL ERROR] Failed to initialize core components: {e}")
        sys.exit(1)

    print("\nInitializing CampusPilot Agent for introduction...")
    intro_response = get_agent_introduction(bedrock_agent)
    print("\n" + "="*50)
    print("CampusPilot Agent Response:")
    print("="*50)
    print(intro_response or "Agent introduction failed.")
    print("="*50)

    local_user_data_folder = os.path.join(project_root, "TemporaryUserInfoFiles")
    load_and_structure_data_into_bucket(s3_manager, bedrock_agent, local_user_data_folder)

    print("\n--- CampusPilot Workflow Finished ---")
