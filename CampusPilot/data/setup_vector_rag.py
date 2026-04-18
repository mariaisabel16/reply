import os
import glob
from pathlib import Path

# Load environment variables if available
from dotenv import load_dotenv
load_dotenv()

import boto3
from langchain_aws.embeddings import BedrockEmbeddings
from langchain_aws.vectorstores.s3_vectors import AmazonS3Vectors
from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

# ==============================================================================
# CONFIGURATION
# ==============================================================================
VECTOR_BUCKET_NAME = 'tum-hackathon-vectors-2026'
VECTOR_INDEX_NAME = 'campus-pilot-index'
AWS_REGION = 'eu-central-1'
EMBEDDING_MODEL_ID = 'amazon.titan-embed-text-v1'
EMBEDDING_DIMENSIONS = 1536 # Titan is 1536

# Directories
BASE_DIR = Path(__file__).parent.parent
RAG_OUTPUT_DIR = BASE_DIR / "data" / "rag_output"
PDF_DIR_INFORMATIK = BASE_DIR / "data" / "Bachelors" / "Informatik" / "Studienordnung"
PDF_DIR_WINFO = BASE_DIR / "data" / "Bachelors" / "Winfo" / "Studienordnung"

def create_vector_store():
    """Initializes the S3 Vector Bucket and Index."""
    print("--- Setting up S3 Vector Bucket ---")
    s3_vectors_client = boto3.client('s3vectors', region_name=AWS_REGION)
    
    try:
        print(f"Creating vector bucket: {VECTOR_BUCKET_NAME}...")
        s3_vectors_client.create_vector_bucket(vectorBucketName=VECTOR_BUCKET_NAME)
        print("Bucket created.")
    except s3_vectors_client.exceptions.ConflictException:
        print(f"Bucket '{VECTOR_BUCKET_NAME}' already exists. Proceeding.")
        
    try:
        print(f"Creating vector index: {VECTOR_INDEX_NAME}...")
        s3_vectors_client.create_index(
            vectorBucketName=VECTOR_BUCKET_NAME,
            indexName=VECTOR_INDEX_NAME,
            dataType='float32',
            dimension=EMBEDDING_DIMENSIONS,
            distanceMetric='cosine',
        )
        print("Index created.")
    except s3_vectors_client.exceptions.ConflictException:
        print(f"Index '{VECTOR_INDEX_NAME}' already exists. Proceeding.")
        
    return s3_vectors_client


def load_and_chunk_documents():
    """Loads TXT and PDF files and splits them into chunks."""
    print("\n--- Loading Documents ---")
    all_documents = []
    
    # 1. Load TXT Files (Modules)
    txt_files = list(RAG_OUTPUT_DIR.glob("*.txt"))
    print(f"Found {len(txt_files)} module text files.")
    for file_path in txt_files:
        try:
            loader = TextLoader(str(file_path), encoding="utf-8")
            all_documents.extend(loader.load())
        except Exception as e:
            print(f"Error loading {file_path.name}: {e}")
            
    # 2. Load PDF Files (Studienordnung)
    pdf_files = []
    if (PDF_DIR_INFORMATIK / "Studienordnung.pdf").exists():
        pdf_files.append(PDF_DIR_INFORMATIK / "Studienordnung.pdf")
    if (PDF_DIR_WINFO / "Studienordnung.pdf").exists():
        pdf_files.append(PDF_DIR_WINFO / "Studienordnung.pdf")
        
    print(f"Found {len(pdf_files)} PDF rules files.")
    for pdf_path in pdf_files:
        try:
            loader = PyPDFLoader(str(pdf_path))
            all_documents.extend(loader.load())
        except Exception as e:
            print(f"Error loading PDF {pdf_path.name}: {e}. Make sure pypdf is installed.")
            
    print(f"Total raw document objects loaded: {len(all_documents)}")
    
    # 3. Chunking
    print("\n--- Chunking Documents ---")
    # For a mix of short texts and long PDFs, a RecursiveCharacterTextSplitter is best.
    # 600 chunk size with 150 overlap gives the LLM enough context per chunk without getting confused.
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=600,
        chunk_overlap=150,
    )
    
    splits = text_splitter.split_documents(all_documents)
    print(f"Successfully split documents into {len(splits)} chunks!")
    return splits


def ingest_into_vector_store(s3_vectors_client, splits):
    """Embeds the chunks and uploads them to the S3 vector store."""
    print("\n--- Ingesting into Vector Store ---")
    bedrock_client = boto3.client('bedrock-runtime', region_name=AWS_REGION)
    
    embedding = BedrockEmbeddings(
        client=bedrock_client,
        region_name=AWS_REGION,
        model_id=EMBEDDING_MODEL_ID,
    )
    
    vector_store = AmazonS3Vectors(
        vector_bucket_name=VECTOR_BUCKET_NAME,
        index_name=VECTOR_INDEX_NAME,
        embedding=embedding,
        region_name=AWS_REGION,
        client=s3_vectors_client
    )
    
    print(f"Embedding and uploading {len(splits)} chunks to S3 Vectors... (this may take a minute or two)")
    vector_store.add_documents(splits)
    print("✅ Successfully ingested all chunks into the Vector Store!")


if __name__ == "__main__":
    print("🚀 Starting LangChain S3 Vector RAG Setup Process")
    client = create_vector_store()
    doc_splits = load_and_chunk_documents()
    if doc_splits:
        ingest_into_vector_store(client, doc_splits)
    print("🎉 Done! Your Custom RAG Database is ready to be queried by your Agent.")
