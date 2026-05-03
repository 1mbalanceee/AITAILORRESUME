import sqlite3
import os
import time

db_path = os.path.join('data', 'applications.db')
if os.path.exists(db_path):
    try:
        # Connect with timeout to wait for lock to release
        conn = sqlite3.connect(db_path, timeout=20)
        cursor = conn.cursor()
        cursor.execute("UPDATE applications SET kanban_status = NULL WHERE is_analyzed = 1 AND kanban_status = 'wishlist';")
        print(f"Rows updated: {cursor.rowcount}")
        conn.commit()
        conn.close()
    except sqlite3.OperationalError as e:
        print(f"Error: {e}. Please stop the backend server for a moment so I can fix the DB.")
else:
    print(f"Database not found at {db_path}")
