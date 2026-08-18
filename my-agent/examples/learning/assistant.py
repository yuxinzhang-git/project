from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from dotenv import load_dotenv
import os
print(f"当前系统的代理设置是: {os.environ.get('ALL_PROXY')}")

for key in list(os.environ.keys()):
    if 'proxy' in key.lower():
        del os.environ[key]

# 加载环境变量（这样可以读取 .env 文件中的 API 密钥）

load_dotenv()

# 创建 LLM 实例
# 这就是我们的 Agent 的"大脑"

llm = ChatOpenAI(
    model="deepseek-v4-flash",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
    temperature=0.7,
    timeout=30,
    max_retries=3,
)

# 创建一个没有工具的基础 Agent（我们待会再加工具）
agent = create_agent(
    model=llm,
    tools=[],  # 暂时没有工具
    # system_prompt="你是一个友好、有帮助的AI助手。用中文回答用户的问题。"
    system_prompt="你是一位创意十足的诗人。用中文用诗歌或富有意境的语言来回答问题。"
)

# # 现在让我们测试这个 Agent
# if __name__ == "__main__":
#     # 向 Agent 提问
#     user_question = "什么是人工智能？"
    
#     print(f"用户: {user_question}")
#     print("-" * 50)
    
#     # 调用 Agent（invoke 表示"调用"）
#     response = agent.invoke(
#         {
#             "messages": [{"role": "user", "content": user_question}]
#         }
#     )
    
#     # 获取 Agent 的最终回答
#     final_message = response["messages"][-1]
#     print(f"助手: {final_message.content}")




if __name__ == "__main__":
    user_question = "请给我三个关于Python的学习建议"
    
    print(f"用户: {user_question}")
    print("-" * 50)
    print("Agent 正在思考...\n")
    
    # 使用 stream 而不是 invoke，可以看到实时进展
    for event in agent.stream(
        {"messages": [{"role": "user", "content": user_question}]},
        stream_mode="values"
    ):
        # 从事件中获取最新的消息
        latest_message = event["messages"][-1]
        
        # 只打印AI助手的消息
        if latest_message.type == "ai":
            if latest_message.content:
                print(latest_message.content, end="", flush=True)
    
    print("\n")