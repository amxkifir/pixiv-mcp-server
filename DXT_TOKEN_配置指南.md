# DXT Token 配置指南

## 🔧 问题说明

当 Pixiv MCP Server 打包为 DXT 扩展后，由于 DXT 包是只读的，无法通过修改环境变量文件来设置 Pixiv refresh token。为了解决这个问题，我们提供了运行时配置方案。

## 💡 解决方案

### 方案一：运行时设置 Token（推荐）

安装 DXT 扩展后，使用 `set_refresh_token` 工具来配置您的 Pixiv token：

```
使用 set_refresh_token 工具，参数：
{
  "refresh_token": "您的_refresh_token_这里"
}
```

**优势：**
- ✅ 无需重新打包
- ✅ 即时生效
- ✅ 支持 token 更新
- ✅ 自动验证 token 有效性

### 方案二：Claude Desktop 配置

在 Claude Desktop 的配置文件中设置环境变量：

**Windows 配置文件位置：**
```
%APPDATA%\Claude\claude_desktop_config.json
```

**macOS 配置文件位置：**
```
~/Library/Application Support/Claude/claude_desktop_config.json
```

**配置示例：**
```json
{
  "mcpServers": {
    "pixiv-mcp-server": {
      "command": "dxt",
      "args": ["run", "pixiv-mcp-server.dxt"],
      "env": {
        "PIXIV_REFRESH_TOKEN": "您的_refresh_token_这里",
        "DOWNLOAD_PATH": "C:\\Downloads\\Pixiv",
        "FILENAME_TEMPLATE": "{author} - {title}_{id}"
      }
    }
  }
}
```

## 🚀 快速配置步骤

### 步骤 1：获取 Refresh Token

1. 运行 token 获取脚本：
   ```bash
   python get_token.py
   ```

2. 按照提示完成 Pixiv 登录

3. 复制获得的 refresh token

### 步骤 2：配置 Token

**使用方案一（推荐）：**

1. 在 Claude Desktop 中找到 Pixiv MCP Server 扩展
2. 使用 `set_refresh_token` 工具
3. 输入您的 refresh token
4. 系统会自动验证并完成认证

**使用方案二：**

1. 编辑 Claude Desktop 配置文件
2. 添加环境变量配置
3. 重启 Claude Desktop

### 步骤 3：验证配置

使用任意 Pixiv 功能测试，例如：
```
使用 illust_recommended 工具获取推荐作品
```

如果返回作品列表，说明配置成功！

## 🔄 Token 更新

当您的 refresh token 过期时：

1. **运行时更新（推荐）：**
   - 重新获取新的 refresh token
   - 使用 `set_refresh_token` 工具更新

2. **配置文件更新：**
   - 更新 Claude Desktop 配置文件
   - 重启 Claude Desktop

## 🛠️ 故障排除

### 认证失败

**错误信息：** "错误：未认证"

**解决方案：**
1. 检查 refresh token 是否正确
2. 使用 `refresh_token` 工具重新认证
3. 如果仍然失败，重新获取 refresh token

### Token 无效

**错误信息：** "认证失败: ..."

**解决方案：**
1. 确认 token 格式正确（无多余空格）
2. 重新运行 `get_token.py` 获取新 token
3. 检查网络连接和代理设置

### 网络问题

**错误信息：** 连接超时或网络错误

**解决方案：**
1. 检查网络连接
2. 配置代理（如需要）：
   ```json
   "env": {
     "https_proxy": "http://your-proxy:port"
   }
   ```

## 📋 可用工具列表

配置完成后，您可以使用以下 15 个工具：

### 🔧 配置工具
- `set_refresh_token` - 设置/更新 refresh token
- `refresh_token` - 手动刷新认证
- `set_download_path` - 设置下载路径

### 🎨 内容工具
- `search_illust` - 搜索插画
- `illust_detail` - 获取作品详情
- `illust_related` - 相关作品
- `illust_ranking` - 排行榜
- `illust_recommended` - 推荐作品
- `illust_follow` - 关注用户作品
- `trending_tags_illust` - 热门标签

### 👤 用户工具
- `search_user` - 搜索用户
- `user_bookmarks` - 用户收藏
- `user_following` - 关注列表

### 📥 下载工具
- `download` - 下载作品
- `download_random_from_recommendation` - 随机下载推荐

## 🔒 安全提示

- 🔐 Refresh token 具有账户访问权限，请妥善保管
- 🚫 不要在公共场所或不安全的环境中输入 token
- 🔄 定期更新 token 以确保安全
- 📝 建议使用配置文件而非直接在聊天中输入敏感信息

## 📞 技术支持

如果您在配置过程中遇到问题：

1. 📖 查看完整文档：`DXT_README_CN.md`
2. 🔍 检查安装指南：`安装指南.md`
3. 🚀 参考快速开始：`快速开始.md`
4. 🐛 提交问题：[GitHub Issues](https://github.com/amxkifir/pixiv-mcp-server/issues)

---

**注意：** 这个配置指南专门针对 DXT 扩展的特殊需求。如果您使用的是标准 MCP 服务器，可以直接通过环境变量配置。