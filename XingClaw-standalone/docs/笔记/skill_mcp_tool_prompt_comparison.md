# Skill、Tool、MCP 与 Prompt 的区别

本文结合 XingClaw 项目的实现，说明 `Skill`、`Tool`、`MCP` 和 `Prompt` 的职责边界，以及它们如何共同扩展 Agent 能力。

## 一、整体关系

```text
Prompt：提出当前任务或约束
    ↓
Skill：规定某类任务的标准流程
    ↓
Tool：执行具体的本地操作
    ↓
MCP：将部分 Tool 调用转发到外部服务
    ↓
Agent Loop：把模型推理、工具调用和结果反馈串成闭环
```

最简单的区分方式是：

```text
Prompt 是“这次要做什么”
Skill 是“这类任务应该怎么做”
Tool 是“实际能执行什么动作”
MCP 是“如何连接外部动作提供方”
```

## 二、Skill、Tool 和 MCP 的区别

| 概念 | 解决的问题 | 本质 | 是否直接执行环境操作 | 项目中的实现 |
| --- | --- | --- | --- | --- |
| Skill | Agent 应该如何完成某类任务 | 可复用的 Markdown 流程和提示词 | 通常不直接执行 | `.xingclaw/skills/*.md` |
| Tool | Agent 如何读写文件、搜索代码和执行命令 | 带参数定义和执行函数的能力对象 | 是 | `AgentTool`、`builtin_tools.py` |
| MCP | Agent 如何使用外部服务能力 | MCP 工具代理 | 间接执行 | `mcp/bridge.py` |

### 1. Skill：扩展做事方法

Skill 是面向流程和领域知识的扩展，通常放在：

```text
.xingclaw/skills/*.md
```

示例：

```markdown
---
name: 代码审查
command: review
description: 按规范执行代码审查
---

1. 先读取相关文件
2. 检查正确性、安全性和性能
3. 按严重程度排序
4. 给出文件路径和行号
5. 不直接修改代码
```

加载代码位于 [`src/coding_agent/extensions/skills.py`](src/coding_agent/extensions/skills.py)。加载过程会：

1. 扫描 Skill 文件；
2. 解析名称、命令和描述；
3. 创建 `SkillSpec`；
4. 将 Skill 内容追加到系统提示词；
5. 注册对应命令，例如 `/review`。

Skill 本身通常不读取文件，也不执行命令。它指导模型按流程选择已有 Tool。

### 2. Tool：扩展实际执行能力

Tool 定义在 [`src/agent_core/types.py`](src/agent_core/types.py) 中，核心结构是：

```python
AgentTool(
    name="read",
    label="Read File",
    description="读取文件内容",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string"}
        }
    },
    execute=read_tool,
)
```

一个 Tool 包含：

- `name`：模型调用时使用的名称；
- `description`：告诉模型工具能做什么；
- `parameters`：参数 JSON Schema；
- `execute`：本地真正执行的函数。

项目中的内置 Tool 位于 [`src/coding_agent/builtin_tools.py`](src/coding_agent/builtin_tools.py)，包括：

```text
ls       查看目录
read     读取文件
write    写入文件
edit     修改文件
grep     搜索文件内容
find     查找文件
bash     执行命令
```

典型调用流程是：

```text
模型生成 ToolCall
    ↓
Agent 根据名称找到 Tool
    ↓
执行 execute()
    ↓
生成 AgentToolResult
    ↓
转换为 ToolResultMessage
    ↓
反馈给模型继续推理
```

例如模型不会直接操作文件，而是返回：

```json
{
  "name": "read",
  "arguments": {
    "path": "src/main.py"
  }
}
```

真正读取文件的是本地 Python 函数。

### 3. MCP：扩展外部服务能力

MCP 在本项目中采用代理模式，核心代码位于 [`src/coding_agent/mcp/bridge.py`](src/coding_agent/mcp/bridge.py)。

MCP 工具配置可以表示为：

