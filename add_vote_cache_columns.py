"""
Migration script to add vote count cache columns to the Bill table.
"""
from app import app
from models import db

def add_vote_count_columns():
    with app.app_context():
        print("Adding vote count cache columns to Bill table...")
        
        # Add columns using raw SQL
        sql_commands = [
            "ALTER TABLE bill ADD COLUMN IF NOT EXISTS vote_count_yes INTEGER DEFAULT 0;",
            "ALTER TABLE bill ADD COLUMN IF NOT EXISTS vote_count_no INTEGER DEFAULT 0;",
            "ALTER TABLE bill ADD COLUMN IF NOT EXISTS vote_count_abstain INTEGER DEFAULT 0;",
            "ALTER TABLE bill ADD COLUMN IF NOT EXISTS vote_counts_updated_at TIMESTAMP;"
        ]
        
        for sql in sql_commands:
            try:
                db.session.execute(db.text(sql))
                print(f"  ✓ Executed: {sql[:60]}...")
            except Exception as e:
                print(f"  ⚠ Error (might already exist): {e}")
        
        db.session.commit()
        print("✓ Migration complete!")

if __name__ == '__main__':
    add_vote_count_columns()
