from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch, MagicMock, call

from bs4 import BeautifulSoup
from httpx import AsyncClient, ConnectTimeout, Response

from src.parser.parser import Parser


class TestParser(IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.base_url = 'https://github.com/'
        self.headers = {'Accept': 'text/html'}
        self.input_data = {
            'keywords': ['openstack', 'nova', 'css'],
            'proxies': ['proxy1', 'proxy2'],
            'type': 'Repositories'
        }
        self.parser = Parser(self.base_url, self.input_data)
        self.client = AsyncMock(AsyncClient)

    @patch('src.parser.parser.get_proxy', return_value='proxy')
    @patch('src.parser.parser.AsyncClient')
    async def test_fetch_url_content_success(self, mock_client, mock_get_proxy):
        mock_client = mock_client.return_value.__aenter__.return_value
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.get = AsyncMock(return_value=mock_response)
        response = await self.parser.fetch_url_content(self.base_url, self.headers)
        mock_client.get.assert_awaited_once_with(self.base_url, headers=self.headers)
        mock_get_proxy.assert_called_once()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response, mock_response)

    @patch('src.parser.parser.get_proxy', return_value=None)
    @patch('src.parser.parser.AsyncClient')
    async def test_fetch_url_content_retry_on_exception(self, mock_client, mock_get_proxy):
        connect_timeout_error = ConnectTimeout('Connect timeout', request=None)
        mock_response = AsyncMock(spec=Response)
        mock_response.status_code = 200
        mock_client.return_value.__aenter__.return_value.get.side_effect = [
            connect_timeout_error,
            AsyncMock(spec=Response)
        ]
        await self.parser.fetch_url_content(self.base_url, self.headers)
        self.assertEqual(mock_client.return_value.__aenter__.return_value.get.call_count, 2)
        calls = [call(self.base_url, headers=self.headers)] * 2
        mock_client.return_value.__aenter__.return_value.get.assert_has_calls(calls)
        mock_get_proxy.assert_has_calls([call(self.input_data), call(self.input_data)])

    def test_build_search_url(self):
        keywords = ['testkeyword', 'testkeyword2']
        expected_url = 'https://github.com/search?q=testkeyword+testkeyword2&type=repositories'
        actual_url = self.parser.build_search_url(keywords)
        self.assertEqual(expected_url, actual_url)

    @patch('src.parser.parser.extract_repository_owner', return_value='test_owner')
    @patch('src.parser.parser.extract_language_statistics', return_value={'Python': '100%'})
    @patch.object(Parser, 'fetch_html_soups', return_value=['test_resp1', 'test_reps2'])
    async def test_parse_github_data_repos(self, mock_fetch_html_soups, mock_get_lang_stats, mock_get_owner):
        urls = ['http://test_url1', 'http://test_url2']
        result = await self.parser.parse_github_data(urls)
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

    @patch('src.parser.parser.extract_repository_owner', return_value='test_owner')
    @patch('src.parser.parser.extract_language_statistics', return_value={'Python': '100%'})
    @patch.object(Parser, 'fetch_html_soups', return_value=['test_resp1', 'test_reps2'])
    async def test_parse_github_data_issues(self, mock_fetch_html_soups, mock_get_lang_stats, mock_get_owner):
        self.input_data['type'] = 'Issues'
        urls = ['http://test_url1', 'http://test_url2']
        result = await self.parser.parse_github_data(urls)
        expected_result = [
            {
                'url': 'http://test_url1',
            },
            {
                'url': 'http://test_url2',
            }
        ]
        self.assertEqual(result, expected_result)
        mock_fetch_html_soups.assert_awaited()
        mock_get_lang_stats.assert_not_called()
        mock_get_owner.assert_not_called()

    @patch.object(Parser, 'parse_github_data')
    @patch.object(Parser, 'fetch_url_content')
    async def test_gather_data(self, mock_fetch_url_content, mock_parse_github_data):
        search_response = MagicMock()
        search_response.text = '''
        <html>
            <div class='search-title'>
                <a href='/test_repo1'></a>
                <a href='/test_repo2'></a>
            </div>
        </html>
        '''
        mock_fetch_url_content.return_value = search_response
        expected_result = [
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
        mock_parse_github_data.return_value = expected_result
        result = await self.parser.gather_data()
        self.assertEqual(result, expected_result)
        mock_fetch_url_content.assert_awaited()
        mock_parse_github_data.assert_awaited()

    @patch.object(Parser, 'gather_data')
    async def test_run_crawler(self, mock_gather_data):
        mock_response = AsyncMock(return_value=[{'key': 'value'}])
        mock_gather_data.return_value = mock_response
        result = await self.parser.run_crawler()
        assert result == mock_response

    @patch.object(Parser, 'fetch_url_content')
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
        soups = await self.parser.fetch_html_soups(urls)
        self.assertIsInstance(soups, list)
        self.assertEqual(len(soups), 2)
        self.assertTrue(all(isinstance(soup, BeautifulSoup) for soup in soups))
        self.assertEqual(soups[0].text, 'Content 1')
        self.assertEqual(soups[1].text, 'Content 2')
