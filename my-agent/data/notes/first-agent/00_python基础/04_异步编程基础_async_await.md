# 异步编程基础 `async/await`

## 要学习什么

Python 的 `async/await` 语法让程序能在等待 I/O 操作（如网络请求、文件读写）时去干别的事，而不是空等。

## 概念解释

### 煮咖啡的类比

**同步方式**：先煮小明那杯咖啡——等 2 分钟直到煮好，再煮小红那杯——又等 2 分钟。总共 4 分钟，期间啥也没干。

**异步方式**：同时开始煮两杯咖啡——虽然每杯都要 2 分钟，但它们同时进行，总共只用 2 分钟。

### 代码对比

```python
import asyncio, time

# 同步版本：一杯一杯来
def sync_make_coffee(drinker: str):
    print(f"{drinker}: 开始煮咖啡...")
    time.sleep(2)
    print(f"{drinker}: 咖啡煮好了！")
    return f"{drinker} 的咖啡"

start = time.time()
sync_make_coffee("小明")
sync_make_coffee("小红")
print(f"同步总用时: {time.time() - start:.1f} 秒")

# 异步版本：两杯同时煮
async def async_make_coffee(drinker: str):
    print(f"{drinker}: 开始煮咖啡...")
    await asyncio.sleep(2)
    print(f"{drinker}: 咖啡煮好了！")
    return f"{drinker} 的咖啡"

async def main():
    task1 = asyncio.create_task(async_make_coffee("小明"))
    task2 = asyncio.create_task(async_make_coffee("小红"))
    coffee1 = await task1
    coffee2 = await task2
    print("异步总用时约 2 秒（并行）")

asyncio.run(main())
```

### 三个关键词

- **`async def`**：定义一个"可以异步执行"的函数
- **`await`**："我在这里等结果，但不阻塞其他人"
- **`create_task`**："把这个任务放到后台跑"

## 关联的实际用法

XingClaw 的 `prompt()` 方法就是异步的，因为它内部要发 HTTP 请求（网络 I/O）：

```python
async def prompt(self, message: str) -> list[Message]:
    # 内部发 HTTP 请求时用 await，不阻塞事件循环
    ...

# 流式读取数据
async for event in stream:
    # 每次有新数据就处理，没有就自动等待
    print(event)
```

当模型生成长文本时，SDK 通过 `async for` 边生成边推送 `text_delta` 事件，调用方实时收到每个增量片段，而不是等全部生成完才拿到结果。
