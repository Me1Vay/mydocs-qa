"""W3：只练 Chroma upsert / query。

运行（在项目根目录）:
  python practice/p1/chroma_hello.py
"""

from pathlib import Path

import chromadb

ROOT = Path(__file__).resolve().parents[2]


def chunk_text(text: str, chunk_size: int = 40, overlap: int = 10) -> list[str]:
    chunks = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + chunk_size, n)
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end == n:
            break
        start = max(0, end - overlap)
    return chunks


chroma_client = chromadb.Client()
collection = chroma_client.get_or_create_collection(name="my_collection")
text = (ROOT / "data" / "sample.txt").read_text(encoding="utf-8")
chunks = chunk_text(text)
ids = [str(i) for i in range(len(chunks))]
collection.upsert(
    documents=chunks,
    ids=ids,
)

results = collection.query(
    query_texts=["老周为什么叹气?"],
    n_results=4,
)

print(results)
