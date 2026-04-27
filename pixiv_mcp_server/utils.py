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

def handle_api_error(response, description: str = "") -> Optional[str]:
    """处理来自 Pixiv API 的错误响应并格式化"""
    # Handle Exception objects passed from server/main.py
    if isinstance(response, Exception):
        return f"操作失败({description}): {response}" if description else f"操作失败: {response}"
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

async def handle_api_error_with_retry(api_call, description: str = "", *args, **kwargs) -> Optional[dict]:
    """执行API调用并自动处理token过期重试（新约定：传入可调用对象）

    Args:
        api_call: 返回API响应的可调用对象（如 lambda）
        description: 操作描述（用于日志）

    Returns:
        API响应dict，或None表示无法恢复的错误
    """
    import asyncio as _asyncio
    try:
        response = await api_call()
    except Exception as e:
        logger.error(f"API调用异常({description}): {e}")
        return None

    if not response:
        logger.warning(f"API响应为空({description})")
        return None

    if 'error' in response:
        error_details = response['error']
        msg = error_details.get('message', '未知错误')
        reason = error_details.get('reason', '')

        # Token相关错误，尝试刷新后重试
        if ('invalid_grant' in msg.lower() or 'oauth' in msg.lower() or 'unauthorized' in msg.lower()):
            logger.warning(f"检测到token错误: {msg}，尝试刷新token并重试...")
            if await refresh_token_if_needed():
                try:
                    new_response = await api_call()
                    if new_response and 'error' not in new_response:
                        logger.info("Token刷新后重试成功")
                        return new_response
                except Exception as e:
                    logger.error(f"重试异常: {e}")

        logger.error(f"API返回非token错误({description}): msg={msg}, reason={reason}, 完整响应={str(response)[:500]}")
        return None

    return response

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

def _generate_path_from_template(illust: dict) -> str:
    """从 DOWNLOAD_PATH_TEMPLATE 生成相对于 download_path 的子目录路径"""
    template = state.download_path_template.strip()
    if not template:
        return ''

    author = _sanitize_filename(illust.get('user', {}).get('name', 'UnknownAuthor'))
    title = _sanitize_filename(illust.get('title', 'Untitled'))
    illust_id = illust.get('id', 0)
    illust_type = illust.get('type', 'illust')

    tags = illust.get('tags', [])
    if tags and len(tags) > 0:
        tag = _sanitize_filename(tags[0].get('name', 'untagged'))
    else:
        tag = 'untagged'

    raw_path = template.format(
        author=author,
        title=title,
        id=illust_id,
        type=illust_type,
        tag=tag,
    )

    raw_path = raw_path.strip('/')
    while '//' in raw_path:
        raw_path = raw_path.replace('//', '/')

    return raw_path

def format_illust_summary(illust: dict, include_thumbnail: bool = False) -> str:
    tags = ", ".join([tag.get('name', '') for tag in illust.get('tags', [])[:5]])
    
    # 基础信息
    summary = (
        f"ID: {illust.get('id')} - \"{illust.get('title')}\"\n"
        f"  作者: {illust.get('user', {}).get('name')} (ID: {illust.get('user', {}).get('id')})\n"
        f"  类型: {illust.get('type')}\n"
        f"  标签: {tags}\n"
        f"  收藏数: {illust.get('total_bookmarks', 0)}, 浏览数: {illust.get('total_view', 0)}"
    )
    
    # 添加缩略图URL（如果请求）
    if include_thumbnail:
        thumbnail_url = _extract_thumbnail_url(illust)
        if thumbnail_url:
            # 使用新的函数处理Pixiv图片访问，传入illust_id以提供base64获取指引
            thumbnail_info = get_pixiv_image_with_referer(thumbnail_url, illust.get('id'))
            if thumbnail_info != thumbnail_url:  # 如果返回了特殊说明
                summary += f"\n\n{thumbnail_info}"
            else:
                summary += f"\n  缩略图: {thumbnail_url}"
        else:
            summary += "\n  缩略图: 暂无"
    
    return summary

def _extract_thumbnail_url(illust: dict) -> str:
    """从illust对象中提取缩略图URL"""
    # 优先使用square_medium缩略图
    image_urls = illust.get('image_urls', {})
    if image_urls.get('square_medium'):
        return image_urls['square_medium']
    
    # 备选：使用medium尺寸
    if image_urls.get('medium'):
        return image_urls['medium']
    
    # 对于多页作品，使用第一页的缩略图
    meta_pages = illust.get('meta_pages', [])
    if meta_pages and len(meta_pages) > 0:
        first_page_urls = meta_pages[0].get('image_urls', {})
        if first_page_urls.get('square_medium'):
            return first_page_urls['square_medium']
        if first_page_urls.get('medium'):
            return first_page_urls['medium']
    
    # 最后尝试：单页作品的原图URL（虽然不是缩略图，但总比没有好）
    meta_single_page = illust.get('meta_single_page', {})
    if meta_single_page.get('original_image_url'):
        return meta_single_page['original_image_url']
    
    return ""

def get_pixiv_image_with_referer(url: str, illust_id: int = None) -> str:
    """获取带有正确Referer头的Pixiv图片访问说明"""
    if not url:
        return "无可用图片URL"
    
    # 检查是否为Pixiv图片URL
    if 'pximg.net' in url or 'pixiv.net' in url:
        base64_hint = ""
        if illust_id:
            base64_hint = f"\n5. 获取可直接显示的缩略图: 使用get_thumbnail_base64工具，参数illust_id={illust_id}"
        
        return f"""⚠️ Pixiv图片需要特殊访问方式：

🔗 图片URL: {url}

📋 访问方法：
1. 复制上述URL
2. 在浏览器中打开 https://www.pixiv.net
3. 登录您的Pixiv账号
4. 在同一浏览器标签页中粘贴并访问图片URL{base64_hint}

💡 原因说明：
Pixiv的图片服务器有防盗链保护，需要正确的Referer头才能访问。直接访问会返回403 Forbidden错误。通过先访问Pixiv主站再访问图片URL可以绕过这个限制。

🛠️ 技术细节：
- 需要Referer: https://www.pixiv.net/ 或 https://app-api.pixiv.net/
- 或者使用专门的Pixiv图片查看器扩展"""
    
    return url

def format_user_summary(user: dict) -> str:
    return (
        f"用户ID: {user.get('id')} - {user.get('name')} (@{user.get('account')})\n"
        f"  关注状态: {'已关注' if user.get('is_followed') else '未关注'}\n"
        f"  简介: {user.get('comment', '无')}"
    )
