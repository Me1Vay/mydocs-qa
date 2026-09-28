"""W2：只练文档切块。

运行（在项目根目录）:
  python practice/p1/p1_chunk_test.py
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def chunk_text(text: str, chunk_size: int = 80, overlap: int = 20) -> list[str]:
    """按字符数粗切：后续 RAG 的第一步。"""
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


def main():
    path = ROOT / "data" / "sample.txt"
    text = path.read_text(encoding="utf-8")
    chunks = chunk_text(text)

    print(f"原文长度: {len(text)} 字")
    print(f"切成 {len(chunks)} 块\n")
    for i, c in enumerate(chunks, 1):
        print(f"--- 块 {i} ---")
        print(c)
        print()


if __name__ == "__main__":
    main()
