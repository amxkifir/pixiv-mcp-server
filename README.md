# Pixiv MCP Server

通过 MCP 协议为 LLM 提供 Pixiv 插画/小说浏览、搜索与下载能力。支持 26 个工具。

## 环境要求

- Python 3.10+
- FFmpeg（可选，Ugoira 动图转 GIF 需要）

## 安装

```bash
git clone https://github.com/amxkifir/pixiv-mcp-server.git
cd pixiv-mcp-server

# 推荐使用 uv
pip install uv
uv venv
uv pip install -e .

# 或使用 pip
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -e .
```

## 获取 Token

```bash
python get_token.py
```

按终端提示完成 OAuth 登录，自动生成 `.env` 文件。

## 配置 MCP 客户端

```json
{
  "mcpServers": {
    "pixiv": {
      "command": "uv",
      "args": [
        "--directory", "项目绝对路径",
        "run", "pixiv-mcp-server"
      ],
      "env": {
        "PIXIV_REFRESH_TOKEN": "从 .env 复制",
        "DOWNLOAD_PATH": "./downloads",
        "DOWNLOAD_PATH_TEMPLATE": "{type}/{author}"
      }
    }
  }
}
```

## 环境变量

| 变量 | 必需 | 说明 | 默认值 |
|------|------|------|--------|
| `PIXIV_REFRESH_TOKEN` | 是 | OAuth refresh token | - |
| `DOWNLOAD_PATH` | 否 | 下载根目录 | `./downloads` |
| `DOWNLOAD_PATH_TEMPLATE` | 否 | 子目录模板，可用 `{type}` `{author}` | `{type}/{author}` |

## 工具列表（26 个）

### 插画

| 工具 | 说明 |
|------|------|
| `search_illust` | 关键词搜索插画 |
| `illust_detail` | 获取插画详情 |
| `illust_ranking` | 排行榜（日/周/月） |
| `illust_recommended` | 个性化推荐 |
| `illust_related` | 相关作品 |
| `illust_follow` | 关注画师最新作品 |
| `trending_tags_illust` | 热门标签 |
| `download` | 下载插画/动图 |
| `download_random_from_recommendation` | 从推荐中随机下载 |

### 小说

| 工具 | 说明 |
|------|------|
| `search_novel` | 搜索小说（支持标签精确/部分匹配） |
| `novel_detail` | 获取小说元数据 |
| `novel_recommended` | 推荐小说 |
| `novel_new` | 最新小说 |
| `novel_follow` | 关注作者新作 |
| `novel_series` | 系列小说 |
| `novel_comments` | 小说评论 |
| `read_novel` | 阅读小说正文 |
| `download_novel` | 下载小说为 .txt |

### 用户

| 工具 | 说明 |
|------|------|
| `search_user` | 搜索用户 |
| `user_bookmarks` | 用户插画收藏 |
| `user_bookmarks_novel` | 用户小说收藏 |
| `user_following` | 用户关注列表 |
| `user_novels` | 用户小说列表 |

### 配置

| 工具 | 说明 |
|------|------|
| `set_download_path` | 设置下载路径 |
| `set_refresh_token` | 更新 refresh token |
| `refresh_token` | 手动刷新认证 |

## 文件名模板

`FILENAME_TEMPLATE` 支持变量：`{author}` `{title}` `{id}`（默认 `{author} - {title}_{id}`）

## 免责声明

请遵守 Pixiv 用户协议，尊重版权和创作者权益。开发者不对账号相关问题承担责任。

---

> 本项目代码由 AI 生成。如有问题欢迎 [提交 Issue](https://github.com/amxkifir/pixiv-mcp-server/issues)。
