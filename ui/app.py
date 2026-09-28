"""MyDocs-QA Streamlit UI —— 本地文档切块 → Chroma 检索 → DeepSeek 带引用回答。

界面层只负责展示；切块/检索/Prompt 全部复用 core.rag_core，逻辑不在这里重复。
"""

from __future__ import annotations

import html
import re
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.rag_core import RagError, answer_question, chunk_text, load_document

st.set_page_config(
    page_title="MyDocs-QA · 本地文档智能问答",
    page_icon="📄",
    layout="centered",
    initial_sidebar_state="expanded",
)

_CSS = """
<style>
:root{
  --mq-accent:#2563EB;
  --mq-accent-d:#1D4ED8;
  --mq-accent-soft:#EFF6FF;
  --mq-accent-line:#BFDBFE;
  --mq-ink:#0F172A;
  --mq-ink-2:#64748B;
  --mq-line:#E2E8F0;
  --mq-surface:#FFFFFF;
  --mq-page:#F6F8FB;
}
.stApp{background:var(--mq-page);}
#MainMenu,footer{visibility:hidden;}
header[data-testid="stHeader"]{background:transparent;}
.block-container{padding-top:2.2rem;padding-bottom:3rem;max-width:880px;}

.mq-hero{text-align:center;margin:0 0 1.6rem;}
.mq-kicker{display:inline-block;font-size:.72rem;font-weight:600;letter-spacing:.08em;
  color:var(--mq-accent-d);background:var(--mq-accent-soft);border:1px solid var(--mq-accent-line);
  border-radius:999px;padding:.2rem .7rem;margin-bottom:.75rem;}
.mq-hero h1{font-size:2rem;line-height:1.25;margin:0 0 .55rem;color:var(--mq-ink);font-weight:700;}
.mq-hero p{font-size:.92rem;line-height:1.78;color:var(--mq-ink-2);margin:0 auto;max-width:608px;}

.mq-stats{display:flex;gap:.6rem;margin:.2rem 0 1.2rem;}
.mq-stat{flex:1 1 0;background:var(--mq-surface);border:1px solid var(--mq-line);
  border-radius:12px;padding:.65rem .5rem;text-align:center;}
.mq-stat b{display:block;font-size:1.2rem;font-weight:700;color:var(--mq-ink);line-height:1.35;}
.mq-stat span{font-size:.75rem;color:var(--mq-ink-2);}

.mq-label{display:flex;align-items:center;gap:.5rem;font-size:.82rem;font-weight:600;
  color:var(--mq-ink-2);margin:1.15rem 0 .5rem;}
.mq-label::before{content:"";width:3px;height:.95rem;background:var(--mq-accent);border-radius:2px;}

.mq-answer{background:var(--mq-surface);border:1px solid var(--mq-line);
  border-left:3px solid var(--mq-accent);border-radius:12px;padding:.95rem 1.1rem;
  font-size:1rem;line-height:1.95;color:var(--mq-ink);}
.mq-cite{display:inline-block;background:var(--mq-accent-soft);color:var(--mq-accent-d);
  border:1px solid var(--mq-accent-line);border-radius:6px;padding:0 .3rem;
  font-size:.82em;font-weight:600;margin:0 1px;}

.mq-hit{display:flex;gap:.65rem;align-items:flex-start;background:var(--mq-surface);
  border:1px solid var(--mq-line);border-radius:11px;padding:.6rem .8rem;margin-bottom:.45rem;}
.mq-hit-idx{flex:0 0 auto;min-width:1.75rem;height:1.55rem;display:flex;align-items:center;
  justify-content:center;background:var(--mq-accent-soft);color:var(--mq-accent-d);
  border:1px solid var(--mq-accent-line);border-radius:7px;font-size:.76rem;font-weight:700;}
.mq-hit-txt{flex:1 1 auto;font-size:.88rem;line-height:1.75;color:#334155;}

.mq-tip{background:var(--mq-surface);border:1px dashed var(--mq-line);border-radius:12px;
  padding:1.4rem 1.2rem;text-align:center;color:var(--mq-ink-2);font-size:.88rem;line-height:1.85;}
.mq-tip b{color:var(--mq-ink);}

.mq-side-title{font-size:.78rem;font-weight:700;color:var(--mq-ink);margin:.2rem 0 .55rem;}
.mq-hr{border:none;border-top:1px solid var(--mq-line);margin:1.05rem 0;}
.mq-chain{margin:0;padding-left:1.1rem;font-size:.79rem;line-height:1.85;color:#475569;}
.mq-chain li{margin-bottom:.2rem;}

.stButton>button{border-radius:10px;font-weight:600;padding:.5rem 1rem;}
.stButton>button[kind="primary"]{background:var(--mq-accent);border:1px solid var(--mq-accent);color:#fff;}
.stButton>button[kind="primary"]:hover{background:var(--mq-accent-d);border-color:var(--mq-accent-d);color:#fff;}
.stTextInput input{border-radius:10px;border:1px solid var(--mq-line);}
[data-testid="stSidebar"]{background:var(--mq-surface);border-right:1px solid var(--mq-line);}
[data-testid="stExpander"]{border:1px solid var(--mq-line);border-radius:12px;}
[data-testid="stAlert"]{border-radius:10px;}
[data-testid="stFileUploaderDropzone"]{border-radius:12px;}
</style>
"""
st.markdown(_CSS, unsafe_allow_html=True)


def _esc(text: str) -> str:
    return html.escape(str(text))


def _answer_html(text: str) -> str:
    """把回答渲染成卡片，并把 [3][4] 这类引用编号做成高亮徽章。"""
    safe = html.escape(text)
    safe = re.sub(r"\[(\d+)\]", r'<span class="mq-cite">[\1]</span>', safe)
    return safe.replace("\n", "<br>")


