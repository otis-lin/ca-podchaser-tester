"""Transcript downloader module."""

import asyncio
import httpx
import time
from pathlib import Path
from typing import List, Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)


class TranscriptDownloader:
    """Handles downloading transcripts from S3 URLs."""

    def __init__(self, output_dir: str = "transcripts"):
        """Initialize transcript downloader.
        
        Args:
            output_dir: Base directory for saving transcripts
        """
        self.output_dir = Path(output_dir)
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
        type_dir = self.output_dir / transcript_type
        type_dir.mkdir(parents=True, exist_ok=True)
        return type_dir / f"{episode_id}.json"

    async def download_transcript(
        self,
        client: httpx.AsyncClient,
        episode_id: str,
        transcript_url: str,
        transcript_type: str,
        max_retries: int = 3
    ) -> Tuple[bool, str]:
        """Download a single transcript from S3.
        
        Args:
            client: Async HTTP client
            episode_id: Episode ID
            transcript_url: S3 URL of the transcript
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
                response = await client.get(transcript_url, timeout=30.0)
                response.raise_for_status()
                download_time = time.time() - start_time
                
                # Save transcript to file
                file_path.write_text(response.text, encoding="utf-8")
                
                self.download_stats["success"] += 1
                logger.info(f"Downloaded {episode_id}/{transcript_type} in {download_time:.3f}s (size: {len(response.text)} bytes)")
                return True, ""
                
            except Exception as e:
                if attempt == max_retries - 1:
                    error_msg = f"Failed to download {episode_id}/{transcript_type}: {str(e)}"
                    logger.error(error_msg)
                    self.download_stats["failed"] += 1
                    return False, error_msg
                else:
                    # Wait before retry
                    await asyncio.sleep(1 * (attempt + 1))
        
        return False, "Max retries exceeded"

    async def download_episode_transcripts(
        self,
        client: httpx.AsyncClient,
        episode: Dict[str, Any]
    ) -> List[Tuple[bool, str]]:
        """Download all transcripts for a single episode.
        
        Args:
            client: Async HTTP client
            episode: Episode data containing transcripts
            
        Returns:
            List of (success, error_message) tuples for each transcript
        """
        episode_id = episode["id"]
        transcripts = episode.get("transcripts", [])
        
        if not transcripts:
            logger.warning(f"No transcripts found for episode {episode_id}")
            return []

        if len(transcripts) != 2:
            logger.warning(
                f"Unexpected number of transcripts ({len(transcripts)}) "
                f"for episode {episode_id}"
                f", transcripts: {transcripts}"
            )
            return []

        tasks = []
        for transcript in transcripts:
            transcript_url = transcript["url"]
            transcript_type = transcript["transcriptType"]

            if transcript_type != "beautified_JSON":
                continue
            
            task = self.download_transcript(
                client, episode_id, transcript_url, transcript_type
            )
            tasks.append(task)
            self.download_stats["total"] += 1
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions that occurred
        processed_results = []
        for result in results:
            if isinstance(result, Exception):
                error_msg = f"Exception during download: {str(result)}"
                logger.error(error_msg)
                self.download_stats["failed"] += 1
                processed_results.append((False, error_msg))
            else:
                processed_results.append(result)
        
        return processed_results

    async def download_batch(self, episodes: List[Dict[str, Any]]) -> int:
        """Download transcripts for a batch of episodes in parallel.
        
        Args:
            episodes: List of episode data
            
        Returns:
            Number of transcripts successfully downloaded
        """
        async with httpx.AsyncClient() as client:
            tasks = [
                self.download_episode_transcripts(client, episode)
                for episode in episodes
            ]
            
            results = await asyncio.gather(*tasks)
            
            # Count successful downloads
            success_count = sum(
                sum(1 for success, _ in episode_results if success)
                for episode_results in results
            )
            
            return success_count

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

