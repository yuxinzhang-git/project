# Agent 长链路成功率提升方案

## 一、什么是 Agent 长链路

普通 LLM 调用通常是：

```text
用户问题 → LLM → 答案
```

Agent 长任务则可能包含很多连续步骤：

```text
解析任务
  ↓
制定计划
  ↓
打开浏览器
  ↓
登录
  ↓
搜索岗位
  ↓
提取信息
  ↓
判断是否符合
  ↓
生成邮件
  ↓
发送
```

假设每一步成功率都是 90%，10 步全部成功的概率为：

```text
0.9^10 = 34.8%
```

因此，Agent 长链路优化的核心不是只提升某一次模型回答，而是：

```text
减少错误传播
提高单步可靠性
保存中间状态
让失败可恢复
建立持续评估和优化闭环
```

## 二、总体架构

```text
                         User Task
                             │
                             ▼
                       Intent Router
                             │
                             ▼
                       Planner Agent
                             │
                             ▼
                         Task Graph
                             │
                 ┌───────────┴───────────┐
                 ▼                       ▼
               Skill                   Memory
                 │                       │
                 └───────────┬───────────┘
                             ▼
                       State Manager
                             │
                             ▼
                      Executor Agent
                             │
                 ┌───────────┴───────────┐
                 ▼                       ▼
                Tool                    MCP
                 │                       │
                 └───────────┬───────────┘
                             ▼
                       External System
                             │
                             ▼
                    Validation / Reflection
                             │
                             ▼
                         Final Answer
```

## 三、优化方向一：任务拆解和规划

很多 Agent 失败并不是执行阶段失败，而是一开始的任务计划就不合理。

例如用户要求分析一个项目，如果 Agent 直接读取所有文件，可能导致：

```text
读取全部文件
  ↓
上下文快速膨胀
  ↓
关键信息被淹没
  ↓
后续推理失败
```

因此可以增加 Planner，将大任务转换为可执行步骤或任务图：

```json
{
  "goal": "分析项目",
  "steps": [
    {
      "id": "scan",
      "task": "扫描项目目录",
      "tool": "find",
      "status": "pending"
    },
    {
      "id": "read_entry",
      "task": "读取入口文件",
      "tool": "read",
      "depends_on": ["scan"],
      "status": "pending"
    }
  ]
}
```

Planner 负责：

- 明确目标；
- 拆分任务；
- 识别步骤依赖；
- 选择 Skill 和工具；
- 预估风险；
- 生成可恢复的执行计划。

Executor 负责：

- 按计划执行当前步骤；
- 调用 Tool 或 MCP；
- 更新状态；
- 处理工具错误；
- 将结果交给下一步。

这就是 Planner-Executor 分离：

```text
Planner：为什么做、做什么
Executor：怎么做、如何执行
```

## 四、优化方向二：显式状态管理

长任务不能只依赖聊天历史。运行几十步之后，Agent 可能：

- 忘记原始目标；
- 重复执行已经完成的步骤；
- 不知道当前执行到哪一步；
- 丢失中间结果；
- 失败后无法判断从哪里恢复。

应设计显式 State：

```json
{
  "goal": "完成代码重构",
  "completed_steps": [
    "分析目录",
    "定位 bug"
  ],
  "current_step": "修改 database.py",
  "pending_tasks": [
    "运行测试",
    "检查回归问题"
  ],
  "artifacts": {
    "target_file": "src/database.py",
    "test_command": "pytest tests/test_database.py"
  },
  "errors": [],
  "last_checkpoint": "step_2"
}
```

每一步执行前：

```text
读取 State
  ↓
判断当前步骤
  ↓
选择下一步动作
  ↓
执行 Tool
  ↓
写回 State
```

在 XingClaw 中，`AgentSession` 和 `SessionStore` 已经承担了部分状态管理职责：

- `session_id` 标识一个长期任务；
- `session.jsonl` 保存消息节点和分支；
- `context.jsonl` 保存当前上下文；
- `events.jsonl` 保存运行事件；
- `leaf_id` 标识当前执行分支；
- `fork`、`switch` 支持从历史节点恢复。

