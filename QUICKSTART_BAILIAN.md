# 阿里百炼Provider - 5分钟快速开始

## 1. 获取API密钥

访问 [阿里云模型工作室](https://help.aliyun.com/zh/model-studio/developer-reference/get-api-key) 获取您的API密钥。

## 2. 配置环境变量

编辑 `.env` 文件，添加以下配置：

```bash
# 阿里百炼API密钥
BAILIAN_API_KEY="sk-your-actual-api-key-here"

# 备用模型列表（当主模型返回403时自动切换）
BAILIAN_MODELS="qwen-max,qwen-plus,qwen-turbo"

# 使用阿里百炼作为默认provider
MODEL="bailian/qwen-max"
```

## 3. 启动服务

```bash
# 安装依赖（如果还没安装）
uv sync

# 启动代理服务器
uv run uvicorn server:app --host 0.0.0.0 --port 8082
```

## 4. 使用Claude Code

### 命令行方式

```bash
# Bash/Linux/macOS
ANTHROPIC_AUTH_TOKEN="freecc" ANTHROPIC_BASE_URL="http://localhost:8082" claude

# PowerShell
$env:ANTHROPIC_AUTH_TOKEN="freecc"; $env:ANTHROPIC_BASE_URL="http://localhost:8082"; claude
```

### VS Code方式

在 `settings.json` 中添加：

```json
"claudeCode.environmentVariables": [
  { "name": "ANTHROPIC_BASE_URL", "value": "http://localhost:8082" },
  { "name": "ANTHROPIC_AUTH_TOKEN", "value": "freecc" }
]
```

## 5. 验证功能

### 测试基本功能

发送一个简单的消息给Claude Code，观察是否正常工作。

### 测试403自动切换

如果您的某个模型返回403错误，系统会自动切换到下一个模型。您可以在日志中看到类似的信息：

```
BAILIAN_MODEL_SWITCH: Attempt 2/4 switching from qwen-max to qwen-plus due to previous 403
```

## 可用模型

阿里百炼提供多个Qwen模型：

| 模型 | 特点 | 适用场景 |
|------|------|----------|
| `qwen-max` | 最强推理能力 | 复杂任务、代码生成 |
| `qwen-plus` | 平衡性能和成本 | 日常使用 |
| `qwen-turbo` | 快速响应 | 简单对话、快速回复 |
| `qwen-long` | 长上下文支持 | 长文档处理 |

## 高级配置

### 为不同Claude模型指定不同百炼模型

```bash
MODEL_OPUS="bailian/qwen-max"      # Opus级别使用最强模型
MODEL_SONNET="bailian/qwen-plus"   # Sonnet级别使用平衡模型
MODEL_HAIKU="bailian/qwen-turbo"   # Haiku级别使用快速模型
MODEL="bailian/qwen-plus"          # 默认fallback
```

### 调整速率限制

```bash
# 每秒最多10个请求
PROVIDER_RATE_LIMIT=10
PROVIDER_RATE_WINDOW=60
```

## 故障排除

### 问题1: 所有模型都返回403

**解决方案**:
1. 检查API密钥是否正确
2. 确认账户有访问这些模型的权限
3. 验证模型名称是否正确

### 问题2: 模型切换不工作

**解决方案**:
1. 确认`BAILIAN_MODELS`配置格式正确（逗号分隔）
2. 至少配置一个备用模型
3. 查看日志确认是否检测到403错误

### 问题3: 响应速度慢

**解决方案**:
1. 减少备用模型数量
2. 选择地理位置更近的节点
3. 检查网络连接

## 下一步

- 阅读完整文档: [docs/bailian_provider.md](docs/bailian_provider.md)
- 查看示例代码: [examples/bailian_example.py](examples/bailian_example.py)
- 查看实现细节: [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)

## 需要帮助？

如果您遇到问题：
1. 检查日志输出
2. 查阅完整文档
3. 提交Issue到GitHub仓库

祝您使用愉快！🎉
