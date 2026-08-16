# Prompt 类型与 Agent 分层

在 LLM / Agent 系统中，Prompt 不只是用户输入的一句话。根据来源、作用位置、控制级别、生命周期和使用目的，可以将 Prompt 分成多类。

不同模型 API 和框架的命名略有差异，但核心思想类似：把稳定规则、产品约束、当前任务、历史信息、外部知识和工具结果分开管理。

## 一、总体结构

一个复杂 Agent 的输入通常可以抽象为：

```text
System Prompt        身份、规则、安全边界
Developer Prompt     产品约束、实现要求
Memory Prompt        用户长期偏好和历史事实
Skill Prompt         某类任务的标准流程
Context Prompt       对话历史、代码、RAG 检索结果
Tool Definitions     可调用工具的描述和参数
User Prompt          当前用户任务
Tool Results         工具执行后的环境反馈
        ↓
      LLM 推理
```

需要注意：这不是所有 API 都支持的固定消息角色层级。`system`、`developer`、`user`、`tool` 等角色以具体模型 API 的协议为准；`Memory`、`Skill`、`RAG` 等通常是应用层注入到上下文或系统提示词中的内容。

## 二、System Prompt

### 定义

System Prompt 是用于定义 Agent 基本身份、行为规范和安全边界的稳定提示词。

它主要回答：

> Agent 是谁？应该遵守什么规则？

例如：

```text
你是一个专业的软件开发助手。

要求：
1. 修改代码前先分析影响范围
2. 不删除用户文件
3. 遇到不确定的问题先说明假设
4. 完成修改后运行相关测试
```

典型内容包括：

- Agent 身份和职责；
- 输出风格；
- 安全边界；
- 可用工具的使用规则；
- 工作目录和环境约束；
- 长期适用的行为规范。

特点：

| 属性 | 说明 |
| --- | --- |
| 控制级别 | 通常较高 |
| 修改频率 | 较低 |
| 作用范围 | 整个会话或 Agent 生命周期 |
| 典型来源 | 系统配置、应用代码、工厂组装逻辑 |

在本项目中，系统提示词由 [`src/coding_agent/system_prompt.py`](src/coding_agent/system_prompt.py) 构建，并可能合并工具说明、Skill、Extension 规则、长期记忆和当前工作目录。

## 三、Developer Prompt

### 定义

Developer Prompt 用于表达开发者或产品层面的约束，通常位于 System Prompt 和 User Prompt 之间。

它主要回答：

> 这个具体产品或 Agent 应该如何运行？

例如：

```text
你正在开发一个企业内部代码助手。

规则：
- 使用 Python 3.12
- 项目采用 FastAPI
- 所有接口必须添加日志
- 不得修改生产配置
```

System Prompt 和 Developer Prompt 的常见区别是：

```text
System：你是谁，以及必须遵守的基础规则
Developer：这个产品如何工作，以及具体业务约束
```

不过，是否存在独立的 `developer` 消息角色取决于模型 API。某些 API 支持显式的 Developer Prompt，其他框架可能将它合并进 System Prompt。

在本项目中，产品级约束主要通过 system prompt 构建器、workspace 配置、Extension、Skill 和工厂参数注入，并不要求必须存在一个名为 `developer` 的独立消息类型。

## 四、User Prompt

### 定义

User Prompt 是用户当前提出的任务或问题。

例如：

```text
帮我分析这个 Agent 架构，并指出上下文压缩的位置。
```

它主要回答：

> 用户现在想让 Agent 完成什么？

特点：

- 动态变化；
- 通常每轮不同；
- 最接近当前任务目标；
- 可以触发 Skill、Tool 或 MCP 能力。

在本项目中，CLI、飞书或其他入口最终都会调用：

```python
await session.prompt(user_text)
```

## 五、Context Prompt

### 定义

Context Prompt 指为当前推理动态注入的相关上下文，不一定是独立消息角色。

它可以包括：

- 历史对话；
- 之前的助手回复；
- 工具执行结果；
- 当前文件内容；
- RAG 检索结果；
- 当前任务状态；
- 环境信息。