相关实现位于 [`src/coding_agent/agent_session.py`](src/coding_agent/agent_session.py) 和 [`src/coding_agent/session_store.py`](src/coding_agent/session_store.py)。

## 五、优化方向三：上下文管理

长链路会不断产生：

```text
用户消息
助手规划
工具调用
工具输出
错误日志
测试结果
反思结果
```

如果全部原样放进上下文，就会导致：

- Context Window 溢出；
- 请求成本上升；
- 推理速度下降；
- 关键任务状态被大量日志淹没。

### 1. Context Compression

压缩前：

```text
用户说了什么
Agent 做了什么
工具返回了什么
大量重复日志和中间过程
```

压缩后：

```text
任务目标：完成代码重构
已完成：定位 database.py 中的连接问题
关键结论：连接池配置不正确
当前步骤：修改配置并运行测试
未完成：回归测试
```

XingClaw 会按消息数、估算 Token 数或模型上下文溢出触发压缩。旧消息交给 LLM 生成摘要，再保留最近消息，具体逻辑在 [`src/coding_agent/agent_session.py:286`](src/coding_agent/agent_session.py:286)。

### 2. Summary Memory

可以将信息分成：

```text
Short Memory：当前任务状态、最近工具结果、未完成步骤
Long Memory：用户偏好、历史经验、长期约束
```

这样既保留任务连续性，又避免把所有历史原文重复发送给模型。

### 3. RAG

不应把整个知识库或整个代码仓库塞进 Prompt，而应按需检索：

```text
Query
  ↓
Embedding
  ↓
Vector DB
  ↓
相关上下文
```

RAG 适合补充：

- 项目代码；
- 设计文档；
- 企业知识；
- 历史任务经验；
- 规范和接口说明。

## 六、优化方向四：提高 Tool 调用可靠性

Agent 的大量失败来自工具调用，而不是模型文本生成。

典型问题包括：

- 工具名称错误；
- 参数缺失；
- 参数类型错误；
- 路径不存在；
- 工具执行超时；
- 工具返回结果不完整；
- 工具实际执行成功，但状态没有更新。

### 1. Schema 约束参数

工具必须提供明确的参数 Schema：

```json
{
  "name": "read_file",
  "parameters": {
    "type": "object",
    "properties": {
      "path": {
        "type": "string",
        "description": "相对于 workspace 的文件路径"
      }
    },
    "required": ["path"],
    "additionalProperties": false
  }
}
```

在本项目中，`AgentTool` 的 `parameters` 字段就是给模型和运行时使用的参数约束，定义见 [`src/agent_core/types.py`](src/agent_core/types.py)。

### 2. 工具结果校验

不能完全相信工具返回的字符串。例如：

```text
create_file() → success
```

更可靠的流程是：

```text
创建文件
  ↓
检查文件是否存在
  ↓
检查内容或状态是否正确
  ↓
更新任务状态
```

对于数据库、部署和外部 API 等任务，应增加明确的 `verify_*` Tool。

### 3. 工具失败分类

可以将失败分成：

```text
参数错误       → 修正参数后重试
资源不存在     → 重新搜索或询问用户
权限错误       → 停止并请求授权
网络超时       → Backoff 重试
业务校验失败   → 重新规划
不可恢复错误   → 保存状态并结束
```

不同错误不能使用同一种重试策略。

## 七、优化方向五：规划和执行分离

简单 Agent 往往让同一个 LLM 同时负责：

```text
规划 + 决策 + 执行 + 结果检查
```

这容易导致计划不断变化、执行目标漂移和错误传播。

更稳妥的结构是：

```text
User
  ↓
Planner Agent
  ↓
Task Plan / Task Graph
  ↓
Executor Agent
  ↓
Tools / MCP
```

这类似于软件工程中的：

```text
架构设计 ≠ 编码实现
```

Planner 生成的计划还可以先经过 Schema 校验或人工确认，再交给 Executor 执行。

## 八、优化方向六：Reflection 和 Validation

