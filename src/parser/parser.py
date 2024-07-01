import asyncio
from typing import Any, Coroutine
from urllib.parse import (
    urljoin,
    urlencode,
    quote_plus,
    urlparse,
    urlunparse,
    ParseResult
)

from bs4 import BeautifulSoup
from httpx import AsyncClient, Response, ConnectError, ConnectTimeout

from .utils import get_proxy, extract_repository_owner, extract_language_statistics


class Parser:
    """
    A class to crawl and parse GitHub repository data based on specified keywords.
    Attributes:
        base_url (str): The base URL for GitHub.
        headers (dict): The HTTP headers to be used in requests.
        input_data (dict): A dictionary containing the search parameters.
    """

    def __init__(self, base_url: str, input_data: dict[str, Any]):
        self.base_url: str = base_url
        self.headers: dict = {'Accept': 'text/html'}
        self.input_data: dict[str, Any] = input_data

    async def fetch_url_content(self, url: str, headers: dict) -> Response:
        """
        Fetch content from a given URL with retries and proxies.
        Args:
            url (str): The URL to fetch content from.
            headers (dict): The headers to include in the request.
        Returns:
            Response: The HTTPX response object containing the fetched content.
        Raises:
            ConnectTimeout: If the connection times out.
            ConnectError: If there is a connection error.
        """
        proxy: str | None = get_proxy(self.input_data)
        async with AsyncClient(proxy=proxy) as client:
            try:
                return await client.get(url, headers=headers)

            except (ConnectTimeout, ConnectError):
                await self.fetch_url_content(url, headers)

    async def parse_github_data(self, urls: list[str]) -> list[dict[str, Any]]:
        """
        Parses repository data from the given list of URLs.
        Args:
            urls (list[str]): A list of repository URLs.
        Returns:
            list[dict[str, Any]]: A list of dictionaries containing parsed repository data.
        """
        parsed_data_list: list[dict[str, Any]] = []
        soups: list[BeautifulSoup] = await self.fetch_html_soups(urls)
        for soup, url in zip(soups, urls):
            parsed_data: dict[str, Any] = {'url': url}
            if self.input_data['type'] == 'repositories':
                parsed_data.update({'extra': {
                    'owner': extract_repository_owner(soup),
                    'language_stats': extract_language_statistics(soup)
                }})
            parsed_data_list.append(parsed_data)
        return parsed_data_list

    def build_search_url(self, keywords: list) -> str:
        """
        Constructs a search URL for the given keyword.
        Args:
            keywords (list): The search keyword.
        Returns:
            str: The constructed search URL.
        """
        url: str = urljoin(self.base_url, 'search')
        parsed_url: ParseResult = urlparse(url)
        params: dict[str, str] = {
            'q': quote_plus(' '.join(keywords)),
            'type': self.input_data['type'].lower()
        }
        return urlunparse((parsed_url.scheme, parsed_url.netloc, parsed_url.path, '', urlencode(params, safe='+'), ''))

    async def fetch_html_soups(self, urls: list[str]) -> list[BeautifulSoup]:
        """
        Creates BeautifulSoup data from the given list of URLs.
        Args:
            urls (list[str]): A list of URLs.
        Returns:
            list[BeautifulSoup]: A list of BeautifulSoup's.
        """
        coros: list[Coroutine[Any, Any, Response]] = [self.fetch_url_content(url, self.headers) for url in urls]
        responses = await asyncio.gather(*coros)
        return [BeautifulSoup(response.text, 'lxml') for response in responses]

    async def gather_data(self) -> list[dict[str, Any]]:
        """
        Parses data for the specified keywords.
        Returns:
            list[dict[str, Any]]: A list of dictionaries containing parsed data.
        """
        url: str = self.build_search_url(self.input_data['keywords'])
        response: Response = await self.fetch_url_content(url, self.headers)
        soup: BeautifulSoup = BeautifulSoup(response.text, 'lxml')
        repo_urls: list[str] = [urljoin(self.base_url, item['href']) for item in soup.select('.search-title > a')]
        github_data: list[dict[str, Any]] = await self.parse_github_data(repo_urls)
        return github_data

    async def run_crawler(self) -> list[dict[str, Any]]:
        """
        The main method to execute the GitHub crawler.
        Returns:
            list[dict[str, Any]]: A list of dictionaries containing parsed data.
        """
        return await self.gather_data()
