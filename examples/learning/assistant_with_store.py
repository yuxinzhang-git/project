from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain.tools import tool, ToolRuntime
from langgraph.store.memory import InMemoryStore
from dataclasses import dataclass
from dotenv import load_dotenv
import os

for key in list(os.environ.keys()):
    if 'proxy' in key.lower():
        del os.environ[key]

load_dotenv()

# 创建存储库
store = InMemoryStore()

# 定义上下文（用于识别用户）
@dataclass
class Context:
    user_id: str

# 创建工具：保存用户信息（长期记忆）
@tool
def save_user_preference(key: str, value: str, runtime: ToolRuntime) -> str:
    """保存用户的偏好或信息。
    
    这些信息会被永久保存，即使重启也不会忘记。
    例如：保存用户的名字、城市、职业等。
    
    Args:
        key: 信息类型（如 "name"、"city"、"profession"）
        value: 信息内容
    """
    user_id = runtime.context.user_id
    namespace = ("users", user_id)
    
    # 获取已有的用户信息
    existing = store.get(namespace, "profile")
    profile = existing.value if existing else {}
    
    # 更新信息
    profile[key] = value
    
    # 保存回存储库
    store.put(namespace, "profile", profile)
    
    return f"✅ 已保存：{key} = {value}"


# 创建工具：获取用户信息（长期记忆）
@tool
def get_user_preferences(runtime: ToolRuntime) -> str:
    """获取用户保存的所有信息。
    
    查看之前保存的用户偏好和信息。
    """
    user_id = runtime.context.user_id
    namespace = ("users", user_id)
    
    stored = store.get(namespace, "profile")
    
    if not stored:
        return "暂无保存的用户信息"
    
    profile = stored.value
    result = "📋 你的保存信息：\n"
    for key, value in profile.items():
        result += f"  • {key}: {value}\n"
    
    return result


llm = ChatOpenAI(
    model="deepseek-v4-flash",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
    temperature=0.7,
    timeout=30,
    max_retries=3,
)

agent = create_agent(
    model=llm,
    tools=[save_user_preference, get_user_preferences],
    store=store,  # ← 传入存储库
    context_schema=Context,
    system_prompt="""你是一个有长期记忆的AI助手。

当用户告诉你关于他们的信息时（如名字、城市、职业等），
你应该使用 save_user_preference 工具来保存这些信息。

这样即使对话结束，下次用户回来时，你也能记住他们。

你可以使用：
- save_user_preference: 保存用户信息
- get_user_preferences: 查看已保存的信息

用中文回答。"""
)


def long_term_memory_demo():
    """演示长期记忆"""
    
    # 假设用户ID是 "user_alice"
    user_id = "user_alice"
    
    print("\n" + "="*70)
    print("🧠 第一次对话（Session 1）")
    print("="*70)
    
    messages = []
    
    # 第一轮：用户介绍自己
    user_msg = "我叫Alice，我是一个数据科学家，我住在上海"
    print(f"\n👤 用户: {user_msg}")
    
    messages.append({"role": "user", "content": user_msg})
    
    response = agent.invoke(
        {"messages": messages},
        context=Context(user_id=user_id)
    )
    
    agent_msg = response["messages"][-1].content
    print(f"🤖 助手: {agent_msg}")
    
    messages.append({"role": "assistant", "content": agent_msg})
    
    # 验证：检查存储库中是否保存了信息
    print("\n✅ 信息已保存到长期记忆")
    
    print("\n" + "="*70)
    print("🧠 第二次对话（Session 2）— 一个小时后")
    print("="*70)
    
    messages = []  # 新的对话历史（模拟新的会话）
    
    # 用户回来了，但没有重新介绍自己
    user_msg2 = "你还记得我吗？"
    print(f"\n👤 用户: {user_msg2}")
    
    messages.append({"role": "user", "content": user_msg2})
    
    # 先让Agent查看保存的信息
    user_msg3 = "查看我保存的信息"
    print(f"👤 用户: {user_msg3}")
    
    messages.append({"role": "user", "content": user_msg3})
    
    response = agent.invoke(
        {"messages": messages},
        context=Context(user_id=user_id)
    )
    
    # 显示所有消息
    for msg in response["messages"]:
        if msg.type == "ai":
            print(f"🤖 助手: {msg.content}")
        elif msg.type == "tool":
            print(f"⚙️  工具结果: {msg.content}")


if __name__ == "__main__":
    long_term_memory_demo()
