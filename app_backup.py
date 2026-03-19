from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Bill, Vote

app = Flask(__name__)
app.config['SECRET_KEY'] = 'changethislater'
import os
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///peoples_chamber.db')
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
if 'supabase' in DATABASE_URL and 'sslmode' not in DATABASE_URL:
    DATABASE_URL += '?sslmode=require'
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 60,
    'pool_size': 2,
    'max_overflow': 0,
    'pool_timeout': 10,
}
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    db.create_all()

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
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
    
    bills = query.all()
    
    # Get filter options
    categories = db.session.query(Bill.category).distinct().all()
    categories = [c[0] for c in categories if c[0]]
    
    houses = db.session.query(Bill.originating_house).distinct().all()
    houses = [h[0] for h in houses if h[0]]
    
    stages = db.session.query(Bill.current_stage).distinct().all()
    stages = [s[0] for s in stages if s[0]]
    
    return render_template('index.html', bills=bills, search=search, 
                         category=category, house=house, stage=stage,
                         categories=categories, houses=houses, stages=stages)

@app.route('/mps')
def mps():
    from sqlalchemy import func
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
    mps = [{'name': m[0], 'party': m[1], 'photo': m[2], 'constituency': m[3], 'colour': m[4], 'bill_count': m[5]} for m in mp_data]
    return render_template('mps.html', mps=mps)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        if User.query.filter_by(email=email).first():
            flash('Email already registered')
            return redirect(url_for('register'))
        hashed = generate_password_hash(password)
        user = User(username=username, email=email, password=hashed)
        db.session.add(user)
        db.session.commit()
        flash('Account created! Please log in.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('index'))
        flash('Invalid email or password')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/bill/<int:bill_id>')
def bill(bill_id):
    bill = Bill.query.get_or_404(bill_id)
    user_vote = None
    if current_user.is_authenticated:
        user_vote = Vote.query.filter_by(user_id=current_user.id, bill_id=bill_id).first()
    yes_votes = Vote.query.filter_by(bill_id=bill_id, choice='yes').count()
    no_votes = Vote.query.filter_by(bill_id=bill_id, choice='no').count()
    abstain_votes = Vote.query.filter_by(bill_id=bill_id, choice='abstain').count()
    return render_template('bill.html', bill=bill, user_vote=user_vote, yes=yes_votes, no=no_votes, abstain=abstain_votes)

@app.route('/vote/<int:bill_id>/<choice>', methods=['POST'])
@login_required
def vote(bill_id, choice):
    if choice not in ['yes', 'no', 'abstain']:
        flash('Invalid vote')
        return redirect(url_for('bill', bill_id=bill_id))
    existing = Vote.query.filter_by(user_id=current_user.id, bill_id=bill_id).first()
    if existing:
        existing.choice = choice
    else:
        vote = Vote(user_id=current_user.id, bill_id=bill_id, choice=choice)
        db.session.add(vote)
    db.session.commit()
    flash(f'Vote recorded: {choice.title()}')
    return redirect(url_for('bill', bill_id=bill_id))

@app.route('/admin', methods=['GET', 'POST'])
@login_required
def admin():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        category = request.form['category']
        bill = Bill(title=title, description=description, category=category)
        db.session.add(bill)
        db.session.commit()
        flash('Bill added successfully')
        return redirect(url_for('admin'))
    bills = Bill.query.all()
    return render_template('admin.html', bills=bills)


@app.route('/mp/<path:name>')
def mp_profile(name):
    from sqlalchemy import func
    bills = Bill.query.filter_by(sponsor_name=name).all()
    if not bills:
        return "MP not found", 404
    mp = bills[0]
    yes_votes = 0
    no_votes = 0
    for bill in bills:
        yes_votes += Vote.query.filter_by(bill_id=bill.id, choice='yes').count()
        no_votes += Vote.query.filter_by(bill_id=bill.id, choice='no').count()
    return render_template('mp_profile.html', mp=mp, bills=bills, yes_votes=yes_votes, no_votes=no_votes)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=8000)