#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Excel to JSON 数据转换程序
功能：读取Excel文件，将数据转换为JSON格式并保存
"""

import json
import os
import sys
from pathlib import Path
from typing import Any


def get_project_root() -> Path:
    """获取项目根目录"""
    # 脚本所在目录的父目录即为项目根目录
    return Path(__file__).parent.parent


def validate_excel_file(file_path: Path) -> bool:
    """
    验证Excel文件是否存在且可读
    
    Args:
        file_path: Excel文件路径
        
    Returns:
        bool: 验证是否通过
    """
    if not file_path.exists():
        print(f"错误：文件不存在 - {file_path}")
        return False
    
    if not file_path.is_file():
        print(f"错误：路径不是文件 - {file_path}")
        return False
    
    # 检查文件扩展名
    valid_extensions = ['.xls', '.xlsx', '.xlsm']
    if file_path.suffix.lower() not in valid_extensions:
        print(f"错误：不支持的文件格式 '{file_path.suffix}'，请使用 .xls 或 .xlsx 格式")
        return False
    
    return True


def read_excel_file(file_path: Path) -> tuple[list[str], list[dict[str, Any]]]:
    """
    读取Excel文件内容
    
    Args:
        file_path: Excel文件路径
        
    Returns:
        tuple: (表头列表, 数据记录列表)
        
    Raises:
        Exception: 读取过程中的各种异常
    """
    try:
        import pandas as pd
    except ImportError:
        print("错误：缺少pandas库，请先安装: pip install pandas xlrd openpyxl")
        raise
    
    try:
        # 读取Excel文件，第一行作为表头
        print(f"正在读取Excel文件: {file_path}")
        df = pd.read_excel(file_path, header=0)
        
        # 获取表头
        headers = df.columns.tolist()
        print(f"发现 {len(headers)} 个字段: {', '.join(headers)}")
        
        # 将DataFrame转换为字典列表
        records = df.to_dict(orient='records')
        print(f"读取到 {len(records)} 条数据记录")
        
        return headers, records
        
    except Exception as e:
        print(f"读取Excel文件时出错: {e}")
        raise


import math

def clean_value(value: Any) -> Any:
    """
    清理数据值，将NaN/Infinity转换为None
    
    Args:
        value: 原始值
        
    Returns:
        Any: 清理后的值
    """
    if value is None:
        return None
    
    # 检查是否为NaN（pandas的NaN是float类型）
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
    
    return value

def clean_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    清理记录列表中的所有NaN值
    
    Args:
        records: 原始记录列表
        
    Returns:
        list[dict[str, Any]]: 清理后的记录列表
    """
    cleaned_records = []
    for record in records:
        cleaned_record = {key: clean_value(value) for key, value in record.items()}
        cleaned_records.append(cleaned_record)
    return cleaned_records

def convert_to_json(headers: list[str], records: list[dict[str, Any]]) -> str:
    """
    将数据转换为JSON格式字符串
    
    Args:
        headers: 表头列表
        records: 数据记录列表
        
    Returns:
        str: 格式化后的JSON字符串
        
    Raises:
        Exception: JSON序列化错误
    """
    try:
        # 清理记录中的NaN值
        cleaned_records = clean_records(records)
        
        # 构建输出数据结构
        output_data = {
            "metadata": {
                "total_records": len(cleaned_records),
                "fields": headers,
                "field_count": len(headers)
            },
            "data": cleaned_records
        }
        
        # 转换为JSON字符串，确保中文字符正常显示
        json_str = json.dumps(
            output_data,
            ensure_ascii=False,
            indent=2,
            default=str  # 处理非标准JSON类型（如日期）
        )
        
        return json_str
        
    except TypeError as e:
        print(f"JSON序列化错误: {e}")
        raise
    except Exception as e:
        print(f"转换JSON时发生未知错误: {e}")
        raise


def write_json_file(json_str: str, output_path: Path) -> bool:
    """
    将JSON字符串写入文件
    
    Args:
        json_str: JSON格式字符串
        output_path: 输出文件路径
        
    Returns:
        bool: 写入是否成功
    """
    try:
        # 确保输出目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 写入文件，使用UTF-8编码
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(json_str)
        
        print(f"JSON文件已保存: {output_path}")
        return True
        
    except PermissionError:
        print(f"错误：没有权限写入文件 - {output_path}")
        return False
    except Exception as e:
        print(f"写入JSON文件时出错: {e}")
        return False


def validate_json_file(file_path: Path, expected_records: int) -> bool:
    """
    验证生成的JSON文件
    
    Args:
        file_path: JSON文件路径
        expected_records: 期望的数据记录数
        
    Returns:
        bool: 验证是否通过
    """
    try:
        # 检查文件是否存在
        if not file_path.exists():
            print(f"验证失败：文件不存在 - {file_path}")
            return False
        
        # 读取并解析JSON
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 验证JSON格式
        data = json.loads(content)
        
        # 验证数据结构
        if not isinstance(data, dict):
            print("验证失败：JSON根元素不是对象")
            return False
        
        if 'data' not in data:
            print("验证失败：缺少'data'字段")
            return False
        
        if 'metadata' not in data:
            print("验证失败：缺少'metadata'字段")
            return False
        
        # 验证记录数
        actual_records = len(data['data'])
        if actual_records != expected_records:
            print(f"验证失败：记录数不匹配 (期望: {expected_records}, 实际: {actual_records})")
            return False
        
        # 验证文件大小
        file_size = file_path.stat().st_size
        print(f"验证通过：")
        print(f"  - 文件大小: {file_size} 字节")
        print(f"  - 数据记录数: {actual_records}")
        print(f"  - 字段数: {data['metadata'].get('field_count', 'N/A')}")
        
        return True
        
    except json.JSONDecodeError as e:
        print(f"验证失败：JSON格式错误 - {e}")
        return False
    except Exception as e:
        print(f"验证过程中发生错误: {e}")
        return False


def main():
    """主函数"""
    print("=" * 60)
    print("Excel to JSON 数据转换程序")
    print("=" * 60)
    
    # 获取项目根目录
    project_root = get_project_root()
    print(f"项目根目录: {project_root}")
    
    # 定义输入输出路径
    input_file = project_root / "public" / "BUG统计数据.xls"
    output_file = project_root / "public" / "BUG统计数据.json"
    
    print(f"输入文件: {input_file}")
    print(f"输出文件: {output_file}")
    print("-" * 60)
    
    try:
        # 步骤1: 验证输入文件
        if not validate_excel_file(input_file):
            sys.exit(1)
        
        # 步骤2: 读取Excel文件
        headers, records = read_excel_file(input_file)
        
        if len(records) == 0:
            print("警告：Excel文件中没有数据记录")
        
        # 步骤3: 转换为JSON
        print("-" * 60)
        print("正在转换为JSON格式...")
        json_str = convert_to_json(headers, records)
        
        # 步骤4: 写入JSON文件
        if not write_json_file(json_str, output_file):
            sys.exit(1)
        
        # 步骤5: 验证生成的文件
        print("-" * 60)
        print("正在验证生成的JSON文件...")
        if not validate_json_file(output_file, len(records)):
            sys.exit(1)
        
        print("-" * 60)
        print("转换完成！")
        print(f"输出文件: {output_file}")
        
    except Exception as e:
        print(f"-" * 60)
        print(f"程序执行失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
