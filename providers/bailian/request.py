"""Alibaba Bailian request body builder.

Converts Anthropic Messages format to OpenAI-compatible chat completions format
for Alibaba Bailian's /compatible-mode/v1 endpoint.
"""

from __future__ import annotations

from typing import Any

from loguru import logger

from config.constants import ANTHROPIC_DEFAULT_MAX_OUTPUT_TOKENS


def build_request_body(request_data: Any, *, thinking_enabled: bool) -> dict:
    """Build an OpenAI-compatible request body for Alibaba Bailian.
    
    Args:
        request_data: Anthropic-style request object
        thinking_enabled: Whether thinking/reasoning is enabled
        
    Returns:
        OpenAI-compatible request body dict
    """
    logger.debug(
        "BAILIAN_REQUEST: conversion start model={} msgs={}",
        getattr(request_data, "model", "?"),
        len(getattr(request_data, "messages", [])),
    )

    # Extract messages and convert system message
    messages = []
    system_content = getattr(request_data, "system", None)
    
    # Add system message if present
    if system_content:
        if isinstance(system_content, str):
            messages.append({"role": "system", "content": system_content})
        elif isinstance(system_content, list):
            # Handle array of system content blocks
            text_parts = []
            for item in system_content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_parts.append(item.get("text", ""))
                elif isinstance(item, str):
                    text_parts.append(item)
            if text_parts:
                messages.append({"role": "system", "content": "\n".join(text_parts)})
    
    # Convert user/assistant messages
    for msg in getattr(request_data, "messages", []):
        # Handle both Pydantic models and dicts
        if hasattr(msg, "role"):
            # Pydantic Message object - use attribute access
            role = msg.role
            content = msg.content
        else:
            # Dict - use .get()
            role = msg.get("role", "")
            content = msg.get("content", "")
        
        # Handle content as string or list
        if isinstance(content, list):
            # Extract text from content blocks
            text_parts = []
            for item in content:
                if isinstance(item, dict):
                    if item.get("type") == "text":
                        text_parts.append(item.get("text", ""))
                    # Skip tool_use, tool_result blocks for now
                elif isinstance(item, str):
                    text_parts.append(item)
            content = "\n".join(text_parts) if text_parts else ""
        elif hasattr(content, "__iter__") and not isinstance(content, str):
            # Content might be a list of ContentBlock objects
            text_parts = []
            for item in content:
                if hasattr(item, "type") and item.type == "text":
                    text_parts.append(getattr(item, "text", ""))
                elif isinstance(item, str):
                    text_parts.append(item)
            content = "\n".join(text_parts) if text_parts else ""
        
        # Map roles
        if role in ("user", "assistant"):
            messages.append({"role": role, "content": content})
        elif role == "system":
            # Additional system messages go to the beginning
            messages.insert(0, {"role": "system", "content": content})
    
    # Build tools array if present
    tools = []
    for tool in getattr(request_data, "tools", []):
        if hasattr(tool, "name"):
            # Pydantic Tool object - use attribute access
            openai_tool = {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": getattr(tool, "description", ""),
                    "parameters": getattr(tool, "input_schema", {}),
                }
            }
        elif isinstance(tool, dict):
            # Dict - use .get()
            openai_tool = {
                "type": "function",
                "function": {
                    "name": tool.get("name", ""),
                    "description": tool.get("description", ""),
                    "parameters": tool.get("input_schema", {}),
                }
            }
        else:
            continue
        tools.append(openai_tool)
    
    # Build request body
    # Note: "stream" is set by OpenAIChatTransport._create_stream(), not here
    
    # Get max_tokens with Bailian-specific limit (8192 for qwen models)
    max_tokens = getattr(request_data, "max_tokens", ANTHROPIC_DEFAULT_MAX_OUTPUT_TOKENS)
    # Cap max_tokens to Bailian's limit
    if max_tokens and max_tokens > 8192:
        max_tokens = 8192
    
    # Get temperature, ensure it's a valid float (not None)
    temperature = getattr(request_data, "temperature", None)
    if temperature is None:
        temperature = 0.7
    
    body = {
        "model": getattr(request_data, "model", "qwen-max"),
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    
    # Add tools if present
    if tools:
        body["tools"] = tools
        body["tool_choice"] = "auto"
    
    # Add thinking/reasoning support if enabled
    if thinking_enabled:
        # Qwen models support reasoning through specific parameters
        # This may vary by model version
        pass
    
    logger.debug(
        "BAILIAN_REQUEST: conversion done model={} msgs={} tools={}",
        body.get("model"),
        len(body.get("messages", [])),
        len(body.get("tools", [])),
    )
    
    return body
