# 并行任务 `asyncio.gather` 与 JSON 序列化

## 要学习什么

两个独立但实用的技能：用 `asyncio.gather` 同时执行多个异步任务，以及用 `json` 模块做序列化与反序列化。

## 概念解释

### 1. `asyncio.gather` — 同时做多件事

```python
import asyncio

async def search_weather(city: str) -> str:
    """模拟查询天气——每个城市查 2 秒"""
    await asyncio.sleep(2)
    weathers = {"北京": "晴 25°C", "上海": "多云 28°C", "深圳": "雷阵雨 30°C"}
    return f"{city}: {weathers.get(city, '未知')}"

async def main():
    # 同时查三个城市
    task1 = asyncio.create_task(search_weather("北京"))
    task2 = asyncio.create_task(search_weather("上海"))
    task3 = asyncio.create_task(search_weather("深圳"))

    # gather 等所有任务完成
    results = await asyncio.gather(task1, task2, task3)
    # 如果是串行要 6 秒，并行只要 ~2 秒

asyncio.run(main())
```

`asyncio.gather` 接收一组任务（或协程），等待它们全部完成后返回结果列表。任务之间真正并行。

### 2. JSON 序列化

JSON 是 AI API 通信的标准格式：

```python
import json

# Python 字典 → JSON 字符串（序列化）
data = {
    "model": "claude-sonnet-4-5",
    "messages": [
        {"role": "user", "content": "你好"},
    ],
    "stream": True,
}
json_str = json.dumps(data, ensure_ascii=False, indent=2)

# JSON 字符串 → Python 字典（反序列化）
parsed = json.loads(json_str)
print(parsed["model"])   # claude-sonnet-4-5
```

### 3. JSONL（JSON Lines）

JSONL 每行一个独立 JSON 对象，适合追加写入和逐行读取：

```python
# 写 JSONL
with open("history.jsonl", "w", encoding="utf-8") as f:
    for msg in messages:
        f.write(json.dumps(msg, ensure_ascii=False) + "\n")

# 读 JSONL
loaded = []
with open("history.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        loaded.append(json.loads(line.strip()))
```

## 关联的实际用法

XingClaw 在多个地方用到这些技术：

- **`gather`**：同时向多个模型或服务发起请求，等所有结果回来后再统一处理
- **JSON**：与 AI API 通信时，请求体和响应体都是 JSON 格式
- **JSONL**：用于存储对话历史，每条消息占一行，方便追加和回溯

AI 厂商返回的流式数据也是 JSON-Lines 风格的 SSE 格式：

```
event: content_block_delta
data: {"type": "content_block_delta", "delta": {"text": "你好"}}

event: content_block_stop
data: {"type": "content_block_stop", "index": 0}
```

每个数据行是一个独立的 JSON 对象，用 `json.loads()` 解析后即可处理。
