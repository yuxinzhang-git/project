# Transformer 是什么

## 一句话解释

Transformer 是一种以 **Attention（注意力机制）** 为核心的深度学习架构。它能够在处理序列时动态关注不同 token 之间的关系，从而理解上下文并生成内容。

GPT、Claude、Gemini、LLaMA 等现代大语言模型（LLM）都以 Transformer 为基础。

## 1. 为什么需要 Transformer

Transformer 出现之前，自然语言处理主要使用 RNN、LSTM 和 GRU 等循环神经网络。它们按照序列顺序处理输入：

```text
A -> B -> C -> D
```

这种方式有两个主要问题：

1. **长距离依赖较难处理**：句子较长时，前面 token 的信息在多次循环后可能逐渐丢失。例如，模型需要判断“我昨天去了北京，那里天气很好”中的“那里”指的是“北京”。
2. **难以并行计算**：第 `n` 个 token 通常需要等待第 `n-1` 个 token 处理完成，GPU 利用率受到限制。

Transformer 可以同时处理一整个序列，并通过注意力机制直接建立远距离 token 之间的联系，因此更适合大规模训练。

## 2. 核心思想：Self-Attention

Self-Attention（自注意力）要解决的问题是：

> 当前 token 应该关注句子中的哪些其他 token？

例如：

> 小明喜欢吃苹果，因为它很好吃。

当模型处理“它”时，会计算“它”与其他 token 的相关程度。通常，“苹果”会获得较高的注意力权重，因此模型能够推断“它”大概率指代“苹果”。

注意力不是固定规则，而是模型根据上下文动态计算出来的权重。

## 3. Q、K、V 如何工作

每个 token 的表示会通过线性变换生成三个向量：

- **Query（Q）**：当前 token 想查找什么信息。
- **Key（K）**：每个 token 可以被怎样匹配。
- **Value（V）**：每个 token 实际提供的内容。

简化后的缩放点积注意力公式为：

$$
\operatorname{Attention}(Q,K,V)
= \operatorname{softmax}\left(\frac{QK^T}{\sqrt{d_k}}\right)V
$$

计算过程可以理解为：

1. 用 `Q · K` 计算 token 之间的相关性。
2. 除以 `sqrt(d_k)`，避免数值过大导致 Softmax 梯度不稳定。
3. 用 Softmax 将相关性转换成注意力权重。
4. 按权重对 `V` 加权求和，得到融合上下文后的新表示。

例如，对“它”这个 token，模型可能得到类似下面的权重：

```text
苹果  0.80
小明  0.10
喜欢  0.05
吃    0.05
```

实际权重由模型学习得到，并不一定等于这个示例中的数值。

## 4. Transformer 的整体结构

原始 Transformer 是 Encoder-Decoder 架构，整体流程如下：

```text
输入 token
    |
Token Embedding
    |
位置编码
    |
Encoder 堆叠
    |
Decoder 堆叠
    |
输出 token
```

其中：

- **Embedding**：将 token 转换为向量。
- **Positional Encoding / Position Embedding**：提供位置信息。因为注意力本身不具备天然的顺序概念，模型需要知道 token 的相对或绝对位置。
- **Encoder**：理解和编码输入序列。
- **Decoder**：根据输入和已生成内容逐步生成输出序列。

## 5. 一个 Transformer Block 的组成

一个典型的 Transformer Layer 通常包含：

```text
输入
  |
Multi-Head Attention
  |
残差连接 + LayerNorm
  |
Feed-Forward Network（FFN）
  |
残差连接 + LayerNorm
  |
输出
```

### 5.1 Multi-Head Attention

Multi-Head Attention 会使用多个注意力头，让模型从不同角度学习关系。例如不同的 head 可能分别关注：

- 实体之间的关系，如“苹果”和“公司”。
- 动作与对象的关系，如“发布”和“手机”。
- 代词指代、语法结构或局部上下文。

多个 head 的结果会被拼接并再次映射，形成最终的注意力输出。

### 5.2 Feed-Forward Network

Attention 主要负责 token 之间的信息交互，FFN 负责对每个位置的表示进行进一步的非线性变换和特征加工。可以粗略理解为：

```text
Attention：谁和谁有关？
FFN：这些关系应该如何加工和表达？
```

### 5.3 残差连接与 LayerNorm

- **残差连接**帮助深层网络保留原始信息，并改善梯度传播。
- **LayerNorm**稳定每一层的数值分布，使训练更容易收敛。

## 6. Transformer 的三种常见类型

### 6.1 Encoder-only

代表模型：BERT。

```text
输入 -> Encoder -> 表示或分类结果
```

特点是擅长理解输入，例如：

- 文本分类
- 情感分析
- 命名实体识别
- 信息抽取

### 6.2 Decoder-only

代表模型：GPT、LLaMA 等。

```text
已有 token -> Decoder -> 下一个 token
```

特点是擅长文本生成、对话和代码生成。现代主流大语言模型大多采用这种架构。

