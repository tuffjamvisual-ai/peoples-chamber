"""
Script to compute and cache vote counts for all bills.
Run this periodically (every hour) to keep vote counts up to date.
"""
from app import app
from models import db, Bill, Vote
from sqlalchemy import func
from datetime import datetime

def update_all_vote_counts():
    """Compute vote counts for all bills and store in database"""
    with app.app_context():
        print("Starting vote count update...")
        
        # Get all bills
        bills = Bill.query.all()
        total_bills = len(bills)
        
        print(f"Updating vote counts for {total_bills} bills...")
        
        updated_count = 0
        for i, bill in enumerate(bills, 1):
            # Count votes for this bill
            yes_count = Vote.query.filter_by(bill_id=bill.id, choice='yes').count()
            no_count = Vote.query.filter_by(bill_id=bill.id, choice='no').count()
            abstain_count = Vote.query.filter_by(bill_id=bill.id, choice='abstain').count()
            
            # Update cached counts
            bill.vote_count_yes = yes_count
            bill.vote_count_no = no_count
            bill.vote_count_abstain = abstain_count
            bill.vote_counts_updated_at = datetime.utcnow()
            
            updated_count += 1
            
            # Progress indicator every 100 bills
            if i % 100 == 0:
                print(f"  Progress: {i}/{total_bills} bills updated...")
        
        # Commit all changes
        db.session.commit()
        
        print(f"✓ Successfully updated vote counts for {updated_count} bills!")
        print(f"  Timestamp: {datetime.utcnow()}")

if __name__ == '__main__':
    update_all_vote_counts()
