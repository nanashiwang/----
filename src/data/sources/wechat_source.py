"""
微信公众号消息接收（Webhook模式）

使用方式：
1. 在资讯源管理中配置微信类型源
2. 将 /api/wechat/callback 设置为微信服务器的回调地址
3. 收到的消息自动存入事件简报
"""
from typing import List, Dict

# 微信推送消息的内存缓存
_message_buffer: List[Dict] = []


def receive_message(msg: Dict):
    """接收微信推送消息"""
    _message_buffer.append({
        "title": msg.get("title", "微信推送"),
        "content": msg.get("content", ""),
        "source": "wechat",
    })


def flush_messages() -> List[Dict]:
    """获取并清空缓存的消息"""
    global _message_buffer
    messages = _message_buffer.copy()
    _message_buffer.clear()
    return messages
