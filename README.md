# Pokémon Nickname Generator

This project uses OpenAI's GPT-4o model to generate nicknames for Pokémon sprites and stores them in a SQLite database.

## Setup

1. Clone this repository
2. Install the required dependencies using uv:

```bash
uv sync
```

3. Create a `.env` file in the root directory with your OpenAI API key:

```plaintext
OPENAI_API_KEY=your_api_key_here
```

## Usage

### Command-line Interface

The application uses Typer to provide a modern command-line interface with rich output formatting:

```bash
# List all available Pokémon

uv run main.py list-pokemon

# Generate nicknames for a specific Pokémon

uv run main.py generate pikachu

# Generate nicknames for a specific Pokémon and display the image

uv run main.py generate pikachu --show-image

# View nicknames for a specific Pokémon

uv run main.py view pikachu

# Generate nicknames for all Pokémon

uv run main.py generate

# Force regeneration of nicknames even if they already exist

uv run main.py generate pikachu --force

# Generate nicknames for all Pokémon and force regeneration

uv run main.py generate --force

# Export the database to a CSV file

uv run main.py export

# Export the database to a custom CSV file

uv run main.py export custom_output.csv
```

### Database

The nicknames are stored in a SQLite database (`pokemon_nicknames.db` by default). You can specify a different database file using the `--db` option:

```bash
uv run main.py generate --db custom_database.db
uv run main.py view pikachu --db custom_database.db
uv run main.py export --db custom_database.db
```

## Project Structure

- `main.py`: The main command-line application using Typer and Rich
- `db.py`: Database operations for storing and retrieving nicknames
- `nickname_generator.py`: Functions for generating nicknames using the OpenAI API
- `sprites/`: Directory containing Pokémon sprite images

## Requirements

- Python 3.8+
- OpenAI API key
