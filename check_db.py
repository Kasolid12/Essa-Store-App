import sqlite3 
conn = sqlite3.connect('essa.db') 
cur = conn.cursor() 
cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name") 
tables = cur.fetchall() 
for t in tables: 
    print('\n=== TABLE:', t[0], '===') 
    cur.execute(f"PRAGMA table_info({t[0]})") 
    for col in cur.fetchall(): 
        print(col) 
conn.close() 
