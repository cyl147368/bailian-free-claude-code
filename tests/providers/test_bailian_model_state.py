"""Tests for Bailian model state management."""

import json
import tempfile
from pathlib import Path

import pytest

from providers.bailian.model_state import BailianModelState


@pytest.fixture
def temp_state_file():
    """Create a temporary state file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write('{}')
        path = Path(f.name)
    yield path
    # Cleanup
    if path.exists():
        path.unlink()


class TestBailianModelState:
    """Test the BailianModelState class."""
    
    def test_init_creates_empty_state(self, temp_state_file):
        """Test initialization creates empty state."""
        state = BailianModelState(state_file=temp_state_file)
        
        assert state.get_failed_models() == []
        assert state.get_working_model() is None
        assert state.get_available_models() == []
    
    def test_mark_model_failed(self, temp_state_file):
        """Test marking a model as failed."""
        state = BailianModelState(state_file=temp_state_file)
        
        state.mark_model_failed("qwen-max")
        
        assert "qwen-max" in state.get_failed_models()
        assert len(state.get_failed_models()) == 1
    
    def test_mark_same_model_failed_once(self, temp_state_file):
        """Test that marking the same model failed twice doesn't duplicate it."""
        state = BailianModelState(state_file=temp_state_file)
        
        state.mark_model_failed("qwen-max")
        state.mark_model_failed("qwen-max")
        
        assert state.get_failed_models().count("qwen-max") == 1
    
    def test_set_working_model(self, temp_state_file):
        """Test setting the working model."""
        state = BailianModelState(state_file=temp_state_file)
        
        state.set_working_model("qwen-turbo")
        
        assert state.get_working_model() == "qwen-turbo"
    
    def test_remove_failed_from_available(self, temp_state_file):
        """Test filtering failed models from available list."""
        state = BailianModelState(state_file=temp_state_file)
        
        all_models = ["qwen-max", "qwen-plus", "qwen-turbo"]
        
        # Mark some as failed
        state.mark_model_failed("qwen-max")
        state.mark_model_failed("qwen-plus")
        
        # Filter
        available = state.remove_failed_from_available(all_models)
        
        assert available == ["qwen-turbo"]
        assert state.get_available_models() == ["qwen-turbo"]
    
    def test_persistence_across_instances(self, temp_state_file):
        """Test that state persists across different instances."""
        # First instance
        state1 = BailianModelState(state_file=temp_state_file)
        state1.mark_model_failed("qwen-max")
        state1.set_working_model("qwen-turbo")
        
        # Second instance (should load saved state)
        state2 = BailianModelState(state_file=temp_state_file)
        
        assert "qwen-max" in state2.get_failed_models()
        assert state2.get_working_model() == "qwen-turbo"
    
    def test_reset_failed_models(self, temp_state_file):
        """Test resetting all failed models."""
        state = BailianModelState(state_file=temp_state_file)
        
        state.mark_model_failed("qwen-max")
        state.mark_model_failed("qwen-plus")
        assert len(state.get_failed_models()) == 2
        
        state.reset_failed_models()
        
        assert state.get_failed_models() == []
    
    def test_clear_state(self, temp_state_file):
        """Test clearing all state."""
        state = BailianModelState(state_file=temp_state_file)
        
        state.mark_model_failed("qwen-max")
        state.set_working_model("qwen-turbo")
        
        state.clear_state()
        
        assert state.get_failed_models() == []
        assert state.get_working_model() is None
        assert state.get_available_models() == []
        assert not temp_state_file.exists()
    
    def test_get_status_summary(self, temp_state_file):
        """Test getting complete status summary."""
        state = BailianModelState(state_file=temp_state_file)
        
        state.mark_model_failed("qwen-max")
        state.set_working_model("qwen-turbo")
        
        summary = state.get_status_summary()
        
        assert "state_file" in summary
        assert summary["current_working_model"] == "qwen-turbo"
        assert summary["failed_models"] == ["qwen-max"]
        assert summary["last_updated"] is not None
    
    def test_load_nonexistent_file(self):
        """Test loading from a nonexistent file starts fresh."""
        with tempfile.TemporaryDirectory() as tmpdir:
            nonexistent = Path(tmpdir) / "nonexistent.json"
            state = BailianModelState(state_file=nonexistent)
            
            assert state.get_failed_models() == []
            assert state.get_working_model() is None
    
    def test_load_corrupted_file(self, temp_state_file):
        """Test loading from a corrupted JSON file uses defaults."""
        # Write invalid JSON
        temp_state_file.write_text("{invalid json}")
        
        # Should not raise, just use defaults
        state = BailianModelState(state_file=temp_state_file)
        
        assert state.get_failed_models() == []
        assert state.get_working_model() is None
    
    def test_state_file_format(self, temp_state_file):
        """Test that state file is properly formatted JSON."""
        state = BailianModelState(state_file=temp_state_file)
        
        state.mark_model_failed("qwen-max")
        state.set_working_model("qwen-turbo")
        
        # Read and parse the file
        with open(temp_state_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        assert isinstance(data, dict)
        assert "failed_models" in data
        assert "current_working_model" in data
        assert "available_models" in data
        assert "last_updated" in data
        assert data["current_working_model"] == "qwen-turbo"
        assert data["failed_models"] == ["qwen-max"]