例如用户说：

```text
继续修改代码。
```

Agent 必须结合之前的上下文理解“代码”指什么、已经改到哪一步、之前的测试是否失败。这些历史信息就是 Context。

本项目通过 `AgentContext.messages` 保存当前消息上下文，并由 `AgentSession` 负责恢复和压缩。相关实现位于 [`src/coding_agent/agent_session.py`](src/coding_agent/agent_session.py)。

## 六、Memory Prompt

### 定义

Memory Prompt 是从长期记忆中提取出来，并在后续任务中重新注入的上下文。

例如用户曾经说明：

```text
Python 代码必须使用 Type Hint，测试使用 pytest。
```

以后 Agent 处理代码任务时，可以注入：

```text
用户偏好：Python 代码使用 Type Hint，测试使用 pytest。
```

Memory 解决的是：

> 跨会话保留哪些稳定事实、偏好和约束？

本项目会读取 workspace 或 IM 相关的长期记忆，并将内容追加到系统提示词中。IM 场景还支持全局记忆和频道级记忆的合并。

Memory 与普通 Context 的区别是：

```text
Context：当前任务临时需要的信息
Memory：跨任务、跨会话可能持续有效的信息
```

## 七、Skill Prompt

### 定义

Skill Prompt 是由 Skill 文件提供的、可复用的任务流程和领域知识。

Skill 通常放在：

```text
.xingclaw/skills/*.md
```

例如：

```markdown
---
name: 代码审查
command: review
description: 按规范执行代码审查
---

1. 先读取相关文件
2. 检查正确性、安全性和性能
3. 按严重程度输出问题
4. 给出文件路径和行号
5. 不直接修改代码
```

Skill 加载后通常会：

1. 解析 Markdown 和元数据；
2. 创建 `SkillSpec`；
3. 将正文追加到 system prompt；
4. 增加提示约束；
5. 注册 `/review` 等运行时命令。

实现位于 [`src/coding_agent/extensions/skills.py`](src/coding_agent/extensions/skills.py)。

Skill 主要解决：

> 这类任务应该按照什么稳定流程完成？

它通常不直接读取文件或执行命令，而是指导模型选择已有 Tool。

## 八、Few-shot Prompt

### 定义

Few-shot Prompt 通过提供若干输入输出示例，让模型模仿指定的格式或判断方式。

例如：

```text
输入：用户说“退款失败”
输出：分类：支付问题

输入：用户说“密码错误”
输出：分类：账号问题

现在输入：用户说“无法登录”
```

期望模型输出：

```text
分类：账号问题
```

Few-shot 常用于：

- 分类；
- 信息抽取；
- 固定格式生成；
- 结构化输出；
- Agent 规划示例；
- 领域术语和风格模仿。

它不需要训练或微调模型，只是在当前上下文中提供示例。

## 九、Tool Prompt 与 Tool Result

在 Agent 系统中，工具相关内容通常包括两部分。

### 1. Tool Definition

Tool Definition 是发送给模型的工具描述，包括：

- 工具名称；
- 工具用途；
- 参数 Schema；
- 参数约束。

例如：

```json
{
  "name": "read",
  "description": "读取文件内容",
  "parameters": {
    "type": "object",
    "properties": {
      "path": {"type": "string"}
    }
  }
}
```

### 2. Tool Result

Tool Result 是工具执行后返回给模型的观察结果。

例如：

```text
Tool: read
Result:
文件内容为：...
```

本项目中，工具返回的结果会转换为 `ToolResultMessage`，再加入 Agent 上下文。它是 ReAct 循环中的 Observation：

```text
模型推理 → ToolCall → 工具执行 → ToolResultMessage → 再次推理
```

严格来说，`Tool Prompt` 不是所有 API 都定义的独立消息类型。更准确的说法是“工具定义和工具结果上下文”。

## 十、Reasoning / Chain-of-Thought Prompt

Reasoning Prompt 用于引导模型按某种步骤分析问题，例如：

