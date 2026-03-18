import requests
import sqlite3
import time
from datetime import datetime

def get_party_color(party_name):
    """Map party names to their traditional colors"""
    colors = {
        'Conservative': '#0087DC',
        'Labour': '#E4003B', 
        'Liberal Democrat': '#FAA61A',
        'SNP': '#FDF83D',
        'Green Party': '#6AB023',
        'DUP': '#D46A4C',
        'Sinn Fein': '#326760',
        'Plaid Cymru': '#005B54',
        'UKIP': '#70147A',
        'Independent': '#999999'
    }
    
    for party, color in colors.items():
        if party.lower() in party_name.lower():
            return color
    return '#666666'  # Default gray

def enrich_bill_from_parliament_api(bill_id, parliament_bill_id):
    """Fetch bill details from Parliament API and update database"""
    try:
        # Get bill details
        url = f"https://bills-api.parliament.uk/api/v1/Bills/{parliament_bill_id}"
        response = requests.get(url, timeout=15)
        
        if response.status_code != 200:
            print(f"Failed to fetch bill {parliament_bill_id}: {response.status_code}")
            return False
            
        data = response.json()
        bill_data = data.get('value', {})
        
        # Extract sponsor information
        sponsors = bill_data.get('sponsors', [])
        sponsor_data = {}
        
        if sponsors:
            sponsor = sponsors[0]  # Take first sponsor
            member = sponsor.get('member', {})
            
            sponsor_data = {
                'sponsor_name': member.get('name'),
                'sponsor_constituency': member.get('latestHouseMembership', {}).get('membershipFrom'),
                'sponsor_party': member.get('latestParty', {}).get('name'),
                'sponsor_photo': member.get('thumbnailUrl'),
            }
            
            # Add party color
            if sponsor_data['sponsor_party']:
                sponsor_data['sponsor_party_colour'] = get_party_color(sponsor_data['sponsor_party'])
        
        # Extract current stage and other details
        current_stage = bill_data.get('currentStage', {}).get('description')
        originating_house = bill_data.get('originatingHouse')
        long_title = bill_data.get('longTitle')
        
        # Update database
        conn = sqlite3.connect('instance/peoples_chamber.db')
        cursor = conn.cursor()
        
        update_fields = []
        update_values = []
        
        if sponsor_data.get('sponsor_name'):
            update_fields.append('sponsor_name = ?')
            update_values.append(sponsor_data['sponsor_name'])
            
        if sponsor_data.get('sponsor_constituency'):
            update_fields.append('sponsor_constituency = ?')
            update_values.append(sponsor_data['sponsor_constituency'])
            
        if sponsor_data.get('sponsor_party'):
            update_fields.append('sponsor_party = ?')
            update_values.append(sponsor_data['sponsor_party'])
            
        if sponsor_data.get('sponsor_party_colour'):
            update_fields.append('sponsor_party_colour = ?')
            update_values.append(sponsor_data['sponsor_party_colour'])
            
        if sponsor_data.get('sponsor_photo'):
            update_fields.append('sponsor_photo = ?')
            update_values.append(sponsor_data['sponsor_photo'])
            
        if current_stage:
            update_fields.append('current_stage = ?')
            update_values.append(current_stage)
            
        if originating_house:
            update_fields.append('originating_house = ?')
            update_values.append(originating_house)
            
        if long_title:
            update_fields.append('long_title = ?')
            update_values.append(long_title)
            
        if update_fields:
            update_values.append(bill_id)
            query = f"UPDATE bill SET {', '.join(update_fields)} WHERE id = ?"
            cursor.execute(query, update_values)
            conn.commit()
            
        conn.close()
        print(f"✓ Updated bill {bill_id} - {sponsor_data.get('sponsor_name', 'N/A')} ({sponsor_data.get('sponsor_party', 'N/A')})")
        return True
        
    except Exception as e:
        print(f"✗ Error enriching bill {bill_id}: {str(e)}")
        return False

def main():
    # Connect to database
    conn = sqlite3.connect('instance/peoples_chamber.db')
    cursor = conn.cursor()
    
    # Get more bills without sponsor data
    cursor.execute("""
        SELECT id, title, parliament_id 
        FROM bill 
        WHERE (sponsor_party IS NULL OR current_stage IS NULL)
        AND parliament_id IS NOT NULL 
        ORDER BY id 
        LIMIT 100
    """)
    
    bills = cursor.fetchall()
    conn.close()
    
    print(f"Found {len(bills)} bills to enrich...")
    
    success_count = 0
    for bill_id, title, parliament_id in bills:
        print(f"Enriching: {title[:60]}...")
        if enrich_bill_from_parliament_api(bill_id, parliament_id):
            success_count += 1
        time.sleep(1)  # Be nice to the API
        
    print(f"\nEnriched {success_count}/{len(bills)} bills successfully")

if __name__ == '__main__':
    main()