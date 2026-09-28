import httpx


CITY_COORDS = {
    "北京": (39.9042, 116.4074), "上海": (31.2304, 121.4737), "广州": (23.1291, 113.2644),
    "深圳": (22.5431, 114.0579), "杭州": (30.2741, 120.1551), "成都": (30.5728, 104.0668),
    "武汉": (30.5928, 114.3054), "南京": (32.0603, 118.7969), "西安": (34.3416, 108.9398),
}
WMO_CODES = {0: "晴", 1: "少云", 2: "多云", 3: "阴", 45: "雾", 48: "雾凇", 51: "毛毛雨", 61: "小雨", 63: "中雨", 65: "大雨", 71: "小雪", 73: "中雪", 75: "大雪", 80: "阵雨", 95: "雷暴"}


def get_weather(city: str) -> dict:
    if not city.strip():
        raise ValueError("请提供城市名称")
    city = city.strip()
    if city in CITY_COORDS:
        latitude, longitude = CITY_COORDS[city]
        city_name = city
    else:
        response = httpx.get("https://geocoding-api.open-meteo.com/v1/search", params={"name": city, "count": 1, "language": "zh", "format": "json"}, timeout=10)
        response.raise_for_status()
        results = response.json().get("results", [])
        if not results:
            return {"city": city, "error": "未找到该城市，请检查名称"}
        match = results[0]
        latitude, longitude, city_name = match["latitude"], match["longitude"], match.get("name", city)
    response = httpx.get("https://api.open-meteo.com/v1/forecast", params={"latitude": latitude, "longitude": longitude, "current": "temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m,wind_direction_10m", "timezone": "Asia/Shanghai"}, timeout=10)
    response.raise_for_status()
    current = response.json().get("current", {})
    return {"city": city_name, "condition": WMO_CODES.get(current.get("weather_code"), "未知"), "temperature": f"{current.get('temperature_2m', '?')}°C", "humidity": f"{current.get('relative_humidity_2m', '?')}%", "wind": f"{current.get('wind_speed_10m', '?')}km/h", "precipitation": f"{current.get('precipitation', 0)}mm", "update_time": current.get("time", "")}

