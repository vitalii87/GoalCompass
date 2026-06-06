import sqlite3
from src.config.config import DB_PATH


conn = sqlite3.connect(DB_PATH)

query = """
SELECT
    process_name,
    window_title,
    total_seconds,
    times_seen,
    last_seen
FROM unknown_titles
ORDER BY last_seen DESC
LIMIT 20;
"""

cursor = conn.cursor()
cursor.execute(query)

for row in cursor.fetchall():
    print(row)

conn.close()