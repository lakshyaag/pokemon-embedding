import os
import sys
from typing import List, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from dotenv import load_dotenv

from db import PokemonDatabase
from nickname_generator import get_nicknames

# Initialize Typer app
app = typer.Typer(help="Generate and store nicknames for Pokémon sprites.")
console = Console()


def load_environment() -> None:
    """
    Load environment variables from .env file.
    """
    load_dotenv()

    # Check if OPENAI_API_KEY is set
    if not os.getenv("OPENAI_API_KEY"):
        console.print(
            "[bold red]Error:[/bold red] OPENAI_API_KEY environment variable is not set."
        )
        console.print("Please set it in your .env file or as an environment variable.")
        sys.exit(1)


def get_pokemon_list() -> List[str]:
    """
    Get a list of all Pokémon based on the sprite files.

    Returns:
        A list of Pokémon names
    """
    pokemon_names = []

    # Check if the sprites directory exists
    if not os.path.isdir("sprites"):
        console.print("[bold red]Error:[/bold red] 'sprites' directory not found.")
        sys.exit(1)

    # Get all sprite files
    for filename in os.listdir("sprites"):
        if filename.endswith("_combined.png"):
            pokemon_name = filename.replace("_combined.png", "")
            pokemon_names.append(pokemon_name)

    return sorted(pokemon_names)


def display_pokemon_image(pokemon_name: str) -> None:
    """
    Display a Pokémon image in the terminal.

    Args:
        pokemon_name: The name of the Pokémon
    """
    from PIL import Image

    image_path = f"sprites/{pokemon_name}_combined.png"

    try:
        # First try using term-image if available
        try:
            from term_image.image import AutoImage

            # Display the image using term-image
            img = AutoImage(Image.open(image_path))
            img.draw()
            return
        except ImportError:
            # If term-image is not available, try using PIL and climage
            try:
                import climage

                # Display the image using climage
                output = climage.convert(image_path, width=40, is_unicode=True)
                print(output)
                return
            except ImportError:
                # If climage is not available, try using PIL directly
                try:
                    # Create a panel with the image path
                    panel = Panel(
                        f"[bold cyan]Image:[/bold cyan] {image_path}",
                        title=f"[bold green]{pokemon_name.capitalize()}[/bold green]",
                        border_style="green",
                    )
                    console.print(panel)

                    # Note about image display
                    console.print(
                        "[yellow]For better image display, install term-image or climage:[/yellow]"
                    )
                    console.print(
                        "[cyan]uv pip install term-image[/cyan] or [cyan]uv pip install climage[/cyan]"
                    )
                except ImportError:
                    console.print(
                        "[yellow]Warning: PIL not installed. Cannot display image information.[/yellow]"
                    )
    except Exception as e:
        console.print(f"[red]Error displaying image: {str(e)}[/red]")

        # Fallback to just showing the image path
        panel = Panel(
            f"[bold cyan]Image:[/bold cyan] {image_path}",
            title=f"[bold green]{pokemon_name.capitalize()}[/bold green]",
            border_style="green",
        )
        console.print(panel)


