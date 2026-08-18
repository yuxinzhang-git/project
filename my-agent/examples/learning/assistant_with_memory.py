from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain.messages import HumanMessage, AIMessage
from dotenv import load_dotenv
import os

for key in list(os.environ.keys()):
    if 'proxy' in key.lower():
        del os.environ[key]

load_dotenv()

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
    tools=[],  # 暂时不用工具，专注于记忆
    system_prompt="""你是一个友好的AI助手。
    
你应该：
1. 认真听用户说的话
2. 记住用户说过的信息
3. 在后续对话中引用之前的信息
4. 用中文回答"""
)

def multi_turn_conversation():
    """模拟多轮对话"""
    
    # 这是我们的对话历史（短期记忆）
    messages = []
    
    while True:
        # 获取用户输入
        user_input = input("\n你: ")
        
        if user_input.lower() in ["退出", "exit", "quit"]:
            print("再见！")
            break
        
        # 添加用户消息到历史
        messages.append({"role": "user", "content": user_input})
        
        # 调用Agent，传入完整的对话历史
        response = agent.invoke(
            {"messages": messages}  # ← 关键：传入所有之前的消息
        )
        
        # 获取Agent的最后回答
        final_message = response["messages"][-1]
        agent_response = final_message.content
        
        # 添加Agent的回答到历史
        messages.append({"role": "assistant", "content": agent_response})
        
        # 显示Agent的回答
        print(f"助手: {agent_response}")
        
        # 显示当前对话历史（调试用）
        print(f"\n[对话历史长度: {len(messages)} 条消息]")


if __name__ == "__main__":
    print("=" * 60)
    print("欢迎来到 AI 助手！")
    print("我会记住我们谈过的内容。输入'退出'结束对话。")
    print("=" * 60)
    
    multi_turn_conversation()
