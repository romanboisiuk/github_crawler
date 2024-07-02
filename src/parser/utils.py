from random import choice
from typing import Any

from bs4 import BeautifulSoup


def get_proxy(input_data) -> str | None:
    """
    Retrieve a proxy URL from the given input data.
    Args:
        input_data (dict[str, Any]): A dictionary containing input data,
                                     including a possible list of proxies.
    Returns:
        Optional[str]: A formatted proxy URL if proxies are available, otherwise None.
    """
    if proxies := input_data['proxies']:
        return f'http://{choice(proxies)}'

    return None


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


def extract_repository_owner(soup: BeautifulSoup) -> str:
    """
    Extracts repository owner from the given HTML elements.
    Args:
        soup: BeautifulSoup
    Returns:
        str: A string containing the repository owner.
    """
    return soup.select_one('[name=\'octolytics-dimension-user_login\']')['content']
