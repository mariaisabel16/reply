# study_planner_agent.py
import json
import os
import sys

# Add the project root to the Python path to enable modular imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

from langchain.tools import tool
from langchain_aws import ChatBedrock
from langchain.agents import create_agent
from langchain.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver

from Agent.prompts import SYSTEM_PROMPT_STUDY_PLANNER
from Database.s3_local import S3Manager

# --- Tool Definitions ---
# These are the functions the agent can decide to call.

# Initialize the S3 manager globally so tools can access it.
# In a real application, this might be a singleton or passed via a context.
try:
    s3_manager = S3Manager(bucket_name="metadaten-tum-hackathon-reply-top90")
except Exception as e:
    print(f"Failed to initialize S3Manager: {e}")
    s3_manager = None

@tool
def get_user_profile(user_id: str) -> dict:
    """
    Retrieves the static profile of a student from the S3 database.
    Args:
        user_id: The unique ID of the user (e.g., "tum_12345").
    Returns:
        A dictionary containing the user's profile data.
    """
    if not s3_manager:
        return {"error": "S3 connection is not available."}
    try:
        s3_key = f"users/{user_id}.json"
        return s3_manager.download_json(s3_key)
    except Exception as e:
        return {"error": f"Could not retrieve profile for {user_id}: {e}"}

@tool
def get_study_plan(study_program: str) -> dict:
    """
    Retrieves the official study plan for a given study program.
    This plan contains all required and elective modules per semester.
    Args:
        study_program: The name of the study program (e.g., "Informatik").
    Returns:
        A dictionary representing the study plan.
    """
    # This is a mock implementation. In a real scenario, this would fetch from a database.
    # We load it from a local mock file for this example.
    try:
        mock_file_path = os.path.join(project_root, "TemporaryUserInfoFiles", "session_logs_20240729_153000", "MockStudy_plan.json")
        with open(mock_file_path, 'r', encoding='utf-8') as f:
            # In a real system, you'd filter here by study_program
            return json.load(f)
    except Exception as e:
        return {"error": f"Could not load study plan: {e}"}

@tool
def get_module_catalog() -> dict:
    """
    Retrieves the complete catalog of all available modules, including electives.
    Returns:
        A dictionary containing a list of all modules.
    """
    # This is a mock implementation loading from a local file.
    try:
        mock_file_path = os.path.join(project_root, "TemporaryUserInfoFiles", "session_logs_20240729_153000", "MockModules.json")
        with open(mock_file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        return {"error": f"Could not load module catalog: {e}"}

# --- Agent Initialization ---

def create_study_planner_agent():
    """
    Creates and configures the Study Planner agent with its tools and system prompt.
    """
    print("Initializing Study Planner Agent...")
    
    # 1. Define the LLM
    # Ensure you have access to this model in your Bedrock region
    model_id = "anthropic.claude-3-haiku-20240307-v1:0" 
    model = ChatBedrock(
        model_id=model_id,
        model_kwargs={"temperature": 0.1},
    )

    # 2. Define the tools the agent can use
    tools = [get_user_profile, get_study_plan, get_module_catalog]
    
    # 3. Create the agent
    # This uses LangChain's built-in ReAct (Reasoning and Acting) agent setup
    agent = create_agent(
        llm=model,
        tools=tools,
        system_prompt=SYSTEM_PROMPT_STUDY_PLANNER,
    )
    
    print("✅ Study Planner Agent initialized.")
    return agent

# --- Main Execution Logic ---

if __name__ == "__main__":
    # This is the main entry point to run the proactive analysis for a user.
    
    # The user ID would typically come from the login event.
    # We use a mock user ID that should exist in your S3 bucket.
    USER_ID_TO_ANALYZE = "tum_12345" 
    
    print(f"--- Starting Proactive Study Analysis for user: {USER_ID_TO_ANALYZE} ---")
    
    planner_agent = create_study_planner_agent()
    
    # The initial prompt to kick off the agent's reasoning process.
    # The agent will follow the steps outlined in the SYSTEM_PROMPT_STUDY_PLANNER.
    initial_prompt = f"Analyze the study progress for the user with ID '{USER_ID_TO_ANALYZE}' and create a plan for the next semester."
    
    # Invoke the agent
    try:
        response = planner_agent.invoke(
            {"messages": [HumanMessage(content=initial_prompt)]}
        )
        
        print("\n" + "="*50)
        print("Study Planner Agent Final Response:")
        print("="*50)
        # The final answer is in the 'output' of the last message
        final_answer = response['messages'][-1].content
        print(final_answer)
        print("="*50)

    except Exception as e:
        print(f"\n❌ An error occurred while invoking the agent: {e}")

    print("\n--- Analysis Finished ---")