Decoder-only 模型使用 **Causal Mask（因果掩码）**，保证当前位置只能看到自己和前面的 token，不能提前看到未来答案。

### 6.3 Encoder-Decoder

代表模型：原始 Transformer、T5。

```text
输入文本 -> Encoder -> Decoder -> 输出文本
```

适合机器翻译、摘要和其他“输入到输出”的转换任务。

## 7. GPT 如何生成文本

GPT 的核心训练目标是预测下一个 token：

```text
输入：今天
预测：天气

输入：今天 天气
预测：很好
```

生成时通常循环执行：

1. 将当前上下文输入 Transformer。
2. 得到词表中每个 token 的概率分布。
3. 按照贪心、采样或其他解码策略选择下一个 token。
4. 把新 token 加入上下文，继续生成。

例如模型可能给出：

```text
很好  60%
不错  30%
恶劣  10%
```

## 8. Transformer 与大语言模型的关系

Transformer 是架构，大语言模型是基于该架构训练出来的具体模型。通常可以通过以下方式扩大模型能力：

```text
Transformer 层堆叠
        +
更多参数
        +
大规模预训练数据
        +
更强的训练和推理方法
        |
       LLM
```

模型在大量文本上学习“预测下一个 token”，逐渐掌握语言规律、事实知识、代码模式以及一定的推理能力。需要注意的是，Transformer 并不是通过显式数据库查询来理解世界，而是把训练数据中的模式编码在参数中。

## 9. Transformer 与 Agent 的关系

在 Agent 系统中，Transformer 通常是 LLM 的核心，用于：

- 理解用户意图。
- 结合上下文进行推理和规划。
- 生成自然语言回答。
- 决定是否调用工具，以及生成工具调用参数。

一个简化的 Agent 结构如下：

```text
Agent
 |
LLM（通常基于 Transformer）
 |
+----------+----------+
|          |          |
Prompt   Memory     Tool
上下文    状态记忆    执行动作
```

例如用户要求查询招聘信息时，模型可以生成工具调用：

```json
{
  "tool": "search_job",
  "query": "AI 岗位"
}
```

工具执行后，结果会再次返回给模型，由模型进行总结或决定下一步行动。因此，Transformer 负责理解和决策，Memory、Tool、MCP 等组件负责提供上下文和执行能力。

## 10. 面试回答版本

Transformer 是一种以 Self-Attention 为核心的深度学习架构，最早广泛应用于自然语言处理任务。它通过计算不同 token 之间的关联关系来动态捕获上下文信息，并且能够对序列进行并行计算，因此比传统 RNN 更适合大规模训练。

Transformer 的典型组成包括 Embedding、位置编码、多头注意力、Feed-Forward Network、残差连接和 LayerNorm。当前主流大语言模型大多采用 Decoder-only Transformer，通过预测下一个 token 进行预训练，从而学习语言规律、知识和一定的推理模式。

在 Agent 系统中，Transformer 作为 LLM 的核心，负责理解任务、推理、规划和生成工具调用决策，而 Memory、Tool、MCP 等组件负责提供信息和执行操作。

## 11. 常见后续问题

- Attention 为什么有效？
- Multi-Head Attention 为什么需要多个 head？
- GPT 为什么主要使用 Decoder，而不是 Encoder？
- Transformer 如何处理长上下文？
- LLM 为什么会产生幻觉？
- RAG 为什么能够缓解幻觉？

## 12. Agent 中的 Encoder 和 Decoder

在 Agent 领域，Encoder 和 Decoder 容易与 Transformer 内部的 Encoder/Decoder 混淆。

如果从 Agent 系统架构理解：

```text
Encoder：理解外部世界
LLM：    推理和决策
Decoder：影响外部世界
```

需要注意，这里的 Encoder/Decoder 通常是**系统层面的功能角色**，不一定对应 Transformer 模型中的具体模块。

### 12.1 Agent 的整体流程

```text
文本 / 图片 / 网页 / 文件 / 数据库
                |
             Encoder
                |
          上下文或内部状态
                |
          LLM 推理与规划
                |
             Decoder
                |
      Tool 调用 / API / 回复 / 行动
                |
              外部世界
```

这对应 Agent 的感知、决策、执行闭环。

### 12.2 Encoder 在 Agent 中做什么

Encoder 负责把外部输入转换成模型能够理解的向量表示、结构化信息或上下文。输入可能包括：

- 用户文本
- 图片和视频
- 网页 DOM 或截图
- 文件和 PDF
- 数据库结果
- 工具返回结果

例如，用户输入：

> 帮我找一下北京地区的 AI 实习岗位

Encoder 可以将文字切分为 token，并转换为 embedding 或上下文信息，使模型识别出：

```text
任务：寻找岗位
地点：北京
岗位：AI 实习
意图：搜索
```

#### Browser Agent 示例

浏览器当前页面可能包含 HTML：

```html
<button>登录</button>
```

网页 Encoder 可以解析 DOM、页面结构和可交互元素，形成类似这样的状态：

```json
{
  "page": "login",
  "elements": [
    {
      "type": "button",
      "name": "登录"
    }
  ]
}
```

