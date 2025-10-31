"""GraphQL client for PodChaser API."""

import httpx
import time
import logging
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class GraphQLClient:
    """Client for interacting with PodChaser GraphQL API."""

    GRAPHQL_ENDPOINT = "https://api.podchaser.com/graphql"

    # GraphQL query for fetching episodes with transcripts
    EPISODES_QUERY = """
    query FetchEpisodes($from: DateTime!, $to: DateTime!, $cursor: String) {
      episodes(
        first: 100
        paginationType: CURSOR
        cursor: $cursor
        filters: {
          hasTranscripts: true,
          airDate: { from: $from, to: $to}
        }
      ) {
        cursorInfo {
          total
          nextCursor
          cursorRefreshed
        }
        data {
          id
          title
          description
          airDate
          imageUrl
          audioUrl
          url
          webUrl
          fileSize
          guid
          length
          explicit
          episodeType
          modifiedDate
          ratingCount
          reviewCount
          ratingAverage
          podcastEstimatedReach
          audienceReach { 
            from
            to
          }
          ratingSummary {
            value
            count
          }
          transcripts {
            url
            source
            transcriptType
            generatedDate
            transcribedAudioUrl
          }
          podcast {
            id
            title
            language
          }
        }
      }
    }
    """

    # GraphQL query for fetching a single episode by ID
    GET_EPISODE_BY_ID = """
    query GET_EPISODE_BY_ID ($episodeId: String!) {
        episode(identifier: {id: $episodeId, type: PODCHASER}) {
            id
            audioUrl
            url
            webUrl
            airDate
            addedDate
            transcripts {
                url
                source
                transcriptType
                generatedDate
                transcribedAudioUrl
            }
        }
    }
    """

    def __init__(self, headers: dict):
        """Initialize GraphQL client with authentication headers.
        
        Args:
            headers: Dictionary containing authorization headers
        """
        self.headers = headers

    async def fetch_episodes_page(
        self,
        client: httpx.AsyncClient,
        start_date: str,
        end_date: str,
        cursor: Optional[str] = None
    ) -> Dict[str, Any]:
        """Fetch a single page of episodes with transcripts.
        
        Args:
            client: Async HTTP client
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            cursor: Optional cursor for pagination
            
        Returns:
            Dictionary containing episodes data and cursor info
            
        Raises:
            httpx.HTTPError: If API request fails
        """
        variables = {
            "from": f"{start_date} 00:00:00",
            "to": f"{end_date} 23:59:59",
            "cursor": cursor
        }

        payload = {
            "query": self.EPISODES_QUERY,
            "variables": variables
        }

        # Time the API call
        start_time = time.time()
        
        response = await client.post(
            self.GRAPHQL_ENDPOINT,
            json=payload,
            headers=self.headers,
            timeout=60.0
        )
        response.raise_for_status()
        
        elapsed_time = time.time() - start_time
        logger.info(f"GraphQL API call completed in {elapsed_time:.2f}s")
        
        data = response.json()
        
        # Check for GraphQL errors
        if "errors" in data:
            raise Exception(f"GraphQL errors: {data['errors']}")
        
        return data["data"]["episodes"]

    async def fetch_all_episodes(
        self,
        start_date: str,
        end_date: str,
        progress_callback=None
    ):
        """Generator that yields pages of episodes with transcripts.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            progress_callback: Optional callback function for progress updates
            
        Yields:
            Dictionary containing episodes data for each page
        """
        cursor = None
        page_num = 0
        
        async with httpx.AsyncClient() as client:
            while True:
                page_num += 1
                
                # Fetch page
                result = await self.fetch_episodes_page(
                    client, start_date, end_date, cursor
                )
                
                episodes = result["data"]
                cursor_info = result["cursorInfo"]
                
                if progress_callback:
                    progress_callback(
                        page=page_num,
                        total=cursor_info.get("total", 0),
                        episodes_in_page=len(episodes)
                    )
                
                yield result
                
                # Check if there are more pages
                next_cursor = cursor_info.get("nextCursor")
                if not next_cursor:
                    break
                    
                cursor = next_cursor

    async def fetch_episode_by_id(
        self,
        client: httpx.AsyncClient,
        episode_id: str
    ) -> Optional[Dict[str, Any]]:
        """Fetch a single episode by its ID.
        
        Args:
            client: Async HTTP client
            episode_id: The episode ID to fetch
            
        Returns:
            Dictionary containing episode data, or None if not found
            
        Raises:
            httpx.HTTPError: If API request fails
        """
        variables = {
            "episodeId": episode_id
        }

        payload = {
            "query": self.GET_EPISODE_BY_ID,
            "variables": variables
        }

        # Time the API call
        start_time = time.time()
        
        response = await client.post(
            self.GRAPHQL_ENDPOINT,
            json=payload,
            headers=self.headers,
            timeout=60.0
        )
        response.raise_for_status()
        
        elapsed_time = time.time() - start_time
        logger.debug(f"GraphQL API call for episode {episode_id} completed in {elapsed_time:.2f}s")
        
        data = response.json()
        
        # Check for GraphQL errors
        if "errors" in data:
            raise Exception(f"GraphQL errors: {data['errors']}")
        
        return data["data"]["episode"]