def process_pokemon(
    pokemon_name: str,
    db: PokemonDatabase,
    show_image: bool = False,
    force: bool = False,
    temperature: float = 0.5,
) -> None:
    """
    Process a single Pokémon: generate nicknames and store them in the database.

    Args:
        pokemon_name: The name of the Pokémon
        db: The database instance
        show_image: Whether to display the Pokémon image
        force: Whether to force regeneration of nicknames
    """
    try:
        # Check if the Pokémon already has nicknames in the database
        existing_nicknames = db.get_nicknames(pokemon_name)

        if existing_nicknames and not force:
            console.print(
                f"[yellow]{pokemon_name.capitalize()} already has nicknames:[/yellow]"
            )

            # Create a table for the nicknames
            table = Table(show_header=False, box=None)
            for nickname in existing_nicknames:
                table.add_row(f"[cyan]•[/cyan] {nickname}")

            console.print(table)

            if show_image:
                display_pokemon_image(pokemon_name)

            return

        # If force is True and there are existing nicknames, remove them
        if force and existing_nicknames:
            db.remove_nicknames(pokemon_name)
            console.print(
                f"[yellow]Removed existing nicknames for {pokemon_name.capitalize()}.[/yellow]"
            )

        # Show a spinner while generating nicknames
        with Progress(
            SpinnerColumn(),
            TextColumn(
                "[bold green]Generating nicknames for {task.description}...[/bold green]"
            ),
            transient=True,
        ) as progress:
            progress.add_task(pokemon_name.capitalize(), total=None)

            # Generate nicknames
            nicknames = get_nicknames(pokemon_name, temperature)

        # Store in database
        db.add_pokemon_with_nicknames(pokemon_name, nicknames)

        # Display the results
        console.print(
            f"[bold green]Added nicknames for {pokemon_name.capitalize()}:[/bold green]"
        )

        # Create a table for the nicknames
        table = Table(show_header=False, box=None)
        for nickname in nicknames:
            table.add_row(f"[cyan]•[/cyan] {nickname}")

        console.print(table)

        if show_image:
            display_pokemon_image(pokemon_name)

    except Exception as e:
        console.print(f"[bold red]Error processing {pokemon_name}:[/bold red] {str(e)}")


@app.command()
def list_pokemon():
    """List all available Pokémon."""
    load_environment()

    pokemon_list = get_pokemon_list()

    console.print("[bold]Available Pokémon:[/bold]")

    # Create a table for the Pokémon list
    table = Table(show_header=False, box=None)

    # Add Pokémon names in multiple columns
    columns = 5
    rows = (len(pokemon_list) + columns - 1) // columns

    for i in range(rows):
        row_data = []
        for j in range(columns):
            idx = i + j * rows
            if idx < len(pokemon_list):
                row_data.append(f"[cyan]•[/cyan] {pokemon_list[idx].capitalize()}")
            else:
                row_data.append("")

        table.add_row(*row_data)

    console.print(table)
    console.print(f"[italic]Total: {len(pokemon_list)} Pokémon[/italic]")


@app.command()
def generate(
    pokemon_name: Optional[str] = typer.Argument(
        None, help="Name of the Pokémon to process (omit to process all)"
    ),
    db_path: str = typer.Option(
        "pokemon_nicknames.db", "--db", help="Path to the SQLite database file"
    ),
    show_image: bool = typer.Option(
        False, "--show-image", "-i", help="Display the Pokémon image"
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Force regeneration of nicknames even if they already exist",
    ),
    temperature: float = typer.Option(
        0.5, "--temperature", "-t", help="Temperature for the nickname generator"
    ),
):
    """Generate nicknames for a Pokémon or all Pokémon."""
    load_environment()

    # Initialize the database
    db = PokemonDatabase(db_path)

    # Process a single Pokémon if specified
    if pokemon_name:
        pokemon_name = pokemon_name.lower()

        # Check if the Pokémon exists
        pokemon_list = get_pokemon_list()
        if pokemon_name not in pokemon_list:
            console.print(
                f"[bold red]Error:[/bold red] Pokémon '{pokemon_name}' not found."
            )
            console.print(
                "Use [bold]uv run main.py list-pokemon[/bold] to see available Pokémon."
            )
            return

        process_pokemon(pokemon_name, db, show_image, force, temperature)
    else:
        # Process all Pokémon
        pokemon_list = get_pokemon_list()
        console.print(f"[bold]Processing {len(pokemon_list)} Pokémon...[/bold]")

        with Progress() as progress:
            task = progress.add_task("[green]Processing...", total=len(pokemon_list))

            for pokemon_name in pokemon_list:
                progress.update(
                    task,
                    description=f"[green]Processing {pokemon_name.capitalize()}...",
                )

                # If force is True, process all Pokémon
                # Otherwise, skip Pokémon that already have nicknames
                if not force and db.get_nicknames(pokemon_name):
                    progress.update(task, advance=1)
                    continue

                try:
                    # If force is True and there are existing nicknames, remove them
                    if force and db.get_nicknames(pokemon_name):
                        db.remove_nicknames(pokemon_name)

                    # Generate nicknames without showing images in batch mode
                    nicknames = get_nicknames(pokemon_name)
                    db.add_pokemon_with_nicknames(pokemon_name, nicknames)
                    progress.update(task, advance=1)
                except Exception as e:
                    console.print(
                        f"[red]Error processing {pokemon_name}: {str(e)}[/red]"
                    )
                    progress.update(task, advance=1)

        console.print("[bold green]Done![/bold green]")


