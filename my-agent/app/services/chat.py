import json
import os

from app.config import settings  # Load .env before reading the API key.

from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

from app.tools import calculator, calculate_loan_interest


class ChatService:
    def __init__(self) -> None:
        api_key = os.getenv("DEEPSEEK_API_KEY", "")
        self.agent = None
        if api_key:
            self.agent = create_agent(
                model=ChatOpenAI(model="deepseek-v4-flash", api_key=api_key, base_url="https://api.deepseek.com", temperature=0.3, timeout=30, max_retries=3),
                tools=[calculator, calculate_loan_interest],
                system_prompt="你是专业的数学计算助手。优先使用计算工具，并用中文清晰说明结果。",
            )

    def reply(self, message: str, history: list[dict] | None) -> dict:
        if self.agent is None:
            raise RuntimeError("DEEPSEEK_API_KEY is not configured")
        messages = list(history or []) + [{"role": "user", "content": message}]
        response = self.agent.invoke({"messages": messages})
        tool_calls, final_reply = [], ""
        for item in response["messages"]:
            if item.type == "ai" and item.content:
                final_reply = item.content
            elif item.type == "tool":
                tool_calls.append({"tool": item.name, "input": json.dumps(getattr(item, "additional_kwargs", {}), ensure_ascii=False), "output": item.content})
        return {"reply": final_reply, "tool_calls": tool_calls}
