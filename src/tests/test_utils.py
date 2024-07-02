from unittest import TestCase
from unittest.mock import patch

from bs4 import BeautifulSoup

from src.parser.utils import get_proxy, extract_language_statistics, extract_repository_owner


class TestUtils(TestCase):

    def setUp(self):
        self.base_url = 'https://github.com/'
        self.headers = {'Accept': 'text/html'}
        self.input_data = {
            'keywords': ['openstack', 'nova', 'css'],
            'proxies': ['proxy1', 'proxy2'],
            'type': 'repositories'
        }

    @patch('src.parser.utils.choice')
    def test_proxies_present(self, mock_choice):
        mock_choice.return_value = 'proxy1'
        input_data = {
            'keywords': ['example'],
            'proxies': ['proxy1', 'proxy2'],
            'type': 'example'
        }
        result = get_proxy(input_data)
        self.assertEqual(result, 'http://proxy1')

    def test_proxies_absent(self):
        input_data = {
            'keywords': ['example'],
            'proxies': None,
            'type': 'example'
        }
        result = get_proxy(input_data)
        self.assertIsNone(result)

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
        actual_result = extract_language_statistics(soup)
        self.assertEqual(expected_result, actual_result)

    def test_extract_repository_owner(self):
        html_content = '<html><head><meta name=\'octolytics-dimension-user_login\' content=\'testuser\'></head></html>'
        soup = BeautifulSoup(html_content, 'lxml')
        owner = extract_repository_owner(soup)
        self.assertEqual(owner, 'testuser')
