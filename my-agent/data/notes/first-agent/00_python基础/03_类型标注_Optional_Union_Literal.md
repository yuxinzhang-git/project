# 类型标注：Optional、Union、Literal

## 要学习什么

三种常用的 Python 类型标注——`Optional`（可能有值也可能没有）、`Union`（多种类型之一）、`Literal`（固定选项之一）。

## 概念解释

### 1. Optional — 可能有值，也可能没有

等价于 `Union[类型, None]`，表示结果要么是你期待的类型，要么是 `None`：

```python
from typing import Optional

def find_user(name: str) -> Optional[str]:
    """根据名字查找用户所在城市，找不到返回 None"""
    users = {"小明": "北京", "小红": "上海"}
    return users.get(name)

print(find_user("小明"))  # 北京
print(find_user("小刚"))  # None
```

### 2. Union — 可能有好几种类型

表示一个值可以是几种类型中的任意一种：

```python
from typing import Union
from dataclasses import dataclass

@dataclass
class TextContent:
    type: str = "text"
    text: str = ""

@dataclass
class ImageContent:
    type: str = "image"
    data: str = ""
    mime_type: str = "image/png"

# 内容块可以是文本或图片
ContentBlock = Union[TextContent, ImageContent]

def describe_content(block: ContentBlock) -> str:
    if isinstance(block, TextContent):
        return f"文本：{block.text[:20]}..."
    elif isinstance(block, ImageContent):
        return f"图片：{block.mime_type}，{len(block.data)} 字节"
    return "未知类型"
```

配合 `isinstance` 做类型收窄（Narrowing），是处理联合类型最常用的模式。

### 3. Literal — 值只能是固定选项之一

相当于轻量版的枚举，精确限定取值：

```python
from typing import Literal

def set_mode(mode: Literal["stop", "length", "toolUse", "error"]) -> str:
    return f"模式已设为：{mode}"

print(set_mode("stop"))    # 正确
print(set_mode("error"))   # 正确
# set_mode("paused")       # ⚠️ 类型检查会报错
```

## 关联的实际用法

XingClaw 中 `isinstance` + `Union` 是最常见的判断模式：

```python
@dataclass
class UserMessage:
    role: str = "user"
    content: str = ""

@dataclass
class AssistantMessage:
    role: str = "assistant"
    content: str = ""

Message = Union[UserMessage, AssistantMessage]

def get_role(msg: Message) -> str:
    if isinstance(msg, UserMessage):
        return "用户消息"
    elif isinstance(msg, AssistantMessage):
        return "AI 回复"
    return "未知"
```

而 `Literal` 则用于标记每种内容块的 `type` 标签（`"text"`、`"thinking"`、`"image"`、`"toolCall"`），序列化成 JSON 后再通过 `type` 字段反序列化回对应的类。
