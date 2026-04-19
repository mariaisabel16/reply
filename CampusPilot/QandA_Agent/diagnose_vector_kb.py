"""
Health-Check für search_curriculum_kb (Bedrock Titan + S3 Vectors).
Im Ordner QandA_Agent ausführen:  python diagnose_vector_kb.py
Lädt .env wie die FastAPI-App (config.settings).
"""
from __future__ import annotations

import traceback

from config import settings


def main() -> None:
    print("bedrock_region:", settings.bedrock_region)
    print("bedrock_model_id (Chat, nicht Embeddings):", settings.bedrock_model_id or "(leer)")
    try:
        from vector_kb import VECTOR_BUCKET_NAME, VECTOR_INDEX_NAME, search_curriculum_kb_sync

        print("vector_bucket:", VECTOR_BUCKET_NAME)
        print("vector_index:", VECTOR_INDEX_NAME)
        text = search_curriculum_kb_sync("Pflichtmodule Wirtschaftsinformatik Bachelor", k=2)
        print("\n--- OK: snippet preview (max 1200 Zeichen) ---\n")
        print(text[:1200] or "(leer — evtl. Index ohne passende Dokumente)")
    except Exception:
        print("\n--- FEHLER (Traceback) ---\n")
        traceback.print_exc()
        raise SystemExit(1)


if __name__ == "__main__":
    main()
