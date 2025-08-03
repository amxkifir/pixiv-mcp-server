#!/usr/bin/env python3
"""
Pixiv MCP Server - DXT Extension Entry Point

A powerful Pixiv toolset for Large Language Models via MCP.
This server provides browsing, searching, and downloading capabilities for Pixiv content.
"""

import asyncio
import json
import logging
import os
import sys
import urllib3
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add the parent directory to the path to import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from mcp.server.models import InitializationOptions
    from mcp.server import NotificationOptions, Server
    from mcp.types import (
        CallToolRequest,
        CallToolResult,
        ListToolsRequest,
        TextContent,
        Tool,
    )
    import mcp.server.stdio
except ImportError as e:
    print(f"Error importing MCP modules: {e}", file=sys.stderr)
    print("Please ensure the MCP package is installed: pip install mcp", file=sys.stderr)
    sys.exit(1)

try:
    from pixivpy3 import AppPixivAPI
except ImportError as e:
    print(f"Error importing pixivpy3: {e}", file=sys.stderr)
    print("Please ensure pixivpy3 is installed: pip install pixivpy3", file=sys.stderr)
    sys.exit(1)

# Import our custom modules
try:
    from pixiv_mcp_server.state import state
    from pixiv_mcp_server.downloader import _background_download_single, HAS_FFMPEG
    from pixiv_mcp_server.utils import (
        format_illust_summary,
        format_user_summary,
        handle_api_error,
        handle_api_error_with_retry,
        refresh_token_if_needed
    )
except ImportError as e:
    print(f"Error importing custom modules: {e}", file=sys.stderr)
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr)  # Log to stderr to avoid interfering with stdio transport
    ]
)
logger = logging.getLogger('pixiv-mcp-server')

# Disable urllib3 warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Initialize the MCP server
server = Server("pixiv-mcp-server")

