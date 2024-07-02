# GitHub Parser

## Requirements

- Poetry for Python dependency management
- Python 3.12

### Setting Up Your Environment

1. Create venv and Install Poetry:
   ```bash
   python3.12 -m venv .venv
   pip install poetry
   ```

2. Install dependencies:
   ```bash
   poetry install
   ```
   
3. Run the crawler
   ```bash
   python src/run.py --file_path input_data.json
   ```

4. Run the tests
   ```bash
   coverage run -m unittest discover -v
   coverage report -m
   ```