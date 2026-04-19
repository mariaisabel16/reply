"""
Amazon S3 Vectors + Bedrock Titan embeddings — gleiche Konfiguration wie
`CampusPilot/Agent/strategist_agent.py`, mit optionalen Env-Overrides.
"""
from __future__ import annotations

import os
from typing import Any

from config import settings

VECTOR_BUCKET_NAME = os.environ.get(
    "CAMPUSPILOT_VECTOR_BUCKET", "tum-hackathon-vectors-2026"
).strip() or "tum-hackathon-vectors-2026"
VECTOR_INDEX_NAME = os.environ.get(
    "CAMPUSPILOT_VECTOR_INDEX", "campus-pilot-index"
).strip() or "campus-pilot-index"

_bedrock_client: Any | None = None
_s3_vectors_client: Any | None = None
_vector_store: Any | None = None


def get_vector_store():
    """Lazy-init LangChain AmazonS3Vectors (read-only similarity search)."""
    global _bedrock_client, _s3_vectors_client, _vector_store
    if _vector_store is not None:
        return _vector_store
    try:
        import boto3
        from langchain_aws.embeddings import BedrockEmbeddings
        from langchain_aws.vectorstores.s3_vectors import AmazonS3Vectors
    except ImportError as e:
        raise RuntimeError(
            "Vector-KB benötigt `langchain-aws` (pip install langchain-aws)."
        ) from e

    region = settings.bedrock_region
    _bedrock_client = boto3.client("bedrock-runtime", region_name=region)
    _s3_vectors_client = boto3.client("s3vectors", region_name=region)

    embedding = BedrockEmbeddings(
        client=_bedrock_client,
        region_name=region,
        model_id="amazon.titan-embed-text-v1",
    )
    # LangChain speichert page_content standardmäßig unter `_page_content` in den Metadaten.
    # S3 Vectors erlaubt für *filterbare* Metadaten nur 2048 Bytes — große Chunks würden sonst
    # bei PutVectors scheitern. `_page_content` muss als nicht filterbar deklariert werden
    # (Index muss mit metadataConfiguration angelegt sein — ggf. Index löschen und neu ingesten).
    _vector_store = AmazonS3Vectors(
        vector_bucket_name=VECTOR_BUCKET_NAME,
        index_name=VECTOR_INDEX_NAME,
        embedding=embedding,
        region_name=region,
        client=_s3_vectors_client,
        non_filterable_metadata_keys=["_page_content"],
        page_content_metadata_key="_page_content",
    )
    return _vector_store


def search_curriculum_kb_sync(query: str, k: int = 12) -> str:
    """
    Semantische Suche im offiziellen TUM/CampusPilot-KB (Studienordnung, Module, Credits).
    Gibt formatierten Text für das LLM zurück.
    """
    q = (query or "").strip()
    if not q:
        return ""
    vs = get_vector_store()
    n = max(1, min(int(k), 25))
    tuple_list = vs.similarity_search_with_score(q, k=n)
    results: list[str] = []
    for doc, _score in tuple_list:
        results.append(f"--- Document Snippet ---\n{doc.page_content}\n")
    return "\n".join(results)
