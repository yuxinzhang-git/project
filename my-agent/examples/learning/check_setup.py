import os
from dotenv import load_dotenv

# 加载 .env 文件   注册环境变量
load_dotenv()

print("=" * 50)
print("环境检查")
print("=" * 50)

# 检查 Python 版本
import sys
print(f"✅ Python 版本: {sys.version.split()[0]}")

# 检查 langchain
try:
    import langchain
    print(f"✅ LangChain 已安装")
except ImportError:
    print("❌ LangChain 未安装")

# 检查 langgraph
try:
    import langgraph
    print(f"✅ LangGraph 已安装")
except ImportError:
    print("❌ LangGraph 未安装")

# 检查 API 密钥
api_key = os.getenv("OPENAI_API_KEY")
if api_key:
    print(f"✅ OPENAI_API_KEY 已配置")
else:
    print("❌ OPENAI_API_KEY 未配置，请检查 .env 文件")

print("=" * 50)
