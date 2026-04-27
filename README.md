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

按终端提示完成 OAuth 登录，自动生成 `.env` 文件。**`.env` 仅供终端直接启动时读取，MCP 客户端（Cherry Studio 等）不会自动加载 `.env`，需在客户端配置界面手动填入环境变量。**

## 配置 MCP 客户端

```json
{
  "mcpServers": {
    "pixiv": {
      "command": "uv",
      "args": [
        "--directory", "/path/to/pixiv-mcp-server",
        "run", "pixiv-mcp-server"
      ],
      "env": {
        "PIXIV_REFRESH_TOKEN": "从 .env 复制",
        "DOWNLOAD_PATH": "/path/to/downloads",
        "DOWNLOAD_PATH_TEMPLATE": "{type}/{author}/{series}",
        "FILENAME_TEMPLATE": "{author} - {title}_{id}"
      }
    }
  }
}
```

> **`DOWNLOAD_PATH` 必须使用绝对路径。** MCP 进程的工作目录不一定在项目根，相对路径（如 `./downloads`）会导致文件写入预期之外的位置。

## 下载路径说明

最终文件路径由三个变量拼接而成：

```
{DOWNLOAD_PATH} / {DOWNLOAD_PATH_TEMPLATE} / {FILENAME_TEMPLATE}.扩展名
```

### DOWNLOAD_PATH（下载根目录）

所有下载文件的根目录，**必须使用绝对路径**。

### DOWNLOAD_PATH_TEMPLATE（子目录模板）

控制文件存放的子文件夹层级。可用变量：

| 变量 | 来源 | 说明 |
|------|------|------|
| `{type}` | 自动设定 | `illust` / `novel` |
| `{author}` | 作者名 | 非法文件名字符自动清理 |
| `{series}` | 小说系列名 | **仅小说有此字段。有系列时归入系列子文件夹，无系列时为空**，路径自动退化为上一级 |
| `{tag}` | 第一标签名 | 插画和小说均可用 |
| `{id}` | 作品 ID | |
| `{title}` | 作品标题 | |

默认值：`{type}/{author}/{series}`

### FILENAME_TEMPLATE（文件名模板）

控制单文件命名，可用变量：`{author}` `{title}` `{id}`。默认 `{author} - {title}_{id}`。

---

## 环境变量一览

| 变量 | 必需 | 说明 | 默认值 |
|------|------|------|--------|
| `PIXIV_REFRESH_TOKEN` | 是 | OAuth refresh token | - |
| `DOWNLOAD_PATH` | 否 | 下载根目录，**强烈建议绝对路径** | `./downloads` |
| `DOWNLOAD_PATH_TEMPLATE` | 否 | 子目录结构模板 | `{type}/{author}/{series}` |
| `FILENAME_TEMPLATE` | 否 | 文件命名模板 | `{author} - {title}_{id}` |

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

## 下载效果示例

```
{下载根目录}/
├── illust/画师A/                         ← 插画 {type}=illust
│   └── 画师A - 作品名_12345678.jpg
├── novel/作者B/                          ← 小说无系列，{series}为空
│   └── 作者B - 短篇_87654321.txt
└── novel/作者C/系列名/                   ← 小说有系列，自动归入子文件夹
    └── 作者C - 第一章_11111111.txt
```

## 免责声明

请遵守 Pixiv 用户协议，尊重版权和创作者权益。开发者不对账号相关问题承担责任。

---

> 本项目代码由 AI 生成。如有问题欢迎 [提交 Issue](https://github.com/amxkifir/pixiv-mcp-server/issues)。
