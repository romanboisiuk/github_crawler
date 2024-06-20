from unittest import main, IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch, MagicMock

from bs4 import BeautifulSoup
from httpx import AsyncClient

from parser import GitHubCrawler


class TestGitHubCrawler(IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.base_url = 'https://github.com/'
        self.headers = {'Accept': 'text/html'}
        self.data = {
            'keywords': ['openstack', 'nova', 'css'],
            'proxies': ['proxy1', 'proxy2'],
            'type': 'Repositories'
        }
        self.crawler = GitHubCrawler(self.base_url, self.data)
        self.client = AsyncMock(AsyncClient)

    async def test_fetch_url_content(self):
        response_mock = AsyncMock()
        response_mock.status_code = 200
        response_mock.json = AsyncMock(return_value={'key': 'value'})
        self.client.get = AsyncMock(return_value=response_mock)
        response = await self.crawler.fetch_url_content(self.client, self.base_url, self.headers)
        self.client.get.assert_awaited_once_with(self.base_url, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(await response.json(), {'key': 'value'})

    def test_extract_language_statistics(self):
        html = '''
        <div class='d-inline-flex flex-items-center'>
            <span>Python</span><span>50%</span>
        </div>
        <div class='d-inline-flex flex-items-center'>
            <span>JavaScript</span><span>30%</span>
        </div>
        <div class='d-inline-flex flex-items-center'>
            <span>Java</span><span>20%</span>
        </div>
        '''
        soup = BeautifulSoup(html, 'lxml')
        expected_result = {
            'Python': '50%',
            'JavaScript': '30%',
            'Java': '20%'
        }
        actual_result = self.crawler.extract_language_statistics(soup)
        self.assertEqual(expected_result, actual_result)

    def test_extract_repository_owner(self):
        html_content = '<html><head><meta name=\'octolytics-dimension-user_login\' content=\'testuser\'></head></html>'
        soup = BeautifulSoup(html_content, 'lxml')
        owner = self.crawler.extract_repository_owner(soup)
        self.assertEqual(owner, 'testuser')

    def test_build_search_url(self):
        keyword = 'testkeyword'
        expected_url = 'https://github.com/search?q=testkeyword&type=repositories'
        actual_url = self.crawler.build_search_url(keyword)
        self.assertEqual(expected_url, actual_url)

    @patch.object(GitHubCrawler, 'extract_repository_owner', return_value='test_owner')
    @patch.object(GitHubCrawler, 'extract_language_statistics', return_value={'Python': '100%'})
    @patch.object(GitHubCrawler, 'fetch_html_soups')
    async def test_parse_repository_data(self, mock_fetch_html_soups, mock_get_lang_stats, mock_get_owner):
        mock_response = MagicMock()
        mock_response.text = '''
        <html>
            <meta name='octolytics-dimension-user_login' content='test_owner'/>
            <div class='d-inline-flex flex-items-center'>
                <span>Python</span><span>100%</span>
            </div>
        </html>
        '''
        mock_fetch_html_soups.return_value = [mock_response, mock_response]
        urls = ['http://test_url1', 'http://test_url2']
        result = await self.crawler.parse_repository_data(urls, self.client)
        expected_result = [
            {
                'url': 'http://test_url1',
                'extra': {
                    'owner': 'test_owner',
                    'language_stats': {'Python': '100%'}
                }
            },
            {
                'url': 'http://test_url2',
                'extra': {
                    'owner': 'test_owner',
                    'language_stats': {'Python': '100%'}
                }
            }
        ]
        self.assertEqual(result, expected_result)
        mock_fetch_html_soups.assert_awaited()
        mock_get_lang_stats.assert_called()
        mock_get_owner.assert_called()

    @patch.object(GitHubCrawler, 'parse_repository_data')
    @patch.object(GitHubCrawler, 'fetch_html_soups')
    async def test_gather_data(self, mock_fetch_html_soups, mock_repository_data):
        search_response = MagicMock()
        search_response.text = '''
        <html>
            <div class='search-title'>
                <a href='/test_repo1'></a>
                <a href='/test_repo2'></a>
            </div>
        </html>
        '''
        mock_fetch_html_soups.return_value = [search_response, search_response, search_response]
        repo_data = [
            {
                'url': 'https://github.com/test_repo1',
                'extra': {
                    'owner': 'test_owner',
                    'language_stats': {'Python': '100%'}
                }
            },
            {
                'url': 'https://github.com/test_repo2',
                'extra': {
                    'owner': 'test_owner2',
                    'language_stats': {'Python': '50%'}
                }
            }
        ]
        mock_repository_data.return_value = repo_data
        result = await self.crawler.gather_data(self.client)
        expected_result = repo_data * 3
        self.assertEqual(result, expected_result)
        mock_fetch_html_soups.assert_awaited()
        mock_repository_data.assert_awaited()

    @patch('parser.choice')
    @patch('parser.AsyncClient')
    async def test_run_crawler(self, mock_client, mock_choice):
        mock_choice.return_value = 'proxy1'
        mock_client_instance = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        self.crawler.gather_data = AsyncMock(return_value=[{'key': 'value'}])
        result = await self.crawler.run_crawler()
        expected_proxies = {'http://': 'http://proxy1', 'https://': 'https://proxy1'}
        mock_client.assert_called_once_with(proxies={})
        self.crawler.gather_data.assert_awaited_once_with(mock_client_instance)
        assert result == [{'key': 'value'}]

    @patch.object(GitHubCrawler, 'fetch_url_content')
    async def test_fetch_html_soups(self, mock_fetch_url_content):
        def mock_response(text):
            mock_resp = MagicMock()
            mock_resp.text = text
            return mock_resp

        response_texts = [
            '<html><body>Content 1</body></html>',
            '<html><body>Content 2</body></html>'
        ]
        mock_fetch_url_content.side_effect = [mock_response(text) for text in response_texts]
        urls = ['https://example.com/page1', 'https://example.com/page2']
        soups = await self.crawler.fetch_html_soups(self.client, urls)
        self.assertIsInstance(soups, list)
        self.assertEqual(len(soups), 2)
        self.assertTrue(all(isinstance(soup, BeautifulSoup) for soup in soups))
        self.assertEqual(soups[0].text, 'Content 1')
        self.assertEqual(soups[1].text, 'Content 2')


if __name__ == '__main__':
    main()
