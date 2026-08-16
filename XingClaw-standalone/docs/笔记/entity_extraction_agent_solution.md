# 结合 Agent 的实体抽取解决方案

## 一、问题定义

实体抽取（Entity Extraction）的目标是从非结构化文本中识别具有业务意义的实体，并转换成结构化数据。

例如用户输入：

```text
帮我查一下张三在字节跳动的实习经历，他是 2025 年 7 月入职北京的。
```

可以抽取为：

```json
{
  "person": "张三",
  "company": "字节跳动",
  "position_type": "实习",
  "start_date": "2025-07",
  "location": "北京"
}
```

传统 NLP 通常是：

```text
文本 → 分词 → NER 模型 → 实体
```

结合 Agent 的方案则是：

```text
用户文本
  ↓
意图识别
  ↓
实体抽取
  ↓
Schema 结构化
  ↓
实体标准化
  ↓
实体消歧 / Entity Linking
  ↓
RAG 或 Tool 查询验证
  ↓
结果校验
  ↓
输出最终实体
```

核心思想不是让 Agent 取代 NER，而是让 Agent 负责整体任务编排：

```text
Agent：编排任务
LLM / NER：识别和抽取实体
Schema：约束输出结构
RAG：检索候选知识
Tool：查询外部 API 或数据库
MCP：标准化连接外部 Tool
Validation：校验结果
```

## 二、整体架构

```text
                         用户输入
                             │
                             ▼
                      ┌─────────────┐
                      │ Intent 识别  │
                      └──────┬──────┘
                             │
                             ▼
                      ┌─────────────┐
                      │ Entity Agent │
                      └──────┬──────┘
                             │
                    ┌────────┴────────┐
                    ▼                 ▼
              Entity Schema      Extraction Skill
              实体定义和字段       抽取规则和流程
                    │                 │
                    └────────┬────────┘
                             ▼
                         LLM / NER 抽取
                             │
                             ▼
                       JSON 结构化输出
                             │
                             ▼
                    ┌──────────────────┐
                    │ 标准化 / 实体消歧 │
                    └────────┬─────────┘
                             │
                    ┌────────┴────────┐
                    ▼                 ▼
                 RAG / 知识库       Tool / MCP
                 查询候选实体       外部 API / DB
                    │                 │
                    └────────┬────────┘
                             ▼
                         结果校验
                             │
                             ▼
                       最终结构化实体
```

这里各模块的职责是：

- LLM 负责理解语义和生成候选实体；
- NER 或规则模型负责稳定、明确场景下的识别；
- Skill 规定抽取流程；
- Schema 约束字段和数据类型；
- RAG 提供知识库候选；
- Tool 负责外部查询和验证；
- MCP 为外部 Tool 提供标准化接入；
- Validation 防止格式错误、业务错误和幻觉结果。

## 三、第一步：定义 Entity Schema

Schema 是整个方案的基础。不要只给模型一句：

```text
请从文本中抽取实体。
```

应该先定义实体类型、字段、数据类型、含义和缺省行为。

例如招聘场景：

```json
{
  "type": "object",
  "properties": {
    "person": {
      "type": ["string", "null"],
      "description": "人物姓名"
    },
    "company": {
      "type": ["string", "null"],
      "description": "公司名称"
    },
    "position": {
      "type": ["string", "null"],
      "description": "职位名称"
    },
    "location": {
      "type": ["string", "null"],
      "description": "工作地点"
    },
    "start_date": {
      "type": ["string", "null"],
      "description": "入职时间，格式为 YYYY-MM"
    }
  },
  "required": ["person", "company", "position", "location", "start_date"],
  "additionalProperties": false
}
```

然后要求模型：

```text
严格按照 Entity Schema 输出。
不存在的实体返回 null。
只提取文本中明确出现的信息，不要根据常识猜测。
时间统一标准化为 YYYY-MM。
```

最终结果可以是：

```json
{
  "person": "张三",
  "company": "字节跳动",
  "position": "算法实习生",
  "location": "北京",
  "start_date": "2025-07"
}
```

Schema 的价值在于：

- 约束输出字段；
- 限制数据类型；
- 统一不同请求的结果结构；
- 方便后续数据库入库和接口传输；
- 方便使用 JSON Schema 做自动校验。

## 四、第二步：用 Prompt 约束抽取行为

