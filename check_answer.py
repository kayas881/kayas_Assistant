import sqlite3
import json

conn = sqlite3.connect('.agent/agent.db')
cur = conn.cursor()
# First check schema
cur.execute("PRAGMA table_info(actions)")
print("Schema:", cur.fetchall())
cur.execute('SELECT * FROM actions WHERE run_id = ?', ('2335ef22-71c7-4236-ae20-54d6330b8e0b',))
rows = cur.fetchall()

for r in rows:
    print(f"Full row: {r}")
    # Try to parse JSON from likely result column
    for col in r:
        if col and isinstance(col, str) and col.startswith('{'):
            try:
                result = json.loads(col)
            except:
                continue
        if 'answer' in result:
            print(f"\n✓ FINAL ANSWER:\n{result['answer']}\n")
        if 'sources' in result:
            print(f"Sources ({len(result['sources'])}):")
            for s in result['sources'][:6]:
                print(f"  - {s.get('title', 'Untitled')[:70]} ({s.get('domain', '')})")
    print("---\n")

conn.close()
