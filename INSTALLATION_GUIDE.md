# Pixiv MCP Server - DXT Installation & Testing Guide

## 📦 What Was Built

Your Pixiv MCP Server has been successfully packaged as a Desktop Extension (DXT):

- **File:** `pixiv-mcp-server-2.0.0.dxt`
- **Size:** 17.2MB (42.6MB unpacked)
- **Files:** 2,204 total files including all dependencies
- **Format:** Complete, self-contained DXT extension

## 🚀 Installation Steps

### Step 1: Install in Claude Desktop

1. **Locate the DXT file:**
   ```
   D:\新建文件夹 (5)\pixiv-mcp-server\pixiv-mcp-server-2.0.0.dxt
   ```

2. **Install the extension:**
   - Double-click the `.dxt` file
   - OR drag and drop it onto Claude Desktop
   - OR use Claude Desktop's "Install Extension" option

3. **Follow the installation prompts:**
   - Claude Desktop will verify the extension
   - Accept the installation when prompted

### Step 2: Configure the Extension

After installation, you'll need to configure these settings:

#### Required Configuration

**Pixiv Refresh Token** (Required)
- Get your token using the included `get_token.py` script:
  ```bash
  cd "D:\新建文件夹 (5)\pixiv-mcp-server"
  python get_token.py
  ```
- Follow the OAuth flow in your browser
- Copy the generated refresh token
- Paste it into the extension configuration

#### Optional Configuration

**Download Directory**
- Default: `./downloads`
- Choose where you want downloaded files saved
- Extension will create the directory if it doesn't exist

**Filename Template**
- Default: `{author} - {title}_{id}`
- Customize how downloaded files are named
- Available variables: `{author}`, `{title}`, `{id}`, `{date}`

**Proxy URL** (if needed)
- Format: `http://host:port` or `https://host:port`
- Only needed if behind a corporate firewall

## 🧪 Testing the Installation

### Basic Functionality Test

1. **Open Claude Desktop**
2. **Start a new conversation**
3. **Test basic search:**
   ```
   Search for cat illustrations on Pixiv
   ```

4. **Expected result:**
   - Claude should use the `search_illust` tool
   - You should see a list of cat-related artworks
   - Each result should include title, artist, and artwork details

### Advanced Testing

#### Test Rankings
```
Show me today's top illustrations from Pixiv rankings
```

#### Test Recommendations
```
Get some personalized artwork recommendations
```

#### Test Download (if configured)
```
Download artwork with ID 12345678
```

#### Test User Search
```
Find artists who draw cats on Pixiv
```

## 🔧 Troubleshooting

### Common Installation Issues

**"Extension failed to install"**
- Ensure you have the latest Claude Desktop version
- Check that the `.dxt` file isn't corrupted
- Try restarting Claude Desktop

**"Python not found"**
- Ensure Python 3.10+ is installed and in PATH
- The extension includes its own Python environment, but system Python may be needed

### Common Configuration Issues

**"Authentication failed"**
- Verify your refresh token is correct
- Token format should be a long alphanumeric string
- Try regenerating the token with `get_token.py`

**"Network error"**
- Check internet connection
- If behind a firewall, configure proxy settings
- Verify Pixiv is accessible from your location

### Debug Mode

To enable detailed logging:
1. In Claude Desktop, go to extension settings
2. Add environment variable: `PIXIV_DEBUG=1`
3. Restart Claude Desktop
4. Check logs in Claude Desktop's developer console

## 📋 Verification Checklist

- [ ] DXT file built successfully (17.2MB)
- [ ] Extension installs in Claude Desktop without errors
- [ ] Configuration screen appears with all required fields
- [ ] Pixiv refresh token obtained and configured
- [ ] Basic search functionality works
- [ ] All 14 tools are available and functional
- [ ] Download functionality works (if tested)
- [ ] Error handling works gracefully

## 🎯 Available Tools Summary

Your DXT extension includes these 14 tools:

### Search & Discovery
1. `search_illust` - Search illustrations
2. `search_user` - Find artists
3. `illust_ranking` - Browse rankings
4. `trending_tags_illust` - Get trending tags
5. `illust_recommended` - Get recommendations
6. `illust_related` - Find related works

### Download & Management
7. `download` - Download artworks
8. `download_random_from_recommendation` - Download random art
9. `set_download_path` - Change download location

### Social Features
10. `illust_follow` - Browse followed artists
11. `user_bookmarks` - View bookmarks
12. `user_following` - Check following lists
13. `illust_detail` - Get artwork details

### Utility
14. `refresh_token` - Refresh authentication

## 🔒 Security Features

- **Local execution** - All processing on your machine
- **Secure token storage** - Encrypted by Claude Desktop
- **No data collection** - No analytics or tracking
- **Sandboxed environment** - Isolated Python environment

## 📞 Support

If you encounter issues:

1. **Check this guide** for common solutions
2. **Review logs** in Claude Desktop developer console
3. **Test with simple commands** first
4. **Verify configuration** settings
5. **Report issues** on GitHub if problems persist

---

**Congratulations!** Your Pixiv MCP Server is now packaged as a professional DXT extension, ready for distribution and use in Claude Desktop.