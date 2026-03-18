import requests
import time
from models import Bill
from flask_sqlalchemy import SQLAlchemy
from flask import Flask

app = Flask(__name__)
app.config['SECRET_KEY'] = 'changethislater'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////Users/johnnybot/houseofthepeople/instance/peoples_chamber.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

BILLS_API = "https://bills-api.parliament.uk/api/v1/Bills"

def get_category(title):
    title = title.lower()
    if any(w in title for w in ['health', 'nhs', 'mental', 'care', 'medicine', 'hospital']):
        return 'Health'
    if any(w in title for w in ['school', 'education', 'university', 'children', 'teacher']):
        return 'Education'
    if any(w in title for w in ['environment', 'climate', 'energy', 'green', 'carbon', 'nature']):
        return 'Environment'
    if any(w in title for w in ['housing', 'rent', 'tenant', 'landlord', 'home', 'leasehold']):
        return 'Housing'
    if any(w in title for w in ['crime', 'police', 'justice', 'court', 'prison', 'safety']):
        return 'Justice'
    if any(w in title for w in ['tax', 'economy', 'finance', 'budget', 'wage', 'business', 'trade']):
        return 'Economy'
    if any(w in title for w in ['transport', 'road', 'rail', 'bus', 'aviation', 'driver']):
        return 'Transport'
    if any(w in title for w in ['defence', 'military', 'armed']):
        return 'Defence'
    return 'Other'

def import_all_bills():
    print("Fetching all bills from Parliament API...")
    skip = 0
    take = 50
    total_added = 0

    with app.app_context():
        while True:
            try:
                params = {'skip': skip, 'take': take}
                response = requests.get(BILLS_API, params=params, timeout=15)
                data = response.json()
                items = data.get('items', [])
                if not items:
                    break
                for b in items:
                    title = b.get('shortTitle', '').strip()
                    if not title:
                        continue
                    parliament_id = b.get('billId')
                    try:
                        existing = db.session.execute(
                            db.select(Bill).filter_by(parliament_id=parliament_id)
                        ).scalar_one_or_none()
                    except:
                        db.session.rollback()
                        existing = None
                    if existing:
                        continue
                    try:
                        stage = b['currentStage']['description']
                        sittings = b['currentStage']['stageSittings']
                        stage_date = sittings[0]['date'][:10] if sittings else ''
                    except:
                        stage = 'Unknown'
                        stage_date = ''
                    bill_type_id = b.get('billTypeId', 0)
                    if bill_type_id == 1:
                        bill_type = 'Government Bill'
                    elif bill_type_id in [5, 7, 8, 2]:
                        bill_type = "Private Members Bill"
                    elif bill_type_id == 6:
                        bill_type = 'Private Bill'
                    else:
                        bill_type = 'Other'
                    withdrawn = b.get('billWithdrawn')
                    if withdrawn:
                        withdrawn = withdrawn[:10]
                    description = "Type: " + bill_type + ". Current stage: " + stage + "."
                    new_bill = Bill(
                        parliament_id=parliament_id,
                        title=title,
                        long_title=None,
                        description=description,
                        category=get_category(title),
                        status='Active',
                        current_stage=stage,
                        stage_date=stage_date,
                        originating_house=b.get('originatingHouse'),
                        is_defeated=b.get('isDefeated', False),
                        bill_withdrawn=withdrawn
                    )
                    try:
                        db.session.add(new_bill)
                        db.session.commit()
                        total_added += 1
                    except:
                        db.session.rollback()
                print("Imported " + str(total_added) + " bills so far...")
                skip += take
                total_results = data.get('totalResults', 0)
                if skip >= total_results:
                    break
                time.sleep(0.5)
            except Exception as e:
                print("Error at skip " + str(skip) + ": " + str(e) + ", retrying...")
                time.sleep(5)

    print("Done. Total added: " + str(total_added))

if __name__ == '__main__':
    import_all_bills()