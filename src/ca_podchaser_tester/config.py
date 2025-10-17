"""Configuration module for PodChaser API credentials."""

import os
from dotenv import load_dotenv


class Config:
    """Configuration class for PodChaser API."""

    def __init__(self):
        """Initialize configuration by loading environment variables."""
        load_dotenv()
        self.access_token = os.getenv("PODCHASER_ACCESS_TOKEN")
        self._validate()

    def _validate(self):
        """Validate that required credentials are present."""
        if not self.access_token:
            raise ValueError(
                "PODCHASER_ACCESS_TOKEN environment variable is not set. "
                "Please set it in your .env file or environment."
            )

    @property
    def headers(self) -> dict:
        """Return headers for API authentication."""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

