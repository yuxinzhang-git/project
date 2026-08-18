# field 默认值与工厂函数

## 要学习什么

在 `@dataclass` 中定义可变默认值（如列表、字典）时，需要用 `field(default_factory=...)` 而不是 `=[]` 或 `={}`。

## 概念解释

### 为什么不能用 `=[]`

在 Python 3.12+ 中，直接在 `@dataclass` 里写 `items: list = []` 会直接报错：

```python
from dataclasses import dataclass, field

# ❌ 错误写法：Python 3.12+ 直接在定义时报错
# @dataclass
# class Cart:
#     items: list = []

# ✅ 正确写法：用 field(default_factory=...)
@dataclass
class GoodCart:
    items: list = field(default_factory=list)

c = GoodCart()
d = GoodCart()
c.items.append("苹果")
d.items.append("香蕉")

print(c.items)  # ['苹果']
print(d.items)  # ['香蕉']
print(c.items is d.items)  # False（不是同一个列表）
```

`default_factory` 会在每次创建实例时**调用一次工厂函数**，生成一个新的独立列表，确保实例之间互不影响。

### 复杂工厂函数

`default_factory` 不仅可以传 `list`，还可以传 lambda：

```python
@dataclass
class WordCounter:
    word_counts: dict[str, int] = field(default_factory=lambda: defaultdict(int))

wc = WordCounter()
wc.word_counts["hello"] += 1
wc.word_counts["hello"] += 1
print(dict(wc.word_counts))  # {'hello': 2}
```

## 关联的实际用法

XingClaw 源码中大量使用 `field(default_factory=...)` 来安全地处理可变默认值：

```python
@dataclass
class ToolCall:
    type: str = "toolCall"
    id: str = ""
    name: str = ""
    arguments: dict[str, Any] = field(default_factory=dict)
```

这样每个 `ToolCall` 实例都有自己的 `arguments` 字典，修改一个不会影响其他实例。这在处理多个并发的工具调用时尤为重要。
