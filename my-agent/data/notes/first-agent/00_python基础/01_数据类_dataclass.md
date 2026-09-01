# 数据类 `@dataclass`

## 要学习什么

Python 的 `@dataclass` 装饰器能自动为一个类生成 `__init__`、`__repr__`、`__eq__` 等方法，大幅减少模板代码。

## 概念解释

```python
from dataclasses import dataclass

@dataclass
class ExpressBill:
    sender: str
    receiver: str
    item: str
    weight: float
```

用 `@dataclass` 修饰的类，只需声明字段及其类型，Python 会自动帮你做三件事：

- **自动 `__init__`**：不用手写构造函数，直接 `bill = ExpressBill("小明", "小红", "一本书", 0.5)`
- **自动 `__repr__`**：打印对象看到清晰内容 `ExpressBill(sender='小明', receiver='小红', ...)`
- **自动 `__eq__`**：两个字段值相同的对象可以比较相等 `bill == bill2`

### 运行示例

```python
bill = ExpressBill("小明", "小红", "一本书", 0.5)
print(bill)           # ExpressBill(sender='小明', receiver='小红', item='一本书', weight=0.5)
print(bill.sender)    # 小明

bill2 = ExpressBill("小明", "小红", "一本书", 0.5)
print(bill == bill2)  # True（字段值都相同）

# 字段支持按名称传参，顺序可以任意
bill3 = ExpressBill(weight=1.2, sender="小刚", receiver="小美", item="键盘")
```

## 关联的实际用法

XingClaw 大量使用 `@dataclass` 定义数据模型。例如消息系统中的各种内容块：

```python
@dataclass
class TextContent:
    type: str = "text"
    text: str = ""

@dataclass
class ImageContent:
    type: str = "image"
    data: str = ""
    mime_type: str = "image/png"
```

使用 `@dataclass` 的好处是定义非常简洁，每个字段的类型和默认值一目了然，而且自动生成的 `__init__` 支持按名称传参，实例化代码可读性高。
