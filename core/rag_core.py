"""MyDocs-QA 共用逻辑：切块 → 检索 → 带引用问答。"""

from __future__ import annotations

import os
from pathlib import Path

import chromadb
from dotenv import load_dotenv
from openai import APIError, AuthenticationError, OpenAI, RateLimitError
from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2

# Chroma 默认把 embedding 模型缓存在 C:\Users\<用户>\.cache\chroma（约 166 MB）。
# 注意：chromadb 1.5.9 下 CHROMA_CACHE_DIR 环境变量不生效，必须覆盖类属性 DOWNLOAD_PATH。
# 这里统一改到 D 盘（可用环境变量 CHROMA_CACHE_DIR 覆盖），避免占用系统盘。
CHROMA_CACHE_DIR = os.getenv('CHROMA_CACHE_DIR', r'D:\chroma-cache')
ONNXMiniLM_L6_V2.DOWNLOAD_PATH = Path(CHROMA_CACHE_DIR) / 'onnx_models' / ONNXMiniLM_L6_V2.MODEL_NAME


class RagError(Exception):
    """可展示给用户的业务/配置错误。"""


def chunk_text(text: str, chunk_size: int = 40, overlap: int = 10) -> list[str]:
    if chunk_size < 1:
        raise ValueError("chunk_size 必须 >= 1")
    overlap = min(max(0, overlap), chunk_size - 1)

    chunks: list[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + chunk_size, n)
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end == n:
            break
        start = end - overlap
    return chunks


def load_api_client() -> OpenAI:
    root = Path(__file__).resolve().parent.parent
    load_dotenv(root / ".env")
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise RagError("未找到 DEEPSEEK_API_KEY，请在 .env 里配置。")
    return OpenAI(api_key=api_key, base_url="https://api.deepseek.com")


def load_document(path: Path | str) -> str:
    path = Path(path)
    if not path.exists():
        raise RagError(f"找不到文档: {path}")
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise RagError(f"文档为空: {path}")
    return text


def retrieve(
    chunks: list[str],
    question: str,
    n_results: int = 4,
    collection_name: str = "my_collection",
) -> list[tuple[str, str]]:
    if not question.strip():
        raise RagError("问题不能为空。")
    if not chunks:
        raise RagError("切块结果为空，无法检索。")

    chroma_client = chromadb.Client()
    collection = chroma_client.get_or_create_collection(name=collection_name)
    ids = [str(i) for i in range(len(chunks))]
    collection.upsert(documents=chunks, ids=ids)

    top_k = min(n_results, len(chunks))
    results = collection.query(query_texts=[question], n_results=top_k)
    hit_ids = (results.get("ids") or [[]])[0]
    hit_docs = (results.get("documents") or [[]])[0]
    if not hit_ids or not hit_docs:
        raise RagError("检索无结果。")
    return list(zip(hit_ids, hit_docs))


def ask_llm(client: OpenAI, question: str, hits: list[tuple[str, str]]) -> str:
    context = "\n\n".join(f"[{i}] {c}" for i, c in hits)
    prompt = f"""只根据下列资料回答问题。回答末尾标注用到的编号，如[0]。
如果资料里没有，就说不知道。

资料:
{context}

问题: {question}
"""
    try:
        resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
        )
    except AuthenticationError as e:
        raise RagError("API Key 无效或无权限，请检查 .env。") from e
    except RateLimitError as e:
        raise RagError("触发限流，请稍后再试。") from e
    except APIError as e:
        raise RagError(f"API 调用失败: {e}") from e

    content = resp.choices[0].message.content
    if not content:
        raise RagError("模型返回空内容。")
    return content


def answer_question(
    question: str,
    doc_path: Path | str = "data/sample.txt",
    chunk_size: int = 40,
    overlap: int = 10,
    n_results: int = 4,
) -> tuple[str, list[tuple[str, str]]]:
    """返回 (回答, 引用块列表)。"""
    client = load_api_client()
    text = load_document(doc_path)
    chunks = chunk_text(text, chunk_size=chunk_size, overlap=overlap)
    hits = retrieve(chunks, question, n_results=n_results)
    answer = ask_llm(client, question, hits)
    return answer, hits
