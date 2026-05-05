import os
import csv
import psycopg2
from dotenv import load_dotenv

load_dotenv()

HOST = os.getenv("HOST")
PORT = os.getenv("PORT")
DATABASE = os.getenv("DATABASE")
USER = os.getenv("USER")
PASSWORD = os.getenv("PASSWORD")

TABLE_NAME = "device_nodes"


def export_table_to_csv():
    conn = psycopg2.connect(
        host=HOST, port=PORT, database=DATABASE, user=USER, password=PASSWORD
    )
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM {TABLE_NAME}")
    rows = cur.fetchall()
    colnames = [desc[0] for desc in cur.description]

    os.makedirs("data/raw", exist_ok=True)
    output_path = f"data/raw/{TABLE_NAME}.csv"

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(colnames)
        writer.writerows(rows)

    cur.close()
    conn.close()
    print(f"Exportado a {output_path}")


if __name__ == "__main__":
    export_table_to_csv()