实体抽取 Prompt 可以设计为：

```text
你是一个实体抽取 Agent。

任务：
从用户输入中提取人物、公司、职位、地点和时间实体。

要求：
1. 只提取文本中明确出现的信息
2. 不允许主观推测
3. 对时间进行标准化
4. 公司名称尽可能使用文本中的完整名称
5. 无法确定的字段返回 null
6. 严格按照给定 JSON Schema 输出
7. 保留原始 mention，便于后续标准化和消歧
```

还可以加入 Few-shot 示例：

```text
输入：张三于 2025 年 7 月加入字节跳动，地点在北京。

输出：
{
  "person": "张三",
  "company": "字节跳动",
  "start_date": "2025-07",
  "location": "北京"
}
```

Few-shot 能够帮助模型稳定理解：

- 字段含义；
- 时间格式；
- 缺失字段的表达；
- 输出格式；
- 是否允许推断。

## 五、第三步：用 Skill 组织抽取流程

不要把所有规则都塞进一个很长的 Prompt。可以将实体抽取设计为一个可复用 Skill：

```text
entity_extraction_skill/
├── SKILL.md
├── schema/
│   ├── person.json
│   ├── company.json
│   └── product.json
├── prompts/
│   ├── extraction.md
│   ├── normalization.md
│   └── disambiguation.md
└── rules/
    ├── date.md
    └── company.md
```

Skill 可以规定以下流程：

```text
1. 判断用户意图
2. 确定实体类型
3. 加载对应 Schema
4. 执行实体抽取
5. 保留原始 mention
6. 实体标准化
7. 检索知识库
8. 实体消歧
9. 执行结果校验
10. 输出结构化结果
```

因此：

```text
Prompt 是具体指令；
Skill 是将多个 Prompt、Schema、规则和步骤组织起来的可复用能力。
```

在 XingClaw 中，Skill 文件会被加载并追加到系统提示词，同时可以注册运行时命令。相关实现位于 [`src/coding_agent/extensions/skills.py`](src/coding_agent/extensions/skills.py)。

## 六、第四步：实体标准化

抽取出的 mention 不一定是数据库中的标准名称。例如：

```text
字节
字节跳动
北京字节跳动科技有限公司
ByteDance
```

这些名称可能指向同一个实体。如果直接使用原始结果查询数据库，容易查询失败。

因此需要保留原始 mention，并生成标准化结果：

```text
原始实体 mention
        ↓
Normalization
        ↓
标准实体名称和 ID
```

例如：

```json
{
  "mention": "字节",
  "normalized_name": "北京字节跳动科技有限公司",
  "entity_type": "company"
}
```

标准化可以结合：

- 字典匹配；
- 别名表；
- 规则清洗；
- 向量检索；
- 知识库查询；
- 外部公司信息 API。

## 七、第五步：实体消歧和 Entity Linking

实体消歧比识别实体更进一步，目标是将 mention 映射到知识库中的唯一实体。

例如：

```text
苹果发布了新产品。
```

“苹果”可能是：

- Apple 公司；
- 苹果水果；
- 苹果园或其他组织名称。

一个典型流程是：

```text
Entity Mention
    ↓
Candidate Retrieval
    ↓
候选实体列表
    ↓
结合上下文进行排序
    ↓
LLM 或规则消歧
    ↓
Entity Linking
```

例如：

```text
苹果
  ↓
知识库搜索
  ↓
Apple Inc. / 苹果水果 / 苹果园
  ↓
结合“发布新产品”等上下文
  ↓
Apple Inc.
```

最终可以输出：

```json
{
  "mention": "苹果",
  "canonical_name": "Apple Inc.",
  "entity_id": "company_apple",
  "entity_type": "organization",
  "confidence": 0.96
}
```

## 八、RAG 在实体抽取中的作用

LLM 的通用知识无法替代企业内部知识库。例如：

```text
帮我查一下老王在腾讯的经历。
```

企业员工数据库中可能存在：

```text
王强、王明、王磊、王某
```

模型无法仅凭常识确定“老王”对应哪一个人。这时可以使用 RAG：

```text
实体 mention
    ↓
Embedding
    ↓
向量检索
    ↓
候选实体
    ↓
Rerank
    ↓
LLM 结合上下文消歧
```

RAG 适合解决：

