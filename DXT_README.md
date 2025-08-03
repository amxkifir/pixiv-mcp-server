# Pixiv MCP Server - Desktop Extension (DXT)

> A powerful Pixiv toolset for Large Language Models via MCP, packaged as a Desktop Extension for easy installation and use.

## 🚀 Quick Installation

### Method 1: Direct Installation (Recommended)

1. Download the `.dxt` file from the releases page
2. Double-click the `.dxt` file to install in Claude Desktop
3. Configure your Pixiv refresh token in the extension settings
4. Start using Pixiv tools in Claude!

### Method 2: Build from Source

1. **Install DXT CLI tools:**
   ```bash
   npm install -g @anthropic-ai/dxt
   ```

2. **Clone and prepare the project:**
   ```bash
   git clone https://github.com/222wcnm/pixiv-mcp-server.git
   cd pixiv-mcp-server
   ```

3. **Build the DXT extension:**
   ```bash
   dxt pack
   ```

4. **Install the generated `.dxt` file:**
   - Open the generated `.dxt` file with Claude Desktop
   - Follow the installation prompts

## 🔐 Getting Your Pixiv Refresh Token

**Important:** You need a valid Pixiv refresh token to use this extension.

### Option 1: Use the included token generator

1. Run the token generator script:
   ```bash
   python get_token.py
   ```

2. Follow the OAuth flow in your browser
3. Copy the generated refresh token
4. Paste it into the extension configuration

### Option 2: Manual token extraction

Refer to the [TOKEN_REFRESH_GUIDE.md](TOKEN_REFRESH_GUIDE.md) for detailed instructions on manually obtaining your refresh token.

## ⚙️ Configuration

After installation, configure the extension with these settings:

| Setting | Description | Required | Default |
|---------|-------------|----------|----------|
| **Pixiv Refresh Token** | Your OAuth refresh token | ✅ Yes | - |
| **Download Directory** | Where to save downloaded files | ❌ No | `./downloads` |
| **Filename Template** | Template for file names | ❌ No | `{author} - {title}_{id}` |
| **Proxy URL** | HTTP proxy if needed | ❌ No | - |

### Filename Template Variables

- `{author}` - Artist's name
- `{title}` - Artwork title
- `{id}` - Artwork ID
- `{date}` - Upload date

## 🛠️ Available Tools

### 🔍 Search & Discovery

- **`search_illust`** - Search illustrations by keywords
- **`search_user`** - Find artists and users
- **`illust_ranking`** - Browse daily/weekly/monthly rankings
- **`trending_tags_illust`** - Get trending tags
- **`illust_recommended`** - Get personalized recommendations
- **`illust_related`** - Find related artworks

### 📥 Download & Management

- **`download`** - Download single or multiple artworks
- **`download_random_from_recommendation`** - Download random recommended art
- **`set_download_path`** - Change download location

### 👥 Social Features

- **`illust_follow`** - Browse followed artists' works
- **`user_bookmarks`** - View user bookmarks
- **`user_following`** - Check following lists
- **`illust_detail`** - Get detailed artwork information

### 🔧 Utility

- **`refresh_token`** - Manually refresh authentication

## 🎯 Usage Examples

### Basic Search
```
Search for cat illustrations
```
*Uses: `search_illust` with keyword "cat"*

### Download Artwork
```
Download artwork with ID 12345678
```
*Uses: `download` with illust_id 12345678*

### Browse Rankings
```
Show me today's top illustrations
```
*Uses: `illust_ranking` with mode "day"*

### Get Recommendations
```
Show me some recommended artworks
```
*Uses: `illust_recommended`*

## 🔧 Advanced Features

### Intelligent Download Management

- **Automatic file organization** - Multi-page works get their own folders
- **Ugoira support** - Animated works converted to GIF (requires FFmpeg)
- **Concurrent downloads** - Up to 5 simultaneous downloads
- **Smart filename cleaning** - Prevents filesystem errors

### Authentication Management

- **Auto-refresh** - Tokens refreshed automatically when expired
- **Error recovery** - Automatic retry on authentication failures
- **Detailed diagnostics** - Clear error messages and solutions

### Network Support

- **Proxy support** - Configure HTTP/HTTPS proxies
- **Rate limiting** - Respects Pixiv API limits
- **Timeout handling** - Robust error handling

## 🐛 Troubleshooting

### Common Issues

**"Authentication failed"**
- Check if your refresh token is valid
- Try using the `refresh_token` tool
- Regenerate token using `get_token.py`

**"Network error"**
- Check your internet connection
- Configure proxy if behind corporate firewall
- Verify Pixiv is accessible from your location

**"Download failed"**
- Check download directory permissions
- Ensure sufficient disk space
- Verify artwork ID is correct

### Debug Mode

To enable detailed logging:
1. Set environment variable: `PIXIV_DEBUG=1`
2. Check the extension logs in Claude Desktop

## 📋 System Requirements

- **Python:** 3.10 or higher
- **Operating System:** Windows, macOS, or Linux
- **Claude Desktop:** Latest version with DXT support
- **FFmpeg:** Optional, for Ugoira animation processing

## 🔒 Security & Privacy

- **Local execution** - All processing happens on your machine
- **Secure token storage** - Refresh tokens encrypted by Claude Desktop
- **No data collection** - No usage analytics or tracking
- **Open source** - Full source code available for review

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📞 Support

- **Issues:** [GitHub Issues](https://github.com/222wcnm/pixiv-mcp-server/issues)
- **Documentation:** [Main README](README.md)
- **Token Guide:** [TOKEN_REFRESH_GUIDE.md](TOKEN_REFRESH_GUIDE.md)

---

**Note:** This extension requires a valid Pixiv account and refresh token. Please respect Pixiv's terms of service and rate limits when using this tool.