```python
MCPToolConfig(
    name="search_docs",
    description="搜索外部文档",
    parameters={"type": "object"},
    server="docs-server",
    tool="search",
)
```

执行链路是：

```text
AgentTool
    ↓
MCP Proxy
    ↓
MCPClient.call_tool(server, tool, arguments)
    ↓
外部 MCP Server
    ↓
结果转换为 AgentToolResult
    ↓
反馈给模型
```

MCP 工具最终也会被包装成普通的 `AgentTool`。因此 Agent Loop 不需要知道工具来自本地 Python 还是远程 MCP Server，只需要统一执行：

```python
await tool.execute(tool_call_id, params, ...)
```

MCP 适合接入：

- 数据库；
- 搜索服务；
- 浏览器；
- 企业知识库；
- 工单系统；
- 日历、邮件和第三方 SaaS。

## 三、Skill 与 Prompt 的区别

| 对比项 | Prompt | Skill |
| --- | --- | --- |
| 形式 | 一段提示文本 | 可复用的 Markdown 文件 |
| 生命周期 | 通常只影响当前请求 | 可以被反复加载和调用 |
| 作用 | 表达当前任务或约束 | 定义一类任务的标准流程 |
| 元数据 | 通常没有 | 支持名称、命令、描述 |
| 是否可注册命令 | 不可以 | 可以，例如 `/review` |
| 是否适合团队复用 | 一般 | 适合 |
| 是否直接提供执行能力 | 不能 | 通常不能，依赖 Tool |

### 1. Prompt 是一次性指令

例如：

```text
请检查 src/app.py 的安全问题，并按严重程度输出。
```

它表达的是当前请求，发送给模型后生效。

项目中的系统 Prompt 会由 [`src/coding_agent/system_prompt.py`](src/coding_agent/system_prompt.py) 统一组装，内容可能包含：

- Agent 身份；
- 工作目录；
- 可用工具说明；
- 编码约束；
- Skill 内容；
- Extension 提供的额外规则；
- 长期记忆。

### 2. Skill 是可复用的 Prompt 能力包

Skill 最终也会进入系统 Prompt，但它比普通 Prompt 多了管理能力：

```text
Skill 文件
    ↓
解析元数据和正文
    ↓
追加到系统 Prompt
    ↓
注册 /skill 命令
    ↓
可被多个任务重复使用
```

因此可以认为：

```text
Prompt 是模型看到的一次指令；
Skill 是生成和管理这类指令的可复用机制。
```

## 四、三者如何协同完成任务

以“代码发布”为例：

```text
Skill：定义发布流程
  1. 检查代码
  2. 运行测试
  3. 请求审批
  4. 发布

Tool：执行本地操作
  - read 读取配置
  - grep 检查版本号
  - bash 运行测试

MCP：调用外部系统
  - 查询 CI 状态
  - 创建发布工单
  - 触发部署平台
```

完整关系是：

```text
Prompt 提出当前发布任务
        ↓
Skill 规定发布步骤和输出规范
        ↓
模型根据流程选择 Tool
        ↓
Tool 执行本地操作，MCP 连接外部系统
        ↓
结果反馈给模型
        ↓
Agent 继续规划，直到任务完成
```

## 五、在项目中的统一组装方式

Session 工厂位于 [`src/coding_agent/factory.py`](src/coding_agent/factory.py)，会统一加载：

```text
内置 Tool
Extension Tool
Skill
MCP Proxy Tool
系统 Prompt
```

最终：

- Skill 内容进入 Prompt；
- Extension 可以注册 Tool、命令和 Hook；
- MCP 被包装成 `AgentTool`；
- 所有 Tool 统一进入 Agent Loop；
- Agent 不需要区分能力的来源。

## 六、一句话总结

```text
Prompt：这次要做什么？
Skill：这类事情应该怎么做？
Tool：具体能执行哪些动作？
MCP：如何连接外部动作提供方？
```

