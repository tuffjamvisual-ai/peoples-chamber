from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    votes = db.relationship('Vote', backref='user', lazy=True)

class Bill(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    parliament_id = db.Column(db.Integer, unique=True, nullable=True)
    title = db.Column(db.String(200), nullable=False)
    long_title = db.Column(db.Text, nullable=True)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(50), default='Active')
    current_stage = db.Column(db.String(100), nullable=True)
    stage_date = db.Column(db.String(50), nullable=True)
    sponsor_name = db.Column(db.String(100), nullable=True)
    sponsor_party = db.Column(db.String(100), nullable=True)
    sponsor_party_colour = db.Column(db.String(10), nullable=True)
    sponsor_photo = db.Column(db.String(300), nullable=True)
    sponsor_constituency = db.Column(db.String(100), nullable=True)
    sponsor_page = db.Column(db.String(300), nullable=True)
    originating_house = db.Column(db.String(20), nullable=True)
    is_defeated = db.Column(db.Boolean, default=False)
    bill_withdrawn = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Cached vote counts - updated periodically instead of counting live
    vote_count_yes = db.Column(db.Integer, default=0)
    vote_count_no = db.Column(db.Integer, default=0)
    vote_count_abstain = db.Column(db.Integer, default=0)
    vote_counts_updated_at = db.Column(db.DateTime, nullable=True)
    
    votes = db.relationship('Vote', backref='bill', lazy=True)

class Vote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    bill_id = db.Column(db.Integer, db.ForeignKey('bill.id'), nullable=False)
    choice = db.Column(db.String(10), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('user_id', 'bill_id'),)
