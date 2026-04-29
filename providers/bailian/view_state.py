#!/usr/bin/env python3
"""Utility script to view and manage Bailian model state.

Usage:
    python -m providers.bailian.view_state          # View current state
    python -m providers.bailian.view_state --reset  # Reset failed models
    python -m providers.bailian.view_state --clear  # Clear all state
"""

import argparse
import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from providers.bailian.model_state import BailianModelState


def format_timestamp(timestamp: str | None) -> str:
    """Format timestamp for display."""
    if not timestamp:
        return "Never"
    
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(timestamp)
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except (ValueError, TypeError):
        return timestamp


def view_state(state_manager: BailianModelState) -> None:
    """Display current state in a readable format."""
    status = state_manager.get_status_summary()
    
    print("\n" + "=" * 60)
    print("Bailian Model State")
    print("=" * 60)
    
    print(f"\nState File: {status['state_file']}")
    print(f"Last Updated: {format_timestamp(status['last_updated'])}")
    
    print(f"\nCurrent Working Model:")
    if status['current_working_model']:
        print(f"  ✓ {status['current_working_model']}")
    else:
        print("  (none set)")
    
    print(f"\nAvailable Models ({len(status['available_models'])}):")
    if status['available_models']:
        for i, model in enumerate(status['available_models'], 1):
            marker = "✓" if model == status['current_working_model'] else " "
            print(f"  {marker} {i}. {model}")
    else:
        print("  (no available models)")
    
    print(f"\nFailed Models ({len(status['failed_models'])}):")
    if status['failed_models']:
        for i, model in enumerate(status['failed_models'], 1):
            print(f"  ✗ {i}. {model}")
    else:
        print("  (none)")
    
    print("\n" + "=" * 60)
    
    # Also show raw JSON
    print("\nRaw State (JSON):")
    print(json.dumps(status, indent=2, ensure_ascii=False))
    print()


def main():
    parser = argparse.ArgumentParser(
        description="View and manage Bailian model state"
    )
    parser.add_argument(
        "--state-file",
        type=str,
        default="bailian_model_state.json",
        help="Path to state file (default: bailian_model_state.json)"
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset all failed models"
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear all state and remove state file"
    )
    
    args = parser.parse_args()
    
    # Initialize state manager
    state_manager = BailianModelState(state_file=args.state_file)
    
    if args.reset:
        print("Resetting all failed models...")
        state_manager.reset_failed_models()
        print("Done! All failed models have been reset.")
    elif args.clear:
        print("Clearing all state...")
        state_manager.clear_state()
        print("Done! All state has been cleared.")
    else:
        view_state(state_manager)


if __name__ == "__main__":
    main()
