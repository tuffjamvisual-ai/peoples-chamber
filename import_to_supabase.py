import json
import os
from dotenv import load_dotenv
import psycopg2

# Load environment
load_dotenv('/Users/johnnybot/peoples_chamber/.env')
DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    print("ERROR: DATABASE_URL not set")
    exit(1)

# Read exported bills
with open('/Users/johnnybot/houseofthepeople/bills_export.json', 'r') as f:
    bills = json.load(f)

print(f"Loading {len(bills)} bills into Supabase...")

# Connect to Supabase
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

# Clear existing legislation table
cursor.execute("DELETE FROM legislation")
conn.commit()
print("✓ Cleared existing legislation")

# Insert bills
for i, bill in enumerate(bills):
    try:
        cursor.execute("""
            INSERT INTO legislation (id, title, full_text, summary, votes_agree, votes_disagree)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            str(bill['id']),
            bill['title'][:200],  # Truncate to column limit
            bill['full_text'],
            bill['summary'][:500],  # Truncate summary
            bill['votes_agree'],
            bill['votes_disagree']
        ))
        
        if (i + 1) % 500 == 0:
            conn.commit()
            print(f"  Inserted {i + 1} bills...")
    except Exception as e:
        print(f"ERROR importing bill {bill['id']}: {e}")
        continue

conn.commit()
cursor.close()
conn.close()

print(f"✓ Successfully imported {len(bills)} bills to Supabase!")