长任务不能在最后一步直接相信模型输出。可以增加 Reviewer 或 Reflection 环节：

```text
执行任务
  ↓
生成结果
  ↓
Reviewer 检查
  ↓
发现问题
  ↓
修复或重新执行
```

反思问题可以包括：

1. 是否满足用户原始需求？
2. 是否遗漏了计划中的步骤？
3. 工具是否真的执行成功？
4. 结果是否通过业务校验？
5. 是否需要重新调用工具？
6. 是否存在未解决的错误？

需要区分：

```text
Reflection：模型检查自己的计划和结果
Validation：程序或业务规则检查结构和事实
```

关键结果应优先使用程序校验，而不是只依赖模型自检。

## 九、优化方向七：错误恢复机制

长链路一定可能失败。真正重要的是失败后能否从正确位置恢复。

### 1. Retry

适合网络超时、临时服务不可用等瞬时错误。

### 2. Exponential Backoff

避免失败后立即重复请求：

```text
第 1 次：等待 1 秒
第 2 次：等待 3 秒
第 3 次：等待 10 秒
```

XingClaw 的 `AgentSession` 已实现基于指数退避的自动重试，并记录 `auto_retry_start` 事件，见 [`src/coding_agent/agent_session.py:401`](src/coding_agent/agent_session.py:401)。

### 3. Checkpoint

长任务应在关键步骤后保存检查点：

```text
Step 1 ✓
Step 2 ✓
Step 3 失败
```

恢复时从 Step 3 开始，而不是从头执行。

XingClaw 通过 Session 消息持久化、事件记录、叶子节点和分支恢复，支持从历史状态继续任务。

### 4. 状态恢复

恢复流程是：

```text
读取 session_id
  ↓
读取 meta.json
  ↓
根据 leaf_id 恢复当前消息链
  ↓
恢复 AgentSession
  ↓
continue_run() 或接收新的 User Prompt
```

## 十、优化方向八：Human-in-the-loop

对高风险操作不应该完全自动执行，例如：

- 删除数据库；
- 发送外部邮件；
- 支付；
- 发布生产环境；
- 修改权限；
- 覆盖大量代码。

可以设计为：

```text
Agent
  ↓
Risk Check
  ↓
Human Approval
  ↓
Execute
```

Agent 可以先生成计划和参数，等用户确认后再调用 Tool。

## 十一、优化方向九：Skill 设计

Prompt 过大、规则混杂，也会降低长链路成功率。

可以将领域流程拆成 Skill，按任务动态加载。

例如 Browser Agent：

```text
browser_skill
├── 登录流程
├── 页面识别
├── 异常处理
└── 验证码和人工介入
```

例如 Coding Agent：

```text
coding_skill
├── 代码分析
├── Debug 流程
├── 测试规范
└── 修改和回滚约束
```

Skill 负责提供流程，Tool 负责执行动作，二者分离后可以减少每个任务需要加载的规则数量。

## 十二、优化方向十：MCP 工具生态

当工具数量很多时，不宜把所有自定义 API 都直接耦合到 Agent：

```text
Agent
  ↓
100 个自定义 API
```

可以通过 MCP 标准化工具接入：

```text
Agent
  ↓
MCP Client
  ↓
MCP Server
  ↓
Tools
```

MCP 的价值包括：

- 工具协议标准化；
- 工具来源解耦；
- 外部服务独立部署；
- 能力易于发现和扩展；
- 减少 Agent 与业务 API 的直接耦合。

在 XingClaw 中，MCP 工具会通过 Bridge 转换成统一的 `AgentTool`，因此可以参与同一套 Agent Loop。

## 十三、评估和数据闭环

企业落地不能只凭“感觉效果不错”，必须建立可量化的 Evaluation。

### 1. Task Success Rate

```text
任务成功率 = 成功完成的任务数 / 总任务数
```

例如：

```text
1000 个任务中成功 850 个
任务成功率 = 85%
```

### 2. Step Success Rate

分别统计每一步：

