import os
import csv
import json
import boto3
from pathlib import Path

# ==============================================================================
# CONFIGURATION - UPDATE THESE WITH YOUR AWS RESOURCE NAMES
# ==============================================================================
S3_BUCKET_NAME = "metadaten-tum-hackathon-reply-top90"
KNOWLEDGE_BASE_ID = "your-kb-id"
DATA_SOURCE_ID = "your-ds-id"

# Directories
DATA_DIR = Path(__file__).parent
OUTPUT_DIR = DATA_DIR / "rag_output"

def create_rag_files():
    """Loops through Wahlmodule and Pflichtmodule CSVs and creates .txt and .metadata.json files."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    csv_files = []
    
    # Find all module CSVs
    for path in DATA_DIR.rglob("*.csv"):
        if "Wahlmodule" in path.name or "Pflichtmodule" in path.name:
            csv_files.append(path)

    processed_count = 0
    for csv_file in csv_files:
        print(f"Processing {csv_file.name}...")
        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                mod_id = row.get("Nr", "UNKNOWN").strip()
                mod_name = row.get("Modulbezeichnung", "").strip()
                
                # Skip invalid rows
                if not mod_id or mod_id == "UNKNOWN":
                    continue

                # 1. Create text content
                text_content = (
                    f"Modul: {mod_name} (ID: {mod_id})\n"
                    f"Kategorie: {row.get('Kategorie', '')}\n"
                    f"Credits (ECTS): {row.get('Credits', '')}\n"
                    f"Lehrform: {row.get('Lehrform', '')}\n"
                    f"Semester: {row.get('Sem', '')}\n"
                    f"SWS: {row.get('SWS', '')}\n"
                    f"Prüfungsart: {row.get('Prüfungsart', '')}\n"
                    f"Prüfungsdauer: {row.get('Prüfungsdauer', '')}\n"
                    f"Unterrichtssprache: {row.get('Unterrichtssprache', '')}\n"
                )

                # 2. Create metadata JSON
                # Bedrock metadata requires a "metadataAttributes" structure depending on setup, 
                # but standard JSON key-value pairs work for standard filtering.
                metadata = {
                    "metadataAttributes": {
                        "module_id": mod_id,
                        "module_name": mod_name,
                        "category": row.get('Kategorie', ''),
                        "credits": row.get('Credits', ''),
                        "semester": row.get('Sem', '')
                    }
                }

                # Write files
                safe_name = f"{mod_id}_{mod_name.replace(' ', '_').replace('/', '_')}"
                safe_name = "".join(c for c in safe_name if c.isalnum() or c == "_")[:50]
                
                txt_path = OUTPUT_DIR / f"{safe_name}.txt"
                json_path = OUTPUT_DIR / f"{safe_name}.txt.metadata.json"

                txt_path.write_text(text_content, encoding="utf-8")
                json_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
                
                processed_count += 1

    print(f"✅ Generated {processed_count} text and metadata file pairs in {OUTPUT_DIR}/")


def upload_to_s3():
    """Uploads the generated files to AWS S3."""
    if S3_BUCKET_NAME == "your-s3-bucket-name":
        print("⚠️ Skipping S3 Upload: S3_BUCKET_NAME not configured.")
        return

    s3 = boto3.client("s3")
    files = list(OUTPUT_DIR.glob("*"))
    
    print(f"Uploading {len(files)} files to S3 bucket '{S3_BUCKET_NAME}'...")
    for file_path in files:
        s3_key = f"data/rag_data/{file_path.name}"
        s3.upload_file(str(file_path), S3_BUCKET_NAME, s3_key)
    print("✅ S3 Upload complete!")


def sync_knowledge_base():
    """Triggers an ingestion job for AWS Bedrock Knowledge Base."""
    if KNOWLEDGE_BASE_ID == "your-kb-id" or DATA_SOURCE_ID == "your-ds-id":
        print("⚠️ Skipping Bedrock Sync: KNOWLEDGE_BASE_ID or DATA_SOURCE_ID not configured.")
        return

    bedrock_agent = boto3.client("bedrock-agent")
    print(f"Triggering sync for Knowledge Base {KNOWLEDGE_BASE_ID}...")
    
    response = bedrock_agent.start_ingestion_job(
        knowledgeBaseId=KNOWLEDGE_BASE_ID,
        dataSourceId=DATA_SOURCE_ID
    )
    job_id = response.get("ingestionJob", {}).get("ingestionJobId")
    print(f"✅ Sync started! Job ID: {job_id}")


if __name__ == "__main__":
    print("--- Starting RAG Data Pipeline ---")
    create_rag_files()
    upload_to_s3()
    sync_knowledge_base()
    print("--- Pipeline Finished ---")