- 内部人员和客户实体；
- 企业产品和项目名称；
- 内部简称和别名；
- 业务知识库中的特殊实体；
- 需要实时更新的实体信息。

## 九、Tool 在实体抽取中的作用

Tool 不是用来完全替代实体抽取，而是在模型无法仅凭文本确定实体时，提供查询和验证能力。

例如用户说：

```text
帮我查一下字节的公司信息。
```

模型先抽取：

```json
{
  "company": "字节"
}
```

发现名称不完整后，可以调用：

```text
search_company("字节")
```

Tool 返回：

```json
{
  "canonical_name": "北京字节跳动科技有限公司",
  "english_name": "ByteDance",
  "entity_id": "company_xxx"
}
```

Agent 再将结果合并为：

```json
{
  "mention": "字节",
  "canonical_name": "北京字节跳动科技有限公司",
  "entity_id": "company_xxx",
  "confidence": 0.96
}
```

在本项目中，Tool 通过统一的 `AgentTool` 协议描述和执行，相关定义位于 [`src/agent_core/types.py`](src/agent_core/types.py)。

## 十、MCP 在实体抽取中的作用

如果实体查询能力通过 MCP 暴露，结构可以是：

```text
Entity Agent
    │
    ▼
MCP Client
    │
    ▼
MCP Protocol
    │
    ├── Company MCP：企业信息查询
    ├── Database MCP：员工数据库查询
    └── Search MCP：外部搜索
```

MCP 不是实体抽取算法，也不负责决定实体是什么。它解决的是：

> Agent 如何以统一协议访问外部实体数据库、搜索服务和企业 API？

在本项目中，MCP Tool 会通过 [`src/coding_agent/mcp/bridge.py`](src/coding_agent/mcp/bridge.py) 转换为普通的 `AgentTool`，然后进入 Agent Loop。这样本地 Tool 和外部 MCP Tool 对 Agent 来说使用同一套调用方式。

## 十一、结果校验

LLM 可能出现格式错误、字段遗漏或幻觉，因此抽取后必须进行多层 Validation。

### 1. Schema Validation

```text
company 是不是字符串？
start_date 是不是合法日期？
confidence 是否在 0 到 1 之间？
必填字段是否存在？
是否出现未定义字段？
```

### 2. 业务规则校验

例如：

```text
开始日期不能晚于结束日期
公司实体必须存在于企业库
人员和公司必须满足任职关系
实习经历必须包含人员或时间中的至少一项
```

### 3. Entity Verification

通过 RAG、Tool 或数据库再次验证：

```text
LLM 抽取
    ↓
Schema Validation
    ↓
Business Rule Validation
    ↓
Entity Verification
```

## 十二、低置信度处理

Agent 方案相对于一次性抽取的优势，是可以根据置信度决定下一步动作。

例如：

```json
{
  "company": "苹果",
  "confidence": 0.51
}
```

如果置信度低于阈值 `0.7`，可以触发：

```text
低置信度
    ↓
┌───────────┴───────────┐
▼                       ▼
RAG 检索                 Tool 查询
└───────────┬───────────┘
            ▼
        再次判断
            │
      ┌─────┴─────┐
      ▼           ▼
  高置信度      仍然不确定
      ▼           ▼
    输出       询问用户
```

例如向用户澄清：

```text
你说的“苹果”是指苹果公司，还是水果？
```

这就是典型的 Agentic Entity Extraction：模型不是只输出一次结果，而是根据不确定性主动选择检索、查询或澄清。

## 十三、完整运行示例

用户输入：

```text
帮我找一下张三去年在字节的实习经历。
```

### Step 1：意图识别

```json
{
  "intent": "query_internship_experience"
}
```

### Step 2：实体抽取

```json
{
  "person": "张三",
  "company": "字节",
  "time": "去年",
  "experience_type": "实习"
}
```

### Step 3：实体标准化

```text
字节
  ↓
北京字节跳动科技有限公司
```

### Step 4：时间标准化

根据当前年份，将：

```text
去年 → 2025
```

### Step 5：实体链接

```text
张三
  ↓
员工知识库
  ↓
候选：张三 A、张三 B
```

### Step 6：消歧

结合以下信息排序：

- 公司；
- 经历类型；
- 时间；
- 地点；
- 用户上下文。

### Step 7：Tool 调用

```text
query_internship_experience(
    person_id="xxx",
    company_id="xxx",
    year=2025,
)
```

