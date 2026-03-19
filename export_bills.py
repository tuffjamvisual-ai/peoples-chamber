import sqlite3
import json

# Connect to local SQLite database
conn = sqlite3.connect('/Users/johnnybot/houseofthepeople/instance/peoples_chamber.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Get all bills
cursor.execute("SELECT * FROM bill")
bills = cursor.fetchall()

# Convert to JSON
bills_json = []
for bill in bills:
    bills_json.append({
        'id': bill['parliament_id'],
        'title': bill['title'] or '',
        'full_text': bill['long_title'] or bill['description'] or '',
        'summary': bill['description'] or '',
        'votes_agree': 0,
        'votes_disagree': 0,
    })

# Write to file
with open('/Users/johnnybot/houseofthepeople/bills_export.json', 'w') as f:
    json.dump(bills_json, f, indent=2)

print(f"✓ Exported {len(bills_json)} bills to bills_export.json")
conn.close()
