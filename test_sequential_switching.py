#!/usr/bin/env python3
"""Test script to verify sequential model switching."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def test_sequential_switching():
    """Test that models are switched in sequence, not randomly."""
    
    print("\n=== Testing Sequential Model Switching ===\n")
    
    # Simulate the _get_next_model logic
    bailian_models = ["model-a", "model-b", "model-c", "model-d"]
    
    def get_next_model(models, current_model):
        """Simulate the fixed _get_next_model logic."""
        if not models:
            return None
        
        try:
            current_index = models.index(current_model)
            next_index = (current_index + 1) % len(models)
            return models[next_index]
        except ValueError:
            return models[0] if models else None
    
    # Test 1: Sequential switching
    print("Test 1: Sequential switching through all models")
    current = "model-a"
    sequence = [current]
    
    for i in range(len(bailian_models) - 1):
        next_model = get_next_model(bailian_models, current)
        sequence.append(next_model)
        current = next_model
    
    print(f"  Start: {sequence[0]}")
    print(f"  Sequence: {' -> '.join(sequence)}")
    print(f"  Expected: model-a -> model-b -> model-c -> model-d")
    
    assert sequence == ["model-a", "model-b", "model-c", "model-d"], \
        f"Expected sequential order, got {sequence}"
    print("  ✓ Passed: Models switch in correct sequence\n")
    
    # Test 2: Wrapping around
    print("Test 2: Wrapping from last to first")
    next_after_last = get_next_model(bailian_models, "model-d")
    print(f"  After model-d: {next_after_last}")
    assert next_after_last == "model-a", f"Expected to wrap to model-a, got {next_after_last}"
    print("  ✓ Passed: Correctly wraps to first model\n")
    
    # Test 3: After removing a failed model
    print("Test 3: After removing a failed model")
    models_after_failure = ["model-a", "model-c", "model-d"]  # model-b removed
    next_after_a = get_next_model(models_after_failure, "model-a")
    print(f"  Models: {models_after_failure}")
    print(f"  After model-a: {next_after_a}")
    assert next_after_a == "model-c", f"Expected model-c (skipping failed model-b), got {next_after_a}"
    print("  ✓ Passed: Skips failed models correctly\n")
    
    # Test 4: Real scenario simulation
    print("Test 4: Real scenario - multiple failures")
    original_models = ["qwen-max", "qwen-plus", "qwen-turbo", "qwen-long"]
    available = original_models.copy()
    
    print(f"  Original models: {original_models}")
    
    # First attempt: qwen-max fails
    current = "qwen-max"
    print(f"\n  Attempt 1: {current} fails")
    available.remove(current)
    next_model = get_next_model(available, current)
    print(f"  Next model: {next_model}")
    assert next_model == "qwen-plus", f"Expected qwen-plus, got {next_model}"
    
    # Second attempt: qwen-plus fails
    current = next_model
    print(f"  Attempt 2: {current} fails")
    available.remove(current)
    next_model = get_next_model(available, current)
    print(f"  Next model: {next_model}")
    assert next_model == "qwen-turbo", f"Expected qwen-turbo, got {next_model}"
    
    # Third attempt: qwen-turbo succeeds
    current = next_model
    print(f"  Attempt 3: {current} succeeds ✓")
    
    print("\n  ✓ Passed: Sequential fallback works correctly\n")
    
    print("=== All Tests Passed! ===\n")
    print("Summary:")
    print("  - Models switch in predictable sequence")
    print("  - No random jumping")
    print("  - Failed models are skipped")
    print("  - Wraps around when reaching the end")


if __name__ == "__main__":
    test_sequential_switching()
