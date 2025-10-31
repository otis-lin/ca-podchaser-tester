"""Verification downloader module for transcript verification."""

import json
import time
import requests
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

logger = logging.getLogger(__name__)


class VerificationDownloader:
    """Handles downloading transcripts for verification purposes."""

    def __init__(self, output_dir: str = "transcripts", max_workers: int = 10):
        """Initialize verification downloader.
        
        Args:
            output_dir: Base directory for saving transcripts
            max_workers: Maximum number of concurrent download threads
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.max_workers = max_workers
        self.download_stats = {
            "success": 0,
            "failed": 0,
            "total": 0
        }

    def _get_transcript_path(self, episode_id: str, transcript_type: str) -> Path:
        """Get the file path for a transcript.
        
        Args:
            episode_id: Episode ID
            transcript_type: Type of transcript (e.g., 'raw_JSON', 'beautified_JSON')
            
        Returns:
            Path object for the transcript file
        """
        return self.output_dir / f"{episode_id}_{transcript_type}.json"

    def download_transcript(
        self,
        episode_id: str,
        transcript_url: str,
        transcript_type: str,
        max_retries: int = 3
    ) -> Tuple[bool, str]:
        """Download a single transcript from URL.
        
        Args:
            episode_id: Episode ID
            transcript_url: URL of the transcript
            transcript_type: Type of transcript
            max_retries: Maximum number of retry attempts
            
        Returns:
            Tuple of (success: bool, error_message: str or empty)
        """
        file_path = self._get_transcript_path(episode_id, transcript_type)
        
        # Skip if already downloaded
        if file_path.exists():
            logger.debug(f"Transcript already exists: {file_path}")
            return True, ""
        
        for attempt in range(max_retries):
            try:
                # Measure only the actual HTTP request time
                start_time = time.time()
                response = requests.get(transcript_url, timeout=30.0)
                response.raise_for_status()
                download_time = time.time() - start_time
                
                # Save transcript to file
                file_path.write_text(response.text, encoding="utf-8")
                
                self.download_stats["success"] += 1
                logger.info(f"Downloaded {episode_id}/{transcript_type} in {download_time:.3f}s")
                return True, ""
                
            except Exception as e:
                if attempt == max_retries - 1:
                    error_msg = f"Failed to download {episode_id}/{transcript_type}: {str(e)}"
                    logger.error(error_msg)
                    self.download_stats["failed"] += 1
                    return False, error_msg
                else:
                    # Wait before retry
                    logger.warning(f"Retrying download {episode_id}/{transcript_type}, attempt {attempt + 1}")
                    time.sleep(1 * (attempt + 1))
        
        return False, "Max retries exceeded"

    def download_transcripts_for_episode(self, episode: Dict[str, Any]) -> Tuple[int, int]:
        """Download both transcript types for an episode in parallel.
        
        Args:
            episode: Episode data containing transcripts
            
        Returns:
            Tuple of (success_count, total_count)
        """
        episode_id = episode["id"]
        transcripts = episode.get("transcripts", [])
        
        if not transcripts:
            logger.warning(f"No transcripts found for episode {episode_id}")
            return 0, 0
        
        # Collect all download tasks
        download_tasks = []
        for transcript in transcripts:
            transcript_url = transcript["url"]
            transcript_type = transcript["transcriptType"]
            download_tasks.append((episode_id, transcript_url, transcript_type))
            self.download_stats["total"] += 1
        
        # Download using ThreadPoolExecutor
        success_count = 0
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(
                    self.download_transcript, 
                    episode_id, 
                    transcript_url, 
                    transcript_type
                ): (episode_id, transcript_type)
                for episode_id, transcript_url, transcript_type in download_tasks
            }
            
            for future in as_completed(futures):
                episode_id, transcript_type = futures[future]
                try:
                    success, error_msg = future.result()
                    if success:
                        success_count += 1
                except Exception as e:
                    logger.error(f"Exception downloading {episode_id}/{transcript_type}: {str(e)}")
                    self.download_stats["failed"] += 1
        
        return success_count, len(download_tasks)

    def get_stats(self) -> Dict[str, int]:
        """Get download statistics.
        
        Returns:
            Dictionary with download statistics
        """
        return self.download_stats.copy()

    def reset_stats(self):
        """Reset download statistics."""
        self.download_stats = {
            "success": 0,
            "failed": 0,
            "total": 0
        }


def compose_article(transcript_json: Dict[str, Any]) -> str:
    """Compose a plain text article from transcript JSON.
    
    Args:
        transcript_json: Parsed JSON transcript data
        
    Returns:
        Plain text article with concatenated utterances
        
    Raises:
        KeyError: If transcript structure is invalid
    """
    utterances = transcript_json.get("utterances", [])
    
    if not utterances:
        logger.warning("No utterances found in transcript")
        return ""
    
    # Extract and concatenate utterances
    text_parts = []
    for utterance in utterances:
        utterance_text = utterance.get("utterance", "")
        if utterance_text:
            text_parts.append(utterance_text)
    
    # Join with newlines
    return "\n".join(text_parts)


def save_article(episode_id: str, article_text: str, output_dir: str = "transcripts") -> Path:
    """Save article text to a file.
    
    Args:
        episode_id: Episode ID
        article_text: The article text to save
        output_dir: Directory to save the article
        
    Returns:
        Path to the saved article file
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    article_path = output_path / f"{episode_id}_beautified_post.txt"
    article_path.write_text(article_text, encoding="utf-8")
    
    logger.info(f"Saved article to: {article_path}")
    return article_path

