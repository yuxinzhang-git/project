from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from dotenv import load_dotenv
import os

# 导入我们刚创建的工具
from tools import calculator, get_user_age, get_weather, calculate_loan_interest

for key in list(os.environ.keys()):
    if 'proxy' in key.lower():
        del os.environ[key]

load_dotenv()

# 创建 LLM
# llm = ChatOpenAI(
#     model="gpt-4o-mini",
#     temperature=0.7
# )

llm = ChatOpenAI(
    model="deepseek-v4-flash",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
    temperature=0.7,
    timeout=30,
    max_retries=3,
)

# 创建 Agent，这次包含工具！
agent = create_agent(
    model=llm,
    tools=[calculator, get_user_age, get_weather, calculate_loan_interest],  # ← 关键：传入工具列表
    system_prompt="""你是一个有用的AI助手。
    
你可以使用以下工具来帮助用户：
- calculator：执行数学计算
- get_user_age：查询用户的年龄
- get_weather：查询天气信息

当用户提问时，判断是否需要使用工具来获得更准确的答案。
如果需要，就调用相应的工具。最后用中文回答用户的问题。"""
)

if __name__ == "__main__":
    # 让我们测试不同的场景
    
    test_questions = [
        "帮我计算 123 * 456 等于多少?",
        "Alice 今年多少岁？",
        "深圳的天气如何？",
        "如果我贷款 100000 元，年利率 5%，期限 3 年，需要还多少钱？",
        "帮我计算 (100 + 50) * 2，然后告诉我结果"
    ]
    
    for question in test_questions:
        print(f"\n📝 用户: {question}")
        print("-" * 60)
        
        response = agent.invoke(
            {"messages": [{"role": "user", "content": question}]}
        )
        
        # 获取最后一条消息（Agent的最终回答）
        final_message = response["messages"][-1]
        print(f"🤖 助手: {final_message.content}")
