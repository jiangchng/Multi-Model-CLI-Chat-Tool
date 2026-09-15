"""
天气查询工具 —— 返回指定城市的模拟天气数据。

后续可替换为真实 API（如 OpenWeatherMap、和风天气）。
"""


def get_weather(city: str, unit: str = "celsius") -> dict:
    """获取指定城市的天气信息（当前为模拟数据）。

    Args:
        city: 城市名称，如 "北京"、"上海"
        unit: 温度单位，celsius（摄氏度）或 fahrenheit（华氏度）

    Returns:
        {"city": "...", "condition": "...", "temperature": "...", "humidity": "..."}
    """
    weather_data = {
        "北京": ("晴", "15-25°C", "湿度 30%"),
        "上海": ("多云", "20-28°C", "湿度 65%"),
        "深圳": ("阵雨", "25-30°C", "湿度 80%"),
        "杭州": ("阴", "18-24°C", "湿度 55%"),
    }

    info = weather_data.get(city, (None, None, None))

    return {
        "city": city,
        "condition": info[0] or "未知",
        "temperature": info[1] or "N/A",
        "humidity": info[2] or "N/A",
    }
