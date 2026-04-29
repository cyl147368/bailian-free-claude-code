#!/usr/bin/env python3
"""
阿里百炼Provider使用示例

演示如何配置和使用带有403错误自动处理功能的阿里百炼Provider
"""

import asyncio
import os
from typing import Any

# 设置环境变量（实际使用时从.env文件加载）
os.environ["BAILIAN_API_KEY"] = "your-api-key-here"
os.environ["BAILIAN_MODELS"] = "qwen-max,qwen-plus,qwen-turbo"
os.environ["MODEL"] = "bailian/qwen-max"


class MockRequest:
    """模拟请求对象"""
    def __init__(self):
        self.model = "qwen-max"
        self.messages = [
            {"role": "user", "content": "你好，请介绍一下你自己"}
        ]
        self.max_tokens = 1000
        self.temperature = 0.7
        self.stream = True
        self.system = None
        self.tools = []
        self.thinking = None


async def example_basic_usage():
    """基本使用示例"""
    from providers.bailian import BailianProvider
    from providers.base import ProviderConfig
    
    print("=== 基本使用示例 ===")
    
    # 创建配置
    config = ProviderConfig(
        api_key=os.getenv("BAILIAN_API_KEY"),
        base_url="https://dashscope.aliyuncs.com/api/v1",
        rate_limit=10,
        rate_window=60,
    )
    
    # 解析备用模型列表
    models_str = os.getenv("BAILIAN_MODELS", "")
    fallback_models = [m.strip() for m in models_str.split(",") if m.strip()]
    
    # 创建provider实例
    provider = BailianProvider(config, bailian_models=fallback_models)
    
    print(f"主模型: qwen-max")
    print(f"备用模型: {fallback_models}")
    print()
    
    # 创建请求
    request = MockRequest()
    
    try:
        # 流式响应（会自动处理403错误）
        print("开始流式响应...")
        async for chunk in provider.stream_response(request):
            # 处理每个chunk
            print(chunk, end="", flush=True)
        print("\n完成！")
        
    except Exception as e:
        print(f"错误: {e}")
    
    finally:
        # 清理资源
        await provider.cleanup()


async def example_error_handling():
    """错误处理示例"""
    from providers.bailian import BailianProvider
    from providers.base import ProviderConfig
    import httpx
    
    print("\n=== 错误处理示例 ===")
    
    config = ProviderConfig(
        api_key="invalid-key",  # 故意使用无效密钥
        base_url="https://dashscope.aliyuncs.com/api/v1",
    )
    
    # 配置多个备用模型
    provider = BailianProvider(
        config, 
        bailian_models=["model1", "model2", "model3"]
    )
    
    request = MockRequest()
    
    try:
        async for chunk in provider.stream_response(request):
            print(chunk, end="")
    except httpx.HTTPStatusError as e:
        print(f"\n捕获到HTTP错误: {e.response.status_code}")
        print("这说明403错误处理机制在工作 - 所有模型都尝试完毕后抛出最终错误")
    except Exception as e:
        print(f"\n捕获到其他错误: {type(e).__name__}: {e}")
    finally:
        await provider.cleanup()


def example_configuration():
    """配置示例"""
    print("\n=== 配置示例 ===")
    
    config_template = """
# .env 文件配置示例

# 阿里百炼API密钥
BAILIAN_API_KEY="sk-your-api-key-here"

# 备用模型列表（逗号分隔）
# 当主模型返回403时，系统会依次尝试这些模型
BAILIAN_MODELS="qwen-max,qwen-plus,qwen-turbo,qwen-long"

# 使用阿里百炼作为默认provider
MODEL="bailian/qwen-max"

# 或者为不同的Claude模型指定不同的百炼模型
MODEL_OPUS="bailian/qwen-max"
MODEL_SONNET="bailian/qwen-plus"
MODEL_HAIKU="bailian/qwen-turbo"

# 速率限制配置（可选）
PROVIDER_RATE_LIMIT=10
PROVIDER_RATE_WINDOW=60
    """
    
    print(config_template)


async def main():
    """主函数"""
    print("阿里百炼Provider使用示例\n")
    
    # 显示配置示例
    example_configuration()
    
    # 注意：以下示例需要有效的API密钥才能正常运行
    print("\n注意：以下示例需要有效的API密钥才能正常运行")
    print("如果没有有效密钥，将展示错误处理流程\n")
    
    # 基本使用示例
    # await example_basic_usage()
    
    # 错误处理示例
    await example_error_handling()
    
    print("\n=== 示例完成 ===")
    print("\n要实际使用，请：")
    print("1. 在.env文件中配置您的BAILIAN_API_KEY")
    print("2. 设置BAILIAN_MODELS为您的备用模型列表")
    print("3. 运行: uv run python examples/bailian_example.py")


if __name__ == "__main__":
    asyncio.run(main())