# Tool definitions with proper schemas
TOOLS = [
    Tool(
        name="set_download_path",
        description="Set the default local save location for images and animations. Creates directory if it doesn't exist.",
        inputSchema={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The directory path where files should be downloaded"
                }
            },
            "required": ["path"]
        }
    ),
    Tool(
        name="download",
        description="Download one or more artworks by ID with intelligent storage rules. This is an asynchronous background operation.",
        inputSchema={
            "type": "object",
            "properties": {
                "illust_id": {
                    "type": "integer",
                    "description": "Single artwork ID to download"
                },
                "illust_ids": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "List of artwork IDs to download"
                }
            },
            "anyOf": [
                {"required": ["illust_id"]},
                {"required": ["illust_ids"]}
            ]
        }
    ),
    Tool(
        name="refresh_token",
        description="Manually refresh Pixiv API token when encountering authentication errors.",
        inputSchema={
            "type": "object",
            "properties": {},
            "additionalProperties": False
        }
    ),
    Tool(
        name="download_random_from_recommendation",
        description="Download random artworks from recommendations.",
        inputSchema={
            "type": "object",
            "properties": {
                "count": {
                    "type": "integer",
                    "description": "Number of random artworks to download",
                    "default": 5,
                    "minimum": 1,
                    "maximum": 20
                }
            }
        }
    ),
    Tool(
        name="search_illust",
        description="Search for illustrations using keywords with various filters.",
        inputSchema={
            "type": "object",
            "properties": {
                "word": {
                    "type": "string",
                    "description": "Search keyword or tag"
                },
                "search_target": {
                    "type": "string",
                    "enum": ["partial_match_for_tags", "exact_match_for_tags", "title_and_caption"],
                    "default": "partial_match_for_tags",
                    "description": "Search target type"
                },
                "sort": {
                    "type": "string",
                    "enum": ["date_desc", "date_asc", "popular_desc"],
                    "default": "date_desc",
                    "description": "Sort order"
                },
                "duration": {
                    "type": "string",
                    "enum": ["within_last_day", "within_last_week", "within_last_month"],
                    "description": "Time range filter"
                },
                "offset": {
                    "type": "integer",
                    "default": 0,
                    "minimum": 0,
                    "description": "Pagination offset"
                },
                "search_r18": {
                    "type": "boolean",
                    "default": False,
                    "description": "Include R-18 content"
                }
            },
            "required": ["word"]
        }
    ),
    Tool(
        name="illust_detail",
        description="Get detailed information about a specific artwork.",
        inputSchema={
            "type": "object",
            "properties": {
                "illust_id": {
                    "type": "integer",
                    "description": "The artwork ID"
                }
            },
            "required": ["illust_id"]
        }
    ),
    Tool(
        name="illust_related",
        description="Find artworks related to a specific illustration.",
        inputSchema={
            "type": "object",
            "properties": {
                "illust_id": {
                    "type": "integer",
                    "description": "The artwork ID to find related works for"
                },
                "offset": {
                    "type": "integer",
                    "default": 0,
                    "minimum": 0,
                    "description": "Pagination offset"
                }
            },
            "required": ["illust_id"]
        }
    ),
    Tool(
        name="illust_ranking",
        description="Browse Pixiv rankings (daily, weekly, monthly, etc.).",
        inputSchema={
            "type": "object",
            "properties": {
                "mode": {
                    "type": "string",
                    "enum": ["day", "week", "month", "day_male", "day_female", "week_original", "week_rookie", "day_manga"],
                    "default": "day",
                    "description": "Ranking mode"
                },
                "date": {
                    "type": "string",
                    "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
                    "description": "Date in YYYY-MM-DD format (optional)"
                },
                "offset": {
                    "type": "integer",
                    "default": 0,
                    "minimum": 0,
                    "description": "Pagination offset"
                }
            }
        }
    ),
    Tool(
        name="search_user",
        description="Search for users/artists on Pixiv.",
        inputSchema={
            "type": "object",
            "properties": {
                "word": {
                    "type": "string",
                    "description": "Search keyword for username"
                },
                "offset": {
                    "type": "integer",
                    "default": 0,
                    "minimum": 0,
                    "description": "Pagination offset"
                }
            },
            "required": ["word"]
        }
    ),
    Tool(
        name="illust_recommended",
        description="Get personalized artwork recommendations.",
        inputSchema={
            "type": "object",
            "properties": {
                "offset": {
                    "type": "integer",
                    "default": 0,
                    "minimum": 0,
                    "description": "Pagination offset"
                }
            }
        }
    ),
    Tool(
        name="trending_tags_illust",
        description="Get currently trending illustration tags.",
        inputSchema={
            "type": "object",
            "properties": {},
            "additionalProperties": False
        }
    ),
    Tool(
        name="illust_follow",
        description="Browse artworks from followed artists.",
        inputSchema={
            "type": "object",
            "properties": {
                "restrict": {
                    "type": "string",
                    "enum": ["public", "private"],
                    "default": "public",
                    "description": "Visibility restriction"
                },
                "offset": {
                    "type": "integer",
                    "default": 0,
                    "minimum": 0,
                    "description": "Pagination offset"
                }
            }
        }
    ),
    Tool(
        name="user_bookmarks",
        description="Browse user's bookmarked artworks.",
        inputSchema={
            "type": "object",
            "properties": {
                "user_id_to_check": {
                    "type": "integer",
                    "description": "User ID to check bookmarks for (optional, defaults to current user)"
                },
                "restrict": {
                    "type": "string",
                    "enum": ["public", "private"],
                    "default": "public",
                    "description": "Visibility restriction"
                },
                "tag": {
                    "type": "string",
                    "description": "Filter by specific tag"
                },
                "max_bookmark_id": {
                    "type": "integer",
                    "description": "Maximum bookmark ID for pagination"
                }
            }
        }
    ),
    Tool(
        name="user_following",
        description="View user's following list.",
        inputSchema={
            "type": "object",
            "properties": {
                "user_id_to_check": {
                    "type": "integer",
                    "description": "User ID to check following list for (optional, defaults to current user)"
                },
                "restrict": {
                    "type": "string",
                    "enum": ["public", "private"],
                    "default": "public",
                    "description": "Visibility restriction"
                },
                "offset": {
                    "type": "integer",
                    "default": 0,
                    "minimum": 0,
                    "description": "Pagination offset"
                }
            }
        }
    )
]

