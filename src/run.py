import asyncio
import sys
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
            parser.print_help()
            logger.error('No file path provided. Please provide a file path using the --file_path argument.')
            sys.exit(1)
        return args

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

        try:
            validated_data = InputDataModel(**data).model_dump()
        except ValidationError as e:
            raise e

        input_data: dict[str, Any] = {
            'keywords': validated_data['keywords'],
            'proxies': validated_data['proxies'],
            'type': validated_data['type'],
        }
        parser: Parser = Parser(self.base_url, input_data)
        parsed_data = await parser.run_crawler()
        with open('parse_result.json', 'w') as file:
            file.write(dumps(parsed_data, indent=4))


if __name__ == '__main__':
    asyncio.run(GitHubCrawler().main())
