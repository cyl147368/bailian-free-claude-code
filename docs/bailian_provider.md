# 阿里百炼平台支持

本实现为free-claude-code项目添加了对阿里百炼（DashScope）平台的支持，并实现了403错误时的自动模型切换功能。

## 功能特性

1. **阿里百炼平台支持**: 完全兼容Anthropic Messages API格式
2. **403错误自动处理**: 当请求返回403错误时，自动切换到下一个可用模型
3. **模型循环机制**: 支持配置多个备用模型，按顺序尝试直到成功

## 配置说明

### 环境变量配置

在 `.env` 文件中添加以下配置：

```bash
# 阿里百炼API密钥
BAILIAN_API_KEY="your-api-key-here"

# 可选：备用模型列表（逗号分隔）
# 当主模型返回403时，系统会依次尝试这些模型
BAILIAN_MODELS="qwen-max,qwen-plus,qwen-turbo"
```

### 模型配置

在MODEL配置中使用bailian provider：

```bash
# 使用阿里百炼作为默认provider
MODEL="bailian/qwen-max"

# 或者为不同的Claude模型指定不同的百炼模型
MODEL_OPUS="bailian/qwen-max"
MODEL_SONNET="bailian/qwen-plus" 
MODEL_HAIKU="bailian/qwen-turbo"
```

## 工作原理

### 403错误处理流程

1. **首次请求**: 使用配置的初始模型发起请求
2. **检测403**: 如果收到HTTP 403错误响应
3. **模型切换**: 从`BAILIAN_MODELS`列表中获取下一个模型
4. **重试请求**: 使用新模型重新发起相同的请求
5. **循环尝试**: 重复步骤2-4，直到成功或所有模型都尝试完毕
6. **最终错误**: 如果所有模型都返回403，则抛出最后一个错误

### 示例场景

假设配置：
```bash
MODEL="bailian/qwen-max"
BAILIAN_MODELS="qwen-plus,qwen-turbo,qwen-long"
```

请求流程：
1. 尝试 `qwen-max` → 403错误
2. 自动切换到 `qwen-plus` → 403错误  
3. 自动切换到 `qwen-turbo` → 403错误
4. 自动切换到 `qwen-long` → 成功！

## 技术实现

### 核心组件

1. **BailianProvider** (`providers/bailian/client.py`)
   - 继承自`AnthropicMessagesTransport`
   - 实现403错误检测和模型切换逻辑
   - 支持模型循环使用

2. **配置集成**
   - 在`config/provider_catalog.py`中注册bailian provider
   - 在`config/settings.py`中添加相关配置项
   - 在`providers/registry.py`中注册工厂函数

3. **错误处理**
   - 专门捕获`httpx.HTTPStatusError`异常
   - 检查状态码是否为403
   - 仅对403错误进行重试，其他错误直接抛出

### 代码结构

```
providers/bailian/
├── __init__.py      # 包导出
└── client.py        # BailianProvider实现
```

## 使用示例

### Python代码示例

```python
from providers.bailian import BailianProvider
from providers.base import ProviderConfig

# 创建provider实例
config = ProviderConfig(
    api_key="your-bailian-api-key",
    base_url="https://dashscope.aliyuncs.com/api/v1",
    rate_limit=10,
    rate_window=60,
)

# 配置备用模型
fallback_models = ["qwen-max", "qwen-plus", "qwen-turbo"]
provider = BailianProvider(config, bailian_models=fallback_models)

# 使用provider（会自动处理403错误）
async for chunk in provider.stream_response(request):
    process_chunk(chunk)
```

### 命令行使用

```bash
# 设置环境变量
export BAILIAN_API_KEY="your-api-key"
export BAILIAN_MODELS="qwen-max,qwen-plus,qwen-turbo"
export MODEL="bailian/qwen-max"

# 启动服务
uv run python server.py
```

## 测试

运行单元测试验证功能：

```bash
uv run pytest tests/providers/test_bailian.py -v
```

测试覆盖：
- Provider初始化
- 模型循环机制
- 403错误重试
- 非403错误不重试
- 所有模型都失败的情况

## 注意事项

1. **API密钥安全**: 确保BAILIAN_API密钥的安全性，不要提交到版本控制
2. **模型可用性**: 确保配置的备用模型在您的账户中可用
3. **速率限制**: 多次重试可能会触发速率限制，请合理配置`PROVIDER_RATE_LIMIT`
4. **成本控制**: 模型切换可能导致额外的API调用费用

## 故障排除

### 常见问题

1. **403错误持续出现**
   - 检查API密钥是否正确
   - 确认账户有访问所配置模型的权限
   - 验证模型名称是否正确

2. **模型切换不工作**
   - 检查`BAILIAN_MODELS`配置格式是否正确（逗号分隔）
   - 确认至少配置了一个备用模型
   - 查看日志确认是否检测到403错误

3. **性能问题**
   - 减少备用模型数量
   - 调整速率限制参数
   - 监控API响应时间

### 日志调试

启用详细日志以调试问题：

```bash
LOG_API_ERROR_TRACEBACKS=true
LOG_RAW_API_PAYLOADS=true
```

## 扩展开发

如需添加更多功能，可以扩展`BailianProvider`类：

1. **自定义重试策略**: 修改重试条件和次数
2. **智能模型选择**: 根据历史成功率选择模型
3. **缓存机制**: 缓存成功的模型选择结果
4. **监控指标**: 添加403错误率和模型切换统计

## 兼容性

- 兼容现有的Anthropic Messages API客户端
- 支持所有标准的消息格式和参数
- 与项目的路由、优化和服务层无缝集成

## 贡献

欢迎提交Issue和Pull Request来改进阿里百炼支持功能。
