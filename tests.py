from unittest import main, IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch, MagicMock

from bs4 import BeautifulSoup
from httpx import AsyncClient

from parser import GitHubCrawler


class TestGitHubCrawler(IsolatedAsyncioTestCase):

    def setUp(self):
        self.base_url = 'https://github.com/'
        self.headers = {'Accept': 'text/html'}
        self.data = {
            'keywords': ['openstack', 'nova', 'css'],
            'proxies': ['proxy1', 'proxy2'],
            'type': 'Repositories'
        }
        self.crawler = GitHubCrawler(self.base_url, self.data)
        self.client = AsyncMock(AsyncClient)

    async def test_make_request(self):
        response_mock = AsyncMock()
        response_mock.status_code = 200
        response_mock.json = AsyncMock(return_value={"key": "value"})
        self.client.get = AsyncMock(return_value=response_mock)
        response = await self.crawler.make_request(self.client, self.base_url, self.headers)
        self.client.get.assert_awaited_once_with(self.base_url, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(await response.json(), {"key": "value"})

    def test_get_lang_stats_multiple_items(self):
        html = '''
        <div><span>Python</span><span>50%</span></div>
        <div><span>JavaScript</span><span>30%</span></div>
        <div><span>Java</span><span>20%</span></div>
        '''
        soup = BeautifulSoup(html, 'lxml')
        items = soup.select('div')
        expected_result = {
            'Python': '50%',
            'JavaScript': '30%',
            'Java': '20%'
        }
        actual_result = self.crawler.get_lang_stats(items)
        self.assertEqual(expected_result, actual_result)

    def test_parse_url(self):
        keyword = 'testkeyword'
        expected_url = 'https://github.com/search?q=testkeyword&type=repositories'
        actual_url = self.crawler.parse_url(keyword)
        self.assertEqual(expected_url, actual_url)

    @patch.object(GitHubCrawler, 'get_lang_stats', return_value={'Python': '100%'})
    @patch.object(GitHubCrawler, 'make_request', new_callable=AsyncMock)
    async def test_parse_repo(self, mock_make_request, mock_get_lang_stats):
        mock_response = MagicMock()
        mock_response.text = """
        <html>
            <meta name='octolytics-dimension-user_login' content='test_owner'/>
            <div class='d-inline-flex flex-items-center'>
                <span>Python</span><span>100%</span>
            </div>
        </html>
        """
        mock_make_request.side_effect = [mock_response, mock_response]
        urls = ['http://test_url1', 'http://test_url2']
        result = await self.crawler.parse_repo(urls, self.client)
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
        mock_make_request.assert_awaited()
        mock_get_lang_stats.assert_called()

    @patch.object(GitHubCrawler, 'parse_repo', new_callable=AsyncMock)
    @patch.object(GitHubCrawler, 'make_request', new_callable=AsyncMock)
    async def test_parse_data(self, mock_make_request, mock_parse_repo):
        search_response = MagicMock()
        search_response.text = """
        <html>
            <div class='search-title'>
                <a href='/test_repo1'></a>
                <a href='/test_repo2'></a>
            </div>
        </html>
        """
        mock_make_request.side_effect = [search_response, search_response, search_response]
        repo_data = [
            {
                'url': 'https://github.com/test_repo1',
                'extra': {
                    'owner': 'test_owner',
                    'language_stats': {"Python": "100%"}
                }
            },
            {
                'url': 'https://github.com/test_repo2',
                'extra': {
                    'owner': 'test_owner',
                    'language_stats': {"Python": "100%"}
                }
            }
        ]
        mock_parse_repo.side_effect = [repo_data, repo_data]
        with self.assertRaises(StopAsyncIteration):
            result = await self.crawler.parse_data(self.client)
            expected_result = repo_data * 3
            self.assertNotEquals(result, expected_result)
            mock_make_request.assert_not_awaited()
            mock_parse_repo.assert_awaited()

    @patch('parser.choice')
    @patch('parser.AsyncClient')
    async def test_main_with_proxy(self, mock_client, mock_choice):
        mock_choice.return_value = 'proxy1'
        mock_client_instance = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        self.crawler.parse_data = AsyncMock(return_value=[{'key': 'value'}])
        result = await self.crawler.main()
        expected_proxies = {'http://': 'http://proxy1', 'https://': 'https://proxy1'}
        mock_client.assert_called_once_with(proxies={})
        self.crawler.parse_data.assert_awaited_once_with(mock_client_instance)
        assert result == [{'key': 'value'}]


if __name__ == '__main__':
    main()
