#!/usr/bin/env python3
"""
测试token刷新功能的简单脚本

使用方法:
python test_token_refresh.py
"""

import asyncio
import logging
import os
from pathlib import Path

# 添加项目路径到Python路径
import sys
sys.path.insert(0, str(Path(__file__).parent))

from pixiv_mcp_server.state import state
from pixiv_mcp_server.utils import refresh_token_if_needed, handle_api_error_with_retry

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_token_refresh')

async def test_token_refresh():
    """测试token刷新功能"""
    print("=== Pixiv Token 刷新功能测试 ===")
    
    # 检查环境变量
    if not state.refresh_token:
        print("❌ 错误：未找到PIXIV_REFRESH_TOKEN环境变量")
        print("请先设置环境变量或运行 get_token.py 获取token")
        return
    
    print(f"✅ 找到refresh_token: {state.refresh_token[:20]}...")
    
    # 测试手动刷新
    print("\n--- 测试手动token刷新 ---")
    success = await refresh_token_if_needed()
    if success:
        print("✅ 手动token刷新成功")
        state.is_authenticated = True
    else:
        print("❌ 手动token刷新失败")
        return
    
    # 测试API调用
    print("\n--- 测试API调用 ---")
    try:
        # 尝试获取推荐插画
        result = await asyncio.to_thread(state.api.illust_recommended, offset=0)
        
        if result and 'illusts' in result:
            illusts = result.get('illusts', [])
            print(f"✅ API调用成功，获取到 {len(illusts)} 个推荐插画")
            
            # 显示前3个插画信息
            for i, illust in enumerate(illusts[:3]):
                title = illust.get('title', 'Unknown')
                author = illust.get('user', {}).get('name', 'Unknown')
                illust_id = illust.get('id', 'Unknown')
                print(f"  {i+1}. [{illust_id}] {title} - {author}")
        else:
            print(f"⚠️  API调用返回异常结果: {result}")
            
    except Exception as e:
        print(f"❌ API调用失败: {e}")
    
    # 测试自动重试机制
    print("\n--- 测试自动重试机制 ---")
    print("注意：这个测试需要token实际失效才能看到重试效果")
    print("在正常情况下，应该直接返回成功结果")
    
    try:
        # 模拟API调用
        result = await asyncio.to_thread(state.api.illust_recommended, offset=0)
        error, retry_result = await handle_api_error_with_retry(
            result,
            state.api.illust_recommended,
            offset=0
        )
        
        if retry_result:
            print("✅ 自动重试机制工作正常（使用了重试结果）")
        elif error:
            print(f"❌ 自动重试机制检测到错误: {error}")
        else:
            print("✅ 自动重试机制工作正常（无需重试）")
            
    except Exception as e:
        print(f"❌ 自动重试机制测试失败: {e}")
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    # 加载环境变量
    from dotenv import load_dotenv
    load_dotenv()
    
    asyncio.run(test_token_refresh())