def _hit_html(idx: str, text: str) -> str:
    return (
        f'<div class="mq-hit"><div class="mq-hit-idx">{_esc(idx)}</div>'
        f'<div class="mq-hit-txt">{_esc(text)}</div></div>'
    )


# ─────────────────────────── 抬头 ───────────────────────────

st.markdown(
    '<div class="mq-hero">'
    '<div class="mq-kicker">RAG · ChromaDB · DeepSeek</div>'
    "<h1>MyDocs-QA</h1>"
    "<p>把本地文档切块存进向量库，提问时先检索出最相关的几段，"
    "再让大模型<b>只根据这几段</b>回答，并在答案末尾标出引用编号——"
    "用检索约束降低幻觉，让答案可追溯。</p>"
    "</div>",
    unsafe_allow_html=True,
)

# ─────────────────────────── 侧栏 ───────────────────────────

with st.sidebar:
    st.markdown('<div class="mq-side-title">检索参数</div>', unsafe_allow_html=True)
    chunk_size = st.slider("切块大小", min_value=20, max_value=120, value=40, step=10)
    overlap = st.slider("重叠长度", min_value=0, max_value=40, value=10, step=5)
    n_results = st.slider("检索条数 Top-K", min_value=1, max_value=8, value=4)
    st.markdown('<hr class="mq-hr">', unsafe_allow_html=True)
    st.markdown('<div class="mq-side-title">技术链路</div>', unsafe_allow_html=True)
    st.markdown(
        '<ol class="mq-chain">'
        "<li>读文档 → 按字符切块</li>"
        "<li>本地 ONNX 模型算 embedding</li>"
        "<li>写入 Chroma 向量库</li>"
        "<li>问题向量检索取 Top-K</li>"
        "<li>拼进约束式 Prompt → DeepSeek 回答</li>"
        "</ol>",
        unsafe_allow_html=True,
    )
    st.markdown('<hr class="mq-hr">', unsafe_allow_html=True)
    st.caption("密钥放在 `.env` 的 `DEEPSEEK_API_KEY`，不写入代码。")

# ─────────────────────────── 文档来源 ───────────────────────────

default_doc = ROOT / "data" / "sample.txt"
uploaded = st.file_uploader("上传 .txt（可选，留空则用内置示例文档）", type=["txt"])

work_path = default_doc
if uploaded is not None:
    work_path = ROOT / "data" / "_upload.txt"
    work_path.parent.mkdir(parents=True, exist_ok=True)
    work_path.write_bytes(uploaded.getvalue())

try:
    doc_text = load_document(work_path)
except RagError as err:
    doc_text = ""
    st.error(str(err))

chunks = chunk_text(doc_text, chunk_size=chunk_size, overlap=overlap) if doc_text.strip() else []

st.caption(f"当前文档：`{work_path.name}`")
st.markdown(
    '<div class="mq-stats">'
    f'<div class="mq-stat"><b>{len(doc_text.strip())}</b><span>文档字符数</span></div>'
    f'<div class="mq-stat"><b>{len(chunks)}</b><span>切块数</span></div>'
    f'<div class="mq-stat"><b>{n_results}</b><span>检索 Top-K</span></div>'
    "</div>",
    unsafe_allow_html=True,
)

# ─────────────────────────── 提问 ───────────────────────────

st.markdown('<div class="mq-label">提问</div>', unsafe_allow_html=True)
question = st.text_input(
    "问题",
    value="老周为什么叹气？今晚他想做什么？",
    label_visibility="collapsed",
)

col_run, col_prev = st.columns([3, 2])
with col_run:
    run = st.button("开始问答", type="primary", use_container_width=True)
with col_prev:
    show_chunks = st.checkbox("预览切块", value=False)

if "mq_result" not in st.session_state:
    st.session_state.mq_result = None

if run:
    if not question.strip():
        st.warning("请先输入问题。")
    else:
        with st.spinner("检索并生成中…"):
            try:
                _answer, _hits = answer_question(
                    question,
                    doc_path=work_path,
                    chunk_size=chunk_size,
                    overlap=overlap,
                    n_results=n_results,
                )
            except RagError as err:
                st.error(str(err))
            except Exception as err:  # noqa: BLE001
                st.error(f"未知错误：{type(err).__name__}: {err}")
            else:
                st.session_state.mq_result = (question, _answer, _hits)

# ─────────────────────────── 结果 ───────────────────────────

result = st.session_state.mq_result

if result is not None:
    asked, answer, hits = result
    st.markdown('<div class="mq-label">回答</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="mq-answer">{_answer_html(answer)}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="mq-label">引用块 · Top-{len(hits)}</div>', unsafe_allow_html=True)
    st.markdown("".join(_hit_html(str(i), c) for i, c in hits), unsafe_allow_html=True)
    st.caption(f"提问：{asked}")
elif not show_chunks:
    st.markdown(
        '<div class="mq-tip">点「<b>开始问答</b>」跑一次示例：<br>'
        "它会先检索出相关段落，再让模型只依据这些段落作答，并在末尾标注引用编号。<br>"
        "答案里的 <b>[3] [4]</b> 就是它实际用到的段落，可逐条核对。</div>",
        unsafe_allow_html=True,
    )

if show_chunks and chunks:
    st.markdown(f'<div class="mq-label">切块预览 · 共 {len(chunks)} 块</div>', unsafe_allow_html=True)
    st.markdown("".join(_hit_html(str(i), c) for i, c in enumerate(chunks)), unsafe_allow_html=True)

with st.expander("当前文档预览"):
    try:
        preview = load_document(work_path) if work_path.exists() else doc_text
    except RagError as err:
        preview = str(err)
    st.text(preview[:2000] + ("…" if len(preview) > 2000 else ""))
