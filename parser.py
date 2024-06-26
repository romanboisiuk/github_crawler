import asyncio
from random import choice
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
from loguru import logger


class GitHubCrawler:
    """
    A class to crawl and parse GitHub repository data based on specified keywords.
    Attributes:
        base_url (str): The base URL for GitHub.
        headers (dict): The HTTP headers to be used in requests.
        data (dict): A dictionary containing the search parameters.
    """

    def __init__(self, base_url: str, data: dict[str, Any]):
        self.base_url: str = base_url
        self.headers: dict = {'Accept': 'text/html'}
        self.data: dict[str, Any] = data

    @staticmethod
    def extract_language_statistics(soup: BeautifulSoup) -> dict[str, Any]:
        """
        Extracts language statistics from the given HTML elements.
        Args:
            soup: BeautifulSoup
        Returns:
            dict[str, Any]: A dictionary containing the language statistics.
        """
        lang_stats_data: dict[str, Any] = {}
        for item in soup.select('.d-inline-flex.flex-items-center'):
            language_stats = item.select('span')
            lang_stats_data[language_stats[0].text] = language_stats[1].text
        return lang_stats_data

    async def fetch_url_content(self, url: str, headers: dict, retry: int = 0) -> Response:
        """
        Fetch content from a given URL with retries and proxies.
        Args:
            url (str): The URL to fetch content from.
            headers (dict): The headers to include in the request.
            retry: (int): The current retry attempt. Defaults to 0.
        Returns:
            Response: The HTTPX response object containing the fetched content.
        Raises:
            ConnectTimeout: If the connection times out.
            ConnectError: If there is a connection error.
        """
        proxy = f'http://{choice(self.data['proxies'])}' if retry else None
        async with AsyncClient(proxy=proxy) as client:
            if retry < 5:
                try:
                    return await client.get(url, headers=headers)

                except (ConnectTimeout, ConnectError):
                    await self.fetch_url_content(url, headers, retry=retry + 1)
            else:
                logger.error('Bad proxies, failed 5 times')

    @staticmethod
    def extract_repository_owner(soup: BeautifulSoup) -> str:
        return soup.select_one('[name=\'octolytics-dimension-user_login\']')['content']

    async def parse_repository_data(self, urls: list[str]) -> list[dict[str, Any]]:
        """
        Parses repository data from the given list of URLs.
        Args:
            urls (list[str]): A list of repository URLs.
        Returns:
            list[dict[str, Any]]: A list of dictionaries containing parsed repository data.
        """
        repositories: list[dict[str, Any]] = []
        page_soups: list[BeautifulSoup] = await self.fetch_html_soups(urls)
        for soup, url in zip(page_soups, urls):
            repo_data = {
                'url': url,
                'extra': {
                    'owner': self.extract_repository_owner(soup),
                    'language_stats': self.extract_language_statistics(soup)
                }
            }
            logger.debug(f'Repository data: {repo_data}')
            repositories.append(repo_data)
        return repositories

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
            'type': self.data['type'].lower()
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
        url: str = self.build_search_url(self.data['keywords'])
        response: Response = await self.fetch_url_content(url, self.headers)
        soup: BeautifulSoup = BeautifulSoup(response.text, 'lxml')
        repo_urls: list[str] = [urljoin(self.base_url, item['href']) for item in soup.select('.search-title > a')]
        repository_data: list[dict[str, Any]] = await self.parse_repository_data(repo_urls)
        return repository_data

    async def run_crawler(self) -> list[dict[str, Any]]:
        """
        The main method to execute the GitHub crawler.
        Returns:
            list[dict[str, Any]]: A list of dictionaries containing parsed data.
        """
        return await self.gather_data()


if __name__ == '__main__':
    base_url: str = 'https://github.com/'
    data: dict[str, Any] = {
        'keywords': [
            'openstack',
            'nova',
            'css',
        ],
        'proxies': [
            '116.108.118.117:4009',
            '65.108.118.117:4009',
            '116.34.118.117:4009',
            '116.108.7.117:4009',
            '116.108.118.3:4009',
        ],
        'type': 'Repositories'
    }
    asyncio.run(GitHubCrawler(base_url, data).run_crawler())
