# 异步队列 `asyncio.Queue` — 生产者-消费者模式

## 要学习什么

`asyncio.Queue` 是一个线程安全的异步队列，用于在生产者和消费者之间传递数据。它是实现"生产者-消费者"模式的核心工具。

## 概念解释

### 快递传送带类比

- **生产者** = 仓库工人，不断把包裹放上传送带
- **传送带** = `asyncio.Queue`，临时存放包裹
- **消费者** = 分拣员，从传送带上取走包裹进行处理

### 代码示例

```python
import asyncio

async def producer(queue: asyncio.Queue, name: str, items: list):
    """生产者：往队列里放东西"""
    for item in items:
        print(f"  [{name}] 放入了: {item}")
        await queue.put(item)     # 放入队列
        await asyncio.sleep(0.5)
    await queue.put(None)         # 结束信号
    print(f"  [{name}] 生产完毕")

async def consumer(queue: asyncio.Queue, name: str):
    """消费者：从队列里取东西"""
    while True:
        item = await queue.get()  # 等队列有东西再取
        if item is None:          # 遇到结束信号就退出
            queue.task_done()
            break
        print(f"    [{name}] 取出了: {item}")
        await asyncio.sleep(1)
        queue.task_done()
    print(f"    [{name}] 消费完毕")

async def main():
    queue: asyncio.Queue = asyncio.Queue()
    prod = asyncio.create_task(
        producer(queue, "仓库A", ["包裹1", "包裹2", "包裹3"])
    )
    cons = asyncio.create_task(consumer(queue, "分拣员"))
    await asyncio.gather(prod, cons)

asyncio.run(main())
```

关键点：生产者和消费者同时运行，`queue.get()` 会在队列空时自动等待，不会浪费 CPU。

## 关联的实际用法

XingClaw 的流式事件流就是用 `asyncio.Queue` 实现的：

```python
class AssistantMessageEventStream:
    def __init__(self):
        self._queue = asyncio.Queue()   # 事件队列
        self._result = asyncio.Future() # 最终结果

    def push(self, event):
        # 生产者：数据到达时放入队列
        self._queue.put_nowait(event)

    def end(self, message):
        # 发送结束信号
        self._queue.put_nowait(SENTINEL)

    async def __aiter__(self):
        # 消费者：async for 遍历时调用这里
        while True:
            item = await self._queue.get()
            if item is SENTINEL:
                break
            yield item

# 使用方式：
async for event in stream:          # 一个个取事件
    print(event['type'])             # text_delta, toolcall_end ...
msg = await stream.result()         # 或直接拿最终消息
```

SDK 收到服务器的 SSE 事件后，通过 `push()` 放入队列，调用方通过 `async for` 消费，两者互不阻塞。
