"""Command-line interface for PodChaser transcript downloader."""

import asyncio
import click
import logging
import time
from datetime import datetime
from pathlib import Path

from .config import Config
from .graphql_client import GraphQLClient
from .downloader import TranscriptDownloader
from .writer import JSONLWriter


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


def validate_date(ctx, param, value):
    """Validate date format."""
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return value
    except ValueError:
        raise click.BadParameter(f"Date must be in YYYY-MM-DD format, got: {value}")


@click.command()
@click.option(
    "--start-date",
    required=True,
    callback=validate_date,
    help="Start date for episode search (YYYY-MM-DD)"
)
@click.option(
    "--end-date",
    required=True,
    callback=validate_date,
    help="End date for episode search (YYYY-MM-DD)"
)
@click.option(
    "--output",
    default="episodes.jsonl",
    help="Output JSONL file for episode metadata (default: episodes.jsonl)"
)
@click.option(
    "--transcripts-dir",
    default="transcripts",
    help="Directory for saving transcript files (default: transcripts)"
)
@click.option(
    "--verbose",
    is_flag=True,
    help="Enable verbose logging"
)
def main(start_date: str, end_date: str, output: str, transcripts_dir: str, verbose: bool):
    """Download podcast transcripts from PodChaser API by date range.
    
    This tool fetches episodes with transcripts from PodChaser's GraphQL API
    within the specified date range, downloads all transcript types in parallel,
    and saves episode metadata to a JSONL file.
    
    Example:
        podchaser-dl --start-date 2024-01-01 --end-date 2024-12-31 --output episodes.jsonl
    """
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validate date range
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    
    if start > end:
        raise click.BadParameter("Start date must be before or equal to end date")
    
    logger.info("=" * 80)
    logger.info("PodChaser Transcript Downloader")
    logger.info("=" * 80)
    logger.info(f"Date range: {start_date} to {end_date}")
    logger.info(f"Output file: {output}")
    logger.info(f"Transcripts directory: {transcripts_dir}")
    logger.info("=" * 80)
    
    # Run async main function and track total execution time
    start_time = time.time()
    asyncio.run(async_main(start_date, end_date, output, transcripts_dir))
    total_time = time.time() - start_time
    
    # Log total execution time
    minutes = int(total_time // 60)
    seconds = total_time % 60
    if minutes > 0:
        logger.info(f"Total execution time: {minutes}m {seconds:.2f}s")
    else:
        logger.info(f"Total execution time: {seconds:.2f}s")


async def async_main(start_date: str, end_date: str, output: str, transcripts_dir: str):
    """Async main function that orchestrates the download process."""
    
    try:
        # Initialize components
        logger.info("Loading configuration...")
        config = Config()
        
        logger.info("Initializing clients...")
        graphql_client = GraphQLClient(config.headers)
        downloader = TranscriptDownloader(transcripts_dir)
        writer = JSONLWriter(output)
        
        # Track overall statistics
        total_episodes = 0
        total_pages = 0
        
        # Progress callback
        def log_progress(page, total, episodes_in_page):
            logger.info(
                f"Page {page}: Found {episodes_in_page} episodes "
                f"(Total episodes available: {total})"
            )
        
        logger.info("Starting episode fetch and download process...")
        logger.info("")
        
        # Fetch and process episodes page by page
        async for page_result in graphql_client.fetch_all_episodes(
            start_date, end_date, progress_callback=log_progress
        ):
            total_pages += 1
            episodes = page_result["data"]
            
            if not episodes:
                logger.info("No episodes found in this page")
                continue
            
            # Download transcripts for this batch in parallel
            logger.info(f"Downloading transcripts for {len(episodes)} episodes...")
            start_time = time.time()
            success_count = await downloader.download_batch(episodes)
            total_time = time.time() - start_time
            logger.info(f"Downloaded {success_count} transcripts successfully in {total_time:.2f}s")
            
            # Write episode metadata to JSONL
            logger.info(f"Writing episode metadata to {output}...")
            writer.write_episodes(episodes)
            
            total_episodes += len(episodes)
            
            logger.info(f"Processed page {total_pages} ({len(episodes)} episodes)")
            logger.info("")
        
        # Print final statistics
        logger.info("=" * 80)
        logger.info("Download Complete!")
        logger.info("=" * 80)
        logger.info(f"Total pages processed: {total_pages}")
        logger.info(f"Total episodes processed: {total_episodes}")
        logger.info(f"Episodes metadata written to: {output}")
        
        stats = downloader.get_stats()
        logger.info(f"Transcripts downloaded: {stats['success']}/{stats['total']}")
        if stats['failed'] > 0:
            logger.warning(f"Failed downloads: {stats['failed']}")
        
        logger.info(f"Transcripts saved to: {transcripts_dir}/")
        logger.info("=" * 80)
        
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        raise click.ClickException(str(e))
    except Exception as e:
        logger.error(f"Error during execution: {e}", exc_info=True)
        raise click.ClickException(str(e))


if __name__ == "__main__":
    main()

