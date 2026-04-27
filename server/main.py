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
    from dotenv import load_dotenv
    load_dotenv(override=True)
except ImportError:
    pass

try:
    from pixiv_mcp_server.state import state
    from pixiv_mcp_server.downloader import _background_download_single, _background_download_novel, HAS_FFMPEG
    from pixiv_mcp_server.utils import (
        format_illust_summary,
        format_novel_summary,
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
        name="set_refresh_token",
        description="Set or update the Pixiv refresh token for authentication. This allows configuring the token after DXT installation.",
        inputSchema={
            "type": "object",
            "properties": {
                "refresh_token": {
                    "type": "string",
                    "description": "The Pixiv refresh token obtained from the authentication process"
                }
            },
            "required": ["refresh_token"]
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
    ),
    # === 小说工具 ===
    Tool(
        name="search_novel",
        description="Search for novels with various filters. Supports full-text search and tag-based search.",
        inputSchema={
            "type": "object",
            "properties": {
                "word": {
                    "type": "string",
                    "description": "Search keyword"
                },
                "search_target": {
                    "type": "string",
                    "enum": ["partial_match_for_tags", "exact_match_for_tags", "text", "keyword"],
                    "default": "partial_match_for_tags",
                    "description": "Search target type: partial_match_for_tags, exact_match_for_tags, text (full-text), keyword"
                },
                "sort": {
                    "type": "string",
                    "enum": ["date_desc", "date_asc"],
                    "default": "date_desc",
                    "description": "Sort order"
                },
                "start_date": {
                    "type": "string",
                    "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
                    "description": "Start date in YYYY-MM-DD format (optional)"
                },
                "end_date": {
                    "type": "string",
                    "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
                    "description": "End date in YYYY-MM-DD format (optional)"
                },
                "search_ai_type": {
                    "type": "integer",
                    "enum": [0, 1],
                    "default": 0,
                    "description": "AI type filter: 0=all, 1=non-AI only"
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
        name="novel_detail",
        description="Get detailed information about a specific novel.",
        inputSchema={
            "type": "object",
            "properties": {
                "novel_id": {
                    "type": "integer",
                    "description": "The novel ID"
                }
            },
            "required": ["novel_id"]
        }
    ),
    Tool(
        name="read_novel",
        description="Read the full text of a novel. Content truncated at 3000 characters. Use download_novel to get the complete file.",
        inputSchema={
            "type": "object",
            "properties": {
                "novel_id": {
                    "type": "integer",
                    "description": "The novel ID to read"
                }
            },
            "required": ["novel_id"]
        }
    ),
    Tool(
        name="novel_recommended",
        description="Get personalized novel recommendations.",
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
        name="novel_follow",
        description="Browse novels from followed authors.",
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
        name="novel_new",
        description="Get the latest novels published on Pixiv.",
        inputSchema={
            "type": "object",
            "properties": {
                "max_novel_id": {
                    "type": "integer",
                    "description": "Maximum novel ID for pagination (optional)"
                }
            }
        }
    ),
    Tool(
        name="user_novels",
        description="Get a user's novel list.",
        inputSchema={
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "integer",
                    "description": "The user ID whose novels to list"
                },
                "offset": {
                    "type": "integer",
                    "default": 0,
                    "minimum": 0,
                    "description": "Pagination offset"
                }
            },
            "required": ["user_id"]
        }
    ),
    Tool(
        name="user_bookmarks_novel",
        description="Browse user's bookmarked novels.",
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
        name="download_novel",
        description="Download one or more novels as .txt files. This is an asynchronous background operation.",
        inputSchema={
            "type": "object",
            "properties": {
                "novel_id": {
                    "type": "integer",
                    "description": "Single novel ID to download"
                },
                "novel_ids": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "List of novel IDs to download"
                }
            },
            "anyOf": [
                {"required": ["novel_id"]},
                {"required": ["novel_ids"]}
            ]
        }
    ),
    Tool(
        name="novel_series",
        description="Get details of a novel series including contained novels.",
        inputSchema={
            "type": "object",
            "properties": {
                "series_id": {
                    "type": "integer",
                    "description": "The series ID"
                }
            },
            "required": ["series_id"]
        }
    ),
    Tool(
        name="novel_comments",
        description="Get comments for a specific novel.",
        inputSchema={
            "type": "object",
            "properties": {
                "novel_id": {
                    "type": "integer",
                    "description": "The novel ID"
                },
                "offset": {
                    "type": "integer",
                    "default": 0,
                    "minimum": 0,
                    "description": "Pagination offset"
                },
                "include_total_comments": {
                    "type": "boolean",
                    "default": False,
                    "description": "Include total comment count"
                }
            },
            "required": ["novel_id"]
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
        if name not in ["set_download_path", "refresh_token", "set_refresh_token"]:
            if not state.is_authenticated:
                return [TextContent(
                    type="text",
                    text="错误：未认证。请先使用 set_refresh_token 工具设置 refresh token，或使用 refresh_token 工具进行认证。"
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
        elif name == "set_refresh_token":
            result = await tool_set_refresh_token(arguments["refresh_token"])
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
        elif name == "search_novel":
            result = await tool_search_novel(
                arguments["word"],
                arguments.get("search_target", "partial_match_for_tags"),
                arguments.get("sort", "date_desc"),
                arguments.get("start_date"),
                arguments.get("end_date"),
                arguments.get("search_ai_type", 0),
                arguments.get("offset", 0)
            )
        elif name == "novel_detail":
            result = await tool_novel_detail(arguments["novel_id"])
        elif name == "read_novel":
            result = await tool_read_novel(arguments["novel_id"])
        elif name == "novel_recommended":
            result = await tool_novel_recommended(
                arguments.get("offset", 0)
            )
        elif name == "novel_follow":
            result = await tool_novel_follow(
                arguments.get("restrict", "public"),
                arguments.get("offset", 0)
            )
        elif name == "novel_new":
            result = await tool_novel_new(
                arguments.get("max_novel_id")
            )
        elif name == "user_novels":
            result = await tool_user_novels(
                arguments["user_id"],
                arguments.get("offset", 0)
            )
        elif name == "user_bookmarks_novel":
            result = await tool_user_bookmarks_novel(
                arguments.get("user_id_to_check"),
                arguments.get("restrict", "public"),
                arguments.get("tag"),
                arguments.get("max_bookmark_id")
            )
        elif name == "download_novel":
            result = await tool_download_novel(
                arguments.get("novel_id"),
                arguments.get("novel_ids")
            )
        elif name == "novel_series":
            result = await tool_novel_series(arguments["series_id"])
        elif name == "novel_comments":
            result = await tool_novel_comments(
                arguments["novel_id"],
                arguments.get("offset", 0),
                arguments.get("include_total_comments", False)
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
        if not state.refresh_token:
            return "错误：未设置 refresh token。请先使用 set_refresh_token 工具设置 token。"
        
        state.api.auth(refresh_token=state.refresh_token)
        state.is_authenticated = True
        state.user_id = state.api.user_id
        return f"认证成功！用户 ID: {state.user_id}"
    except Exception as e:
        logger.error(f"Token 刷新失败: {e}")
        return f"认证失败: {str(e)}"

async def tool_set_refresh_token(refresh_token: str) -> str:
    """Set or update the Pixiv refresh token."""
    try:
        if not refresh_token or not refresh_token.strip():
            return "错误：refresh token 不能为空。"
        
        # Update the state with new token
        state.refresh_token = refresh_token.strip()
        
        # Try to authenticate immediately
        state.api.auth(refresh_token=state.refresh_token)
        state.is_authenticated = True
        state.user_id = state.api.user_id
        
        return f"✅ Refresh token 设置成功并已完成认证！\n用户 ID: {state.user_id}\n\n现在您可以使用所有 Pixiv 功能了。"
    except Exception as e:
        # Even if authentication fails, we still save the token
        state.refresh_token = refresh_token.strip()
        return f"⚠️ Refresh token 已保存，但认证失败: {str(e)}\n\n请检查 token 是否有效，或稍后使用 refresh_token 工具重试认证。"

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
        return handle_api_error(e, "获取推荐内容")

async def tool_search_illust(word: str, search_target: str = "partial_match_for_tags", 
                           sort: str = "date_desc", duration: Optional[str] = None, 
                           offset: int = 0, search_r18: bool = False) -> str:
    """Search illust tool implementation."""
    try:
        await refresh_token_if_needed()

        # 直接调用以捕获真实错误
        try:
            raw_result = await asyncio.to_thread(
                state.api.search_illust,
                word=word,
                search_target=search_target,
                sort=sort,
                duration=duration,
                offset=offset
            )
        except Exception as raw_e:
            return f"搜索 '{word}' 异常: {type(raw_e).__name__}: {raw_e}"

        if raw_result is None:
            return f"搜索 '{word}' 失败: API返回None(空响应)。"
        if 'error' in raw_result:
            return f"搜索 '{word}' 失败: API错误 - {raw_result['error']}"
        if 'illusts' not in raw_result:
            return f"搜索 '{word}' 失败: 缺少illusts字段。响应keys: {list(raw_result.keys())} 内容: {str(raw_result)[:500]}"

        json_result = raw_result

        illusts = json_result['illusts']
        
        # Filter R-18 content if not requested
        if not search_r18:
            illusts = [illust for illust in illusts if illust.get('x_restrict', 0) == 0]
        
        summary = "\n".join([format_illust_summary(illust) for illust in illusts[:10]])
        return f"搜索 '{word}' 找到 {len(illusts)} 个结果（显示前10个）：\n\n{summary}"
        
    except Exception as e:
        return handle_api_error(e, f"搜索插画 '{word}'")

async def tool_illust_detail(illust_id: int) -> str:
    """Illust detail tool implementation."""
    try:
        await refresh_token_if_needed()

        try:
            json_result = await asyncio.to_thread(state.api.illust_detail, illust_id)
        except Exception as raw_e:
            return f"获取作品详情异常: {type(raw_e).__name__}: {raw_e}"

        if not json_result:
            return f"无法获取作品 {illust_id} 的详细信息: API返回空。"
        if 'error' in json_result:
            return f"无法获取作品 {illust_id}: API错误 {json_result['error']}"
        if 'illust' not in json_result:
            return f"无法获取作品 {illust_id}: 响应缺少illust字段。keys: {list(json_result.keys())}"

        illust = json_result['illust']
        result = format_illust_summary(illust)
        # 详情页额外添加标签和描述
        tags = ", ".join([tag.get('name', '') for tag in illust.get('tags', [])])
        caption = illust.get('caption', '')
        if caption:
            result += f"\n\n描述: {caption[:500]}"
        return result

    except Exception as e:
        return handle_api_error(e, f"获取作品详情 {illust_id}")

async def tool_illust_related(illust_id: int, offset: int = 0) -> str:
    """Illust related tool implementation."""
    try:
        await refresh_token_if_needed()

        try:
            json_result = await asyncio.to_thread(state.api.illust_related, illust_id, offset=offset)
        except Exception as raw_e:
            return f"获取相关作品异常: {type(raw_e).__name__}: {raw_e}"

        if not json_result:
            return f"无法获取作品 {illust_id} 的相关作品: API返回空。"
        if 'error' in json_result:
            return f"无法获取作品 {illust_id}: API错误 {json_result['error']}"
        if 'illusts' not in json_result:
            return f"无法获取作品 {illust_id}: 响应缺少illusts字段。keys: {list(json_result.keys())}"

        illusts = json_result['illusts']
        if not illusts:
            return f"作品 {illust_id} 没有找到相关作品。"

        summary = "\n".join([format_illust_summary(illust) for illust in illusts[:10]])
        return f"作品 {illust_id} 的相关作品（显示前10个）：\n\n{summary}"

    except Exception as e:
        return handle_api_error(e, f"获取相关作品 {illust_id}")

async def tool_illust_ranking(mode: str = "day", date: Optional[str] = None, offset: int = 0) -> str:
    """Illust ranking tool implementation."""
    try:
        await refresh_token_if_needed()

        try:
            json_result = await asyncio.to_thread(
                state.api.illust_ranking, mode=mode, date=date, offset=offset
            )
        except Exception as raw_e:
            return f"获取排行榜异常: {type(raw_e).__name__}: {raw_e}"

        if not json_result:
            return f"无法获取 {mode} 排行榜: API返回空。"
        if 'error' in json_result:
            return f"无法获取 {mode} 排行榜: API错误 {json_result['error']}"
        if 'illusts' not in json_result:
            return f"无法获取 {mode} 排行榜: 响应缺少illusts字段。keys: {list(json_result.keys())}"

        illusts = json_result['illusts']
        if not illusts:
            return f"{mode} 排行榜暂无内容。"

        summary = "\n".join([format_illust_summary(illust) for illust in illusts[:10]])
        return f"{mode} 排行榜（显示前10个）：\n\n{summary}"

    except Exception as e:
        return handle_api_error(e, f"获取排行榜 {mode}")

async def tool_search_user(word: str, offset: int = 0) -> str:
    """Search user tool implementation."""
    try:
        await refresh_token_if_needed()

        try:
            json_result = await asyncio.to_thread(
                state.api.search_user, word, offset=offset
            )
        except Exception as raw_e:
            return f"搜索用户异常: {type(raw_e).__name__}: {raw_e}"

        if not json_result:
            return f"搜索用户 '{word}' 失败: API返回空。"
        if 'error' in json_result:
            return f"搜索用户 '{word}' 失败: API错误 {json_result['error']}"
        if 'user_previews' not in json_result:
            return f"搜索用户 '{word}' 失败: 缺少user_previews字段。keys: {list(json_result.keys())}"

        users = json_result['user_previews']
        if not users:
            return f"搜索用户 '{word}' 未找到结果。"

        summary = "\n".join([format_user_summary(user['user']) for user in users[:10]])
        return f"搜索用户 '{word}' 找到 {len(users)} 个结果（显示前10个）：\n\n{summary}"

    except Exception as e:
        return handle_api_error(e, f"搜索用户 '{word}'")

async def tool_illust_recommended(offset: int = 0) -> str:
    """Illust recommended tool implementation."""
    try:
        await refresh_token_if_needed()

        try:
            json_result = await asyncio.to_thread(
                state.api.illust_recommended, offset=offset
            )
        except Exception as raw_e:
            return f"获取推荐异常: {type(raw_e).__name__}: {raw_e}"

        if not json_result:
            return "无法获取推荐作品: API返回空。"
        if 'error' in json_result:
            return f"无法获取推荐作品: API错误 {json_result['error']}"
        if 'illusts' not in json_result:
            return f"无法获取推荐作品: 缺少illusts字段。keys: {list(json_result.keys())}"

        illusts = json_result['illusts']
        if not illusts:
            return "暂无推荐作品。"

        summary = "\n".join([format_illust_summary(illust) for illust in illusts[:10]])
        return f"推荐作品（显示前10个）：\n\n{summary}"
        
    except Exception as e:
        return handle_api_error(e, "获取推荐作品")

async def tool_trending_tags_illust() -> str:
    """Trending tags illust tool implementation."""
    try:
        await refresh_token_if_needed()

        try:
            json_result = await asyncio.to_thread(state.api.trending_tags_illust)
        except Exception as raw_e:
            return f"获取热门标签异常: {type(raw_e).__name__}: {raw_e}"

        if not json_result:
            return "无法获取热门标签: API返回空。"
        if 'error' in json_result:
            return f"无法获取热门标签: API错误 {json_result['error']}"
        if 'trend_tags' not in json_result:
            return f"无法获取热门标签: 响应缺少trend_tags字段。keys: {list(json_result.keys())}"

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
        return handle_api_error(e, "获取热门标签")

async def tool_illust_follow(restrict: str = "public", offset: int = 0) -> str:
    """Illust follow tool implementation."""
    try:
        await refresh_token_if_needed()

        try:
            json_result = await asyncio.to_thread(
                state.api.illust_follow, restrict=restrict, offset=offset
            )
        except Exception as raw_e:
            return f"获取关注动态异常: {type(raw_e).__name__}: {raw_e}"

        if not json_result:
            return "无法获取关注动态: API返回空。"
        if 'error' in json_result:
            return f"无法获取关注动态: API错误 {json_result['error']}"
        if 'illusts' not in json_result:
            return f"无法获取关注动态: 响应缺少illusts字段。keys: {list(json_result.keys())}"

        illusts = json_result['illusts']
        if not illusts:
            return "暂无关注动态。"

        summary = "\n".join([format_illust_summary(illust) for illust in illusts[:10]])
        return f"关注动态（显示前10个）：\n\n{summary}"

    except Exception as e:
        return handle_api_error(e, "获取关注动态")

async def tool_user_bookmarks(user_id_to_check: Optional[int] = None, restrict: str = "public",
                            tag: Optional[str] = None, max_bookmark_id: Optional[int] = None) -> str:
    """User bookmarks tool implementation."""
    try:
        await refresh_token_if_needed()

        user_id = user_id_to_check or state.user_id
        if not user_id:
            return "错误：无法确定用户ID。请先认证或提供 user_id_to_check 参数。"

        try:
            json_result = await asyncio.to_thread(
                state.api.user_bookmarks_illust,
                user_id, restrict=restrict, tag=tag, max_bookmark_id=max_bookmark_id
            )
        except Exception as raw_e:
            return f"获取收藏异常: {type(raw_e).__name__}: {raw_e}"

        if not json_result:
            return f"无法获取用户 {user_id} 的收藏: API返回空。"
        if 'error' in json_result:
            return f"无法获取用户 {user_id}: API错误 {json_result['error']}"
        if 'illusts' not in json_result:
            return f"无法获取用户 {user_id}: 响应缺少illusts字段。keys: {list(json_result.keys())}"

        illusts = json_result['illusts']
        if not illusts:
            return f"用户 {user_id} 暂无收藏作品。"

        summary = "\n".join([format_illust_summary(illust) for illust in illusts[:10]])
        return f"用户 {user_id} 的收藏（显示前10个）：\n\n{summary}"

    except Exception as e:
        return handle_api_error(e, f"获取用户收藏")

async def tool_user_following(user_id_to_check: Optional[int] = None, restrict: str = "public",
                            offset: int = 0) -> str:
    """User following tool implementation."""
    try:
        await refresh_token_if_needed()

        user_id = user_id_to_check or state.user_id
        if not user_id:
            return "错误：无法确定用户ID。请先认证或提供 user_id_to_check 参数。"

        try:
            json_result = await asyncio.to_thread(
                state.api.user_following, user_id, restrict=restrict, offset=offset
            )
        except Exception as raw_e:
            return f"获取关注列表异常: {type(raw_e).__name__}: {raw_e}"

        if not json_result:
            return f"无法获取用户 {user_id} 的关注列表: API返回空。"
        if 'error' in json_result:
            return f"无法获取用户 {user_id}: API错误 {json_result['error']}"
        if 'user_previews' not in json_result:
            return f"无法获取用户 {user_id}: 响应缺少user_previews字段。keys: {list(json_result.keys())}"
        
        users = json_result['user_previews']
        if not users:
            return f"用户 {user_id} 暂无关注的用户。"
        
        summary = "\n".join([format_user_summary(user['user']) for user in users[:10]])
        return f"用户 {user_id} 的关注列表（显示前10个）：\n\n{summary}"
        
    except Exception as e:
        return handle_api_error(e, f"获取用户关注列表")


# === 小说工具实现 ===

async def tool_search_novel(word: str, search_target: str = "partial_match_for_tags",
                            sort: str = "date_desc", start_date: Optional[str] = None,
                            end_date: Optional[str] = None, search_ai_type: int = 0,
                            offset: int = 0) -> str:
    """Search novel tool implementation."""
    try:
        await refresh_token_if_needed()

        try:
            raw_result = await asyncio.to_thread(
                state.api.search_novel,
                word=word,
                search_target=search_target,
                sort=sort,
                start_date=start_date,
                end_date=end_date,
                search_ai_type=search_ai_type,
                offset=offset
            )
        except Exception as raw_e:
            return f"搜索小说 '{word}' 异常: {type(raw_e).__name__}: {raw_e}"

        if raw_result is None:
            return f"搜索小说 '{word}' 失败: API返回None(空响应)。"
        if 'error' in raw_result:
            return f"搜索小说 '{word}' 失败: API错误 - {raw_result['error']}"
        if 'novels' not in raw_result:
            return f"搜索小说 '{word}' 失败: 缺少novels字段。响应keys: {list(raw_result.keys())} 内容: {str(raw_result)[:500]}"

        novels = raw_result['novels']
        if not novels:
            return f"搜索小说 '{word}' 未找到结果。"

        summary = "\n".join([format_novel_summary(novel) for novel in novels[:10]])
        return f"搜索小说 '{word}' 找到 {len(novels)} 个结果（显示前10个）：\n\n{summary}"

    except Exception as e:
        return handle_api_error(e, f"搜索小说 '{word}'")


async def tool_novel_detail(novel_id: int) -> str:
    """Novel detail tool implementation."""
    try:
        await refresh_token_if_needed()

        try:
            json_result = await asyncio.to_thread(state.api.novel_detail, novel_id)
        except Exception as raw_e:
            return f"获取小说详情异常: {type(raw_e).__name__}: {raw_e}"

        if not json_result:
            return f"无法获取小说 {novel_id} 的详细信息: API返回空。"
        if 'error' in json_result:
            return f"无法获取小说 {novel_id}: API错误 {json_result['error']}"
        if 'novel' not in json_result:
            return f"无法获取小说 {novel_id}: 响应缺少novel字段。keys: {list(json_result.keys())}"

        novel = json_result['novel']
        result = format_novel_summary(novel)
        caption = novel.get('caption', '')
        if caption:
            result += f"\n\n简介: {caption[:500]}"
        return result

    except Exception as e:
        return handle_api_error(e, f"获取小说详情 {novel_id}")


async def tool_read_novel(novel_id: int) -> str:
    """Read novel full text tool implementation."""
    try:
        await refresh_token_if_needed()

        try:
            json_result = await asyncio.to_thread(state.api.webview_novel, novel_id)
        except Exception as raw_e:
            return f"获取小说正文异常: {type(raw_e).__name__}: {raw_e}"

        if not json_result:
            return f"无法获取小说 {novel_id} 的正文: API返回空。"
        if 'error' in json_result:
            return f"无法获取小说 {novel_id}: API错误 {json_result['error']}"

        novel_text = json_result.get('text', '')
        novel_title = json_result.get('title', 'Untitled')
        novel_author = json_result.get('userName', 'Unknown')

        if not novel_text:
            return f"小说 {novel_id} ('{novel_title}') 正文为空。"

        total_chars = len(novel_text)
        truncated = total_chars > 3000
        display_text = novel_text[:3000] if truncated else novel_text

        result = f"=== {novel_title} ===\n作者: {novel_author}\n\n{display_text}"

        if truncated:
            result += f"\n\n[内容被截断，仅显示前3000字，共{total_chars}字。]"
            result += f"\n提示: 使用 download_novel(novel_id={novel_id}) 可以下载完整小说为 .txt 文件。"

        return result

    except Exception as e:
        return handle_api_error(e, f"阅读小说 {novel_id}")


async def tool_novel_recommended(offset: int = 0) -> str:
    """Novel recommended tool implementation."""
    try:
        await refresh_token_if_needed()

        try:
            json_result = await asyncio.to_thread(
                state.api.novel_recommended, offset=offset
            )
        except Exception as raw_e:
            return f"获取推荐小说异常: {type(raw_e).__name__}: {raw_e}"

        if not json_result:
            return "无法获取推荐小说: API返回空。"
        if 'error' in json_result:
            return f"无法获取推荐小说: API错误 {json_result['error']}"
        if 'novels' not in json_result:
            return f"无法获取推荐小说: 缺少novels字段。keys: {list(json_result.keys())}"

        novels = json_result['novels']
        if not novels:
            return "暂无推荐小说。"

        summary = "\n".join([format_novel_summary(novel) for novel in novels[:10]])
        return f"推荐小说（显示前10个）：\n\n{summary}"

    except Exception as e:
        return handle_api_error(e, "获取推荐小说")


async def tool_novel_follow(restrict: str = "public", offset: int = 0) -> str:
    """Novel follow tool implementation."""
    try:
        await refresh_token_if_needed()

        try:
            json_result = await asyncio.to_thread(
                state.api.novel_follow, restrict=restrict, offset=offset
            )
        except Exception as raw_e:
            return f"获取关注小说动态异常: {type(raw_e).__name__}: {raw_e}"

        if not json_result:
            return "无法获取关注小说动态: API返回空。"
        if 'error' in json_result:
            return f"无法获取关注小说动态: API错误 {json_result['error']}"
        if 'novels' not in json_result:
            return f"无法获取关注小说动态: 缺少novels字段。keys: {list(json_result.keys())}"

        novels = json_result['novels']
        if not novels:
            return "暂无关注作者的小说动态。"

        summary = "\n".join([format_novel_summary(novel) for novel in novels[:10]])
        return f"关注动态 - 小说（显示前10个）：\n\n{summary}"

    except Exception as e:
        return handle_api_error(e, "获取关注小说动态")


async def tool_novel_new(max_novel_id: Optional[int] = None) -> str:
    """Novel new tool implementation."""
    try:
        await refresh_token_if_needed()

        try:
            kwargs = {}
            if max_novel_id:
                kwargs['max_novel_id'] = max_novel_id
            json_result = await asyncio.to_thread(state.api.novel_new, **kwargs)
        except Exception as raw_e:
            return f"获取最新小说异常: {type(raw_e).__name__}: {raw_e}"

        if not json_result:
            return "无法获取最新小说: API返回空。"
        if 'error' in json_result:
            return f"无法获取最新小说: API错误 {json_result['error']}"
        if 'novels' not in json_result:
            return f"无法获取最新小说: 缺少novels字段。keys: {list(json_result.keys())}"

        novels = json_result['novels']
        if not novels:
            return "暂无最新小说。"

        summary = "\n".join([format_novel_summary(novel) for novel in novels[:10]])
        return f"最新小说（显示前10个）：\n\n{summary}"

    except Exception as e:
        return handle_api_error(e, "获取最新小说")


async def tool_user_novels(user_id: int, offset: int = 0) -> str:
    """User novels tool implementation."""
    try:
        await refresh_token_if_needed()

        try:
            json_result = await asyncio.to_thread(
                state.api.user_novels, user_id, offset=offset
            )
        except Exception as raw_e:
            return f"获取用户小说列表异常: {type(raw_e).__name__}: {raw_e}"

        if not json_result:
            return f"无法获取用户 {user_id} 的小说列表: API返回空。"
        if 'error' in json_result:
            return f"无法获取用户 {user_id}: API错误 {json_result['error']}"
        if 'novels' not in json_result:
            return f"无法获取用户 {user_id}: 缺少novels字段。keys: {list(json_result.keys())}"

        novels = json_result['novels']
        if not novels:
            return f"用户 {user_id} 暂无小说作品。"

        summary = "\n".join([format_novel_summary(novel) for novel in novels[:10]])
        return f"用户 {user_id} 的小说列表（显示前10个）：\n\n{summary}"

    except Exception as e:
        return handle_api_error(e, f"获取用户小说列表")


async def tool_user_bookmarks_novel(user_id_to_check: Optional[int] = None,
                                    restrict: str = "public", tag: Optional[str] = None,
                                    max_bookmark_id: Optional[int] = None) -> str:
    """User bookmarks novel tool implementation."""
    try:
        await refresh_token_if_needed()

        user_id = user_id_to_check or state.user_id
        if not user_id:
            return "错误：无法确定用户ID。请先认证或提供 user_id_to_check 参数。"

        try:
            json_result = await asyncio.to_thread(
                state.api.user_bookmarks_novel,
                user_id, restrict=restrict, tag=tag, max_bookmark_id=max_bookmark_id
            )
        except Exception as raw_e:
            return f"获取小说收藏异常: {type(raw_e).__name__}: {raw_e}"

        if not json_result:
            return f"无法获取用户 {user_id} 的小说收藏: API返回空。"
        if 'error' in json_result:
            return f"无法获取用户 {user_id}: API错误 {json_result['error']}"
        if 'novels' not in json_result:
            return f"无法获取用户 {user_id}: 缺少novels字段。keys: {list(json_result.keys())}"

        novels = json_result['novels']
        if not novels:
            return f"用户 {user_id} 暂无收藏小说。"

        summary = "\n".join([format_novel_summary(novel) for novel in novels[:10]])
        return f"用户 {user_id} 的小说收藏（显示前10个）：\n\n{summary}"

    except Exception as e:
        return handle_api_error(e, "获取小说收藏")


async def tool_download_novel(novel_id: Optional[int] = None,
                              novel_ids: Optional[List[int]] = None) -> str:
    """Download novel tool implementation - synchronous for error visibility."""
    if not novel_id and not novel_ids:
        return "错误：必须提供 novel_id (单个ID) 或 novel_ids (ID列表) 参数之一。"

    id_list = []
    if novel_id:
        id_list.append(novel_id)
    if novel_ids:
        id_list.extend(novel_ids)

    unique_ids = sorted(list(set(id_list)))

    results = []
    for an_id in unique_ids:
        try:
            await refresh_token_if_needed()

            # 获取小说元数据
            try:
                detail_result = await asyncio.to_thread(state.api.novel_detail, an_id)
            except Exception as e:
                results.append(f"[{an_id}] 获取元数据异常: {e}")
                continue

            if not detail_result or 'error' in detail_result:
                err = detail_result.get('error', {}) if detail_result else {}
                results.append(f"[{an_id}] 获取元数据失败: {err.get('message', 'API返回空')}")
                continue

            novel = detail_result['novel']

            # 获取小说正文
            try:
                webview_result = await asyncio.to_thread(state.api.webview_novel, an_id)
            except Exception as e:
                results.append(f"[{an_id}] 获取正文异常: {e}")
                continue

            if not webview_result or 'error' in webview_result:
                err = webview_result.get('error', {}) if webview_result else {}
                results.append(f"[{an_id}] 获取正文失败: {err.get('message', 'API返回空')}")
                continue

            novel_text = webview_result.get('text', '')
            if not novel_text:
                results.append(f"[{an_id}] 正文为空")
                continue

            # 保存文件 - 复用路径生成逻辑
            compat_dict = {
                'id': an_id,
                'title': novel.get('title', 'Untitled'),
                'user': novel.get('user', {}),
                'type': 'novel',
                'tags': novel.get('tags', []),
            }
            from pixiv_mcp_server.utils import _generate_path_from_template, _generate_filename
            save_dir = Path(state.download_path) / _generate_path_from_template(compat_dict)
            save_dir.mkdir(parents=True, exist_ok=True)
            filename = _generate_filename(compat_dict) + '.txt'
            filepath = save_dir / filename

            await asyncio.to_thread(filepath.write_text, novel_text, encoding='utf-8')
            results.append(f"[{an_id}] 下载成功 → {filepath}")

        except Exception as e:
            results.append(f"[{an_id}] 下载异常: {e}")

    return f"下载完成 ({len(results)}/{len(unique_ids)})：\n" + "\n".join(results)


async def tool_novel_series(series_id: int) -> str:
    """Novel series tool implementation."""
    try:
        await refresh_token_if_needed()

        try:
            json_result = await asyncio.to_thread(state.api.novel_series, series_id)
        except Exception as raw_e:
            return f"获取系列详情异常: {type(raw_e).__name__}: {raw_e}"

        if not json_result:
            return f"无法获取系列 {series_id} 的详情: API返回空。"
        if 'error' in json_result:
            return f"无法获取系列 {series_id}: API错误 {json_result['error']}"

        series_detail = json_result.get('novel_series_detail', {})
        novel_list = json_result.get('novels', [])

        series_name = series_detail.get('title', 'Unknown')
        series_caption = series_detail.get('caption', '')
        total = series_detail.get('total', 0)

        result = f"系列: {series_name} (ID: {series_id})\n包含 {total} 本小说"
        if series_caption:
            result += f"\n简介: {series_caption[:300]}"

        if novel_list:
            summaries = []
            for novel in novel_list[:10]:
                title = novel.get('title', 'Untitled')
                nid = novel.get('id', 0)
                summaries.append(f"  - [{nid}] {title}")
            result += f"\n\n收录小说（显示前10个）：\n" + "\n".join(summaries)

        return result

    except Exception as e:
        return handle_api_error(e, f"获取系列详情 {series_id}")


async def tool_novel_comments(novel_id: int, offset: int = 0,
                              include_total_comments: bool = False) -> str:
    """Novel comments tool implementation."""
    try:
        await refresh_token_if_needed()

        try:
            json_result = await asyncio.to_thread(
                state.api.novel_comments, novel_id, offset=offset,
                include_total_comments=include_total_comments
            )
        except Exception as raw_e:
            return f"获取小说评论异常: {type(raw_e).__name__}: {raw_e}"

        if not json_result:
            return f"无法获取小说 {novel_id} 的评论: API返回空。"
        if 'error' in json_result:
            return f"无法获取小说 {novel_id}: API错误 {json_result['error']}"

        comments = json_result.get('comments', [])
        total = json_result.get('total_comments', 0)

        if not comments:
            return f"小说 {novel_id} 暂无评论。"

        comment_list = []
        for c in comments[:10]:
            user = c.get('user', {})
            username = user.get('name', 'Anonymous')
            text = c.get('comment', '')
            comment_list.append(f"[{username}]: {text[:200]}")

        result = f"小说 {novel_id} 的评论（共{total}条，显示前{len(comment_list)}条）：\n\n" + "\n\n".join(comment_list)
        return result

    except Exception as e:
        return handle_api_error(e, f"获取小说评论")



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
        logger.info(f"Download path template: {state.download_path_template or '(none, flat structure)'}")
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