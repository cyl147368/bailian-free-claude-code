#!/usr/bin/env python3
"""Test script to demonstrate .env sync functionality."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from providers.bailian.model_state import BailianModelState


def test_sync_to_env():
    """Test syncing state to .env file."""
    
    # Create a test state
    state_manager = BailianModelState()
    
    # Simulate some state
    state_manager.mark_model_failed("qwen3.6-plus")
    state_manager.set_working_model("qvq-max-2025-03-25")
    state_manager.remove_failed_from_available([
        "qwen3.6-plus",
        "qvq-max-2025-03-25", 
        "qwen-turbo",
        "qwen-plus"
    ])
    
    print("\nCurrent State:")
    print(f"  Working Model: {state_manager.get_working_model()}")
    print(f"  Available Models: {state_manager.get_available_models()}")
    print(f"  Failed Models: {state_manager.get_failed_models()}")
    
    # Sync to .env
    print("\nSyncing to .env...")
    success = state_manager.sync_to_env_file()
    
    if success:
        print("✓ Successfully synced to .env")
        
        # Show what was written
        env_path = Path(".env")
        if env_path.exists():
            print("\n.env content (relevant lines):")
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip().startswith(("MODEL=", "BAILIAN_MODELS=")):
                        print(f"  {line.rstrip()}")
    else:
        print("✗ Failed to sync to .env")


if __name__ == "__main__":
    test_sync_to_env()
