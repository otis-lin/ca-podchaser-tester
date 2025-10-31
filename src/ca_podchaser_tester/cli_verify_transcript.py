"""Command-line interface for transcript verification."""

import asyncio
import click
import csv
import json
import logging
import time
from pathlib import Path

import httpx

from .config import Config
from .graphql_client import GraphQLClient
from .verification_downloader import (
    VerificationDownloader,
    compose_article,
    save_article
)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# Disable httpx and httpcore verbose logs
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


@click.command()
@click.option(
    "--csv-file",
    required=True,
    type=click.Path(exists=True),
    help="Path to CSV file containing episode IDs"
)
@click.option(
    "--output-dir",
    default="transcripts",
    help="Directory for saving transcript files and articles (default: transcripts)"
)
@click.option(
    "--verbose",
    is_flag=True,
    help="Enable verbose logging"
)
def main(csv_file: str, output_dir: str, verbose: bool):
    """Verify and download transcripts for episodes from a CSV file.
    
    This tool reads episode IDs from a CSV file, fetches episode data from 
    PodChaser's GraphQL API, downloads both transcript types (beautified_JSON 
    and raw_JSON), and composes plain text articles from the transcripts.
    
    Example:
        verify-transcript --csv-file csv/transcript_malformed.csv
    """
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Read episode IDs from CSV file
    logger.info(f"Reading episode IDs from: {csv_file}")
    episode_ids = read_episode_ids_from_csv(csv_file)
    
    if not episode_ids:
        logger.error("No episode IDs found in CSV file")
        raise click.ClickException("No episode IDs found in CSV file")
    
    logger.info(f"Found {len(episode_ids)} episode IDs")
    
    logger.info("=" * 80)
    logger.info("PodChaser Transcript Verification")
    logger.info("=" * 80)
    logger.info(f"Episode IDs: {len(episode_ids)}")
    logger.info(f"Output directory: {output_dir}")
    logger.info("=" * 80)
    
    # Run async main function and track total execution time
    start_time = time.time()
    asyncio.run(async_main(episode_ids, output_dir))
    total_time = time.time() - start_time
    
    # Log total execution time
    minutes = int(total_time // 60)
    seconds = total_time % 60
    if minutes > 0:
        logger.info(f"Total execution time: {minutes}m {seconds:.2f}s")
    else:
        logger.info(f"Total execution time: {seconds:.2f}s")


def read_episode_ids_from_csv(csv_file: str) -> list[str]:
    """Read episode IDs from CSV file, skipping the header row.
    
    Args:
        csv_file: Path to CSV file
        
    Returns:
        List of episode IDs as strings
    """
    episode_ids = []
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        csv_reader = csv.reader(f)
        # Skip header row
        next(csv_reader, None)
        
        for row in csv_reader:
            if row and row[0].strip():
                episode_ids.append(row[0].strip())
    
    return episode_ids


async def async_main(episode_ids: list[str], output_dir: str):
    """Async main function that orchestrates the verification process."""
    
    try:
        # Initialize components
        logger.info("Loading configuration...")
        config = Config()
        
        logger.info("Initializing clients...")
        graphql_client = GraphQLClient(config.headers)
        downloader = VerificationDownloader(output_dir)
        
        # Track overall statistics
        total_episodes_processed = 0
        total_episodes_failed = 0
        total_transcripts_downloaded = 0
        total_articles_created = 0
        
        logger.info("Starting episode verification process...")
        logger.info("")
        
        async with httpx.AsyncClient() as client:
            for idx, episode_id in enumerate(episode_ids, 1):
                logger.info(f"[{idx}/{len(episode_ids)}] Processing episode ID: {episode_id}")
                
                try:
                    # Fetch episode data from GraphQL API
                    episode = await graphql_client.fetch_episode_by_id(client, episode_id)
                    
                    if not episode:
                        logger.warning(f"Episode {episode_id} not found")
                        total_episodes_failed += 1
                        continue
                    
                    # Check if episode has transcripts
                    transcripts = episode.get("transcripts", [])
                    if not transcripts:
                        logger.warning(f"Episode {episode_id} has no transcripts")
                        total_episodes_failed += 1
                        continue
                    
                    logger.info(f"Found {len(transcripts)} transcript(s) for episode {episode_id}")
                    
                    # Download transcripts
                    success_count, total_count = downloader.download_transcripts_for_episode(episode)
                    total_transcripts_downloaded += success_count
                    logger.info(f"Downloaded {success_count}/{total_count} transcripts")
                    
                    # Compose article from beautified_JSON transcript
                    beautified_path = Path(output_dir) / f"{episode_id}_beautified_JSON.json"
                    
                    if beautified_path.exists():
                        try:
                            with open(beautified_path, 'r', encoding='utf-8') as f:
                                transcript_data = json.load(f)
                            
                            article_text = compose_article(transcript_data)
                            
                            if article_text:
                                save_article(episode_id, article_text, output_dir)
                                total_articles_created += 1
                                logger.info(f"Created article for episode {episode_id}")
                            else:
                                logger.warning(f"No article content generated for episode {episode_id}")
                        
                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to parse transcript JSON for episode {episode_id}: {e}")
                        except Exception as e:
                            logger.error(f"Failed to compose article for episode {episode_id}: {e}")
                    else:
                        logger.warning(f"Beautified transcript not found for episode {episode_id}")
                    
                    total_episodes_processed += 1
                    logger.info("")
                
                except Exception as e:
                    logger.error(f"Error processing episode {episode_id}: {e}", exc_info=True)
                    total_episodes_failed += 1
                    logger.info("")
                    continue
        
        # Print final statistics
        logger.info("=" * 80)
        logger.info("Verification Complete!")
        logger.info("=" * 80)
        logger.info(f"Total episodes processed: {total_episodes_processed}/{len(episode_ids)}")
        logger.info(f"Episodes failed: {total_episodes_failed}")
        
        stats = downloader.get_stats()
        logger.info(f"Transcripts downloaded: {stats['success']}/{stats['total']}")
        if stats['failed'] > 0:
            logger.warning(f"Failed downloads: {stats['failed']}")
        
        logger.info(f"Articles created: {total_articles_created}")
        logger.info(f"Output directory: {output_dir}/")
        logger.info("=" * 80)
        
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        raise click.ClickException(str(e))
    except Exception as e:
        logger.error(f"Error during execution: {e}", exc_info=True)
        raise click.ClickException(str(e))


if __name__ == "__main__":
    main()