@server.list_tools()
async def handle_list_tools() -> List[Tool]:
    """List available tools."""
    return TOOLS

@server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool calls with proper error handling and validation."""
    try:
        logger.info(f"Tool called: {name} with arguments: {arguments}")
        
        # Ensure authentication before API calls
        if name != "set_download_path" and name != "refresh_token":
            if not state.is_authenticated:
                return [TextContent(
                    type="text",
                    text="错误：未认证。请确保已设置有效的 PIXIV_REFRESH_TOKEN 环境变量，或使用 refresh_token 工具进行认证。"
                )]
        
        # Route to appropriate handler
        if name == "set_download_path":
            result = await tool_set_download_path(arguments.get("path"))
        elif name == "download":
            result = await tool_download(
                arguments.get("illust_id"),
                arguments.get("illust_ids")
            )
        elif name == "refresh_token":
            result = await tool_refresh_token()
        elif name == "download_random_from_recommendation":
            result = await tool_download_random_from_recommendation(
                arguments.get("count", 5)
            )
        elif name == "search_illust":
            result = await tool_search_illust(
                arguments["word"],
                arguments.get("search_target", "partial_match_for_tags"),
                arguments.get("sort", "date_desc"),
                arguments.get("duration"),
                arguments.get("offset", 0),
                arguments.get("search_r18", False)
            )
        elif name == "illust_detail":
            result = await tool_illust_detail(arguments["illust_id"])
        elif name == "illust_related":
            result = await tool_illust_related(
                arguments["illust_id"],
                arguments.get("offset", 0)
            )
        elif name == "illust_ranking":
            result = await tool_illust_ranking(
                arguments.get("mode", "day"),
                arguments.get("date"),
                arguments.get("offset", 0)
            )
        elif name == "search_user":
            result = await tool_search_user(
                arguments["word"],
                arguments.get("offset", 0)
            )
        elif name == "illust_recommended":
            result = await tool_illust_recommended(
                arguments.get("offset", 0)
            )
        elif name == "trending_tags_illust":
            result = await tool_trending_tags_illust()
        elif name == "illust_follow":
            result = await tool_illust_follow(
                arguments.get("restrict", "public"),
                arguments.get("offset", 0)
            )
        elif name == "user_bookmarks":
            result = await tool_user_bookmarks(
                arguments.get("user_id_to_check"),
                arguments.get("restrict", "public"),
                arguments.get("tag"),
                arguments.get("max_bookmark_id")
            )
        elif name == "user_following":
            result = await tool_user_following(
                arguments.get("user_id_to_check"),
                arguments.get("restrict", "public"),
                arguments.get("offset", 0)
            )
        else:
            result = f"错误：未知工具 '{name}'"
        
        return [TextContent(type="text", text=result)]
        
    except Exception as e:
        logger.error(f"Error in tool {name}: {e}", exc_info=True)
        return [TextContent(
            type="text",
            text=f"工具执行错误: {str(e)}"
        )]

# Tool implementation functions
async def tool_set_download_path(path: str) -> str:
    """Set download path tool implementation."""
    try:
        Path(path).mkdir(parents=True, exist_ok=True)
        state.download_path = path
        logger.info(f"下载路径已更新为: {state.download_path}")
        return f"下载路径已成功更新为: {path}。之后所有下载的文件都将保存于此。"
    except Exception as e:
        logger.error(f"设置下载路径失败: {e}")
        return f"错误：无法设置下载路径。请检查路径 '{path}' 是否有效且程序有写入权限。错误详情: {e}"

async def tool_download(illust_id: Optional[int] = None, illust_ids: Optional[List[int]] = None) -> str:
    """Download tool implementation."""
    if not illust_id and not illust_ids:
        return "错误：必须提供 illust_id (单个ID) 或 illust_ids (ID列表) 参数之一。"

    id_list = []
    if illust_id:
        id_list.append(illust_id)
    if illust_ids:
        id_list.extend(illust_ids)
    
    unique_ids = sorted(list(set(id_list)))
    
    for an_id in unique_ids:
        asyncio.create_task(_background_download_single(an_id))
    
    return f"已成功将 {len(unique_ids)} 个作品的下载任务派发至后台。请注意，动图(Ugoira)合成可能需要几十秒到数分钟，请耐心等待文件下载和处理完成。"

async def tool_refresh_token() -> str:
    """Refresh token tool implementation."""
    try:
        await refresh_token_if_needed()
        return "Token 刷新成功。"
    except Exception as e:
        logger.error(f"Token 刷新失败: {e}")
        return f"Token 刷新失败: {e}"

async def tool_download_random_from_recommendation(count: int = 5) -> str:
    """Download random from recommendation tool implementation."""
    try:
        await refresh_token_if_needed()
        
        json_result = state.api.illust_recommended()
        if 'illusts' not in json_result or not json_result['illusts']:
            return "无法获取推荐内容，可能是网络问题或需要重新认证。"
        
        illusts = json_result['illusts']
        selected_illusts = illusts[:min(count, len(illusts))]
        
        for illust in selected_illusts:
            asyncio.create_task(_background_download_single(illust['id']))
        
        summary = "\n".join([format_illust_summary(illust) for illust in selected_illusts])
        return f"已从推荐中选择 {len(selected_illusts)} 个作品进行下载：\n\n{summary}\n\n下载任务已派发至后台。"
        
    except Exception as e:
        return await handle_api_error(e, "获取推荐内容")

async def tool_search_illust(word: str, search_target: str = "partial_match_for_tags", 
                           sort: str = "date_desc", duration: Optional[str] = None, 
                           offset: int = 0, search_r18: bool = False) -> str:
    """Search illust tool implementation."""
    try:
        await refresh_token_if_needed()
        
        json_result = await handle_api_error_with_retry(
            lambda: state.api.search_illust(
                word=word,
                search_target=search_target,
                sort=sort,
                duration=duration,
                offset=offset
            ),
            f"搜索插画 '{word}'"
        )
        
        if not json_result or 'illusts' not in json_result:
            return f"搜索 '{word}' 未找到结果。"
        
        illusts = json_result['illusts']
        if not illusts:
            return f"搜索 '{word}' 未找到结果。"
        
        # Filter R-18 content if not requested
        if not search_r18:
            illusts = [illust for illust in illusts if illust.get('x_restrict', 0) == 0]
        
        summary = "\n".join([format_illust_summary(illust) for illust in illusts[:10]])
        return f"搜索 '{word}' 找到 {len(illusts)} 个结果（显示前10个）：\n\n{summary}"
        
    except Exception as e:
        return await handle_api_error(e, f"搜索插画 '{word}'")

async def tool_illust_detail(illust_id: int) -> str:
    """Illust detail tool implementation."""
    try:
        await refresh_token_if_needed()
        
        json_result = await handle_api_error_with_retry(
            lambda: state.api.illust_detail(illust_id),
            f"获取作品详情 {illust_id}"
        )
        
        if not json_result or 'illust' not in json_result:
            return f"无法获取作品 {illust_id} 的详细信息。"
        
        return format_illust_summary(json_result['illust'], detailed=True)
        
    except Exception as e:
        return await handle_api_error(e, f"获取作品详情 {illust_id}")

async def tool_illust_related(illust_id: int, offset: int = 0) -> str:
    """Illust related tool implementation."""
    try:
        await refresh_token_if_needed()
        
        json_result = await handle_api_error_with_retry(
            lambda: state.api.illust_related(illust_id, offset=offset),
            f"获取相关作品 {illust_id}"
        )
        
        if not json_result or 'illusts' not in json_result:
            return f"无法获取作品 {illust_id} 的相关作品。"
        
        illusts = json_result['illusts']
        if not illusts:
            return f"作品 {illust_id} 没有找到相关作品。"
        
        summary = "\n".join([format_illust_summary(illust) for illust in illusts[:10]])
        return f"作品 {illust_id} 的相关作品（显示前10个）：\n\n{summary}"
        
    except Exception as e:
        return await handle_api_error(e, f"获取相关作品 {illust_id}")

async def tool_illust_ranking(mode: str = "day", date: Optional[str] = None, offset: int = 0) -> str:
    """Illust ranking tool implementation."""
    try:
        await refresh_token_if_needed()
        
        json_result = await handle_api_error_with_retry(
            lambda: state.api.illust_ranking(mode=mode, date=date, offset=offset),
            f"获取排行榜 {mode}"
        )
        
        if not json_result or 'illusts' not in json_result:
            return f"无法获取 {mode} 排行榜。"
        
        illusts = json_result['illusts']
        if not illusts:
            return f"{mode} 排行榜暂无内容。"
        
        summary = "\n".join([format_illust_summary(illust) for illust in illusts[:10]])
        return f"{mode} 排行榜（显示前10个）：\n\n{summary}"
        
    except Exception as e:
        return await handle_api_error(e, f"获取排行榜 {mode}")

async def tool_search_user(word: str, offset: int = 0) -> str:
    """Search user tool implementation."""
    try:
        await refresh_token_if_needed()
        
        json_result = await handle_api_error_with_retry(
            lambda: state.api.search_user(word, offset=offset),
            f"搜索用户 '{word}'"
        )
        
        if not json_result or 'user_previews' not in json_result:
            return f"搜索用户 '{word}' 未找到结果。"
        
        users = json_result['user_previews']
        if not users:
            return f"搜索用户 '{word}' 未找到结果。"
        
        summary = "\n".join([format_user_summary(user['user']) for user in users[:10]])
        return f"搜索用户 '{word}' 找到 {len(users)} 个结果（显示前10个）：\n\n{summary}"
        
    except Exception as e:
        return await handle_api_error(e, f"搜索用户 '{word}'")

async def tool_illust_recommended(offset: int = 0) -> str:
    """Illust recommended tool implementation."""
    try:
        await refresh_token_if_needed()
        
        json_result = await handle_api_error_with_retry(
            lambda: state.api.illust_recommended(offset=offset),
            "获取推荐作品"
        )
        
        if not json_result or 'illusts' not in json_result:
            return "无法获取推荐作品。"
        
        illusts = json_result['illusts']
        if not illusts:
            return "暂无推荐作品。"
        
        summary = "\n".join([format_illust_summary(illust) for illust in illusts[:10]])
        return f"推荐作品（显示前10个）：\n\n{summary}"
        
    except Exception as e:
        return await handle_api_error(e, "获取推荐作品")

async def tool_trending_tags_illust() -> str:
    """Trending tags illust tool implementation."""
    try:
        await refresh_token_if_needed()
        
        json_result = await handle_api_error_with_retry(
            lambda: state.api.trending_tags_illust(),
            "获取热门标签"
        )
        
        if not json_result or 'trend_tags' not in json_result:
            return "无法获取热门标签。"
        
        tags = json_result['trend_tags']
        if not tags:
            return "暂无热门标签。"
        
        tag_list = []
        for tag_info in tags[:20]:
            tag = tag_info.get('tag', '')
            translated_name = tag_info.get('translated_name', '')
            if translated_name and translated_name != tag:
                tag_list.append(f"{tag} ({translated_name})")
            else:
                tag_list.append(tag)
        
        return f"当前热门标签：\n\n{', '.join(tag_list)}"
        
    except Exception as e:
        return await handle_api_error(e, "获取热门标签")

async def tool_illust_follow(restrict: str = "public", offset: int = 0) -> str:
    """Illust follow tool implementation."""
    try:
        await refresh_token_if_needed()
        
        json_result = await handle_api_error_with_retry(
            lambda: state.api.illust_follow(restrict=restrict, offset=offset),
            "获取关注动态"
        )
        
        if not json_result or 'illusts' not in json_result:
            return "无法获取关注动态。"
        
        illusts = json_result['illusts']
        if not illusts:
            return "暂无关注动态。"
        
        summary = "\n".join([format_illust_summary(illust) for illust in illusts[:10]])
        return f"关注动态（显示前10个）：\n\n{summary}"
        
    except Exception as e:
        return await handle_api_error(e, "获取关注动态")

async def tool_user_bookmarks(user_id_to_check: Optional[int] = None, restrict: str = "public", 
                            tag: Optional[str] = None, max_bookmark_id: Optional[int] = None) -> str:
    """User bookmarks tool implementation."""
    try:
        await refresh_token_if_needed()
        
        user_id = user_id_to_check or state.user_id
        if not user_id:
            return "错误：无法确定用户ID。请先认证或提供 user_id_to_check 参数。"
        
        json_result = await handle_api_error_with_retry(
            lambda: state.api.user_bookmarks_illust(
                user_id, restrict=restrict, tag=tag, max_bookmark_id=max_bookmark_id
            ),
            f"获取用户 {user_id} 的收藏"
        )
        
        if not json_result or 'illusts' not in json_result:
            return f"无法获取用户 {user_id} 的收藏。"
        
        illusts = json_result['illusts']
        if not illusts:
            return f"用户 {user_id} 暂无收藏作品。"
        
        summary = "\n".join([format_illust_summary(illust) for illust in illusts[:10]])
        return f"用户 {user_id} 的收藏（显示前10个）：\n\n{summary}"
        
    except Exception as e:
        return await handle_api_error(e, f"获取用户收藏")

async def tool_user_following(user_id_to_check: Optional[int] = None, restrict: str = "public", 
                            offset: int = 0) -> str:
    """User following tool implementation."""
    try:
        await refresh_token_if_needed()
        
        user_id = user_id_to_check or state.user_id
        if not user_id:
            return "错误：无法确定用户ID。请先认证或提供 user_id_to_check 参数。"
        
        json_result = await handle_api_error_with_retry(
            lambda: state.api.user_following(user_id, restrict=restrict, offset=offset),
            f"获取用户 {user_id} 的关注列表"
        )
        
        if not json_result or 'user_previews' not in json_result:
            return f"无法获取用户 {user_id} 的关注列表。"
        
        users = json_result['user_previews']
        if not users:
            return f"用户 {user_id} 暂无关注的用户。"
        
        summary = "\n".join([format_user_summary(user['user']) for user in users[:10]])
        return f"用户 {user_id} 的关注列表（显示前10个）：\n\n{summary}"
        
    except Exception as e:
        return await handle_api_error(e, f"获取用户关注列表")

def setup_environment():
    """Setup environment variables and configuration."""
    # Parse environment variables that might be in KEY=VALUE format
    for key, value in os.environ.items():
        if '=' in value:
            try:
                k, v = value.split('=', 1)
                os.environ[k] = v
            except ValueError:
                pass

async def main():
    """Main entry point for the DXT extension."""
    try:
        # Setup environment
        setup_environment()
        
        # Initialize state
        os.makedirs(state.download_path, exist_ok=True)
        
        logger.info("Pixiv MCP Server (DXT) starting...")
        logger.info(f"Default download path: {state.download_path}")
        logger.info(f"Filename template: {state.filename_template}")
        logger.info(f"FFmpeg support: {'Yes' if HAS_FFMPEG else 'No'}")
        
        # Auto-authenticate if refresh token is available
        if state.refresh_token:
            logger.info("Attempting auto-authentication with PIXIV_REFRESH_TOKEN...")
            try:
                state.api.auth(refresh_token=state.refresh_token)
                state.is_authenticated = True
                state.user_id = state.api.user_id
                logger.info(f"Auto-authentication successful, user ID: {state.user_id}")
            except Exception as e:
                logger.warning(f"Auto-authentication failed: {e}")
                logger.warning("Please check your REFRESH_TOKEN validity or network/proxy settings.")
        else:
            logger.info("No PIXIV_REFRESH_TOKEN found, manual authentication required.")
        
        # Run the MCP server
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="pixiv-mcp-server",
                    server_version="2.0.0",
                    capabilities=server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )
            
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())