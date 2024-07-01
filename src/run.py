import asyncio
from argparse import ArgumentParser
from typing import Any

from loguru import logger
from pydantic import ValidationError

from parser.models import InputDataModel
from parser.parser import Parser


class GitHubCrawler:
    base_url: str = 'https://github.com/'

    @staticmethod
    def parse_args():
        parser: ArgumentParser = ArgumentParser(description='Process some data.')
        parser.add_argument('--keywords', nargs='+', help='List of keywords')
        parser.add_argument('--proxies', nargs='+', help='List of proxies IP\'s')
        parser.add_argument('--type', help='Type of data')
        return parser.parse_args()

    async def main(self):
        args = self.parse_args()
        input_data: dict[str, Any] = {
            'keywords': args.keywords,
            'proxies': args.proxies,
            'type': args.type
        }
        try:
            validated_data = InputDataModel(**input_data)
        except ValidationError as e:
            raise e

        parser: Parser = Parser(self.base_url, validated_data.model_dump())
        data = await parser.run_crawler()
        logger.info(data)


if __name__ == '__main__':
    asyncio.run(GitHubCrawler().main())
