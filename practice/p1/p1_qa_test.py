import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.rag_core import RagError, answer_question


def main():
    question = "老周为什么叹气？今晚他想做什么？"
    try:
        answer, hits = answer_question(question, doc_path=ROOT / "data" / "sample.txt")
    except RagError as e:
        print(f"错误: {e}")
        sys.exit(1)

    print("问题:", question)
    print("引用块:")
    for i, c in hits:
        print(f"  [{i}] {c}")
    print("\n正在生成回答...\n")
    print(answer)


if __name__ == "__main__":
    main()
