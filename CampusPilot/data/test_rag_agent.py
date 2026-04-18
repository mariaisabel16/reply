import os
import boto3
from dotenv import load_dotenv

from langchain_aws.embeddings import BedrockEmbeddings
from langchain_aws.vectorstores.s3_vectors import AmazonS3Vectors
from langchain_aws import ChatBedrock
from langchain.tools import tool
from langchain.agents import create_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain.messages import HumanMessage

# Load environment variables
load_dotenv()

# ==============================================================================
# 1. SETUP VECTOR STORE CONNECTION
# ==============================================================================
VECTOR_BUCKET_NAME = 'tum-hackathon-vectors-2026'
VECTOR_INDEX_NAME = 'campus-pilot-index'
AWS_REGION = 'eu-central-1'

print("Connecting to Bedrock and S3 Vectors...")
bedrock_client = boto3.client('bedrock-runtime', region_name=AWS_REGION)
s3_vectors_client = boto3.client('s3vectors', region_name=AWS_REGION)

embedding = BedrockEmbeddings(
    client=bedrock_client, 
    region_name=AWS_REGION, 
    model_id="amazon.titan-embed-text-v1"
)

vector_store = AmazonS3Vectors(
    vector_bucket_name=VECTOR_BUCKET_NAME,
    index_name=VECTOR_INDEX_NAME,
    embedding=embedding,
    region_name=AWS_REGION,
    client=s3_vectors_client
)

# ==============================================================================
# 2. DEFINE AGENT TOOL
# ==============================================================================
@tool
def similarity_search(text: str):
    """ Finds similar strings in a vector database.
    Args:
        text: A string to run similarity search for

    Return value:
        A list containing dictionaries of the search results.
    """
    print(f"\n[Agent Tool] 🔍 Searching Vector Store for: '{text}'")
    tuple_list = vector_store.similarity_search_with_score(text)
    
    res = [{'page_content': tup[0].page_content, 'similarity_score': tup[1]} for tup in tuple_list]
    return res

# ==============================================================================
# 3. SETUP LLM & AGENT
# ==============================================================================
# Note: Reusing the model ID from your notebook. If it fails, change to "anthropic.claude-3-haiku-20240307-v1:0"
model_id = "eu.anthropic.claude-haiku-4-5-20251001-v1:0" 

model = ChatBedrock(
    model_id=model_id,
    client=bedrock_client,
    model_kwargs={"temperature": 0, "top_k": 1},
)

memory = MemorySaver()

agent = create_agent(
    model=model,
    tools=[similarity_search],
    checkpointer=memory,
    system_prompt="You are a helpful TUM student advisor. Use the similarity search tool to look up information before answering questions about TUM examinations and required modules.",
)

# ==============================================================================
# 4. RUN TEST PROMPTS
# ==============================================================================
if __name__ == "__main__":
    print("\n🚀 Agent is ready! Running tests...\n")
    config = {"configurable": {"thread_id": "test_thread_1"}}
    
    # Test Question 1
    query_1 = "How many credits do I get for taking the module IN0001 (Einführung in die Informatik)?"
    print(f"👤 User: {query_1}")
    
    response = agent.invoke({"messages": [HumanMessage(content=query_1)]}, config)
    
    print("\n🤖 Agent:")
    # The last message is the final answer from the agent
    print(response["messages"][-1].content)
    
    print("\n" + "="*50 + "\n")
    
    # Test Question 2 (Testing Studienordnung PDF data)
    query_2 = "According to the Studienordnung, what happens if I fail an exam?"
    print(f"👤 User: {query_2}")
    
    response = agent.invoke({"messages": [HumanMessage(content=query_2)]}, config)
    
    print("\n🤖 Agent:")
    print(response["messages"][-1].content)
