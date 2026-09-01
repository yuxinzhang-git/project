import httpx


def get_billing(api_key: str) -> dict:
    masked_key = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "未配置"
    try:
        response = httpx.get("https://api.deepseek.com/user/balance", headers={"Authorization": f"Bearer {api_key}"}, timeout=10)
        balance = response.json() if response.status_code == 200 else {"error": f"查询失败 (HTTP {response.status_code})"}
    except Exception as exc:
        balance = {"error": f"查询失败: {exc}"}
    return {"api_name": "DeepSeek (deepseek-v4-flash)", "api_key": masked_key, "base_url": "https://api.deepseek.com", "balance": balance}

