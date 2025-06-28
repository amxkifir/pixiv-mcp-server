# Pixiv MCP 服务器

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

这是一个基于Pixiv API的Model Context Protocol (MCP)服务器实现，提供完整的Pixiv功能集成。

## 功能特性

- 📥 支持插画、漫画和Ugoira动图下载
- 🔍 全面的搜索功能（标签、用户、排行榜等）
- 🔑 安全的令牌认证管理
- ⚡ 后台异步下载处理
- 🎨 智能文件命名和存储管理

## 安装指南

### 前置要求
- Python 3.8+
- FFmpeg（用于Ugoira转换）

### 安装步骤
1. 克隆仓库：
   ```bash
   git clone https://github.com/your-username/pixiv-mcp-server.git
   cd pixiv-mcp-server
   ```

2. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```

3. 配置环境：
   - 复制`.env.example`为`.env`
   - 在`.env`中添加您的Pixiv Refresh Token

4. 运行服务器：
   ```bash
   python pixiv_mcp_server.py
   ```

## 使用说明

### 获取API令牌
使用内置工具获取Pixiv API令牌：
```bash
python get_token.py
```

### 基本命令
启动MCP服务器后，您可以使用以下工具：
```json
{
  "set_download_path": "设置下载路径",
  "auth": "认证Pixiv账户",
  "download": "下载指定作品",
  "search_illust": "搜索插画",
  "user_bookmarks": "获取用户收藏"
  // 更多工具请查看API文档
}
```

## API文档
完整的API文档请参考[API参考文档](docs/API_REFERENCE.md)

## 贡献指南
欢迎提交Issue和Pull Request！请确保：
1. 遵循现有代码风格
2. 添加适当的单元测试
3. 更新相关文档

## 许可证
本项目采用[MIT许可证](LICENSE)
