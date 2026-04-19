import csv
import os
from pathlib import Path

# Load environment variables if available
from dotenv import load_dotenv
load_dotenv()

import boto3
from langchain_aws.embeddings import BedrockEmbeddings
from langchain_aws.vectorstores.s3_vectors import AmazonS3Vectors
from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

# ==============================================================================
# CONFIGURATION
# ==============================================================================
VECTOR_BUCKET_NAME = os.environ.get(
    "CAMPUSPILOT_VECTOR_BUCKET", "tum-hackathon-vectors-2026"
).strip() or "tum-hackathon-vectors-2026"
VECTOR_INDEX_NAME = os.environ.get(
    "CAMPUSPILOT_VECTOR_INDEX", "campus-pilot-index"
).strip() or "campus-pilot-index"
AWS_REGION = os.environ.get("BEDROCK_REGION", "eu-central-1").strip() or "eu-central-1"
EMBEDDING_MODEL_ID = 'amazon.titan-embed-text-v1'
EMBEDDING_DIMENSIONS = 1536 # Titan is 1536

# Directories
BASE_DIR = Path(__file__).parent.parent
RAG_OUTPUT_DIR = BASE_DIR / "data" / "rag_output"
PDF_DIR_INFORMATIK = BASE_DIR / "data" / "Bachelors" / "Informatik" / "Studienordnung"
PDF_DIR_WINFO = BASE_DIR / "data" / "Bachelors" / "Winfo" / "Studienordnung"
CSV_PFlicht_WINFO = BASE_DIR / "data" / "Bachelors" / "Winfo" / "Pflichtmodule_info.csv"
CSV_PFlicht_INFO = BASE_DIR / "data" / "Bachelors" / "Informatik" / "Pflichtmodule_info.csv"


def _markdown_table_from_csv_rows(rows: list[dict[str, str]], headers: list[str]) -> str:
    esc = lambda s: str(s or "").replace("|", "\\|").replace("\n", " ")
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for r in rows:
        out.append("| " + " | ".join(esc(r.get(h, "")) for h in headers) + " |")
    return "\n".join(out)


def build_pflichtmodule_aggregate_documents() -> list[Document]:
    """
    Ein Dokument pro Studiengang mit der **vollständigen** Pflichtmodul-Tabelle aus der CSV.
    So findet die semantische Suche bei Fragen wie „alle Pflichtmodule Wirtschaftsinformatik“
    einen einzigen Chunk mit der kompletten Liste (statt nur PDF-Fragmenten).
    """
    specs: list[tuple[Path, str, str]] = [
        (
            CSV_PFlicht_WINFO,
            "Bachelor Wirtschaftsinformatik (TUM)",
            "Pflichtmodule Wirtschaftsinformatik Bachelor vollständige Modulliste Studienordnung ECTS SWS",
        ),
        (
            CSV_PFlicht_INFO,
            "Bachelor Informatik (TUM)",
            "Pflichtmodule Informatik Bachelor vollständige Modulliste Studienordnung ECTS SWS",
        ),
    ]
    docs: list[Document] = []
    for csv_path, program_title, retrieval_keywords in specs:
        if not csv_path.is_file():
            continue
        with csv_path.open(encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            headers = list(reader.fieldnames or [])
            rows = [dict(r) for r in reader]
        if not rows or not headers:
            continue
        table = _markdown_table_from_csv_rows(rows, headers)
        body = (
            f"# {program_title} — vollständige Pflichtmodule (kanonische CSV)\n\n"
            f"Suchbegriffe: {retrieval_keywords}\n\n"
            f"Die folgende Tabelle enthält **alle** Zeilen aus `{csv_path.name}` "
            "(alle Kategorien der Datei, vollständig für RAG-Abfragen „alle Pflichtmodule“).\n\n"
            f"{table}\n"
        )
        docs.append(
            Document(
                page_content=body,
                metadata={
                    "source": str(csv_path),
                    "doc_type": "pflichtmodule_csv_vollstaendig",
                    "program": program_title,
                },
            )
        )
    return docs


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

    # 2b. Vollständige Pflichtmodul-Listen (CSV → ein Embedding pro Studiengang)
    agg = build_pflichtmodule_aggregate_documents()
    if agg:
        print(f"Added {len(agg)} aggregate Pflichtmodul document(s) from CSV (full tables).")
        all_documents.extend(agg)

    # 3. Chunking
    print("\n--- Chunking Documents ---")
    # Kleine Chunks (z. B. 600) zerschneiden PDF-Tabellen mitten in der Zeile und ergeben
    # bei Top-k-Suche keine vollständigen Modullisten. Größere Chunks + Overlap für PDFs/Ordnungen;
    # kanonische CSV-Dokumente sind meist <8k und bleiben oft in einem Chunk.
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=3800,
        chunk_overlap=400,
        length_function=len,
        separators=["\n\n## ", "\n\n# ", "\n\n", "\n", " ", ""],
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
        client=s3_vectors_client,
        non_filterable_metadata_keys=["_page_content"],
        page_content_metadata_key="_page_content",
    )

    if os.environ.get("CAMPUSPILOT_S3_VECTORS_RESET_INDEX", "").strip().lower() in (
        "1",
        "true",
        "yes",
    ):
        print(
            "⚠️  CAMPUSPILOT_S3_VECTORS_RESET_INDEX gesetzt: lösche den kompletten Vektor-Index "
            f"'{VECTOR_INDEX_NAME}' (alle Vektoren), lege ihn mit nonFilterableMetadataKeys neu an."
        )
        vector_store.delete()
    
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
    print(
        "Hinweis: `add_documents` erneut ausführen legt **zusätzliche** Vektoren an (Duplikate). "
        "Für einen sauberen Neuaufbau: `CAMPUSPILOT_S3_VECTORS_RESET_INDEX=true` setzen (löscht den Index!) "
        "oder neuen `CAMPUSPILOT_VECTOR_INDEX` wählen.\n"
        "S3 Vectors: große Texte liegen in `_page_content` (nicht filterbar). Ein Index, der **ohne** "
        "`nonFilterableMetadataKeys` erstellt wurde, muss einmal gelöscht und neu aufgebaut werden, "
        "sonst schlägt PutVectors mit „Filterable metadata … 2048 bytes“ fehl."
    )
