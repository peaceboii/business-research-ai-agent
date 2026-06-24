import sqlite3

def check():
    try:
        conn = sqlite3.connect('business_research.db')
        cursor = conn.cursor()
        
        # Get table list
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [r[0] for r in cursor.fetchall()]
        print("Tables:", tables)
        
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"Table '{table}' has {count} rows")
            
            # Print a sample if rows exist
            if count > 0:
                cursor.execute(f"SELECT * FROM {table} LIMIT 1")
                row = cursor.fetchone()
                # Get column names
                cursor.execute(f"PRAGMA table_info({table})")
                cols = [c[1] for c in cursor.fetchall()]
                print(f"Sample from {table}:", dict(zip(cols, row)))
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check()