- 登录成功率；
- 搜索成功率；
- 信息提取成功率；
- 工具调用成功率；
- 代码修改成功率；
- 测试通过率；
- 最终交付成功率。

这样可以定位真正的瓶颈。

### 3. Trace 分析

记录完整链路：

```text
Input
  ↓
Plan
  ↓
Tool Call
  ↓
Observation
  ↓
State Update
  ↓
Reflection
  ↓
Final Answer
```

XingClaw 已通过 Agent Event 和 `events.jsonl` 保存运行过程，可以基于这些事件统计：

- 每个工具的失败率；
- 平均重试次数；
- 上下文压缩次数；
- 单任务运行时长；
- 任务在哪个步骤失败；
- 哪些 Skill 或 MCP 工具最容易出错。

可进一步接入 OpenTelemetry、LangSmith 或 Arize Phoenix 等链路观测系统。

## 十四、完整企业级方案

```text
User
  ↓
Intent Router
  ↓
Planner Agent
  ↓
Task Graph
  ↓
State Manager
  ├── Skill
  ├── Memory
  └── RAG
  ↓
Executor Agent
  ├── Tool
  └── MCP
  ↓
External System
  ↓
Validation
  ↓
Reflection / Reviewer
  ↓
Retry / Recovery / Human Approval
  ↓
Final Answer
```

## 十五、结合 XingClaw 的对应关系

| 长链路可靠性能力 | XingClaw 对应实现 |
| --- | --- |
| Agent Loop | `src/agent_core/agent_loop.py` |
| 工具协议和参数 Schema | `src/agent_core/types.py`、`builtin_tools.py` |
| 工具执行前后 Hook | `before_tool_call`、`after_tool_call` |
| Skill 流程 | `src/coding_agent/extensions/skills.py` |
| MCP 工具接入 | `src/coding_agent/mcp/bridge.py` |
| 会话状态 | `AgentSession` |
| 消息树和检查点 | `SessionStore`、`session.jsonl` |
| 上下文压缩 | `AgentSession._compact_context_if_needed()` |
| 任务恢复 | `session_id`、`leaf_id`、`continue_run()` |
| 自动重试 | `AgentSession._run_with_retry()` |
| 运行追踪 | Agent Events、`events.jsonl` |
| 人机交互入口 | CLI、RPC、IM Bridge |

## 十六、面试回答版本

Agent 长链路成功率提升的核心，是降低单步失败概率、减少错误传播，并让失败能够恢复。

首先，在任务层面通过 Planner 对复杂任务进行拆解，将任务转换成带依赖关系的步骤或任务图；其次，引入显式 State，保存任务目标、已完成步骤、当前步骤、中间结果和错误信息，避免只依赖长对话历史。

在上下文层面，通过上下文压缩、摘要记忆和 RAG 控制上下文规模，只把当前任务相关的信息交给模型。XingClaw 中已经通过 `AgentSession` 实现消息数和 Token 阈值检查、LLM 摘要以及历史消息保留。

在执行层面，通过 Tool Schema 约束参数，增加工具结果校验和业务验证，并采用 Planner-Executor 分离架构。对于外部系统，可以通过 MCP 标准化工具接入；对于领域流程，可以通过 Skill 封装，避免把所有规则塞进一个巨大 Prompt。

在可靠性层面，通过异常分类、Retry、Exponential Backoff、Checkpoint 和 Session 恢复处理失败；对于复杂任务，再增加 Reflection 和 Reviewer 做执行后的检查与修正。高风险操作则引入 Human-in-the-loop，要求人工确认后执行。

最后建立 Evaluation 和 Trace 体系，分别统计任务成功率、步骤成功率、工具失败率、重试次数、运行时长和失败位置，形成数据闭环。

总体来说，提升 Agent 长链路成功率不是简单地更换一个模型，而是通过：

```text
规划优化
+ 状态管理
+ 上下文控制
+ 工具可靠性
+ 规划执行分离
+ 反思校验
+ 错误恢复
+ 人工兜底
+ 评估闭环
```

共同提高整个任务链路的可靠性。