```text
先分析问题和约束，再列出候选方案，最后给出结论。
```

在 Agent 中常见的结构是：

```text
分析任务
    ↓
选择行动
    ↓
调用工具
    ↓
读取观察结果
    ↓
继续分析
```

也就是 ReAct：

```text
Reasoning → Action → Observation → Reasoning
```

需要注意，Reasoning Prompt 不等于要求系统暴露模型的完整内部思维过程。工程实现更适合要求模型输出可验证的计划、决策依据、工具调用和结果摘要。

## 十一、Agent 专用 Prompt

复杂 Agent 还会根据内部职责进一步拆分 Prompt。

### Planner Prompt

负责任务拆解：

```text
将用户需求拆成多个可执行步骤，并说明步骤依赖关系。
```

例如：

```text
Step 1：定位相关文件
Step 2：分析现有实现
Step 3：修改代码
Step 4：运行测试
Step 5：总结结果
```

### Router Prompt

负责选择能力或路径：

```text
判断任务属于代码生成、网页操作还是数据分析，并选择对应的 Skill 或工具。
```

### Reflection Prompt

负责结果检查：

```text
检查刚才的修改是否满足需求，测试是否通过；如果失败，分析原因并提出下一步行动。
```

在本项目中，这些职责不一定对应独立的 Prompt 类或独立 Agent，而可以通过 system prompt、Skill、Extension Hook 和 Agent Loop 的多轮调用组合实现。

## 十二、Prompt 层级和生命周期

可以从两个维度理解 Prompt。

### 按控制层级

```text
System / Developer：稳定规则和产品约束
        ↓
Skill / Memory：可复用流程和长期信息
        ↓
Context / Tool Result：当前任务状态和环境观察
        ↓
User：当前任务目标
```

### 按生命周期

```text
长期：System、Developer、部分 Memory
会话级：Skill、会话历史、频道记忆
任务级：Planner、Router、Reflection Context
单轮级：User Prompt、Tool Result、临时 RAG 结果
```

实际 API 会根据消息角色和协议对这些内容进行组合，不应机械地认为每一类都必须是独立的消息类型。

## 十三、结合本项目的实际组合

以代码审查任务为例：

```text
System Prompt：你是安全可靠的编程 Agent
Developer Prompt：项目使用 Python，禁止修改生产配置
Skill Prompt：按照代码审查流程执行
Memory Prompt：用户偏好 Type Hint 和 pytest
Context Prompt：已有会话历史和目标文件内容
User Prompt：请审查 src/app.py
Tool Definition：read、grep、find 等工具描述
Tool Result：工具返回的代码和搜索结果
```

之后 Agent Loop 执行：

```text
读取任务上下文
    ↓
模型规划审查步骤
    ↓
调用 read / grep / find
    ↓
接收工具结果
    ↓
继续分析或反思
    ↓
输出最终审查报告
```

## 十四、面试回答版本

Prompt 在 Agent 系统中通常按照来源和作用分为 System Prompt、Developer Prompt、User Prompt、Context Prompt、Memory Prompt、Skill Prompt、Tool Definition / Tool Result 和 Few-shot Prompt 等。

它们的核心区别是职责和生命周期不同：

- System Prompt 定义 Agent 身份、基础规则和安全边界；
- Developer Prompt 约束产品行为和实现要求；
- User Prompt 表达当前任务；
- Context Prompt 提供当前任务所需的历史和外部信息；
- Memory Prompt 注入跨任务保留的用户偏好和事实；
- Skill Prompt 定义一类任务的标准流程；
- Tool Definition 描述可调用能力，Tool Result 提供环境执行反馈；
- Few-shot Prompt 通过示例约束格式和行为。

结合本项目，System、Skill、Memory 和 Extension 内容会在 Session 工厂中组装到 Agent 上下文，User Prompt 由 CLI 或 IM 传入，Tool Definition 和 Tool Result 参与 Agent Loop，最终形成：

```text
规则约束 + 任务流程 + 历史上下文 + 用户任务 + 工具反馈
                         ↓
                       Agent 推理
```

