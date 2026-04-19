import json
import boto3
from dotenv import load_dotenv

from langchain_aws.embeddings import BedrockEmbeddings
from langchain_aws.vectorstores.s3_vectors import AmazonS3Vectors
from langchain_aws import ChatBedrock
from langchain.tools import tool
from langchain.agents import create_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain.messages import HumanMessage, SystemMessage

# Load environment variables
load_dotenv()

# ==============================================================================
# GLOBAL CONFIGURATION
# ==============================================================================
VECTOR_BUCKET_NAME = 'tum-hackathon-vectors-2026'
VECTOR_INDEX_NAME = 'campus-pilot-index'
AWS_REGION = 'eu-central-1'

# Global clients to prevent re-initialization
_bedrock_client = None
_s3_vectors_client = None
_vector_store = None

def get_vector_store():
    global _bedrock_client, _s3_vectors_client, _vector_store
    if _vector_store is None:
        _bedrock_client = boto3.client('bedrock-runtime', region_name=AWS_REGION)
        _s3_vectors_client = boto3.client('s3vectors', region_name=AWS_REGION)
        
        embedding = BedrockEmbeddings(
            client=_bedrock_client, 
            region_name=AWS_REGION, 
            model_id="amazon.titan-embed-text-v1"
        )
        
        _vector_store = AmazonS3Vectors(
            vector_bucket_name=VECTOR_BUCKET_NAME,
            index_name=VECTOR_INDEX_NAME,
            embedding=embedding,
            region_name=AWS_REGION,
            client=_s3_vectors_client,
            non_filterable_metadata_keys=["_page_content"],
            page_content_metadata_key="_page_content",
        )
    return _vector_store

# ==============================================================================
# AGENT TOOL
# ==============================================================================
@tool
def search_curriculum_kb(query: str):
    """
    Searches the official TUM Knowledge Base for information about modules,
    credit requirements, and the Studienordnung (official study regulations).
    
    Args:
        query: The search query (e.g., 'What are the required modules for Winfo?', 'How many credits is IN0001?')
    """
    print(f"\n[Strategist] 🔍 Searching Knowledge Base for: '{query}'")
    vs = get_vector_store()
    tuple_list = vs.similarity_search_with_score(query, k=5)
    
    # Return formatted text for the LLM
    results = []
    for doc, score in tuple_list:
        results.append(f"--- Document Snippet ---\n{doc.page_content}\n")
    return "\n".join(results)

# ==============================================================================
# STRATEGIST AGENT CLASS
# ==============================================================================
class StrategistAgent:
    def __init__(self, model_id="eu.anthropic.claude-haiku-4-5-20251001-v1:0"):
        """
        Initializes the Strategist Agent.
        Uses Claude 3.5 Sonnet by default for strong analytical and reasoning capabilities.
        """
        # Ensure clients are initialized
        get_vector_store()
        
        self.model = ChatBedrock(
            model_id=model_id,
            client=_bedrock_client,
            model_kwargs={"temperature": 0.2}, # Slight temperature for strategic advice
        )
        
        self.memory = MemorySaver()
        self.thread_counter = 0

    def invoke(self, query: str, user_context: list | dict, thread_id: str = None) -> str:
        """
        Invokes the Strategist Agent with the user's query and their current progress context.
        
        Args:
            query (str): The user's question or the orchestrator's request.
            user_context (list|dict): JSON data from the Webcrawler showing current modules and status.
            thread_id (str): Optional session ID for memory.
            
        Returns:
            str: The strategic advice from the agent.
        """
        if not thread_id:
            self.thread_counter += 1
            thread_id = f"strategist_thread_{self.thread_counter}"
            
        config = {"configurable": {"thread_id": thread_id}}
        
        # Convert context to formatted string
        context_str = json.dumps(user_context, indent=2, ensure_ascii=False)
        
        # Build the dynamic system prompt
        system_prompt = f"""You are a highly strategic and analytical TUM Student Advisor. 
Your role is to orchestrate and plan the student's career based on their live progress and official rules.

You have access to the student's live TUMonline data. Here is their current progress context:
<user_context>
{context_str}
</user_context>

CRITICAL INSTRUCTIONS:
1. Always use the `search_curriculum_kb` tool to look up official rules, modules, and prerequisites from the Knowledge Base.
2. Compare the official requirements from the KB against the <user_context>.
3. Be EXTREMELY cautious about inconsistencies. Explicitly point out if the student is missing mandatory modules (Pflichtmodule) or is behind on credits.
4. Give actionable, strategic advice for their current or upcoming semester.
5. Do not make up rules. If you cannot find the answer in the KB, state that clearly.
"""

        # We recreate the agent per invocation to inject the dynamic system prompt safely
        agent_executor = create_agent(
            model=self.model,
            tools=[search_curriculum_kb],
            checkpointer=self.memory,
            system_prompt=system_prompt,
        )
        
        print("\n[Strategist] 🤔 Analyzing context and formulating strategy...")
        response = agent_executor.invoke({"messages": [HumanMessage(content=query)]}, config)
        
        # Return the final message content
        return response["messages"][-1].content


# ==============================================================================
# MOCK TEST FOR VERIFICATION
# ==============================================================================
if __name__ == "__main__":
    print("🚀 Initializing Strategist Agent Test...")
    
    # Dummy context mimicking the Webcrawler output
    mock_user_context = [
        {
            "module_name": "Einführung in die Informatik (IN0001)",
            "is_required": True,
            "status": "POSITIVE",
            "credits_current": "6",
            "credits_total": "6",
            "raw_credits_text": "6/6"
        },
        {
            "module_name": "Grundlagenpraktikum Programmierung (IN0002)",
            "is_required": True,
            "status": "FAILED",
            "credits_current": "0",
            "credits_total": "6",
            "raw_credits_text": "0/6"
        }
    ]
    
    agent = StrategistAgent()
    
    test_query = "I just finished my first semester. Based on my context, what should my strategy be for the next semester? Am I missing any critical mandatory modules?"
    
    print(f"\n👤 Orchestrator/User: {test_query}")
    
    answer = agent.invoke(query=test_query, user_context=mock_user_context)
    
    print("\n🤖 Strategist Agent:")
    print(answer)