@app.command()
def view(
    pokemon_name: str = typer.Argument(..., help="Name of the Pokémon to view"),
    db_path: str = typer.Option(
        "pokemon_nicknames.db", "--db", help="Path to the SQLite database file"
    ),
    show_image: bool = typer.Option(
        True, "--show-image", "-i", help="Display the Pokémon image"
    ),
):
    """View nicknames for a specific Pokémon."""
    load_environment()

    # Initialize the database
    db = PokemonDatabase(db_path)

    pokemon_name = pokemon_name.lower()

    # Check if the Pokémon exists
    pokemon_list = get_pokemon_list()
    if pokemon_name not in pokemon_list:
        console.print(
            f"[bold red]Error:[/bold red] Pokémon '{pokemon_name}' not found."
        )
        console.print(
            "Use [bold]uv run main.py list-pokemon[/bold] to see available Pokémon."
        )
        return

    # Get nicknames
    nicknames = db.get_nicknames(pokemon_name)

    if not nicknames:
        console.print(
            f"[yellow]No nicknames found for {pokemon_name.capitalize()}.[/yellow]"
        )
        console.print(
            f"Use [bold]uv run main.py generate {pokemon_name}[/bold] to generate nicknames."
        )
        return

    # Display the results
    console.print(
        f"[bold green]Nicknames for {pokemon_name.capitalize()}:[/bold green]"
    )

    # Create a table for the nicknames
    table = Table(show_header=False, box=None)
    for nickname in nicknames:
        table.add_row(f"[cyan]•[/cyan] {nickname}")

    console.print(table)

    if show_image:
        display_pokemon_image(pokemon_name)


