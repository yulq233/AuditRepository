"""
共享工具函数
"""
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
import json


def generate_id() -> str:
    """生成唯一ID"""
    return str(uuid.uuid4())


def get_now() -> datetime:
    """获取当前时间"""
    return datetime.now()


def extract_json_from_llm_response(response: str) -> dict:
    """
    从LLM响应中提取JSON

    Args:
        response: LLM返回的响应文本

    Returns:
        解析后的JSON对象
    """
    json_str = response

    # 提取JSON代码块
    if "```json" in response:
        json_str = response.split("```json")[1].split("```")[0]
    elif "```" in response:
        json_str = response.split("```")[1].split("```")[0]

    return json.loads(json_str.strip())


def format_amount(amount: float) -> str:
    """
    格式化金额显示

    Args:
        amount: 金额

    Returns:
        格式化后的金额字符串
    """
    if not amount:
        return "0.00"
    return f"{amount:,.2f}"


def safe_json_loads(data: Any, default=None) -> Any:
    """
    安全的JSON解析

    Args:
        data: 要解析的数据
        default: 解析失败时的默认返回值

    Returns:
        解析后的对象或默认值
    """
    if isinstance(data, (dict, list)):
        return data
    if isinstance(data, str):
        try:
            return json.loads(data)
        except (json.JSONDecodeError, ValueError):
            return default if default is not None else {}
    return default