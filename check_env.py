#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import glob
import platform

print("==== 环境检查工具 ====")
print(f"Python版本: {sys.version}")
print(f"系统平台: {platform.platform()}")
print(f"当前工作目录: {os.getcwd()}")

print("\n==== 环境变量检查 ====")
required_vars = [
    "FC_USERNAME", 
    "FC_PASSWORD", 
    "FC_MACHINE_ID", 
    "TELEGRAM_BOT_TOKEN", 
    "TELEGRAM_CHAT_ID"
]

for var in required_vars:
    value = os.getenv(var)
    if value:
        masked = value[:2] + "*" * (len(value) - 4) + value[-2:] if len(value) > 4 else "****"
        print(f"{var}: {masked} [已设置]")
    else:
        print(f"{var}: [未设置]")

print("\n==== 目录内容 ====")
for item in sorted(os.listdir(".")):
    if os.path.isdir(item):
        print(f"📁 {item}/")
    else:
        print(f"📄 {item} ({os.path.getsize(item)} 字节)")

print("\n==== 查找脚本文件 ====")
script_paths = glob.glob("**/*freecloud*py", recursive=True)
if script_paths:
    print("找到以下脚本文件:")
    for path in script_paths:
        print(f"- {path} ({os.path.getsize(path)} 字节)")
else:
    print("未找到任何匹配 *freecloud*py 的脚本文件")

print("\n==== 文件检查 ====")
files_to_check = [
    "freecloud_renewer.py",
    "requirements.txt",
    ".github/workflows/renew.yml"
]

for file_path in files_to_check:
    if os.path.exists(file_path):
        print(f"✅ {file_path} 存在 ({os.path.getsize(file_path)} 字节)")
    else:
        print(f"❌ {file_path} 不存在")

print("\n==== 检查完成 ====") 