LLM 根据这个状态就能判断下一步可能是点击“登录”按钮。

#### RAG 示例

在 RAG 中，Embedding 模型也可以看作一种 Encoder：

```text
文档 -> Embedding -> 向量 -> Vector Database
查询 -> Embedding -> 向量搜索 -> 相关文档
```

它把文档和查询转换到同一个向量空间，以便检索语义相关的内容。

Agent 中常见的 Encoder 包括：

- Tokenizer 和文本 Embedding 模型
- 图像或视频 Encoder
- OCR 模型
- 网页 DOM 解析器
- 多模态模型的视觉 Encoder
- 文件解析器和数据库适配器

### 12.3 Decoder 在 Agent 中做什么

Decoder 负责将 LLM 的内部决策转换成外部可以使用或执行的输出，例如：

- 自然语言回复
- Tool Calling 及其参数
- API 请求
- 浏览器操作
- 机器人移动、抓取等动作

例如用户说：

> 帮我查北京的天气

LLM 做出“需要调用天气工具”的决策，Decoder 将其转换为结构化调用：

```json
{
  "tool": "weather",
  "arguments": {
    "city": "北京"
  }
}
```

如果是 Browser Agent，Decoder 可能生成：

```text
browser.type(username)
browser.click(login)
```

随后由 Playwright 等工具执行，并将环境反馈再次交给 Encoder 和 LLM，形成循环。

### 12.4 Encoder-LLM-Decoder 架构

Agent 中常见的系统结构可以概括为：

```text
用户任务 / 环境状态
        |
      Encoder
        |
    Context State
        |
  LLM：理解、推理、规划
        |
   Action Decision
        |
      Decoder
        |
Tool / API / 自然语言回复
        |
     环境反馈
        |
      Encoder
```

以 Browser Agent 为例：

```text
用户任务
  -> 读取 DOM、截图和浏览器状态
  -> Encoder 形成页面表示
  -> LLM 规划下一步
  -> Decoder 生成点击、输入等动作
  -> Playwright 执行
  -> 获取新页面状态
  -> 循环
```

### 12.5 与 Transformer Encoder/Decoder 的区别

| 对比项 | Transformer 中的 Encoder/Decoder | Agent 中的 Encoder/Decoder |
| --- | --- | --- |
| 所属层次 | 模型内部结构 | 系统架构中的功能角色 |
| Encoder 输入 | token 序列 | 文本、图片、网页、文件、工具结果等 |
| Encoder 输出 | 隐藏状态表示 | embedding、结构化状态或上下文 |
| Decoder 输出 | 生成 token | 回复、工具调用、API 请求或环境动作 |
| 是否必须成对出现 | 取决于模型架构 | 通常可以由多个外部组件共同实现 |

Transformer 中，Encoder 负责编码输入，Decoder 负责生成输出；原始 Transformer 就是 Encoder-Decoder 结构。

而在 Agent 中，Encoder 可能是 OCR、Embedding 模型、DOM 解析器或视觉模型，Decoder 可能是 Tool Calling、API 适配器、浏览器控制器或机器人动作执行器。

### 12.6 GPT 为什么没有传统 Encoder

GPT、Claude、LLaMA 等主流大语言模型主要采用 **Decoder-only Transformer**：

```text
输入 token -> Decoder Block 堆叠 -> 预测下一个 token
```

它们没有原始 Transformer 中独立的 Encoder，但 Agent 系统仍然可以在模型外部添加 Encoder 和 Decoder：

```text
网页 -> 网页 Encoder -> GPT -> Tool Decoder -> 浏览器操作
```

因此：

> Agent 中的 Encoder/Decoder 不等于 Transformer 中的 Encoder/Decoder。

前者描述系统的感知和执行职责，后者描述神经网络的具体组织方式。

### 12.7 面试回答版本

在 Agent 系统中，Encoder 主要负责将外部环境信息转换成模型可理解的表示，例如用户输入、网页 DOM、图片、文件内容或 RAG 检索结果，可以通过 Embedding、解析器或多模态模型形成上下文状态。Decoder 负责将 LLM 的决策转换成具体输出，例如自然语言回复、Tool Calling 参数、API 请求或机器人动作。

它们共同构成 Agent 的感知和执行闭环：Encoder 负责理解环境，LLM 负责推理和决策，Decoder 负责执行动作。需要区分的是，Agent 中的 Encoder/Decoder 是系统层面的概念，而 Transformer 中的 Encoder/Decoder 是模型结构概念。即使主流 LLM 采用 Decoder-only Transformer，Agent 仍然可以通过外部 Encoder 和 Decoder 实现多模态感知与工具执行。

### 12.8 相关延伸问题

- Agent 和普通 LLM 调用有什么区别？
- Agent 如何实现感知、决策、执行闭环？
- ReAct 中的 Thought、Action、Observation 分别对应什么？
- Browser Agent 如何理解网页状态？
- 多模态 Agent 中的视觉 Encoder 是什么？
