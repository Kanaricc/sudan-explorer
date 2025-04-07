#!/usr/bin/env python3

import argparse
import os
from pathlib import Path
from typing import List, Set


def search_file_content(file_path: Path, keyword: str) -> bool:
    """在文件内容中搜索关键字

    Args:
        file_path: 文件路径
        keyword: 要搜索的关键字（不区分大小写）

    Returns:
        bool: 如果找到关键字则返回True，否则返回False
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().lower()
            return keyword.lower() in content
    except UnicodeDecodeError:
        # 如果UTF-8解码失败，尝试其他编码
        try:
            with open(file_path, 'r', encoding='gbk') as f:
                content = f.read().lower()
                return keyword.lower() in content
        except Exception as e:
            print(f"警告: 无法读取文件 {file_path}: {e}")
            return False
    except Exception as e:
        print(f"错误: 处理文件 {file_path} 时出错: {e}")
        return False


def search_json_files(directory: Path, keyword: str) -> List[Path]:
    """搜索目录中包含关键字的JSON文件

    Args:
        directory: 要搜索的目录
        keyword: 要搜索的关键字

    Returns:
        List[Path]: 包含关键字的JSON文件路径列表
    """
    matching_files: List[Path] = []
    processed_files: Set[Path] = set()
    
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.json'):
                file_path = Path(root) / file
                
                # 避免处理重复文件
                if file_path in processed_files:
                    continue
                processed_files.add(file_path)
                
                if search_file_content(file_path, keyword):
                    matching_files.append(file_path)
    
    return matching_files


def main() -> None:
    """主函数，处理命令行参数并执行搜索"""
    parser = argparse.ArgumentParser(description='在JSON文件中搜索关键字')
    parser.add_argument('keyword', help='要搜索的关键字')
    parser.add_argument('--dir', '-d', default='config', help='要搜索的目录，默认为config')
    args = parser.parse_args()
    
    # 构建目录路径
    base_dir = Path(__file__).parent
    search_dir = base_dir / args.dir
    
    if not search_dir.exists() or not search_dir.is_dir():
        print(f"错误: 目录 {search_dir} 不存在或不是一个有效的目录")
        return
    
    print(f"正在搜索目录 {search_dir} 中包含关键字 '{args.keyword}' 的JSON文件...")
    matching_files = search_json_files(search_dir, args.keyword)
    
    if matching_files:
        print(f"\n找到 {len(matching_files)} 个匹配的文件:")
        for file_path in matching_files:
            # 显示相对于项目根目录的路径
            rel_path = file_path.relative_to(base_dir)
            print(f"- {rel_path}")
    else:
        print(f"\n未找到包含关键字 '{args.keyword}' 的JSON文件")


if __name__ == '__main__':
    main()
