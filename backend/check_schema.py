import sqlite3
import os

db_path = os.path.join('data', 'applications.db')
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(applications);")
    columns = cursor.fetchall()
    for col in columns:
        print(col) # (id, name, type, notnull, dflt_value, pk)
    conn.close()
else:
    print("DB not found")
