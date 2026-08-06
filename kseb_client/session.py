"""
HTTP session management with retries for KSEB Client SDK.

This module provides a configured requests.Session with automatic retry logic,
exponential backoff, and timeout handling.
"""

import logging
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .constants import DEFAULT_BACKOFF_FACTOR, DEFAULT_RETRIES, DEFAULT_TIMEOUT, USER_AGENT
from .exceptions import KSEBNetworkError

logger = logging.getLogger(__name__)


class KSEBSession:
    """Manages HTTP communication with retry logic and exponential backoff."""

    def __init__(
        self,
        timeout: int = DEFAULT_TIMEOUT,
        retries: int = DEFAULT_RETRIES,
        backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
    ):
        """
        Initialize KSEB session.

        Args:
            timeout: HTTP request timeout in seconds. Defaults to 15.
            retries: Number of retries for failed requests. Defaults to 3.
            backoff_factor: Exponential backoff multiplier. Defaults to 0.3.
        """
        self.timeout = timeout
        self.retries = retries
        self.backoff_factor = backoff_factor
        self._session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Create a requests.Session with retry configuration."""
        session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=self.retries,
            backoff_factor=self.backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "PUT", "DELETE"],
        )

        # Mount adapter for both HTTP and HTTPS
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # Set user agent
        session.headers.update({"User-Agent": USER_AGENT})

        return session

    def get(self, url: str, **kwargs: Any) -> requests.Response:
        """
        Perform a GET request.

        Args:
            url: URL to request
            **kwargs: Additional arguments to pass to requests.get()

        Returns:
            Response object

        Raises:
            KSEBNetworkError: If request fails after retries
        """
        kwargs.setdefault("timeout", self.timeout)
        try:
            logger.debug(f"GET {url}")
            response = self._session.get(url, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"GET request failed: {url} - {e}")
            raise KSEBNetworkError(f"Failed to GET {url}: {str(e)}") from e

    def post(self, url: str, **kwargs: Any) -> requests.Response:
        """
        Perform a POST request.

        Args:
            url: URL to request
            **kwargs: Additional arguments to pass to requests.post()

        Returns:
            Response object

        Raises:
            KSEBNetworkError: If request fails after retries
        """
        kwargs.setdefault("timeout", self.timeout)
        try:
            logger.debug(f"POST {url}")
            response = self._session.post(url, **kwargs)
            # Note: Don't call raise_for_status() here as some endpoints
            # return 200 with error data inside
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"POST request failed: {url} - {e}")
            raise KSEBNetworkError(f"Failed to POST {url}: {str(e)}") from e

    def close(self) -> None:
        """Close the session and release resources."""
        self._session.close()
        logger.debug("Session closed")

    def __enter__(self) -> "KSEBSession":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.close()
