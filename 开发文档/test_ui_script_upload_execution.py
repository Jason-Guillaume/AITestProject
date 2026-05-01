"""
UI自动化脚本上传与执行功能测试脚本

测试内容：
1. 上传LINEAR脚本
2. 上传POM脚本（ZIP包）
3. 执行脚本
4. 查询执行日志
5. 查询执行历史
"""

import requests
import time
import json
from pathlib import Path

# API基础URL
BASE_URL = "http://localhost:8000/api/assistant"

# 测试用例1：上传LINEAR脚本
def test_upload_linear_script():
    """测试上传单个Python文件"""
    print("\n=== 测试1：上传LINEAR脚本 ===")

    # 创建测试脚本内容
    script_content = """
import pytest

def test_example():
    '''示例测试用例'''
    print("执行测试用例")
    assert 1 + 1 == 2
    print("测试通过")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
"""

    # 保存到临时文件
    temp_file = Path("test_linear.py")
    temp_file.write_text(script_content, encoding='utf-8')

    try:
        # 上传脚本
        with open(temp_file, 'rb') as f:
            files = {'file_path': ('test_linear.py', f, 'text/x-python')}
            data = {
                'name': 'LINEAR测试脚本',
                'script_type': 'LINEAR',
                'entry_point': 'test_linear.py'
            }

            response = requests.post(
                f"{BASE_URL}/ui-scripts/",
                files=files,
                data=data
            )

        if response.status_code == 201:
            result = response.json()
            print(f"✓ 上传成功，脚本ID: {result['id']}")
            print(f"  名称: {result['name']}")
            print(f"  类型: {result['script_type']}")
            return result['id']
        else:
            print(f"✗ 上传失败: {response.status_code}")
            print(f"  错误: {response.text}")
            return None

    finally:
        # 清理临时文件
        if temp_file.exists():
            temp_file.unlink()


# 测试用例3：执行脚本
def test_execute_script(script_id):
    """测试执行脚本"""
    print(f"\n=== 测试3：执行脚本 (ID: {script_id}) ===")

    response = requests.post(
        f"{BASE_URL}/ui-script-executions/execute/",
        json={
            'script_id': script_id,
            'triggered_by': 'test'
        }
    )

    if response.status_code == 202:
        result = response.json()
        print(f"✓ 执行已启动")
        print(f"  执行ID: {result['execution_id']}")
        print(f"  状态: {result['status_display']}")
        return result['id'], result['execution_id']
    else:
        print(f"✗ 执行失败: {response.status_code}")
        print(f"  错误: {response.text}")
        return None, None


# 测试用例4：查询执行日志
def test_get_execution_logs(execution_id):
    """测试获取执行日志"""
    print(f"\n=== 测试4：查询执行日志 (ID: {execution_id}) ===")

    # 等待执行开始
    time.sleep(2)

    response = requests.get(
        f"{BASE_URL}/ui-script-executions/{execution_id}/logs/"
    )

    if response.status_code == 200:
        result = response.json()
        print(f"✓ 获取日志成功，共 {result['total']} 条")

        # 显示前10条日志
        for log in result['logs'][:10]:
            print(f"  [{log['type']}] {log['message'][:80]}")

        return True
    else:
        print(f"✗ 获取日志失败: {response.status_code}")
        return False


# 主测试流程
def main():
    """主测试流程"""
    print("=" * 60)
    print("UI自动化脚本上传与执行功能测试")
    print("=" * 60)

    # 测试1：上传LINEAR脚本
    linear_script_id = test_upload_linear_script()

    if linear_script_id:
        # 测试3：执行LINEAR脚本
        execution_id, execution_uuid = test_execute_script(linear_script_id)

        if execution_id:
            # 测试4：查询执行日志
            test_get_execution_logs(execution_id)

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
