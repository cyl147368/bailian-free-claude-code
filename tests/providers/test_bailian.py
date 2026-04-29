"""Tests for Alibaba Bailian provider."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import httpx

from providers.base import ProviderConfig
from providers.bailian import BailianProvider


class MockRequest:
    """Mock request for testing."""
    def __init__(self, model="test-model"):
        self.model = model
        self.messages = [{"role": "user", "content": "test"}]
        self.max_tokens = 100
        self.temperature = 0.5
        self.stream = True
        self.system = None
        self.tools = []
        self.thinking = None


@pytest.fixture
def bailian_config():
    return ProviderConfig(
        api_key="test_bailian_key",
        base_url="https://dashscope.aliyuncs.com/api/v1",
        rate_limit=10,
        rate_window=60,
    )


@pytest.fixture
def bailian_provider(bailian_config):
    return BailianProvider(bailian_config, bailian_models=["model1", "model2", "model3"])


def test_init_with_fallback_models(bailian_provider):
    """Test provider initialization with fallback models."""
    assert bailian_provider._bailian_models == ["model1", "model2", "model3"]
    assert bailian_provider._current_model_index == 0


def test_get_next_model_cycles(bailian_provider):
    """Test that model cycling works correctly."""
    assert bailian_provider._get_next_model() == "model1"
    assert bailian_provider._get_next_model() == "model2"
    assert bailian_provider._get_next_model() == "model3"
    assert bailian_provider._get_next_model() == "model1"  # Should cycle back


def test_init_without_fallback_models(bailian_config):
    """Test provider initialization without fallback models."""
    provider = BailianProvider(bailian_config)
    assert provider._bailian_models == []


@pytest.mark.asyncio
async def test_stream_response_no_fallback(bailian_config):
    """Test streaming without fallback models uses parent implementation."""
    provider = BailianProvider(bailian_config)
    request = MockRequest()
    
    # Mock the parent stream_response to verify it's called
    with patch.object(BailianProvider.__bases__[0], 'stream_response') as mock_super:
        mock_super.return_value.__aiter__ = MagicMock(return_value=iter(["chunk1", "chunk2"]))
        
        chunks = []
        async for chunk in provider.stream_response(request):
            chunks.append(chunk)
        
        assert chunks == ["chunk1", "chunk2"]
        mock_super.assert_called_once()


@pytest.mark.asyncio
async def test_stream_response_403_triggers_fallback(bailian_provider):
    """Test that 403 errors trigger model fallback."""
    request = MockRequest(model="original-model")
    
    call_count = 0
    
    async def mock_stream(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        
        if call_count == 1:
            # First call fails with 403
            response = MagicMock()
            response.status_code = 403
            raise httpx.HTTPStatusError("Forbidden", request=MagicMock(), response=response)
        else:
            # Second call succeeds
            yield "success_chunk"
    
    with patch.object(BailianProvider.__bases__[0], 'stream_response', side_effect=mock_stream):
        chunks = []
        async for chunk in bailian_provider.stream_response(request):
            chunks.append(chunk)
        
        # Should have tried twice (original + one fallback)
        assert call_count == 2
        assert chunks == ["success_chunk"]


@pytest.mark.asyncio  
async def test_stream_response_all_models_fail(bailian_provider):
    """Test that all models failing results in final error."""
    request = MockRequest(model="original-model")
    
    async def mock_stream_always_fail(*args, **kwargs):
        response = MagicMock()
        response.status_code = 403
        raise httpx.HTTPStatusError("Forbidden", request=MagicMock(), response=response)
    
    with patch.object(BailianProvider.__bases__[0], 'stream_response', side_effect=mock_stream_always_fail):
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            async for _ in bailian_provider.stream_response(request):
                pass
        
        assert exc_info.value.response.status_code == 403


@pytest.mark.asyncio
async def test_stream_response_non_403_error_no_retry(bailian_provider):
    """Test that non-403 errors are not retried."""
    request = MockRequest()
    
    async def mock_stream_500(*args, **kwargs):
        response = MagicMock()
        response.status_code = 500
        raise httpx.HTTPStatusError("Internal Server Error", request=MagicMock(), response=response)
    
    with patch.object(BailianProvider.__bases__[0], 'stream_response', side_effect=mock_stream_500):
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            async for _ in bailian_provider.stream_response(request):
                pass
        
        # Should only be called once (no retry for 500 errors)
        assert exc_info.value.response.status_code == 500
