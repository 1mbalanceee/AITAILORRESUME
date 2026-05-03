import sqlite3
import os

db_path = os.path.join('data', 'applications.db')
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. Create a temporary table with the correct schema
    # Based on your current columns but making kanban_status nullable
    cursor.execute("""
    CREATE TABLE applications_new (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        job_title VARCHAR(255),
        company VARCHAR(255),
        job_url TEXT,
        jd_raw TEXT,
        match_score FLOAT,
        match_report TEXT,
        work_mode VARCHAR(50),
        location_req VARCHAR(255),
        experience_gap TEXT,
        status VARCHAR(50) NOT NULL DEFAULT 'analyzed',
        gdoc_url TEXT,
        cover_letter TEXT,
        notes TEXT,
        applicants_count INTEGER,
        tailoring_report TEXT,
        last_status_change DATETIME,
        is_saved BOOLEAN DEFAULT 0,
        is_hidden BOOLEAN DEFAULT 0,
        kanban_status TEXT,
        is_analyzed BOOLEAN NOT NULL DEFAULT 0
    );
    """)
    
    # 2. Copy data from old to new
    # Mapping columns precisely
    cols = [
        "id", "created_at", "updated_at", "job_title", "company", "job_url", 
        "jd_raw", "match_score", "match_report", "work_mode", "location_req", 
        "experience_gap", "status", "gdoc_url", "cover_letter", "notes", 
        "applicants_count", "tailoring_report", "last_status_change", 
        "is_saved", "is_hidden", "kanban_status", "is_analyzed"
    ]
    cols_str = ", ".join(cols)
    cursor.execute(f"INSERT INTO applications_new ({cols_str}) SELECT {cols_str} FROM applications;")
    
    # 3. Drop old table and rename new
    cursor.execute("DROP TABLE applications;")
    cursor.execute("ALTER TABLE applications_new RENAME TO applications;")
    
    conn.commit()
    conn.close()
    print("Migration successful! kanban_status is now nullable.")
else:
    print("DB not found")
