# XingClaw 独立版使用说明

## 最少需要配置什么

Windows 用户编辑项目目录中的 .env.ps1。第一次运行 run_cli.bat 时，如果该文件不存在，脚本会从 .env.ps1.example 自动创建。

至少填写一种模型的 Key，并让 provider/model-id 匹配：

| provider | model-id 示例 | API Key 环境变量 | 适用接口 |
|---|---|---|---|
| anthropic | claude-sonnet-4-5 | ANTHROPIC_API_KEY | Anthropic 官方 |
| anthropic | glm-4.7 | ANTHROPIC_API_KEY | 智谱 Anthropic 兼容接口 |
| openai-standard | gpt-4o-mini | OPENAI_API_KEY | OpenAI |
| openai-standard | deepseek-v4-pro | OPENAI_API_KEY | DeepSeek OpenAI 兼容接口 |

例如使用 OpenAI：

    $env:OPENAI_API_KEY = "sk-你的真实密钥"
    $env:XINGCLAW_PROVIDER = "openai-standard"
    $env:XINGCLAW_MODEL_ID = "gpt-4o-mini"

例如使用智谱 GLM：

    $env:ANTHROPIC_API_KEY = "你的智谱密钥"
    $env:XINGCLAW_PROVIDER = "anthropic"
    $env:XINGCLAW_MODEL_ID = "glm-4.7"

不要把真实 Key 提交到 Git 或发给他人。 .env.ps1 已被 .gitignore 忽略。

## CLI 运行

双击 run_cli.bat，或运行：

    .\run_cli.bat

首次运行会创建 .venv 并安装依赖。网络不可用时，需要先准备 Python 3.10+ 和依赖缓存。

## 飞书运行

除模型 Key 外，还需在 .env.ps1 填写：

    $env:FEISHU_APP_ID = "cli_你的应用ID"
    $env:FEISHU_APP_SECRET = "你的应用Secret"
    $env:FEISHU_VERIFY_TOKEN = "可选的事件校验Token"

然后双击 run_feishu.bat。它使用飞书长连接模式，不需要先配置公网 Webhook 地址；飞书应用仍需在开放平台开通机器人和相应事件权限。

## 快捷方式

双击 make_shortcuts.bat，会在独立项目目录和 Windows 桌面创建 XingClaw-CLI、XingClaw-Feishu 两个快捷方式。

## 数据位置和安全边界

传给 Agent 的工作区默认是独立项目目录。会话、IM 路由和记忆会写到该目录下的 .xingclaw。默认会启用读写文件和命令工具，并拦截危险命令；处理重要代码前建议先使用 CLI 的 --read-only 模式或备份工作区。
