import asyncio
from asyncio import run, Task
from random import choice
from typing import Any
from urllib.parse import urljoin, urlencode

from bs4 import BeautifulSoup
from httpx import AsyncClient, ConnectTimeout
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
    def get_lang_stats(items: list) -> dict[str, Any]:
        """
        Extracts language statistics from the given HTML elements.
        Args:
            items (list): A list of BeautifulSoup elements containing language stats.
        Returns:
            dict[str, Any]: A dictionary containing the language statistics.
        """
        lang_stats_data: dict[str, Any] = {}
        for item in items:
            language_stats = item.select('span')
            lang_stats_data[language_stats[0].text] = language_stats[1].text
        return lang_stats_data

    @staticmethod
    async def make_request(client: AsyncClient, url: str, headers=None):
        """
        Makes an asynchronous GET request to the given URL.
        Args:
            client (AsyncClient): The HTTPX asynchronous client.
            url (str): The URL to send the GET request to.
            headers (dict, optional): Additional headers to include in the request.
        Returns:
            Response: The HTTPX response object.
        """
        return await client.get(url, headers=headers)

    async def parse_repo(self, urls: list[str], client: AsyncClient) -> list[dict[str, Any]]:
        """
        Parses repository data from the given list of URLs.
        Args:
            urls (list[str]): A list of repository URLs.
            client (AsyncClient): The HTTPX asynchronous client.
        Returns:
            list[dict[str, Any]]: A list of dictionaries containing parsed repository data.
        """
        repos_data: list[dict[str, Any]] = []
        tasks: list[Task] = [asyncio.create_task(self.make_request(client, url)) for url in urls]
        responses = await asyncio.gather(*tasks)
        soups: list[BeautifulSoup] = [BeautifulSoup(response.text, 'lxml') for response in responses]
        for soup, url in zip(soups, urls):
            owner: str = soup.select_one('[name=\'octolytics-dimension-user_login\']')['content']
            lang_stats: dict[str, Any] = self.get_lang_stats(soup.select('.d-inline-flex.flex-items-center'))
            repos_data.append({
                'url': url,
                'extra': {
                    'owner': owner,
                    'language_stats': lang_stats
                }
            })
        return repos_data

    def parse_url(self, keyword: str) -> str:
        """
        Constructs a search URL for the given keyword.
        Args:
            keyword (str): The search keyword.
        Returns:
            str: The constructed search URL.
        """
        url = urljoin(self.base_url, 'search')
        params = {
            'q': keyword,
            'type': self.data['type'].lower()
        }
        return f'{url}?{urlencode(params)}'

    async def parse_data(self, client: AsyncClient) -> list[dict[str, Any]]:
        """
        Parses data for the specified keywords.
        Args:
            client (AsyncClient): The HTTPX asynchronous client.
        Returns:
            list[dict[str, Any]]: A list of dictionaries containing parsed data.
        """
        repos_data: list[dict[str, Any]] = []
        keyword_urls: list[str] = [self.parse_url(keyword) for keyword in self.data['keywords']]
        tasks: list[Task] = [asyncio.create_task(self.make_request(client, url, self.headers)) for url in keyword_urls]
        responses = await asyncio.gather(*tasks)
        soups: list[BeautifulSoup] = [BeautifulSoup(response.text, 'lxml') for response in responses]
        for soup in soups:
            urls: list[str] = [urljoin(self.base_url, item['href']) for item in soup.select('.search-title > a')]
            parse_repo = await self.parse_repo(urls, client)
            repos_data.extend(parse_repo)
        logger.debug(repos_data)
        return repos_data

    async def main(self):
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
            return await self.parse_data(client)


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
    run(GitHubCrawler(base_url, data).main())