@app.command()
def details(
    pokemon_name: str = typer.Argument(
        ..., help="Name of the Pokémon to view details for"
    ),
    db_path: str = typer.Option(
        "pokemon_nicknames.db", "--db", help="Path to the SQLite database file"
    ),
    show_image: bool = typer.Option(
        True, "--show-image", "-i", help="Display the Pokémon image"
    ),
):
    """View detailed information about a specific Pokémon."""
    load_environment()

    # Initialize the database
    db = PokemonDatabase(db_path)

    pokemon_name = pokemon_name.lower()

    # Check if the Pokémon exists
    pokemon_list = get_pokemon_list()
    if pokemon_name not in pokemon_list:
        console.print(
            f"[bold red]Error:[/bold red] Pokémon '{pokemon_name}' not found."
        )
        console.print(
            "Use [bold]uv run main.py list-pokemon[/bold] to see available Pokémon."
        )
        return

    # Get Pokémon details
    details = db.get_pokemon_details(pokemon_name)

    if not details:
        console.print(
            f"[yellow]No details found for {pokemon_name.capitalize()}.[/yellow]"
        )
        console.print(
            f"Use [bold]uv run main.py generate {pokemon_name}[/bold] to fetch Pokémon details."
        )
        return

    # Display the results
    console.print(f"[bold green]Details for {pokemon_name.capitalize()}:[/bold green]")

    # Create a panel for the details
    details_text = []

    # Add basic information
    details_text.append(f"[bold]Pokédex ID:[/bold] {details['pokedex_id']}")
    details_text.append(
        f"[bold]Height:[/bold] {details['height'] / 10} m"
    )  # Convert to meters
    details_text.append(
        f"[bold]Weight:[/bold] {details['weight'] / 10} kg"
    )  # Convert to kg

    # Add types
    types_str = ", ".join([t.capitalize() for t in details["types"]])
    details_text.append(f"[bold]Types:[/bold] {types_str}")

    # Add color and habitat if available
    if details["color"]:
        details_text.append(f"[bold]Color:[/bold] {details['color'].capitalize()}")
    if details["habitat"]:
        details_text.append(f"[bold]Habitat:[/bold] {details['habitat'].capitalize()}")

    # Create a panel with the details
    panel = Panel(
        "\n".join(details_text),
        title=f"[bold]{pokemon_name.capitalize()}[/bold]",
        border_style="green",
    )
    console.print(panel)

    # Display moves in a table
    if details["moves"]:
        console.print("[bold]Moves:[/bold]")

        # Create a table for the moves
        table = Table(show_header=False, box=None)

        # Add moves in multiple columns
        columns = 3
        moves = sorted(details["moves"])
        rows = (len(moves) + columns - 1) // columns

        for i in range(rows):
            row_data = []
            for j in range(columns):
                idx = i + j * rows
                if idx < len(moves):
                    move_name = moves[idx].replace("-", " ").title()
                    row_data.append(f"[cyan]•[/cyan] {move_name}")
                else:
                    row_data.append("")

            table.add_row(*row_data)

        console.print(table)

    # Get and display nicknames if available
    nicknames = db.get_nicknames(pokemon_name)
    if nicknames:
        console.print("[bold]Nicknames:[/bold]")

        # Create a table for the nicknames
        table = Table(show_header=False, box=None)
        for nickname in nicknames:
            table.add_row(f"[cyan]•[/cyan] {nickname}")

        console.print(table)

    if show_image:
        display_pokemon_image(pokemon_name)


@app.command()
def export(
    output_path: str = typer.Argument(
        "pokemon_nicknames.csv", help="Path to the output CSV file"
    ),
    db_path: str = typer.Option(
        "pokemon_nicknames.db", "--db", help="Path to the SQLite database file"
    ),
    detailed: bool = typer.Option(
        False, "--detailed", "-d", help="Export detailed Pokémon information"
    ),
):
    """Export the database to a CSV file."""
    # Initialize the database
    db = PokemonDatabase(db_path)

    # Check if the database exists
    if not os.path.exists(db_path):
        console.print(
            f"[bold red]Error:[/bold red] Database file '{db_path}' not found."
        )
        return

    # Export the database
    with Progress(
        SpinnerColumn(),
        TextColumn(
            "[bold green]Exporting database to {task.description}...[/bold green]"
        ),
        transient=True,
    ) as progress:
        progress.add_task(output_path, total=None)

        try:
            if detailed:
                rows_exported = db.export_detailed_csv(output_path)
            else:
                rows_exported = db.export_to_csv(output_path)
        except Exception as e:
            console.print(f"[bold red]Error exporting database:[/bold red] {str(e)}")
            return

    # Display the results
    if detailed:
        console.print(
            f"[bold green]Successfully exported {rows_exported} Pokémon with detailed information to {output_path}[/bold green]"
        )
    else:
        console.print(
            f"[bold green]Successfully exported {rows_exported} Pokémon to {output_path}[/bold green]"
        )

    # Show a preview of the CSV file
    try:
        import csv

        with open(output_path, "r", newline="") as csvfile:
            reader = csv.reader(csvfile)
            headers = next(reader)

            # Create a table for the preview
            table = Table(title="CSV Preview (First 5 rows)")

            for header in headers:
                table.add_column(header.capitalize())

            # Add the first 5 rows
            for i, row in enumerate(reader):
                if i >= 5:
                    break

                table.add_row(*row)

            console.print(table)
    except Exception as e:
        console.print(f"[yellow]Could not show preview: {str(e)}[/yellow]")


if __name__ == "__main__":
    app()
