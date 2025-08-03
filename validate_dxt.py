#!/usr/bin/env python3
"""
Pixiv MCP Server DXT Validation Script

This script validates that the DXT extension is properly structured
and all components are correctly configured.
"""

import json
import os
import sys
from pathlib import Path

def validate_manifest():
    """Validate the manifest.json file."""
    print("🔍 Validating manifest.json...")
    
    manifest_path = Path("manifest.json")
    if not manifest_path.exists():
        print("❌ manifest.json not found")
        return False
    
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
        
        # Check required fields
        required_fields = ['name', 'version', 'description', 'server']
        for field in required_fields:
            if field not in manifest:
                print(f"❌ Missing required field: {field}")
                return False
        
        # Check server configuration
        server = manifest.get('server', {})
        mcp_config = server.get('mcp_config', {})
        if 'command' not in mcp_config:
            print("❌ Missing server.mcp_config.command")
            return False
        
        if 'args' not in mcp_config:
            print("❌ Missing server.mcp_config.args")
            return False
        
        # Check tools list
        tools = manifest.get('tools', [])
        if len(tools) == 0:
            print("❌ No tools defined")
            return False
        
        print(f"✅ Manifest valid - {len(tools)} tools defined")
        return True
        
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in manifest.json: {e}")
        return False
    except Exception as e:
        print(f"❌ Error reading manifest.json: {e}")
        return False

def validate_server_structure():
    """Validate the server directory structure."""
    print("🔍 Validating server structure...")
    
    server_dir = Path("server")
    if not server_dir.exists():
        print("❌ server/ directory not found")
        return False
    
    main_py = server_dir / "main.py"
    if not main_py.exists():
        print("❌ server/main.py not found")
        return False
    
    # Check if main.py has the required structure
    try:
        with open(main_py, 'r', encoding='utf-8') as f:
            content = f.read()
        
        required_imports = [
            'from mcp.server',
            'import asyncio',
            'from pixiv_mcp_server'
        ]
        
        for import_stmt in required_imports:
            if import_stmt not in content:
                print(f"❌ Missing import in main.py: {import_stmt}")
                return False
        
        # Check for main function
        if 'async def main()' not in content:
            print("❌ Missing main() function in server/main.py")
            return False
        
        print("✅ Server structure valid")
        return True
        
    except Exception as e:
        print(f"❌ Error reading server/main.py: {e}")
        return False

def validate_dependencies():
    """Validate that all dependencies are properly configured."""
    print("🔍 Validating dependencies...")
    
    # Check package.json
    package_json = Path("package.json")
    if not package_json.exists():
        print("❌ package.json not found")
        return False
    
    # Check requirements.txt
    requirements_txt = Path("requirements.txt")
    if not requirements_txt.exists():
        print("❌ requirements.txt not found")
        return False
    
    try:
        with open(requirements_txt, 'r', encoding='utf-8') as f:
            requirements = f.read()
        
        required_packages = [
            'mcp>=1.0.0',
            'pixivpy3>=3.7.0',
            'aiohttp>=3.8.0'
        ]
        
        for package in required_packages:
            if package not in requirements:
                print(f"❌ Missing required package: {package}")
                return False
        
        print("✅ Dependencies valid")
        return True
        
    except Exception as e:
        print(f"❌ Error reading requirements.txt: {e}")
        return False

def validate_dxt_package():
    """Validate the built DXT package."""
    print("🔍 Validating DXT package...")
    
    # Look for .dxt file
    dxt_files = list(Path(".").glob("*.dxt"))
    if not dxt_files:
        print("❌ No .dxt file found - run 'dxt pack' first")
        return False
    
    dxt_file = dxt_files[0]
    file_size = dxt_file.stat().st_size
    
    # Check reasonable file size (should be several MB)
    if file_size < 1024 * 1024:  # Less than 1MB
        print(f"❌ DXT file seems too small: {file_size / 1024:.1f}KB")
        return False
    
    print(f"✅ DXT package valid: {dxt_file.name} ({file_size / 1024 / 1024:.1f}MB)")
    return True

def validate_original_structure():
    """Validate that original project structure is intact."""
    print("🔍 Validating original project structure...")
    
    required_files = [
        "pixiv_mcp_server/__main__.py",
        "pixiv_mcp_server/tools.py",
        "pixiv_mcp_server/state.py",
        "pyproject.toml",
        "get_token.py"
    ]
    
    for file_path in required_files:
        if not Path(file_path).exists():
            print(f"❌ Missing original file: {file_path}")
            return False
    
    print("✅ Original project structure intact")
    return True

def main():
    """Run all validation checks."""
    print("🚀 Pixiv MCP Server DXT Validation")
    print("=" * 40)
    
    checks = [
        ("Manifest", validate_manifest),
        ("Server Structure", validate_server_structure),
        ("Dependencies", validate_dependencies),
        ("Original Structure", validate_original_structure),
        ("DXT Package", validate_dxt_package)
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ {name} validation failed with error: {e}")
            results.append((name, False))
        print()
    
    # Summary
    print("📊 Validation Summary")
    print("=" * 20)
    
    all_passed = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{name:20} {status}")
        if not passed:
            all_passed = False
    
    print()
    if all_passed:
        print("🎉 All validations passed! Your DXT extension is ready.")
        print("📦 You can now install the .dxt file in Claude Desktop.")
        return 0
    else:
        print("⚠️  Some validations failed. Please fix the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())