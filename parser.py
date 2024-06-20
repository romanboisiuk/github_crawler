import asyncio
from asyncio import run
from random import choice
from typing import Any, Coroutine
from urllib.parse import urljoin, urlencode, quote_plus

from bs4 import BeautifulSoup
from httpx import AsyncClient, Response
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

    @staticmethod
    async def fetch_url_content(client: AsyncClient, url: str, headers: dict) -> Response:
        """
        Makes an asynchronous GET request to the given URL.
        Args:
            client (AsyncClient): The HTTPX asynchronous client.
            url (str): The URL to send the GET request to.
            headers (dict): Additional headers to include in the request.
        Returns:
            Response: The HTTPX response object.
        """
        return await client.get(url, headers=headers)

    @staticmethod
    def extract_repository_owner(soup: BeautifulSoup) -> str:
        return soup.select_one('[name=\'octolytics-dimension-user_login\']')['content']

    async def parse_repository_data(self, urls: list[str], client: AsyncClient) -> list[dict[str, Any]]:
        """
        Parses repository data from the given list of URLs.
        Args:
            urls (list[str]): A list of repository URLs.
            client (AsyncClient): The HTTPX asynchronous client.
        Returns:
            list[dict[str, Any]]: A list of dictionaries containing parsed repository data.
        """
        repositories: list[dict[str, Any]] = []
        page_soups: list[BeautifulSoup] = await self.fetch_html_soups(client, urls)
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
        url = urljoin(self.base_url, 'search')
        params = {
            'q': quote_plus(' '.join(keywords)),
            'type': self.data['type'].lower()
        }
        return f'{url}?{urlencode(params, safe='+')}'

    async def fetch_html_soups(self, client: AsyncClient, urls: list[str]) -> list[BeautifulSoup]:
        coros: list[Coroutine[Any, Any, Response]] = [self.fetch_url_content(client, url, self.headers) for url in urls]
        responses = await asyncio.gather(*coros)
        return [BeautifulSoup(response.text, 'lxml') for response in responses]

    async def gather_data(self, client: AsyncClient) -> list[dict[str, Any]]:
        """
        Parses data for the specified keywords.
        Args:
            client (AsyncClient): The HTTPX asynchronous client.
        Returns:
            list[dict[str, Any]]: A list of dictionaries containing parsed data.
        """
        url: str = self.build_search_url(self.data['keywords'])
        response: Response = await self.fetch_url_content(client, url, self.headers)
        soup: BeautifulSoup = BeautifulSoup(response.text, 'lxml')
        repo_urls: list[str] = [urljoin(self.base_url, item['href']) for item in soup.select('.search-title > a')]
        repository_data: list[dict[str, Any]] = await self.parse_repository_data(repo_urls, client)
        return repository_data

    async def run_crawler(self):
        """
        The main method to execute the GitHub crawler.
        Selects a random proxy, creates an asynchronous client, and parses data.
        Returns:
            list[dict[str, Any]]: A list of dictionaries containing parsed data.
        """
        proxy = choice(self.data['proxies'])
        # proxies = {'http://': f'http://{proxy}', 'https://': f'https://{proxy}'}
        proxies = {}
        async with AsyncClient(proxies=proxies) as client:
            return await self.gather_data(client)


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
        ],
        'type': 'Repositories'
    }
    run(GitHubCrawler(base_url, data).run_crawler())
