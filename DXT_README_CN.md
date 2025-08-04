# Pixiv MCP 服务器 - 桌面扩展 (DXT)

一个强大的 Pixiv 工具集，通过模型上下文协议 (MCP) 为大型语言模型提供服务。

## 🌟 功能特色

### 🔍 多维度搜索
- **关键词搜索** - 按标题、标签或描述搜索插画
- **用户搜索** - 查找特定艺术家和创作者
- **标签搜索** - 探索热门和趋势标签
- **排行榜** - 浏览每日、每周、每月热门作品
- **趋势内容** - 发现当前流行的艺术作品
- **相关作品** - 基于现有作品找到相似内容

### 📥 智能下载
- **单个/批量下载** - 支持单张或多张作品同时下载
- **异步处理** - 高效的并发下载管理
- **智能文件组织** - 多页作品和动图自动创建子文件夹
- **FFmpeg 转换** - 自动将 Ugoira 动图转换为 GIF/MP4
- **随机下载** - 从推荐中随机下载作品
- **自定义文件名** - 可配置的文件命名模板

### 🌐 社区内容浏览
- **个性化推荐** - 基于您的喜好获取推荐内容
- **关注动态** - 查看关注艺术家的最新作品
- **收藏管理** - 浏览和管理您的收藏
- **作品详情** - 获取完整的作品信息和统计数据

### 🔐 安全认证
- **OAuth 2.0 PKCE** - 安全的现代认证流程
- **自动令牌刷新** - 无缝的会话管理
- **错误处理** - 强大的认证错误恢复
- **本地存储** - 令牌安全存储在本地

## 📋 系统要求

- **Python** 3.10 或更高版本
- **Claude Desktop** 最新版本
- **FFmpeg** (可选，用于动图转换)
- **网络连接** 访问 Pixiv API

## 🚀 快速开始

### 安装扩展

1. **下载 DXT 文件**
   - 获取 `pixiv-mcp-server-2.0.0.dxt` 文件

2. **安装到 Claude Desktop**
   - 双击 `.dxt` 文件
   - 或拖拽到 Claude Desktop 窗口
   - 或使用 Claude Desktop 的"安装扩展"选项

3. **按照安装提示操作**
   - Claude Desktop 将验证扩展
   - 出现提示时接受安装
   - **重要：** 由于 DXT 包是只读的，推荐使用 `set_refresh_token` 工具进行运行时配置
   - 或者在 Claude Desktop 配置文件中设置环境变量（见下方配置部分）

### 获取 Pixiv 令牌

1. **运行令牌获取脚本**
   ```bash
   python get_token.py
   ```

2. **完成 OAuth 流程**
   - 脚本将打开浏览器
   - 登录您的 Pixiv 账户
   - 授权应用访问

3. **复制刷新令牌**
   - 脚本将显示您的刷新令牌
   - 复制这个长字符串

### 配置扩展

#### 🔧 DXT 专用配置方法

**方法一：运行时配置（推荐）**

安装扩展后，直接使用 `set_refresh_token` 工具：
```
工具：set_refresh_token
参数：{"refresh_token": "您的_refresh_token"}
```

**方法二：Claude Desktop 配置文件**

编辑配置文件（`%APPDATA%\Claude\claude_desktop_config.json`）：
```json
{
  "mcpServers": {
    "pixiv-mcp-server": {
      "command": "dxt",
      "args": ["run", "pixiv-mcp-server.dxt"],
      "env": {
        "PIXIV_REFRESH_TOKEN": "您的_refresh_token",
        "DOWNLOAD_PATH": "C:\\Downloads\\Pixiv",
        "FILENAME_TEMPLATE": "{author} - {title}_{id}"
      }
    }
  }
}
```

#### 📋 配置参数说明

**必需配置：**
- **Pixiv 刷新令牌** - 粘贴从上一步获取的令牌

**可选配置：**
- **下载目录** - 选择文件保存位置（默认：`./downloads`）
- **文件名模板** - 自定义文件命名格式（默认：`{author} - {title}_{id}`）
- **代理 URL** - 如果需要代理访问（格式：`http://host:port`）

> 💡 **提示：** 详细的 DXT token 配置指南请参考 `DXT_TOKEN_配置指南.md`

## 🛠️ 可用工具 (15个)

### 🔧 配置工具
- **set_refresh_token** - 设置/更新 Pixiv refresh token（DXT 专用）
- **set_download_path** - 设置下载路径
- **refresh_token** - 刷新认证令牌

### 搜索与发现

#### `search_illust` - 搜索插画
```
在 Pixiv 上搜索猫咪插画
```