### Step 8：结果校验

```text
person ✓
company ✓
year ✓
experience_type ✓
```

### Step 9：最终结果

```json
{
  "person": {
    "name": "张三",
    "id": "person_xxx"
  },
  "company": {
    "name": "北京字节跳动科技有限公司",
    "id": "company_xxx"
  },
  "experience_type": "实习",
  "year": 2025
}
```

## 十四、传统 NER、LLM 与 Agent 方案对比

| 能力 | 传统 NER | 直接 LLM | Agent 实体抽取 |
| --- | --- | --- | --- |
| 基础实体识别 | 强 | 强 | 强 |
| 复杂语义理解 | 一般 | 强 | 强 |
| 结构化输出 | 需要额外处理 | 较强 | 强 |
| 实体标准化 | 弱 | 一般 | 强 |
| 实体消歧 | 弱 | 一般 | 强 |
| 外部知识查询 | 无或需要额外系统 | 有限 | 强 |
| Tool 调用 | 无 | 有限 | 强 |
| 复杂多步任务 | 弱 | 一般 | 强 |
| 可解释性 | 较高 | 一般 | 较高 |
| 工程复杂度 | 低 | 中 | 高 |

正确的架构观点不是：

```text
Agent 取代 NER
```

而是：

```text
Agent 负责整体编排
LLM / NER 负责实体识别
RAG 负责知识检索
Tool 负责外部查询
Schema 负责结构约束
Validation 负责结果校验
```

## 十五、推荐的混合落地方案

实际项目中可以采用“LLM + 规则 + NER + RAG + Agent”的混合架构：

```text
                         用户文本
                             │
                             ▼
                       Intent Classifier
                             │
                             ▼
                      Entity Extraction
                       ┌─────┴─────┐
                       ▼           ▼
                      LLM         NER / 规则
                       └─────┬─────┘
                             ▼
                        Schema 校验
                             │
                             ▼
                           标准化
                             │
                             ▼
                        Entity Linking
                             │
                    ┌────────┴────────┐
                    ▼                 ▼
                   RAG              Tool / MCP
                 知识库检索        外部 API / DB
                    │                 │
                    └────────┬────────┘
                             ▼
                            消歧
                             │
                             ▼
                         Confidence
                             │
                    ┌────────┴────────┐
                    ▼                 ▼
                 高置信度           低置信度
                    ▼                 ▼
                   输出           再检索 / 询问
```

适合使用传统 NER 或规则的场景：

- 实体边界明确；
- 格式固定；
- 追求低延迟和低成本；
- 领域标注数据充分；
- 结果需要高确定性。

适合使用 LLM 和 Agent 的场景：

- 语义复杂；
- 需要结合上下文；
- 实体存在歧义；
- 需要调用多个外部系统；
- 任务本身包含检索、验证和澄清。

## 十六、面试回答版本

如果让我设计一个实体抽取系统，我不会只使用传统 NER，而会结合 LLM 和 Agent 做结构化抽取。

首先根据业务定义 Entity Schema，明确实体类型、字段、数据类型和输出格式，然后通过 Prompt 或 Few-shot 约束 LLM 按 Schema 进行抽取。对于规则明确、格式稳定的实体，可以结合传统 NER 和规则模型，提高效率和确定性。

抽取完成后，我会增加实体标准化和 Entity Linking，把“字节”“ByteDance”等 mention 映射到统一实体。对于存在歧义的实体，通过 RAG 从知识库召回候选实体，再利用 LLM 结合上下文进行排序和消歧。

如果需要查询外部数据库或第三方 API，则通过 Tool 提供具体执行能力；如果希望不同 Agent 或不同模型统一访问这些能力，可以通过 MCP 标准化暴露 Tool。

最后增加 Schema Validation、业务规则校验、实体验证和置信度判断。对于低置信度结果，可以让 Agent 重新检索、调用 Tool 验证，或者向用户发起澄清。

所以整个方案实际上是一个 Agent 编排的实体抽取 Pipeline：

```text
LLM：负责理解和抽取
Skill：负责抽取流程
Schema：负责结构约束
规则 / NER：负责稳定场景识别
RAG：负责知识增强
Tool / MCP：负责外部信息获取
Validation：负责结果校验
Agent：负责根据结果决定下一步动作
```

