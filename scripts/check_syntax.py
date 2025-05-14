#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
语法检查工具

该工具用于检查项目中Python文件的语法错误，特别是pydantic兼容性问题。
可以验证代码在不同版本的pydantic下是否能正常工作。
"""

import ast
import importlib
import os
import sys
from pathlib import Path
from typing import List, Optional, Set, Tuple


def check_file_syntax(file_path: Path) -> List[str]:
    """
    检查文件的语法错误。
    
    Args:
        file_path: 要检查的文件路径
        
    Returns:
        错误消息列表
    """
    errors = []
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()
        
        # 检查语法
        ast.parse(source, filename=str(file_path))
    except SyntaxError as e:
        errors.append(f"{file_path}: {e.msg} (行 {e.lineno}, 列 {e.offset})")
    except Exception as e:
        errors.append(f"{file_path}: {str(e)}")
    
    return errors


def check_pydantic_v1_compatibility(file_path: Path) -> List[str]:
    """
    检查文件对pydantic v1的兼容性。
    
    Args:
        file_path: 要检查的文件路径
        
    Returns:
        错误消息列表
    """
    errors = []
    
    # 检查文件是否导入了pydantic
    with open(file_path, "r", encoding="utf-8") as f:
        source = f.read()
    
    if "pydantic" not in source:
        return errors  # 文件不使用pydantic，无需进一步检查
    
    # 尝试进行兼容性检查
    try:
        # 先检查是否安装了v1版本的pydantic
        if not is_pydantic_v1_installed():
            errors.append(f"{file_path}: 无法检查pydantic v1兼容性，pydantic v1未安装")
            return errors
            
        # 检查是否使用了v2特有的特性
        if "pydantic_settings import BaseSettings" in source:
            errors.append(f"{file_path}: 使用了pydantic v2特有的模块 'pydantic_settings'")
        
        # 检查v1中已废弃但在v2中移除的特性
        if "validator(" in source and "pre=True" in source:
            errors.append(f"{file_path}: 使用了在pydantic v2中移除的'pre=True'参数")
            
    except Exception as e:
        errors.append(f"{file_path}: 检查pydantic兼容性时出错: {str(e)}")
    
    return errors


def check_pydantic_v2_compatibility(file_path: Path) -> List[str]:
    """
    检查文件对pydantic v2的兼容性。
    
    Args:
        file_path: 要检查的文件路径
        
    Returns:
        错误消息列表
    """
    errors = []
    
    # 检查文件是否导入了pydantic
    with open(file_path, "r", encoding="utf-8") as f:
        source = f.read()
    
    if "pydantic" not in source:
        return errors  # 文件不使用pydantic，无需进一步检查
    
    # 尝试进行兼容性检查
    try:
        # 先检查是否安装了v2版本的pydantic
        if not is_pydantic_v2_installed():
            errors.append(f"{file_path}: 无法检查pydantic v2兼容性，pydantic v2未安装")
            return errors
            
        # 检查是否使用了v1特有的特性
        if "from pydantic import BaseSettings" in source:
            errors.append(f"{file_path}: 使用了pydantic v1特有的'BaseSettings'导入方式")
            
    except Exception as e:
        errors.append(f"{file_path}: 检查pydantic兼容性时出错: {str(e)}")
    
    return errors


def is_pydantic_v1_installed() -> bool:
    """
    检查是否安装了pydantic v1。
    
    Returns:
        是否安装了pydantic v1
    """
    try:
        import pydantic
        return not hasattr(pydantic, "__version__") or pydantic.__version__.startswith("1.")
    except ImportError:
        return False


def is_pydantic_v2_installed() -> bool:
    """
    检查是否安装了pydantic v2。
    
    Returns:
        是否安装了pydantic v2
    """
    try:
        import pydantic
        return hasattr(pydantic, "__version__") and pydantic.__version__.startswith("2.")
    except ImportError:
        return False


def check_directory(directory: Path, file_patterns: List[str] = None, 
                   exclude_patterns: List[str] = None) -> List[str]:
    """
    检查目录中的Python文件。
    
    Args:
        directory: 要检查的目录路径
        file_patterns: 要包含的文件模式（默认为所有.py文件）
        exclude_patterns: 要排除的文件模式
        
    Returns:
        错误消息列表
    """
    if file_patterns is None:
        file_patterns = ["*.py"]
    if exclude_patterns is None:
        exclude_patterns = ["__pycache__/*", "*.pyc", "venv/*", ".env/*"]
    
    errors = []
    
    # 收集符合条件的文件
    python_files = set()
    for pattern in file_patterns:
        python_files.update(directory.glob(f"**/{pattern}"))
    
    # 排除文件
    for pattern in exclude_patterns:
        exclude_files = set(directory.glob(f"**/{pattern}"))
        python_files -= exclude_files
    
    # 检查每个文件
    for file_path in sorted(python_files):
        # 语法检查
        syntax_errors = check_file_syntax(file_path)
        errors.extend(syntax_errors)
        
        # 如果没有语法错误，进行pydantic兼容性检查
        if not syntax_errors:
            v1_errors = check_pydantic_v1_compatibility(file_path)
            v2_errors = check_pydantic_v2_compatibility(file_path)
            
            # 只添加v1和v2都有的错误
            for error in v1_errors:
                if any(error.split(": ", 1)[1] in v2_error for v2_error in v2_errors):
                    errors.append(error)
    
    return errors


def main():
    """
    主函数。
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="检查项目中Python文件的语法错误和pydantic兼容性")
    parser.add_argument("-d", "--directory", type=str, default=".",
                        help="要检查的目录路径（默认为当前目录）")
    parser.add_argument("-p", "--pattern", type=str, nargs="*", default=["*.py"],
                        help="要检查的文件模式（默认为所有.py文件）")
    parser.add_argument("-e", "--exclude", type=str, nargs="*",
                        default=["__pycache__/*", "*.pyc", "venv/*", ".env/*"],
                        help="要排除的文件模式")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="显示详细信息")
    
    args = parser.parse_args()
    
    directory = Path(args.directory)
    if not directory.exists():
        print(f"错误：目录'{directory}'不存在")
        return 1
    
    if args.verbose:
        print(f"检查目录：{directory}")
        print(f"文件模式：{args.pattern}")
        print(f"排除模式：{args.exclude}")
        print()
    
    errors = check_directory(directory, args.pattern, args.exclude)
    
    if errors:
        print("发现以下错误：")
        for error in errors:
            print(f"- {error}")
        return 1
    else:
        print("未发现语法错误或兼容性问题！")
        return 0


if __name__ == "__main__":
    sys.exit(main()) 