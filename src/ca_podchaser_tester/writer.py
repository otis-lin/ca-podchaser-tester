"""JSONL writer module for episode metadata."""

import json
from pathlib import Path
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class JSONLWriter:
    """Handles writing episode metadata to JSONL files."""

    def __init__(self, output_file: str):
        """Initialize JSONL writer.
        
        Args:
            output_file: Path to the output JSONL file
        """
        self.output_file = Path(output_file)
        self.episodes_written = 0

    def write_episodes(self, episodes: List[Dict[str, Any]]) -> int:
        """Write episodes to JSONL file in append mode.
        
        Args:
            episodes: List of episode dictionaries
            
        Returns:
            Number of episodes written
        """
        try:
            # Ensure parent directory exists
            self.output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Write episodes to file in append mode
            with open(self.output_file, "a", encoding="utf-8") as f:
                for episode in episodes:
                    json_line = json.dumps(episode, ensure_ascii=False)
                    f.write(json_line + "\n")
                    self.episodes_written += 1
            
            logger.info(f"Wrote {len(episodes)} episodes to {self.output_file}")
            return len(episodes)
            
        except Exception as e:
            logger.error(f"Error writing to JSONL file: {e}")
            raise

    def get_episodes_written(self) -> int:
        """Get the total number of episodes written.
        
        Returns:
            Number of episodes written
        """
        return self.episodes_written