#### `search_user` - 搜索用户
```
查找画猫咪的艺术家
```

#### `illust_ranking` - 浏览排行榜
```
显示今天的插画排行榜
```

#### `trending_tags_illust` - 热门标签
```
获取当前热门的插画标签
```

### 推荐与相关

#### `illust_recommended` - 个性化推荐
```
给我一些个性化的艺术作品推荐
```

#### `illust_related` - 相关作品
```
找到与作品 ID 12345678 相关的插画
```

### 下载管理

#### `download` - 下载作品
```
下载 ID 为 12345678 的作品
```

#### `download_random_from_recommendation` - 随机下载
```
从推荐中随机下载一些作品
```

#### `set_download_path` - 设置下载路径
```
将下载路径设置为 D:/Pixiv_Downloads
```

### 社交功能

#### `illust_follow` - 关注动态
```
显示我关注的艺术家的最新作品
```

#### `user_bookmarks` - 用户收藏
```
显示用户 ID 123456 的公开收藏
```

#### `user_following` - 关注列表
```
显示用户 ID 123456 关注的艺术家
```

### 详情与工具

#### `illust_detail` - 作品详情
```
获取作品 ID 12345678 的详细信息
```

#### `refresh_token` - 刷新令牌
```
刷新我的 Pixiv 认证令牌
```

## ⚙️ 高级功能

### 文件命名模板

自定义下载文件的命名方式：

- `{author}` - 艺术家名称
- `{title}` - 作品标题
- `{id}` - 作品 ID
- `{date}` - 发布日期

**示例模板：**
- `{author} - {title}_{id}` (默认)
- `[{id}] {title} by {author}`
- `{date}_{author}_{title}`

### 代理配置

如果您在防火墙后面或需要代理访问：

```
https_proxy=http://proxy.company.com:8080
```

### 并发下载

系统自动管理下载队列，最多同时进行 5 个下载任务，确保稳定性和性能。

## 🔧 故障排除

### 常见安装问题

**"扩展安装失败"**
- 确保您使用的是最新版本的 Claude Desktop
- 检查 `.dxt` 文件是否完整
- 尝试重启 Claude Desktop

**"找不到 Python"**
- 确保安装了 Python 3.10 或更高版本
- 检查 Python 是否在系统 PATH 中

### 常见配置问题

**"认证失败"**
- 验证刷新令牌是否正确
- 令牌应该是一个长的字母数字字符串
- 尝试使用 `get_token.py` 重新生成令牌

**"网络错误"**
- 检查网络连接
- 如果在防火墙后面，配置代理设置
- 验证是否可以访问 Pixiv

**"下载失败"**
- 检查下载目录是否存在且可写
- 验证磁盘空间是否充足
- 确认作品 ID 是否有效

### 调试模式

启用详细日志记录：
1. 在 Claude Desktop 扩展设置中
2. 添加环境变量：`PIXIV_DEBUG=1`
3. 重启 Claude Desktop
4. 在开发者控制台中查看日志

## 📊 使用统计

扩展包含以下组件：
- **14 个 MCP 工具** - 完整的 Pixiv 功能集
- **2,200+ 文件** - 包含所有依赖项
- **17.3MB 压缩包** - 高效的分发格式
- **本地执行** - 无数据收集或跟踪

## 🔒 隐私与安全

- **本地处理** - 所有操作在您的机器上执行
- **安全令牌存储** - 由 Claude Desktop 加密存储
- **无数据收集** - 不进行分析或跟踪
- **沙盒环境** - 隔离的 Python 执行环境
- **开源透明** - 所有代码公开可审查

## 📄 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

## 🤝 贡献

欢迎贡献！请查看我们的贡献指南：

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

## 📞 支持

如果您遇到问题：

1. **查看故障排除部分** - 常见问题的解决方案
2. **检查日志** - Claude Desktop 开发者控制台
3. **简单测试** - 从基本命令开始
4. **验证配置** - 确认所有设置正确
5. **报告问题** - 在 GitHub 上创建 issue

## 🔗 相关链接

- [GitHub 仓库](https://github.com/amxkifir/pixiv-mcp-server)
- [问题报告](https://github.com/amxkifir/pixiv-mcp-server/issues)
- [Pixiv 官网](https://www.pixiv.net/)
- [MCP 协议文档](https://modelcontextprotocol.io/)

---

**享受使用 Pixiv MCP 服务器！** 🎨✨

通过这个强大的扩展，您可以在 Claude Desktop 中无缝访问 Pixiv 的丰富内容库，发现新的艺术作品，管理您的收藏，并下载您喜爱的插画。