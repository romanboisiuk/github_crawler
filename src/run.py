import asyncio
from argparse import ArgumentParser
from json import load, dumps, JSONDecodeError
from typing import Any

from loguru import logger
from pydantic import ValidationError

from parser.models import InputDataModel
from parser.parser import Parser


class GitHubCrawler:
    base_url: str = 'https://github.com/'

    @staticmethod
    def parse_args():
        parser: ArgumentParser = ArgumentParser()
        parser.add_argument('--file_path', type=str, help='The path to the file')
        args = parser.parse_args()
        if not args.file_path:
            logger.error('No file path provided. Please provide a file path using the --file_path argument.')
            return

        return parser.parse_args()

    async def main(self):
        args = self.parse_args()
        try:
            with open(args.file_path, 'r') as json_file:
                data = load(json_file)
        except FileNotFoundError:
            logger.error(f'File not found: {args.file_path}')
            return

        except JSONDecodeError:
            logger.error(f'Error decoding JSON from file: {args.file_path}')
            return

        input_data: dict[str, Any] = {
            'keywords': data['keywords'],
            'proxies': data['proxies'],
            'type': data['type'],
        }
        try:
            validated_data = InputDataModel(**input_data)
        except ValidationError as e:
            raise e

        parser: Parser = Parser(self.base_url, validated_data.model_dump())
        parsed_data = await parser.run_crawler()
        with open('parse_result.json', 'w') as file:
            file.write(dumps(parsed_data, indent=4))


if __name__ == '__main__':
    asyncio.run(GitHubCrawler().main())
