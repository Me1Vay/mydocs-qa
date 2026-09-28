"""零额外依赖的简易网页 UI（stdlib），网络装不上 Streamlit 时也能演示 P1。

用法（在项目根目录）:
  python ui/ui_hello.py
然后浏览器打开 http://127.0.0.1:7860
装好 Streamlit 后更推荐: streamlit run ui/app.py
"""

from __future__ import annotations

import html
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.rag_core import RagError, answer_question

HOST, PORT = "127.0.0.1", 7860
DOC = ROOT / "data" / "sample.txt"


def page(question: str = "", answer: str = "", hits_html: str = "", err: str = "") -> bytes:
    q = html.escape(question)
    a = html.escape(answer)
    e = html.escape(err)
    body = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <title>MyDocs-QA</title>
  <style>
    body {{ font-family: Segoe UI, sans-serif; max-width: 720px; margin: 2rem auto; padding: 0 1rem; }}
    textarea, input, button {{ width: 100%; box-sizing: border-box; margin: 0.4rem 0; padding: 0.6rem; }}
    button {{ background: #1f6feb; color: #fff; border: 0; cursor: pointer; }}
    .err {{ color: #b42318; }}
    .hit {{ background: #f6f8fa; padding: 0.6rem; margin: 0.4rem 0; border-radius: 6px; }}
  </style>
</head>
<body>
  <h1>MyDocs-QA</h1>
  <p>文档: <code>{html.escape(str(DOC))}</code> · 切块 → Chroma → DeepSeek</p>
  <form method="POST">
    <label>问题</label>
    <textarea name="question" rows="3">{q or "老周为什么叹气？今晚他想做什么？"}</textarea>
    <button type="submit">开始问答</button>
  </form>
  {"<p class='err'>" + e + "</p>" if e else ""}
  {"<h2>回答</h2><p>" + a + "</p>" if a else ""}
  {"<h2>引用块</h2>" + hits_html if hits_html else ""}
</body>
</html>"""
    return body.encode("utf-8")


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self._reply(page())

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode("utf-8", errors="replace")
        question = (parse_qs(raw).get("question") or [""])[0]
        try:
            answer, hits = answer_question(question, doc_path=DOC)
            hits_html = "".join(
                f"<div class='hit'><b>[{html.escape(i)}]</b> {html.escape(c)}</div>"
                for i, c in hits
            )
            self._reply(page(question=question, answer=answer, hits_html=hits_html))
        except RagError as exc:
            self._reply(page(question=question, err=str(exc)))
        except Exception as exc:
            self._reply(page(question=question, err=f"{type(exc).__name__}: {exc}"))

    def _reply(self, content: bytes):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, fmt, *args):
        print("[%s] %s" % (self.log_date_time_string(), fmt % args))


def main():
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"MyDocs-QA UI: http://{HOST}:{PORT}")
    print("按 Ctrl+C 结束")
    server.serve_forever()


if __name__ == "__main__":
    main()
