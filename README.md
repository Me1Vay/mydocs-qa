# MyDocs-QA · 本地文档智能问答（RAG）

把本地文档切块存入向量库，提问时先检索出最相关的几段，再让大模型**只根据这几段**回答，
并在答案末尾标注引用编号 —— 用检索约束降低幻觉，让答案可追溯。

全链路本地可跑：**文档切块 → 本地 ONNX 向量化 → Chroma 检索 → DeepSeek 带引用生成**。
不需要联网下载模型权重之外的外部服务，embedding 完全离线。

## 效果

问题：`老周为什么叹气？今晚他想做什么？`

回答：

> 老周叹气是因为想到画眉跟他三年，比儿子回家的次数都多，又觉得不该跟一只鸟计较这些[3][4]。
> 今晚他想给儿子打个电话，哪怕只是问[10]。

答案里的 `[3] [4] [10]` 就是模型实际用到的段落，界面会把对应引用块并排列出，可逐条核对——
这是"答案有出处"最直接的证据。

## 技术链路

```
① 读文档
   ↓
② 按字符切块（chunk_size=40, overlap=10，均可在界面调）
   ↓
③ 本地 ONNX 模型（all-MiniLM-L6-v2）算 embedding → 写入 Chroma 向量库
   ↓
④ 用户问题做相似度检索，取 Top-K（默认 4）
   ↓
⑤ 拼进约束式 Prompt → DeepSeek 回答（带引用编号）
```

代码位置（`core/rag_core.py` 是唯一实现，CLI 与网页共用）：

| 环节 | 函数 |
|---|---|
| 切块 | `chunk_text()` |
| 检索 | `retrieve()` |
| Prompt + 调模型 | `ask_llm()` |
| 串流程 | `answer_question()` |

## 功能

- 文档加载与按字符切块（`chunk_size` / `overlap` 可在界面实时调整）
- Chroma 向量入库与相似度检索（Top-K 可调）
- 约束式 Prompt：「只根据资料回答」+ 无资料就拒答 + 末尾标注引用编号
- **网页界面**：卡片化布局、引用编号高亮徽章、切块预览、参数实时调节
- **CLI 入口**：不依赖任何 UI，适合脚本化验证
- API Key 走 `.env`，异常按类型分类返回中文提示

## 目录结构

```
mydocs-qa/
├── core/
│   └── rag_core.py          # 共用 RAG 逻辑（CLI / UI 都调用）
├── ui/
│   ├── app.py               # Streamlit 主界面
│   └── ui_hello.py          # 备用界面（零额外依赖，装不上 Streamlit 时用）
├── practice/                # 分步验证脚本
│   ├── p0/chat_test.py          # 只验证 API 连通
│   └── p1/
│       ├── p1_chunk_test.py     # 只验证切块
│       ├── chroma_hello.py      # 只验证 Chroma upsert / query
│       └── p1_qa_test.py        # 完整链路 CLI 问答（推荐先用它验证）
├── data/sample.txt          # 示例文档
├── app.py                   # Streamlit 入口（转发到 ui/app.py）
├── requirements.txt
├── .env.example
└── README.md
```

## 快速开始

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # Windows PowerShell
pip install -r requirements.txt
```

在项目根目录创建 `.env`（已被 `.gitignore` 忽略，不会提交）：

```env
DEEPSEEK_API_KEY=你的密钥
```

**先用 CLI 验证链路**（能看到带 `[编号]` 的回答就算通）：

```bash
python practice/p1/p1_qa_test.py
```

**再开网页界面**：

```bash
streamlit run ui/app.py
# 或：streamlit run app.py
# 打开 http://127.0.0.1:8501
```

装不上 Streamlit 时可用零依赖备用界面：`python ui/ui_hello.py`

## 设计要点

**1. 约束式 Prompt（降幻觉的核心）**

三条约束写在同一条 prompt 里：①「只根据下列资料回答问题」把模型限制在检索结果内；
②「如果资料里没有，就说不知道」宁可拒答也不编；③「末尾标注用到的编号，如 `[0]`」让答案可溯源。

**2. 异常分类处理**

`AuthenticationError` / `RateLimitError` / `APIError` 分别映射成明确的中文提示
（Key 无效 / 触发限流 / 调用失败），不把原始堆栈甩给用户。

**3. 单一实现 + 双入口**

CLI 和网页都调用 `core/rag_core.py`，逻辑不重复；API Key 统一走 `.env`，不硬编码。

**4. Chroma 模型缓存重定向**

Chroma 默认把 embedding 模型缓存在系统盘（约 166MB）。这里覆盖类属性把它挪到自定义目录：

```python
CHROMA_CACHE_DIR = os.getenv('CHROMA_CACHE_DIR', r'D:\chroma-cache')
ONNXMiniLM_L6_V2.DOWNLOAD_PATH = Path(CHROMA_CACHE_DIR) / 'onnx_models' / ONNXMiniLM_L6_V2.MODEL_NAME
```

注意：`chromadb` 1.5.x 下 `CHROMA_CACHE_DIR` 环境变量**本身不生效**，必须覆盖 `DOWNLOAD_PATH` 类属性。

## 已知不足与改进方向

这个项目是练手项目，短板我很清楚，按优先级排：

1. **没有评估指标** —— 目前靠肉眼验证，没有测试集和检索命中率。**这是最大的问题**，
   下一步应该先建一个小测试集（20~30 条问题 + 标注答案）统计检索命中率与回答忠实度。
2. **embedding 偏英文** —— 用的是 Chroma 默认的 `all-MiniLM-L6-v2`，中文效果一般，
   换成 `bge-small-zh` 这类中文模型会有明显提升。
3. **没有 rerank** —— Top-K 里可能混入无关块。更严谨的做法是加相似度阈值或加一层重排。
4. 切块是固定字符数，真实文档应按语义/段落切。

## 复杂度说明

- 切块是在文本上线性扫描，约 **O(n)**（n = 文本长度）
- 小规模暴力相似度检索需要对每个 chunk 算一遍再取 Top-K，约 **O(m)**（m = chunk 数）
- 向量索引（Chroma / ANN）的意义就是把这个"每次全扫"换成近似最近邻结构

## 环境

Python 3.13 + `chromadb` 1.5 + `openai` 2.x + `streamlit` 1.6x + RapidOCR 无关（纯 RAG）。
embedding 为 CPU ONNX 推理，无需 GPU。
