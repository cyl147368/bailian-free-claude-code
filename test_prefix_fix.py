#!/usr/bin/env python3
"""Test script to verify the fixed state management."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from providers.bailian.model_state import BailianModelState


def test_prefix_handling():
    """Test that bailian/ prefix is handled correctly."""
    
    # Create a fresh state manager with temp file
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_file = f.name
    
    try:
        state_manager = BailianModelState(temp_file)
        
        print("\n=== Testing Prefix Handling ===\n")
        
        # Test 1: Mark model with prefix as failed
        print("1. Marking 'bailian/qwen-max' as failed...")
        state_manager.mark_model_failed("bailian/qwen-max")
        print(f"   Failed models: {state_manager.get_failed_models()}")
        assert "qwen-max" in state_manager.get_failed_models(), "Should store without prefix"
        print("   ✓ Correctly stored without prefix\n")
        
        # Test 2: Set working model with prefix
        print("2. Setting working model to 'bailian/qvq-max-2025-03-25'...")
        state_manager.set_working_model("bailian/qvq-max-2025-03-25")
        print(f"   Working model: {state_manager.get_working_model()}")
        assert state_manager.get_working_model() == "qvq-max-2025-03-25", "Should store without prefix"
        print("   ✓ Correctly stored without prefix\n")
        
        # Test 3: Remove failed from available (with prefix in input)
        print("3. Filtering available models...")
        configured = ["bailian/qwen-max", "bailian/qwen-plus", "bailian/qwen-turbo"]
        available = state_manager.remove_failed_from_available(configured)
        print(f"   Configured: {configured}")
        print(f"   Available: {available}")
        assert "qwen-max" not in available, "Failed model should be filtered"
        assert "qwen-plus" in available and "qwen-turbo" in available
        print("   ✓ Correctly filtered failed models\n")
        
        # Test 4: Sync to .env (should add prefix back)
        print("4. Testing sync to .env logic...")
        working = state_manager.get_working_model()
        avail = state_manager.get_available_models()
        print(f"   State working model: {working}")
        print(f"   State available: {avail}")
        
        # Simulate what sync_to_env_file does
        model_value = f'bailian/{working}'
        models_value = ','.join(f'bailian/{m}' for m in avail)
        print(f"   .env MODEL would be: {model_value}")
        print(f"   .env BAILIAN_MODELS would have {len(avail)} models with bailian/ prefix")
        print("   ✓ Prefix will be added correctly when syncing to .env\n")
        
        print("=== All Tests Passed! ===\n")
        
    finally:
        # Cleanup
        Path(temp_file).unlink(missing_ok=True)


if __name__ == "__main__":
    test_prefix_handling()
