"""P0：先打通 DeepSeek 聊天 API。

运行（在项目根目录）:
  python practice/p0/chat_test.py
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

print("1. 开始")
print("2. Key是否读到:", bool(os.getenv("DEEPSEEK_API_KEY")))

if not os.getenv("DEEPSEEK_API_KEY"):
    print("请在项目根目录 .env 中配置 DEEPSEEK_API_KEY")
    sys.exit(1)

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)

print("3. 正在请求 DeepSeek...")
resp = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {"role": "user", "content": "用一句话介绍你自己"},
    ],
)

print("4. 回复:")
print(resp.choices[0].message.content)
