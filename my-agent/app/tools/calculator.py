from langchain.tools import tool

@tool
def calculator(expression: str) -> str:
    """执行数学计算。
    
    使用此工具来解决任何数学问题，例如加法、减法、乘法、除法等。
    支持基本的数学表达式如 "2+2"、"100*5"、"1000/4" 等。
    
    Args:
        expression: 数学表达式，例如 "2+2" 或 "sqrt(16)"
    
    Returns:
        计算结果
    """
    try:
        # 在真实应用中，你可能想限制支持的函数（比如只允许 math 模块的函数）
        # 这里为了简单起见，我们使用 eval（注意：生产环境中要小心安全问题）
        result = eval(expression)
        return f"{expression} = {result}"
    except Exception as e:
        return f"计算错误：{str(e)}"


@tool
def get_user_age(name: str) -> str:
    """根据姓名获取用户的年龄。
    
    使用此工具当用户提到特定的人名时，查询这个人的年龄信息。
    
    Args:
        name: 用户的姓名
    
    Returns:
        用户的年龄或 "未找到" 信息
    """
    # 在真实应用中，这里会查询数据库
    users = {
        "Alice": 28,
        "Bob": 35,
        "Charlie": 42,
        "Diana": 31
    }
    
    age = users.get(name, None)
    if age:
        return f"{name} 的年龄是 {age} 岁"
    else:
        return f"没有找到 {name} 的年龄信息"


@tool
def get_weather(city: str) -> str:
    """获取指定城市的天气信息。
    
    使用此工具当用户询问任何关于天气的问题时。
    
    Args:
        city: 城市名称
    
    Returns:
        天气信息（温度、条件等）
    """
    # 在真实应用中，这里会调用真实的天气API（如 OpenWeather）
    weather_data = {
        "北京": "晴，25°C，东风2级",
        "上海": "多云，23°C，无风",
        "深圳": "阴，28°C，南风3级",
        "成都": "小雨，20°C，西南风4级"
    }
    
    result = weather_data.get(city, f"暂无 {city} 的天气数据")
    return f"{city}：{result}"


@tool
def calculate_loan_interest(principal: float, annual_rate: float, years: int) -> str:
    """计算贷款的利息和还款总额。
    
    使用此工具来计算贷款相关的数据。
    
    Args:
        principal: 贷款本金（元）
        annual_rate: 年利率（百分比，例如 5 表示 5%）
        years: 贷款年数
    
    Returns:
        利息和还款总额信息
    """
    # 简单的利息计算（实际应用中可能更复杂）
    total_interest = principal * (annual_rate / 100) * years
    total_amount = principal + total_interest
    monthly_payment = total_amount / (years * 12)
    
    return f"""
贷款信息：
- 本金：¥{principal:,.2f}
- 年利率：{annual_rate}%
- 贷款年数：{years}年
- 总利息：¥{total_interest:,.2f}
- 还款总额：¥{total_amount:,.2f}
- 月还款额：¥{monthly_payment:,.2f}
"""
