import asyncio
import logging
import re
import subprocess
import sys
from typing import Optional

from .state import state

logger = logging.getLogger('pixiv-mcp-server')

def check_ffmpeg() -> bool:
    """检测系统是否安装了FFmpeg"""
    try:
        creationflags = 0
        if sys.platform == 'win32':
            creationflags = subprocess.CREATE_NO_WINDOW
        
        subprocess.run(['ffmpeg', '-version'], 
                     capture_output=True, check=True, creationflags=creationflags)
        logger.info("FFmpeg 已检测 - GIF 转换功能可用")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.warning("未找到 FFmpeg - GIF 转换功能已禁用")
        return False

async def refresh_token_if_needed() -> bool:
    """尝试刷新token，返回是否成功"""
    if not state.refresh_token:
        logger.error("无法刷新token：未找到refresh_token")
        return False
    
    try:
        logger.info("检测到token失效，正在尝试刷新...")
        result = await asyncio.to_thread(state.api.auth, refresh_token=state.refresh_token)
        
        if result and 'access_token' in result:
            state.is_authenticated = True
            logger.info("Token刷新成功")
            return True
        else:
            logger.error(f"Token刷新失败: {result}")
            return False
    except Exception as e:
        logger.error(f"Token刷新过程中发生异常: {e}")
        return False

def handle_api_error(response: dict) -> Optional[str]:
    """处理来自 Pixiv API 的错误响应并格式化"""
    if not response:
        return "API 响应为空。"
    if 'error' in response:
        error_details = response['error']
        msg = error_details.get('message', '未知错误')
        reason = error_details.get('reason', '')
        
        # 检查是否为token相关错误
        if 'invalid_grant' in msg.lower() or 'oauth' in msg.lower() or 'unauthorized' in msg.lower():
            return f"Token已失效: {msg} - {reason}。请使用refresh_token工具刷新或重新获取token。".strip()
        
        return f"Pixiv API 错误: {msg} - {reason}".strip()
    return None

async def handle_api_error_with_retry(response: dict, retry_func=None, *args, **kwargs) -> tuple[Optional[str], Optional[dict]]:
    """处理API错误并在token失效时自动重试
    
    Args:
        response: API响应
        retry_func: 重试的函数
        *args, **kwargs: 重试函数的参数
    
    Returns:
        (error_message, new_response): 错误信息和新的响应（如果重试成功）
    """
    if not response:
        return "API 响应为空。", None
        
    if 'error' in response:
        error_details = response['error']
        msg = error_details.get('message', '未知错误')
        reason = error_details.get('reason', '')
        
        # 检查是否为token相关错误
        if ('invalid_grant' in msg.lower() or 'oauth' in msg.lower() or 'unauthorized' in msg.lower()) and retry_func:
            logger.warning(f"检测到token错误: {msg}，尝试刷新token并重试...")
            
            # 尝试刷新token
            if await refresh_token_if_needed():
                try:
                    # 重试API调用
                    new_response = await asyncio.to_thread(retry_func, *args, **kwargs)
                    if new_response and 'error' not in new_response:
                        logger.info("Token刷新后重试成功")
                        return None, new_response
                    else:
                        return f"重试后仍然失败: {new_response.get('error', {}).get('message', '未知错误')}", None
                except Exception as e:
                    return f"重试过程中发生异常: {e}", None
            else:
                return f"Token刷新失败: {msg} - {reason}。请手动重新获取token。".strip(), None
        
        return f"Pixiv API 错误: {msg} - {reason}".strip(), None
    
    return None, None

def _sanitize_filename(name: str) -> str:
    """移除文件名中的非法字符"""
    return re.sub(r'[\\/*?:"<>|]', '_', name)

def _generate_filename(illust: dict, page_num: int = 0) -> str:
    """根据模板生成文件名"""
    author = _sanitize_filename(illust.get('user', {}).get('name', 'UnknownAuthor'))
    title = _sanitize_filename(illust.get('title', 'Untitled'))
    illust_id = illust.get('id', 0)
    
    base_name = state.filename_template.format(
        author=author,
        title=title,
        id=illust_id
    )
    
    if illust.get('page_count', 1) > 1:
        return f"{base_name}_p{page_num}"
    return base_name

def format_illust_summary(illust: dict) -> str:
    tags = ", ".join([tag.get('name', '') for tag in illust.get('tags', [])[:5]])
    return (
        f"ID: {illust.get('id')} - \"{illust.get('title')}\"\n"
        f"  作者: {illust.get('user', {}).get('name')} (ID: {illust.get('user', {}).get('id')})\n"
        f"  类型: {illust.get('type')}\n"
        f"  标签: {tags}\n"
        f"  收藏数: {illust.get('total_bookmarks', 0)}, 浏览数: {illust.get('total_view', 0)}"
    )

def format_user_summary(user_preview: dict) -> str:
    user = user_preview.get('user', {})
    return (
        f"用户ID: {user.get('id')} - {user.get('name')} (@{user.get('account')})\n"
        f"  关注状态: {'已关注' if user.get('is_followed') else '未关注'}\n"
        f"  简介: {user.get('comment', '无')}"
    )
