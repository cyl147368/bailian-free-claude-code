# Bailian Provider 配置说明

## 为什么需要 `bailian/` 前缀？

### 1. 统一的模型命名规范

项目使用 **provider_type/model_name** 的格式来唯一标识模型，例如：

```
bailian/qwen-max          # 阿里百炼的 qwen-max
nvidia_nim/glm4.7         # NVIDIA NIM 的 glm4.7
open_router/anthropic/claude-3  # OpenRouter 的 Claude-3
deepseek/deepseek-chat    # DeepSeek 的 deepseek-chat
```

### 2. 多 Provider 路由

系统支持多个 AI 提供商，前缀用于：
- **区分来源**：识别模型属于哪个 provider
- **正确路由**：将请求发送到正确的 API 端点
- **避免冲突**：不同 provider 可能有同名模型

### 3. 配置示例

#### `.env` 文件
```env
# MODEL 配置 - 需要前缀（用于路由）
MODEL="bailian/qvq-max-2025-03-25"

# BAILIAN_MODELS - 不需要前缀（只是模型名称列表）
BAILIAN_MODELS="qwen-max,qwen-plus,qwen-turbo"
```

**重要区别**：
- `MODEL` 需要 `bailian/` 前缀，因为系统需要根据前缀路由到正确的 provider
- `BAILIAN_MODELS` **不需要**前缀，它只是一个简单的模型名称列表

#### 状态文件 `bailian_model_state.json`（不需要前缀）
```json
{
  "current_working_model": "qvq-max-2025-03-25",
  "failed_models": ["qwen3.6-plus"],
  "available_models": ["qwen-max", "qwen-plus", "qwen-turbo"]
}
```

### 4. 自动处理机制

系统会自动处理前缀：

1. **MODEL 配置**：需要 `bailian/` 前缀
   - 用于路由到正确的 provider
   - 格式：`provider_type/model_name`

2. **BAILIAN_MODELS 配置**：不需要前缀
   - 只是模型名称的逗号分隔列表
   - 例如：`qwen-max,qwen-plus,qwen-turbo`

3. **状态文件**：内部存储不带前缀
   - 简化比较和管理逻辑
   - 同步到 `.env` 时，`MODEL` 会添加前缀，`BAILIAN_MODELS` 保持无前缀

这样设计的好处：
- ✅ `MODEL` 可以正确路由到 provider
- ✅ `BAILIAN_MODELS` 简洁易读，无需重复前缀
- ✅ 状态文件内部管理简单

### 5. 常见问题

**Q: 我可以不使用前缀吗？**  
A: 不建议。虽然某些情况下可能工作，但会导致：
- 多 provider 环境下无法正确路由
- 与项目其他部分不一致
- 可能的配置冲突

**Q: 为什么状态文件中没有前缀？**  
A: 为了简化内部管理和比较逻辑。前缀只在需要区分 provider 时才添加。

**Q: 如果我想切换到其他 provider 怎么办？**  
A: 修改 `MODEL` 配置即可：
```env
# 从百炼切换到 NVIDIA NIM
MODEL="nvidia_nim/glm4.7"

# 从百炼切换到 DeepSeek
MODEL="deepseek/deepseek-chat"
```

## 最佳实践

1. **始终使用前缀**：在 `.env` 中配置模型时使用完整格式
2. **不要手动编辑状态文件**：让系统自动管理
3. **定期检查日志**：查看哪些模型被标记为失败
4. **额度刷新后重置**：运行 `uv run python -m providers.bailian --reset`

## 相关文件

- `.env` - 主配置文件（需要前缀）
- `bailian_model_state.json` - 状态跟踪文件（无前缀）
- `providers/bailian/model_state.py` - 状态管理实现
- `providers/bailian/client.py` - Provider 客户端实现
