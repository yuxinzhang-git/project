# Project Workspace

This repository is a workspace that contains two related but independent AI projects.

## Projects

| Path | Purpose | Best entry point |
| --- | --- | --- |
| `XingClaw-standalone/` | A standalone Python AI coding assistant framework with a unified LLM API layer, agent loop, CLI, and Feishu IM bridge. | `XingClaw-standalone/START_HERE.md` |
| `my-agent/` | A local FastAPI assistant application with web pages, deterministic command parsing, runtime skills, and browser automation adapters for sites such as Bilibili, Taobao, and Xianyu. | `my-agent/README.md` |

## Which One Should I Open?

Start with `XingClaw-standalone/` if you want to study or run the reusable agent framework.

Start with `my-agent/` if you want to run the personal web assistant and browser automation app.

The two directories do not share one package manager or one runtime. Install and run each project from its own directory.

## Repository Hygiene

Local virtual environments, browser profiles, logs, generated sessions, editor settings, and secret files are intentionally ignored. Do not commit real API keys, browser state, runtime logs, or generated `.xingclaw` session data.
