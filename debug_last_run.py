import sqlite3
import sys

run_id = sys.argv[1] if len(sys.argv) > 1 else "4bba1e7e-c21f-41a1-a85b-bea82fff2a16"

conn = sqlite3.connect('.agent/agent_memory.db')
cursor = conn.cursor()

# Get messages
print("=== MESSAGES ===")
cursor.execute('SELECT role, content FROM messages WHERE run_id = ? ORDER BY timestamp', (run_id,))
for role, content in cursor.fetchall():
    print(f"{role}: {content[:300]}")
    print()

# Get actions
print("\n=== ACTIONS ===")
cursor.execute('SELECT name, params, result FROM actions WHERE run_id = ? ORDER BY timestamp', (run_id,))
for name, params, result in cursor.fetchall():
    print(f"Action: {name}")
    print(f"Params: {params[:200]}")
    print(f"Result: {result[:200]}")
    print()

conn.close()
