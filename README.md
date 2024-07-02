# GitHub Parser

## Requirements

- Poetry for Python dependency management
- Python 3.12

### Setting Up Your Environment

1. Install Poetry:
   ```bash
   pip install poetry
   ```

2. Install dependencies:
   ```bash
   poetry install
   ```
   
3. Run the crawler
   ```bash
   python src/run.py --keywords openstack nova css --type issues
   python src/run.py --keywords openstack nova css --proxies 116.108.118.117:4009 65.108.118.117:4009 --type repositories
   ```

4. Run the tests
   ```bash
   coverage run -m unittest discover
   coverage report -m
   ```