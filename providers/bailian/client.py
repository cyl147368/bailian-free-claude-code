"""Alibaba Bailian (DashScope) provider implementation.

Uses OpenAI-compatible /v1/chat/completions endpoint with Anthropic SSE conversion.
"""

from __future__ import annotations

import copy
from collections.abc import AsyncIterator
from typing import Any

import httpx
from loguru import logger

from providers.openai_compat import OpenAIChatTransport
from providers.base import ProviderConfig
from config.provider_catalog import BAILIAN_DEFAULT_BASE
from config.nim import NimSettings
from .model_state import BailianModelState


class BailianProvider(OpenAIChatTransport):
    """Alibaba Bailian provider using OpenAI-compatible chat completions API.
    
    Supports automatic model fallback on 403 errors by cycling through configured models.
    Converts OpenAI-style responses to Anthropic SSE format.
    """

    def __init__(self, config: ProviderConfig, *, bailian_models: list[str] | None = None):
        super().__init__(
            config,
            provider_name="BAILIAN",
            base_url=config.base_url or BAILIAN_DEFAULT_BASE,
            api_key=config.api_key,
        )
        # Store the original configured models
        self._original_bailian_models = bailian_models or []
        
        # Initialize persistent state manager
        self._state_manager = BailianModelState()
        
        # Get available models (excluding failed ones from persistent state)
        self._bailian_models = self._state_manager.remove_failed_from_available(
            self._original_bailian_models
        )
        
        logger.info(
            "BAILIAN_INIT: Configured {} models, {} available after filtering failed ones",
            len(self._original_bailian_models),
            len(self._bailian_models)
        )
        
        # Sync state to .env file on startup (optional, for persistence across restarts)
        # This updates MODEL and BAILIAN_MODELS in .env to reflect current working state
        if self._state_manager.get_working_model() and self._state_manager.get_available_models():
            self._state_manager.sync_to_env_file()

    def _get_next_model(self, current_model: str) -> str | None:
        """Get the next model in sequence after the current one (excluding failed models).
        
        Args:
            current_model: The model that just failed
            
        Returns:
            The next model to try, or None if no more models available
        """
        if not self._bailian_models:
            return None
        
        # Find the index of the current model
        try:
            current_index = self._bailian_models.index(current_model)
            # Get the next model in sequence
            next_index = (current_index + 1) % len(self._bailian_models)
            return self._bailian_models[next_index]
        except ValueError:
            # Current model not in list, start from beginning
            return self._bailian_models[0] if self._bailian_models else None

    def _build_request_body(
        self, request: Any, thinking_enabled: bool | None = None
    ) -> dict:
        """Build OpenAI-compatible request body for Bailian."""
        from .request import build_request_body
        
        thinking_enabled = self._is_thinking_enabled(request, thinking_enabled)
        return build_request_body(request, thinking_enabled=thinking_enabled)

    async def stream_response(
        self,
        request: Any,
        input_tokens: int = 0,
        *,
        request_id: str | None = None,
        thinking_enabled: bool | None = None,
    ) -> AsyncIterator[str]:
        """Stream response with 403/400 error handling and model fallback."""
        # Check if we should try multiple models on 403/400
        should_retry_with_fallback = bool(self._bailian_models)
        
        if should_retry_with_fallback:
            # Try with model fallback
            max_attempts = len(self._bailian_models) + 1  # Original + fallbacks
            last_error_message = None
            
            for attempt in range(max_attempts):
                try:
                    # Get the next model to try
                    if attempt > 0:
                        # Use the model from the previous attempt to find the next one
                        prev_model = current_request.model if 'current_request' in locals() else request.model
                        next_model = self._get_next_model(prev_model)
                        if next_model:
                            # Create a modified request with the new model
                            modified_request = copy.deepcopy(request)
                            modified_request.model = next_model
                            # Restore original max_tokens when switching models (for 403/400 fallback)
                            # This allows using the full context window on fallback models
                            if hasattr(request, 'max_tokens'):
                                modified_request.max_tokens = request.max_tokens
                            
                            logger.info(
                                "BAILIAN_MODEL_SWITCH: Attempt {}/{} switching from {} to {} due to previous error, restoring max_tokens={}",
                                attempt + 1,
                                max_attempts,
                                request.model,
                                next_model,
                                getattr(request, 'max_tokens', 'default')
                            )
                            current_request = modified_request
                        else:
                            current_request = request
                    else:
                        current_request = request
                    
                    # Track if we received any successful chunks
                    received_chunks = False
                    error_occurred = False
                    error_msg = None
                    
                    # Try streaming with current request
                    async for chunk in super().stream_response(
                        current_request, 
                        input_tokens, 
                        request_id=request_id, 
                        thinking_enabled=thinking_enabled
                    ):
                        # DEBUG: Log all chunks to see their format
                        logger.debug(
                            "BAILIAN_CHUNK: type={}, length={}, preview={}",
                            type(chunk).__name__,
                            len(chunk),
                            chunk[:200] if isinstance(chunk, str) else str(chunk)[:200]
                        )
                        
                        # Check if this chunk contains error information
                        # Parent class converts exceptions to user-friendly error messages
                        chunk_lower = chunk.lower() if isinstance(chunk, str) else str(chunk).lower()
                        is_error_chunk = any(keyword in chunk_lower for keyword in [
                            'provider api request failed',
                            'permission denied',
                            'free tier',
                            'allocationquota',
                            'error code: 403',
                            'error code: 400'
                        ])
                        
                        if is_error_chunk:
                            logger.warning(
                                "BAILIAN_STREAM: Detected error in SSE chunk from parent, length={}",
                                len(chunk)
                            )
                            # This is an error event from parent, break and retry
                            error_occurred = True
                            error_msg = chunk
                            last_error_message = chunk
                            break
                        
                        received_chunks = True
                        yield chunk
                    
                    # If we received chunks without error, success!
                    if received_chunks and not error_occurred:
                        # Mark this model as working in persistent state
                        successful_model = current_request.model
                        self._state_manager.set_working_model(successful_model)
                        
                        # Update available models in persistent state
                        self._state_manager.remove_failed_from_available(
                            self._original_bailian_models
                        )
                        
                        logger.info(
                            "BAILIAN_MODEL_SUCCESS: Using working model {} (available: {})",
                            successful_model,
                            self._state_manager.get_available_models()
                        )
                        return  # Success, exit early
                    
                    # If error occurred or no chunks, log and continue to next model
                    if error_occurred:
                        # Track the failed model in persistent state
                        failed_model = current_request.model
                        self._state_manager.mark_model_failed(failed_model)
                        
                        # Update available models list
                        self._bailian_models = self._state_manager.remove_failed_from_available(
                            self._original_bailian_models
                        )
                        
                        # Immediately sync updated state to .env file
                        self._state_manager.sync_to_env_file()
                        
                        logger.warning(
                            "BAILIAN_STREAM: Error detected on model {}, will retry with next model (attempt {}/{})",
                            failed_model,
                            attempt + 1,
                            max_attempts
                        )
                        continue
                    else:
                        # No chunks received at all
                        logger.warning(
                            "BAILIAN_STREAM: No chunks received, will retry with next model (attempt {}/{})",
                            attempt + 1,
                            max_attempts
                        )
                        continue
                    
                except Exception as e:
                    # For unexpected exceptions, just re-raise
                    logger.error("BAILIAN_STREAM: Unexpected exception: {}", str(e))
                    raise
            
            # If we exhausted all attempts, emit the last error
            if last_error_message:
                logger.error(
                    "BAILIAN_STREAM: All {} attempts failed, emitting final error",
                    max_attempts
                )
                yield last_error_message
        else:
            # No fallback models configured, use standard streaming
            async for chunk in super().stream_response(
                request, input_tokens, request_id=request_id, thinking_enabled=thinking_enabled
            ):
                yield chunk
