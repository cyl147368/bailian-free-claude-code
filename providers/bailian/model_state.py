"""Bailian model state manager for persistent tracking of model availability."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from loguru import logger


class BailianModelState:
    """Manages persistent state for Bailian provider model availability.
    
    Tracks which models have failed and which model is currently working,
    persisting this information to a JSON file so it survives service restarts.
    """
    
    def __init__(self, state_file: str | Path = "bailian_model_state.json"):
        """Initialize the model state manager.
        
        Args:
            state_file: Path to the JSON file for persisting state
        """
        self.state_file = Path(state_file)
        self._state: dict[str, Any] = {
            "failed_models": [],
            "current_working_model": None,
            "available_models": [],
            "last_updated": None,
        }
        self._load_state()
    
    def _load_state(self) -> None:
        """Load state from the JSON file if it exists."""
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    loaded_state = json.load(f)
                
                # Validate and merge with defaults
                self._state = {
                    "failed_models": loaded_state.get("failed_models", []),
                    "current_working_model": loaded_state.get("current_working_model"),
                    "available_models": loaded_state.get("available_models", []),
                    "last_updated": loaded_state.get("last_updated"),
                }
                
                logger.info(
                    "BAILIAN_STATE: Loaded state from {} - working_model={}, failed={}, available={}",
                    self.state_file,
                    self._state["current_working_model"],
                    len(self._state["failed_models"]),
                    len(self._state["available_models"])
                )
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(
                    "BAILIAN_STATE: Failed to load state from {}: {}, using defaults",
                    self.state_file,
                    e
                )
        else:
            logger.info(
                "BAILIAN_STATE: No existing state file at {}, starting fresh",
                self.state_file
            )
    
    def _save_state(self) -> None:
        """Save current state to the JSON file."""
        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(self._state, f, indent=2, ensure_ascii=False)
            
            logger.debug(
                "BAILIAN_STATE: Saved state to {} - working_model={}, failed={}, available={}",
                self.state_file,
                self._state["current_working_model"],
                len(self._state["failed_models"]),
                len(self._state["available_models"])
            )
        except IOError as e:
            logger.error(
                "BAILIAN_STATE: Failed to save state to {}: {}",
                self.state_file,
                e
            )
    
    def mark_model_failed(self, model_name: str) -> None:
        """Mark a model as failed/unavailable.
        
        Args:
            model_name: The name of the model that failed (with or without 'bailian/' prefix)
        """
        # Strip bailian/ prefix if present
        clean_model = model_name.removeprefix("bailian/")
        
        if clean_model not in self._state["failed_models"]:
            self._state["failed_models"].append(clean_model)
            self._state["last_updated"] = self._get_timestamp()
            self._save_state()
            
            logger.info(
                "BAILIAN_STATE: Marked model '{}' as failed (total failed: {})",
                clean_model,
                len(self._state["failed_models"])
            )
    
    def set_working_model(self, model_name: str) -> None:
        """Set the current working model.
        
        Args:
            model_name: The name of the model that is currently working (with or without 'bailian/' prefix)
        """
        # Strip bailian/ prefix if present
        clean_model = model_name.removeprefix("bailian/")
        
        old_model = self._state["current_working_model"]
        self._state["current_working_model"] = clean_model
        self._state["last_updated"] = self._get_timestamp()
        
        # Add to available models if not already there
        if clean_model not in self._state["available_models"]:
            self._state["available_models"].append(clean_model)
        
        self._save_state()
        
        logger.info(
            "BAILIAN_STATE: Working model changed from '{}' to '{}'",
            old_model or "none",
            clean_model
        )
    
    def remove_failed_from_available(self, all_configured_models: list[str]) -> list[str]:
        """Filter out failed models from the configured model list.
        
        Args:
            all_configured_models: Complete list of configured models (may have 'bailian/' prefix)
            
        Returns:
            List of models excluding failed ones (without prefix)
        """
        # Strip bailian/ prefix from configured models for comparison
        clean_models = [m.removeprefix("bailian/") for m in all_configured_models]
        
        available = [
            m for m in clean_models 
            if m not in self._state["failed_models"]
        ]
        
        # Update available models in state (store without prefix)
        self._state["available_models"] = available
        self._state["last_updated"] = self._get_timestamp()
        self._save_state()
        
        return available
    
    def get_failed_models(self) -> list[str]:
        """Get list of failed models.
        
        Returns:
            List of model names that have failed
        """
        return self._state["failed_models"].copy()
    
    def get_working_model(self) -> str | None:
        """Get the current working model.
        
        Returns:
            Name of the working model, or None if not set
        """
        return self._state["current_working_model"]
    
    def get_available_models(self) -> list[str]:
        """Get list of available (non-failed) models.
        
        Returns:
            List of available model names
        """
        return self._state["available_models"].copy()
    
    def reset_failed_models(self) -> None:
        """Reset all failed models (e.g., after manual intervention)."""
        self._state["failed_models"] = []
        self._state["last_updated"] = self._get_timestamp()
        self._save_state()
        
        logger.info("BAILIAN_STATE: Reset all failed models")
    
    def clear_state(self) -> None:
        """Clear all state and remove the state file."""
        self._state = {
            "failed_models": [],
            "current_working_model": None,
            "available_models": [],
            "last_updated": None,
        }
        
        if self.state_file.exists():
            try:
                self.state_file.unlink()
                logger.info("BAILIAN_STATE: Cleared state and removed file {}", self.state_file)
            except IOError as e:
                logger.error("BAILIAN_STATE: Failed to remove state file {}: {}", self.state_file, e)
        else:
            logger.info("BAILIAN_STATE: State cleared (no file existed)")
    
    @staticmethod
    def _get_timestamp() -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()
    
    def get_status_summary(self) -> dict[str, Any]:
        """Get a complete status summary.
        
        Returns:
            Dictionary with complete state information
        """
        return {
            "state_file": str(self.state_file),
            "current_working_model": self._state["current_working_model"],
            "failed_models": self._state["failed_models"].copy(),
            "available_models": self._state["available_models"].copy(),
            "last_updated": self._state["last_updated"],
        }
    
    def sync_to_env_file(self, env_file: str | Path = ".env") -> bool:
        """Sync current state to .env file by updating BAILIAN_MODELS and MODEL.
        
        This updates the .env file so that on next service restart, the configuration
        reflects the current working model and available models.
        
        Args:
            env_file: Path to the .env file (default: .env in project root)
            
        Returns:
            True if successfully updated, False otherwise
        """
        env_path = Path(env_file)
        
        if not env_path.exists():
            logger.warning("BAILIAN_STATE: .env file not found at {}", env_path)
            return False
        
        try:
            # Read current .env content
            with open(env_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            # Prepare new values
            working_model = self._state["current_working_model"]
            available_models = self._state["available_models"]
            
            if not working_model or not available_models:
                logger.info("BAILIAN_STATE: No working model or available models to sync")
                return False
            
            # Format values - BAILIAN_MODELS does NOT need prefix, MODEL needs prefix
            model_value = f'bailian/{working_model}'
            models_value = ','.join(available_models)  # No prefix for BAILIAN_MODELS
            
            # Track if we updated each field
            updated_model = False
            updated_models = False
            
            # Update lines
            new_lines = []
            for line in lines:
                stripped = line.strip()
                
                # Update MODEL= line
                if stripped.startswith("MODEL=") and not stripped.startswith("MODEL_"):
                    new_lines.append(f'MODEL="{model_value}"\n')
                    updated_model = True
                    logger.info(
                        "BAILIAN_STATE_SYNC: Updated MODEL to '{}'",
                        model_value
                    )
                # Update BAILIAN_MODELS= line
                elif stripped.startswith("BAILIAN_MODELS="):
                    new_lines.append(f'BAILIAN_MODELS="{models_value}"\n')
                    updated_models = True
                    logger.info(
                        "BAILIAN_STATE_SYNC: Updated BAILIAN_MODELS to {} models",
                        len(available_models)
                    )
                else:
                    new_lines.append(line)
            
            # If fields weren't found, append them
            if not updated_model:
                new_lines.append(f'\n# Auto-updated by Bailian state manager\nMODEL="{model_value}"\n')
                logger.info("BAILIAN_STATE_SYNC: Added MODEL='{}' to .env", model_value)
            
            if not updated_models:
                new_lines.append(f'BAILIAN_MODELS="{models_value}"\n')
                logger.info(
                    "BAILIAN_STATE_SYNC: Added BAILIAN_MODELS with {} models to .env",
                    len(available_models)
                )
            
            # Write back to .env
            with open(env_path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
            
            logger.info(
                "BAILIAN_STATE_SYNC: Successfully synced state to {} - working={}, available={}",
                env_path,
                model_value,
                len(available_models)
            )
            return True
            
        except IOError as e:
            logger.error(
                "BAILIAN_STATE_SYNC: Failed to sync to {}: {}",
                env_path,
                e
            )
            return False
