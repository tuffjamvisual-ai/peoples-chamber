from flask import jsonify, request
from flask_login import login_required, current_user
from models import db, Bill, Vote, User
from sqlalchemy import func

def register_api_routes(app):
    
    @app.route('/api/bills', methods=['GET'])
    def api_bills():
        """Get paginated list of bills with filters"""
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', '')
        category = request.args.get('category', '')
        house = request.args.get('house', '')
        stage = request.args.get('stage', '')
        
        query = Bill.query.filter_by(status='Active')
        
        if search:
            query = query.filter(Bill.title.contains(search))
        if category:
            query = query.filter(Bill.category == category)
        if house:
            query = query.filter(Bill.originating_house == house)
        if stage:
            query = query.filter(Bill.current_stage == stage)
        
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        bills_data = []
        for bill in pagination.items:
            yes_count = Vote.query.filter_by(bill_id=bill.id, choice='yes').count()
            no_count = Vote.query.filter_by(bill_id=bill.id, choice='no').count()
            abstain_count = Vote.query.filter_by(bill_id=bill.id, choice='abstain').count()
            
            bills_data.append({
                'id': bill.id,
                'title': bill.title,
                'description': bill.description,
                'category': bill.category,
                'current_stage': bill.current_stage,
                'sponsor_name': bill.sponsor_name,
                'sponsor_party': bill.sponsor_party,
                'sponsor_photo': bill.sponsor_photo,
                'sponsor_party_colour': bill.sponsor_party_colour,
                'originating_house': bill.originating_house,
                'votes': {
                    'yes': yes_count,
                    'no': no_count,
                    'abstain': abstain_count
                }
            })
        
        return jsonify({
            'bills': bills_data,
            'pagination': {
                'page': pagination.page,
                'per_page': pagination.per_page,
                'total': pagination.total,
                'pages': pagination.pages
            }
        })
    
    @app.route('/api/bills/<int:bill_id>', methods=['GET'])
    def api_bill_detail(bill_id):
        """Get single bill with full details and vote counts"""
        bill = Bill.query.get_or_404(bill_id)
        
        yes_count = Vote.query.filter_by(bill_id=bill.id, choice='yes').count()
        no_count = Vote.query.filter_by(bill_id=bill.id, choice='no').count()
        abstain_count = Vote.query.filter_by(bill_id=bill.id, choice='abstain').count()
        
        user_vote = None
        if current_user.is_authenticated:
            vote = Vote.query.filter_by(user_id=current_user.id, bill_id=bill_id).first()
            if vote:
                user_vote = vote.choice
        
        return jsonify({
            'id': bill.id,
            'title': bill.title,
            'long_title': bill.long_title,
            'description': bill.description,
            'category': bill.category,
            'status': bill.status,
            'current_stage': bill.current_stage,
            'stage_date': bill.stage_date,
            'sponsor_name': bill.sponsor_name,
            'sponsor_party': bill.sponsor_party,
            'sponsor_party_colour': bill.sponsor_party_colour,
            'sponsor_photo': bill.sponsor_photo,
            'sponsor_constituency': bill.sponsor_constituency,
            'originating_house': bill.originating_house,
            'votes': {
                'yes': yes_count,
                'no': no_count,
                'abstain': abstain_count
            },
            'user_vote': user_vote
        })
    
    @app.route('/api/mps', methods=['GET'])
    def api_mps():
        """Get list of MPs with bill counts"""
        mp_data = db.session.query(
            Bill.sponsor_name,
            Bill.sponsor_party,
            Bill.sponsor_photo,
            Bill.sponsor_constituency,
            Bill.sponsor_party_colour,
            func.count(Bill.id).label('bill_count')
        ).filter(
            Bill.sponsor_name != None
        ).group_by(
            Bill.sponsor_name,
            Bill.sponsor_party,
            Bill.sponsor_photo,
            Bill.sponsor_constituency,
            Bill.sponsor_party_colour
        ).order_by(func.count(Bill.id).desc()).all()
        
        mps = [{
            'name': m[0],
            'party': m[1],
            'photo': m[2],
            'constituency': m[3],
            'party_colour': m[4],
            'bill_count': m[5]
        } for m in mp_data]
        
        return jsonify({'mps': mps})
    
    @app.route('/api/mp/<path:name>', methods=['GET'])
    def api_mp_profile(name):
        """Get single MP profile with their bills"""
        bills = Bill.query.filter_by(sponsor_name=name).all()
        if not bills:
            return jsonify({'error': 'MP not found'}), 404
        
        mp_info = bills[0]
        
        bills_data = []
        total_yes = 0
        total_no = 0
        total_abstain = 0
        
        for bill in bills:
            yes_count = Vote.query.filter_by(bill_id=bill.id, choice='yes').count()
            no_count = Vote.query.filter_by(bill_id=bill.id, choice='no').count()
            abstain_count = Vote.query.filter_by(bill_id=bill.id, choice='abstain').count()
            
            total_yes += yes_count
            total_no += no_count
            total_abstain += abstain_count
            
            bills_data.append({
                'id': bill.id,
                'title': bill.title,
                'category': bill.category,
                'current_stage': bill.current_stage,
                'votes': {
                    'yes': yes_count,
                    'no': no_count,
                    'abstain': abstain_count
                }
            })
        
        return jsonify({
            'name': mp_info.sponsor_name,
            'party': mp_info.sponsor_party,
            'photo': mp_info.sponsor_photo,
            'constituency': mp_info.sponsor_constituency,
            'party_colour': mp_info.sponsor_party_colour,
            'bill_count': len(bills),
            'total_votes': {
                'yes': total_yes,
                'no': total_no,
                'abstain': total_abstain
            },
            'bills': bills_data
        })
    
    @app.route('/api/vote/<int:bill_id>', methods=['POST'])
    @login_required
    def api_vote(bill_id):
        """Submit or change a vote"""
        data = request.get_json()
        choice = data.get('choice')
        
        if choice not in ['yes', 'no', 'abstain']:
            return jsonify({'error': 'Invalid vote choice'}), 400
        
        bill = Bill.query.get_or_404(bill_id)
        
        existing = Vote.query.filter_by(user_id=current_user.id, bill_id=bill_id).first()
        if existing:
            existing.choice = choice
        else:
            vote = Vote(user_id=current_user.id, bill_id=bill_id, choice=choice)
            db.session.add(vote)
        
        db.session.commit()
        
        yes_count = Vote.query.filter_by(bill_id=bill_id, choice='yes').count()
        no_count = Vote.query.filter_by(bill_id=bill_id, choice='no').count()
        abstain_count = Vote.query.filter_by(bill_id=bill_id, choice='abstain').count()
        
        return jsonify({
            'success': True,
            'choice': choice,
            'votes': {
                'yes': yes_count,
                'no': no_count,
                'abstain': abstain_count
            }
        })
    
    @app.route('/api/filters', methods=['GET'])
    def api_filters():
        """Get available filter options"""
        categories = db.session.query(Bill.category).distinct().all()
        categories = [c[0] for c in categories if c[0]]
        
        houses = db.session.query(Bill.originating_house).distinct().all()
        houses = [h[0] for h in houses if h[0]]
        
        stages = db.session.query(Bill.current_stage).distinct().all()
        stages = [s[0] for s in stages if s[0]]
        
        return jsonify({
            'categories': sorted(categories),
            'houses': sorted(houses),
            'stages': sorted(stages)
        })
