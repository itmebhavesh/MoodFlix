import sqlite3
import csv
from pathlib import Path

# Database aur CSV file ka path
db_path = Path("moodflix_catalog.sqlite3")
csv_path = Path("movies_omdb_10000.csv")

# Database exist karta hai ya nahi
if not db_path.exists():
    raise FileNotFoundError(f"Database nahi mila: {db_path}")

# Database connect karo
connection = sqlite3.connect(db_path)
connection.row_factory = sqlite3.Row

# Table se saare saved records nikalo
rows = connection.execute(
    "SELECT * FROM omdb_movies ORDER BY title"
).fetchall()

if not rows:
    print("Database mein koi movie nahi mili.")
else:
    # CSV mein export karo
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=rows[0].keys()
        )
        writer.writeheader()
        writer.writerows([dict(row) for row in rows])

    print(f"CSV successfully created: {csv_path}")
    print(f"Total movies exported: {len(rows)}")

connection.close()