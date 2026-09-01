import asyncio
from collections import deque

class AsyncioRingBuffer:
    """
    一个协程安全的环形缓冲区实现，基于 collections.deque。
    """
    def __init__(self, capacity):
        if not isinstance(capacity, int) or capacity <= 0:
            raise ValueError("容量必须是大于0的整数。")
        self.buffer = deque(maxlen=capacity)
        self._lock = asyncio.Lock()

    async def push(self, item):
        """
        在缓冲区中放入一个元素。如果已满，最旧的元素会被自动移除。
        """
        async with self._lock:
            self.buffer.append(item)

    async def pop(self):
        """
        从缓冲区中移除并返回最旧的元素。
        注意：这可能导致队列为空，因此在多协程环境下需要自行处理同步问题。
        """
        async with self._lock:
            if not self.buffer:
                return None
            return self.buffer.popleft()

    async def peek(self):
        """
        返回缓冲区中最新元素的拷贝
        """
        async with self._lock:
            if not self.buffer:
                return None
            return self.buffer[-1].clone()

    async def get_all(self):
        """
        安全地获取缓冲区中的所有元素的拷贝。
        """
        async with self._lock:
            if not self.buffer:
                return []
            if len(self.buffer) == 0:
                return []
            return [e.clone() for e in list(self.buffer)]

    def __len__(self):
        """返回缓冲区的当前大小。"""
        return len(self.buffer)

    def __repr__(self):
        """返回缓冲区的字符串表示。"""
        return f"AsyncioRingBuffer({list(self.buffer)}, maxlen={self.buffer.maxlen})"

# --- 使用示例 ---
async def producer(buffer, name, num_items):
    for i in range(num_items):
        item = f"{name}-{i}"
        await buffer.push(item)
        print(f"[{name}] 放入: {item}, 缓冲区: {buffer}")
        await asyncio.sleep(0.01)

async def test():
    ring_buffer = AsyncioRingBuffer(capacity=5)

    print(f"初始缓冲区: {ring_buffer}")

    # 启动两个并发的生产者协程
    task1 = asyncio.create_task(producer(ring_buffer, "P1", 8))
    task2 = asyncio.create_task(producer(ring_buffer, "P2", 8))

    await asyncio.gather(task1, task2)

    print("-" * 20)
    print(f"最终缓冲区: {ring_buffer}")
    print(f"最终大小: {len(ring_buffer)}")

    # 获取并清空所有元素
    final_items = await ring_buffer.get_all()
    print(f"获取所有元素: {final_items}")
    print(f"清空后缓冲区: {ring_buffer}")

if __name__ == "__main__":
    asyncio.run(test())

