# Token 自动刷新功能指南

## 🔄 功能概述

本项目新增了智能的 Pixiv API token 自动刷新机制，解决了 token 快速失效导致的 API 调用失败问题。

## ✨ 新增功能

### 1. 自动 Token 刷新
- **智能检测**：自动识别 token 失效错误（`invalid_grant`、`oauth`、`unauthorized`）
- **自动重试**：检测到 token 失效时自动刷新并重试 API 调用
- **无缝体验**：用户无需手动干预，API 调用自动恢复

### 2. 手动 Token 刷新工具
- **新增工具**：`refresh_token` - 手动刷新 Pixiv API token
- **错误诊断**：提供详细的失败原因和解决建议
- **状态反馈**：实时显示刷新进度和结果

### 3. 增强的错误处理
- **详细错误信息**：区分不同类型的 API 错误
- **智能重试逻辑**：仅在 token 相关错误时触发重试
- **日志记录**：完整的操作日志便于问题排查

## 🛠️ 使用方法

### 自动刷新（推荐）

大多数 API 工具现在都支持自动 token 刷新，无需额外操作：

```python
# 这些工具现在支持自动 token 刷新
- search_illust()          # 搜索插画
- illust_recommended()     # 获取推荐插画
# 更多工具将逐步支持...
```

### 手动刷新

当遇到认证问题时，可以使用新的手动刷新工具：

```python
# 通过 MCP 调用
refresh_token()
```

### 测试功能

运行测试脚本验证功能：

```bash
python test_token_refresh.py
```

## 🔧 技术实现

### 核心函数

#### `refresh_token_if_needed()`
```python
async def refresh_token_if_needed() -> bool:
    """尝试刷新token，返回是否成功"""
```
- 使用现有的 `refresh_token` 自动刷新
- 更新 `state.is_authenticated` 状态
- 返回刷新是否成功

#### `handle_api_error_with_retry()`
```python
async def handle_api_error_with_retry(response, retry_func, *args, **kwargs):
    """处理API错误并在token失效时自动重试"""
```
- 检测 token 相关错误
- 自动调用 `refresh_token_if_needed()`
- 重试原始 API 调用
- 返回错误信息或新的响应结果

### 错误检测逻辑

系统会检测以下错误模式来判断 token 是否失效：
- `invalid_grant`
- `oauth`
- `unauthorized`

## 📋 支持的工具

### 已支持自动刷新的工具
- ✅ `search_illust` - 搜索插画
- ✅ `illust_recommended` - 获取推荐插画
- ✅ `refresh_token` - 手动刷新 token

### 计划支持的工具
- 🔄 `illust_detail` - 插画详情
- 🔄 `illust_related` - 相关插画
- 🔄 `illust_ranking` - 插画排行榜
- 🔄 `search_user` - 搜索用户
- 🔄 `trending_tags_illust` - 热门标签
- 🔄 `illust_follow` - 关注的插画
- 🔄 `user_bookmarks` - 用户收藏
- 🔄 `user_following` - 用户关注

## 🚨 故障排除

### 常见问题

#### 1. "未找到refresh_token"错误
**原因**：环境变量 `PIXIV_REFRESH_TOKEN` 未设置
**解决**：
```bash
python get_token.py
# 选择选项1重新获取token，或选项2刷新现有token
```

#### 2. "Token刷新失败"错误
**可能原因**：
- refresh_token 已过期
- 网络连接问题
- 代理设置问题

**解决步骤**：
1. 检查网络连接
2. 验证代理设置（如果使用）
3. 重新获取 token：`python get_token.py`

#### 3. "重试后仍然失败"错误
**原因**：即使刷新 token 后 API 仍然失败
**解决**：
1. 检查 Pixiv 服务状态
2. 验证 API 参数是否正确
3. 查看详细日志信息

### 日志分析

关键日志信息：
```
INFO - 检测到token失效，正在尝试刷新...
INFO - Token刷新成功
INFO - Token刷新后重试成功
```

错误日志：
```
ERROR - 无法刷新token：未找到refresh_token
ERROR - Token刷新失败: [详细错误信息]
WARNING - 检测到token错误: [错误信息]，尝试刷新token并重试...
```

## 🔮 未来计划

1. **全面支持**：为所有 API 工具添加自动刷新支持
2. **预防性刷新**：在 token 过期前主动刷新（如50分钟时）
3. **智能重试**：添加指数退避重试策略
4. **监控仪表板**：token 状态和使用情况监控
5. **配置选项**：允许用户自定义重试策略

## 📞 技术支持

如果遇到问题：
1. 查看日志文件获取详细错误信息
2. 运行 `python test_token_refresh.py` 进行诊断
3. 检查 `PIXIV_REFRESH_TOKEN` 环境变量设置
4. 确认网络和代理配置正确

---

**注意**：此功能需要有效的 `PIXIV_REFRESH_TOKEN`。如果没有，请先运行 `get_token.py` 获取。