# PodChaser Transcript Downloader

A Python CLI tool to download podcast transcripts from PodChaser's API by date range.

## Features

- Fetch episodes with transcripts from PodChaser GraphQL API by date range
- Handle cursor-based pagination for large result sets (10,000+ episodes)
- Download all transcript types (raw_JSON, beautified_JSON, etc.) in parallel
- Process 100 episodes at a time for memory efficiency
- Save episode metadata to JSONL format
- Organize transcripts by type in separate folders
- Comprehensive error handling and retry logic
- Progress logging and statistics

## Installation

1. Install dependencies using Poetry:

```bash
poetry install
```

2. Create a `.env` file in the project root with your PodChaser API credentials:

```bash
cp .env.example .env
```

Edit the `.env` file and add your access token:

```
PODCHASER_ACCESS_TOKEN=your_access_token_here
```

## Usage

### Basic Usage

```bash
poetry run podchaser-dl --start-date 2024-01-01 --end-date 2024-12-31
```

### With Custom Output File

```bash
poetry run podchaser-dl --start-date 2024-01-01 --end-date 2024-12-31 --output my_episodes.jsonl
```

### With Custom Transcripts Directory

```bash
poetry run podchaser-dl --start-date 2024-01-01 --end-date 2024-12-31 --transcripts-dir my_transcripts
```

### Enable Verbose Logging

```bash
poetry run podchaser-dl --start-date 2024-01-01 --end-date 2024-12-31 --verbose
```

### All Options

```bash
poetry run podchaser-dl --help
```

## CLI Options

- `--start-date`: Start date for episode search (YYYY-MM-DD) [required]
- `--end-date`: End date for episode search (YYYY-MM-DD) [required]
- `--output`: Output JSONL file for episode metadata (default: episodes.jsonl)
- `--transcripts-dir`: Directory for saving transcript files (default: transcripts)
- `--verbose`: Enable verbose logging
- `--help`: Show help message

## Output Structure

### Episode Metadata (JSONL)

The tool creates a JSONL (JSON Lines) file where each line is a complete JSON object containing all episode metadata from the PodChaser API:

```json
{"id": "268160043", "title": "Episode Title", "description": "...", "airDate": "2025-10-06", ...}
{"id": "268126279", "title": "Another Episode", "description": "...", "airDate": "2025-10-06", ...}
```

### Transcripts

Transcripts are organized by type in separate folders:

```
transcripts/
├── raw_JSON/
│   ├── 268160043.json
│   ├── 268126279.json
│   └── ...
├── beautified_JSON/
│   ├── 268160043.json
│   ├── 268126279.json
│   └── ...
└── [other_transcript_types]/
    └── ...
```

## How It Works

1. **Authentication**: Loads PodChaser API access token from environment variables
2. **Query Episodes**: Fetches episodes with transcripts using GraphQL API with date range filters
3. **Pagination**: Handles cursor-based pagination (100 episodes per page)
4. **Parallel Downloads**: Downloads all transcript types for 100 episodes concurrently
5. **Save Metadata**: Writes episode metadata to JSONL file incrementally
6. **Progress Tracking**: Logs progress and statistics throughout the process

## Example Output

```
================================================================================
PodChaser Transcript Downloader
================================================================================
Date range: 2024-01-01 to 2024-12-31
Output file: episodes.jsonl
Transcripts directory: transcripts
================================================================================
Loading configuration...
Initializing clients...
Starting episode fetch and download process...

Page 1: Found 100 episodes (Total episodes available: 150)
Downloading transcripts for 100 episodes...
Downloaded 200 transcripts successfully
Writing episode metadata to episodes.jsonl...
Processed page 1 (100 episodes)

Page 2: Found 50 episodes (Total episodes available: 150)
Downloading transcripts for 50 episodes...
Downloaded 100 transcripts successfully
Writing episode metadata to episodes.jsonl...
Processed page 2 (50 episodes)

================================================================================
Download Complete!
================================================================================
Total pages processed: 2
Total episodes processed: 150
Episodes metadata written to: episodes.jsonl
Transcripts downloaded: 300/300
Transcripts saved to: transcripts/
================================================================================
```

## Error Handling

- **Configuration Errors**: Validates access token on startup
- **Network Errors**: Retries failed downloads up to 3 times with exponential backoff
- **Partial Failures**: Continues processing even if individual downloads fail
- **Logging**: All errors are logged for troubleshooting

## Development

### Running Tests

```bash
poetry run pytest
```

### Code Structure

```
src/ca_podchaser_tester/
├── __init__.py          # Package initialization
├── cli.py               # Command-line interface
├── config.py            # Configuration and credentials
├── graphql_client.py    # GraphQL API client
├── downloader.py        # Transcript downloader
└── writer.py            # JSONL writer
```

## Requirements

- Python >= 3.12
- click >= 8.1.0
- httpx >= 0.27.0
- python-dotenv >= 1.0.0

## License

See LICENSE file for details.

