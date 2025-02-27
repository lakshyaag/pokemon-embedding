import sqlite3
from typing import List, Optional, Dict, Any
import csv
import pokebase as pb


class PokemonDatabase:
    """
    A class to handle database operations for storing Pokémon nicknames and details.
    """

    def __init__(self, db_path: str = "pokemon_nicknames.db"):
        """
        Initialize the database connection.

        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self._create_tables_if_not_exist()

    def _create_tables_if_not_exist(self) -> None:
        """
        Create the necessary tables if they don't exist.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create the pokemon table with only basic identification
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS pokemon (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            pokedex_id INTEGER
        )
        """)

        # Create a separate table for Pokémon details
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS pokemon_details (
            pokemon_id INTEGER PRIMARY KEY,
            height INTEGER,
            weight INTEGER,
            types TEXT,
            color TEXT,
            habitat TEXT,
            FOREIGN KEY (pokemon_id) REFERENCES pokemon (id)
        )
        """)

        # Create a table for Pokémon moves
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS pokemon_moves (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pokemon_id INTEGER,
            move_name TEXT,
            FOREIGN KEY (pokemon_id) REFERENCES pokemon (id),
            UNIQUE (pokemon_id, move_name)
        )
        """)

        # Create the nicknames table with a fixed number of nickname slots
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS nicknames (
            pokemon_id INTEGER PRIMARY KEY,
            nickname1 TEXT,
            nickname2 TEXT,
            nickname3 TEXT,
            nickname4 TEXT,
            nickname5 TEXT,
            FOREIGN KEY (pokemon_id) REFERENCES pokemon (id)
        )
        """)

        conn.commit()
        conn.close()

    def _fetch_pokemon_details(self, pokemon_name: str) -> Dict[str, Any]:
        """
        Fetch Pokémon details from pokebase.

        Args:
            pokemon_name: The name of the Pokémon

        Returns:
            A dictionary containing Pokémon details
        """
        try:
            # Fetch basic Pokémon data
            pokemon = pb.pokemon(pokemon_name.lower())

            # Get types as a comma-separated string
            types = ",".join([t.type.name for t in pokemon.types])

            # Get species information
            species = pokemon.species

            # Get moves (limit to 20 to avoid excessive data)
            moves = [move.move.name for move in pokemon.moves[:20]]

            # Prepare the details dictionary
            details = {
                "pokedex_id": pokemon.id,
                "height": pokemon.height,
                "weight": pokemon.weight,
                "types": types,
                "moves": moves,
                "color": species.color.name
                if hasattr(species, "color") and species.color
                else None,
                "habitat": species.habitat.name
                if hasattr(species, "habitat") and species.habitat
                else None,
            }

            return details
        except Exception:
            # If there's an error, return a dictionary with None values
            return {
                "pokedex_id": None,
                "height": None,
                "weight": None,
                "types": None,
                "moves": [],
                "color": None,
                "habitat": None,
            }

    def add_pokemon_with_nicknames(
        self, pokemon_name: str, nicknames: List[str]
    ) -> None:
        """
        Add a Pokémon and its nicknames to the database.
        If the Pokémon already exists, update its nicknames and details.

        Args:
            pokemon_name: The name of the Pokémon
            nicknames: A list of nicknames for the Pokémon (up to 5)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Fetch Pokémon details from pokebase
            details = self._fetch_pokemon_details(pokemon_name)

            # Insert or replace the Pokémon with basic details
            cursor.execute(
                """
            INSERT OR REPLACE INTO pokemon (
                name, pokedex_id
            ) VALUES (?, ?)
            """,
                (pokemon_name.lower(), details["pokedex_id"]),
            )

            # Get the Pokémon ID
            cursor.execute(
                "SELECT id FROM pokemon WHERE name = ?", (pokemon_name.lower(),)
            )
            pokemon_id = cursor.fetchone()[0]

            # Insert or replace the Pokémon details
            cursor.execute(
                """
            INSERT OR REPLACE INTO pokemon_details (
                pokemon_id, height, weight, types, color, habitat
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    pokemon_id,
                    details["height"],
                    details["weight"],
                    details["types"],
                    details["color"],
                    details["habitat"],
                ),
            )

            # Delete existing moves for this Pokémon
            cursor.execute(
                "DELETE FROM pokemon_moves WHERE pokemon_id = ?", (pokemon_id,)
            )

            # Insert the moves
            for move in details["moves"]:
                cursor.execute(
                    """
                INSERT OR IGNORE INTO pokemon_moves (
                    pokemon_id, move_name
                ) VALUES (?, ?)
                """,
                    (pokemon_id, move),
                )

            # Ensure we have exactly 5 nicknames (pad with None if needed)
            padded_nicknames = nicknames[:5] + [None] * (5 - len(nicknames[:5]))

            # Insert or replace the nicknames
            cursor.execute(
                """
            INSERT OR REPLACE INTO nicknames (
                pokemon_id, nickname1, nickname2, nickname3, nickname4, nickname5
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
                (pokemon_id, *padded_nicknames),
            )

            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def remove_nicknames(self, pokemon_name: str) -> bool:
        """
        Remove all nicknames for a specific Pokémon.

        Args:
            pokemon_name: The name of the Pokémon

        Returns:
            True if nicknames were removed, False otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Get the Pokémon ID
            cursor.execute(
                "SELECT id FROM pokemon WHERE name = ?", (pokemon_name.lower(),)
            )
            result = cursor.fetchone()

            if not result:
                return False

            pokemon_id = result[0]

            # Delete the nicknames
            cursor.execute("DELETE FROM nicknames WHERE pokemon_id = ?", (pokemon_id,))

            rows_affected = cursor.rowcount
            conn.commit()

            return rows_affected > 0
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def get_nicknames(self, pokemon_name: str) -> List[str]:
        """
        Get the nicknames for a specific Pokémon.

        Args:
            pokemon_name: The name of the Pokémon

        Returns:
            A list of nicknames for the Pokémon
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
        SELECT n.nickname1, n.nickname2, n.nickname3, n.nickname4, n.nickname5
        FROM nicknames n
        JOIN pokemon p ON n.pokemon_id = p.id
        WHERE p.name = ?
        """,
            (pokemon_name.lower(),),
        )

        result = cursor.fetchone()
        conn.close()

        if not result:
            return []

        # Filter out None values
        return [nick for nick in result if nick]

    def get_pokemon_details(self, pokemon_name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific Pokémon.

        Args:
            pokemon_name: The name of the Pokémon

        Returns:
            A dictionary containing Pokémon details, or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get basic Pokémon information and details
        cursor.execute(
            """
        SELECT 
            p.name, p.pokedex_id, 
            d.height, d.weight, d.types, d.color, d.habitat
        FROM pokemon p
        LEFT JOIN pokemon_details d ON p.id = d.pokemon_id
        WHERE p.name = ?
        """,
            (pokemon_name.lower(),),
        )

        result = cursor.fetchone()

        if not result:
            conn.close()
            return None

        # Convert the result to a dictionary
        columns = [
            "name",
            "pokedex_id",
            "height",
            "weight",
            "types",
            "color",
            "habitat",
        ]

        details = dict(zip(columns, result))

        # Get the Pokémon ID
        cursor.execute("SELECT id FROM pokemon WHERE name = ?", (pokemon_name.lower(),))
        pokemon_id = cursor.fetchone()[0]

        # Get the moves
        cursor.execute(
            """
        SELECT move_name
        FROM pokemon_moves
        WHERE pokemon_id = ?
        ORDER BY move_name
        """,
            (pokemon_id,),
        )

        moves = [row[0] for row in cursor.fetchall()]
        details["moves"] = moves

        conn.close()

        # Parse the types
        if details["types"]:
            details["types"] = details["types"].split(",")
        else:
            details["types"] = []

        return details

    def get_all_pokemon(self) -> List[str]:
        """
        Get a list of all Pokémon in the database.

        Returns:
            A list of Pokémon names
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM pokemon ORDER BY name")
        pokemon_names = [row[0] for row in cursor.fetchall()]

        conn.close()
        return pokemon_names

    def get_all_pokemon_with_nicknames(self) -> List[Dict[str, Any]]:
        """
        Get all Pokémon with their nicknames.

        Returns:
            A list of dictionaries containing Pokémon names and their nicknames
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
        SELECT 
            p.name, 
            n.nickname1, n.nickname2, n.nickname3, n.nickname4, n.nickname5
        FROM pokemon p
        LEFT JOIN nicknames n ON p.id = n.pokemon_id
        ORDER BY p.name
        """)

        results = cursor.fetchall()
        conn.close()

        pokemon_with_nicknames = []
        for row in results:
            pokemon_name = row[0]
            nicknames = [nick for nick in row[1:] if nick]
            pokemon_with_nicknames.append(
                {"pokemon": pokemon_name, "nicknames": nicknames}
            )

        return pokemon_with_nicknames

    def export_to_csv(self, csv_path: str) -> int:
        """
        Export the database to a CSV file with nicknames.

        Args:
            csv_path: Path to the CSV file

        Returns:
            The number of rows exported
        """
        data = self.get_all_pokemon_with_nicknames()

        with open(csv_path, "w", newline="") as csvfile:
            fieldnames = [
                "pokemon",
                "nickname1",
                "nickname2",
                "nickname3",
                "nickname4",
                "nickname5",
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()

            for row in data:
                pokemon = row["pokemon"]
                nicknames = row["nicknames"]

                # Pad the nicknames list to ensure it has 5 elements
                nicknames_padded = nicknames + [""] * (5 - len(nicknames))

                writer.writerow(
                    {
                        "pokemon": pokemon,
                        "nickname1": nicknames_padded[0],
                        "nickname2": nicknames_padded[1],
                        "nickname3": nicknames_padded[2],
                        "nickname4": nicknames_padded[3],
                        "nickname5": nicknames_padded[4],
                    }
                )

        return len(data)

    def export_detailed_csv(self, csv_path: str) -> int:
        """
        Export the database with detailed Pokémon information to a CSV file.

        Args:
            csv_path: Path to the CSV file

        Returns:
            The number of rows exported
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get all Pokémon with their details
        cursor.execute("""
        SELECT 
            p.name, p.pokedex_id, 
            d.height, d.weight, d.types, d.color, d.habitat
        FROM pokemon p
        LEFT JOIN pokemon_details d ON p.id = d.pokemon_id
        ORDER BY p.name
        """)

        results = cursor.fetchall()

        # Prepare the data for export
        export_data = []
        for row in results:
            pokemon_name = row[0]

            # Get the Pokémon ID
            cursor.execute("SELECT id FROM pokemon WHERE name = ?", (pokemon_name,))
            pokemon_id = cursor.fetchone()[0]

            # Get the moves
            cursor.execute(
                """
            SELECT move_name
            FROM pokemon_moves
            WHERE pokemon_id = ?
            ORDER BY move_name
            """,
                (pokemon_id,),
            )

            moves = [row[0] for row in cursor.fetchall()]
            moves_str = ",".join(moves)

            # Get the nicknames
            cursor.execute(
                """
            SELECT nickname1, nickname2, nickname3, nickname4, nickname5
            FROM nicknames
            WHERE pokemon_id = ?
            """,
                (pokemon_id,),
            )

            nickname_row = cursor.fetchone()
            nicknames = [nick for nick in nickname_row] if nickname_row else [None] * 5

            # Add to export data
            export_data.append(row + (moves_str,) + tuple(nicknames))

        conn.close()

        with open(csv_path, "w", newline="") as csvfile:
            fieldnames = [
                "pokemon",
                "pokedex_id",
                "height",
                "weight",
                "types",
                "color",
                "habitat",
                "moves",
                "nickname1",
                "nickname2",
                "nickname3",
                "nickname4",
                "nickname5",
            ]
            writer = csv.writer(csvfile)

            writer.writerow(fieldnames)
            writer.writerows(export_data)

        return len(export_data)
