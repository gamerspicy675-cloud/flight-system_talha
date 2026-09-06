import os
import asyncio
from pinecone import Pinecone, ServerlessSpec
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from app.core.config import settings

def ingest():
    if not settings.PINECONE_API_KEY or not settings.GEMINI_API_KEY:
        print("[ERROR] Ensure PINECONE_API_KEY and GEMINI_API_KEY are configured in .env")
        return

    # 1. Init Pinecone & Gemini Embeddings
    pc = Pinecone(api_key=settings.PINECONE_API_KEY)
    embeddings = GoogleGenerativeAIEmbeddings(
        model="gemini-embedding-001",
        google_api_key=settings.GEMINI_API_KEY,
        # Must match the existing Pinecone index dimension.
        output_dimensionality=768,
        task_type="RETRIEVAL_DOCUMENT",
    )

    index_name = settings.PINECONE_INDEX_NAME

    # Create a serverless index matching the 768-dimensional Gemini embeddings.
    existing_indexes = [idx["name"] for idx in pc.list_indexes()]
    if index_name not in existing_indexes:
        print(f"Creating Pinecone index: {index_name}...")
        pc.create_index(
            name=index_name,
            dimension=768,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1")
        )

    index = pc.Index(index_name)

    # 2. Read policy file
    file_path = "data/policy_docs/fare_rules.txt"
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    sections = [s.strip() for s in content.split("\n\n") if s.strip()]
    
    # 3. Embed and upsert
    print(f"Embedding {len(sections)} policy sections...")
    vectors = []
    for idx, text_block in enumerate(sections):
        vector_vals = embeddings.embed_query(text_block)
        vectors.append({
            "id": f"policy-{idx}",
            "values": vector_vals,
            "metadata": {"text": text_block}
        })

    index.upsert(vectors=vectors)
    print("[SUCCESS] Policy documents ingested into Pinecone.")

if __name__ == "__main__":
    ingest()
