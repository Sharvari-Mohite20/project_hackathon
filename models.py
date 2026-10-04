from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default='student')  # 'student', 'staff', 'admin'
    student_id = db.Column(db.String(50), nullable=True)  # Roll number or Staff ID
    department = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    items = db.relationship('Item', backref='reporter', lazy='dynamic', cascade='all, delete-orphan')
    claims = db.relationship('Claim', backref='claimant', lazy='dynamic', foreign_keys='Claim.claimant_id', cascade='all, delete-orphan')
    notifications = db.relationship('Notification', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    @property
    def is_admin(self):
        return self.role == 'admin'
    
    def __repr__(self):
        return f'<User {self.email} ({self.role})>'


class CampusLocation(db.Model):
    __tablename__ = 'campus_locations'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    zone = db.Column(db.String(50), default='Academic')  # Academic, Residential, Recreational, Administrative
    description = db.Column(db.Text, nullable=True)
    icon = db.Column(db.String(50), default='map-pin')
    map_x = db.Column(db.Float, default=50.0)  # Percentage on map 0 - 100
    map_y = db.Column(db.Float, default=50.0)
    
    items = db.relationship('Item', backref='location', lazy='dynamic')
    
    def __repr__(self):
        return f'<Location {self.name}>'


class Item(db.Model):
    __tablename__ = 'items'
    
    id = db.Column(db.Integer, primary_key=True)
    item_type = db.Column(db.String(10), nullable=False)  # 'lost' or 'found'
    title = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=False)
    
    # Location
    location_id = db.Column(db.Integer, db.ForeignKey('campus_locations.id'), nullable=True)
    specific_location = db.Column(db.String(150), nullable=True)  # e.g., "Desk 24, 2nd Floor Reading Room"
    
    date_lost_or_found = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    image_path = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(20), default='active')  # 'active', 'pending_claim', 'resolved', 'closed'
    
    # Features
    is_urgent = db.Column(db.Boolean, default=False)
    reward_amount = db.Column(db.Float, nullable=True, default=0.0)
    secret_verification_question = db.Column(db.Text, nullable=True)  # Anti-fraud question for found items
    safe_custody_info = db.Column(db.String(255), nullable=True)  # Where finder deposited/kept it
    storage_locker_number = db.Column(db.String(50), nullable=True)  # For Security Office inventory
    contact_preference = db.Column(db.String(50), default='in_app')  # 'in_app', 'email', 'phone'
    
    # Audit & User
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    claims = db.relationship('Claim', backref='item', lazy='dynamic', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'item_type': self.item_type,
            'title': self.title,
            'category': self.category,
            'description': self.description,
            'location': self.location.name if self.location else self.specific_location,
            'specific_location': self.specific_location,
            'date': self.date_lost_or_found.strftime('%b %d, %Y') if self.date_lost_or_found else '',
            'image_path': self.image_path,
            'status': self.status,
            'is_urgent': self.is_urgent,
            'reward_amount': self.reward_amount,
            'created_at': self.created_at.strftime('%b %d, %Y %I:%M %p')
        }
    
    def __repr__(self):
        return f'<Item #{self.id} [{self.item_type.upper()}] {self.title}>'


class Claim(db.Model):
    __tablename__ = 'claims'
    
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('items.id'), nullable=False)
    claimant_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    claim_description = db.Column(db.Text, nullable=False)  # Why you claim it's yours
    answer_to_secret_question = db.Column(db.Text, nullable=True)
    proof_image_path = db.Column(db.String(255), nullable=True)
    
    status = db.Column(db.String(20), default='pending')  # 'pending', 'approved', 'rejected', 'completed'
    handover_pin = db.Column(db.String(6), nullable=True)  # 6-digit PIN generated on approval
    qr_code_path = db.Column(db.String(255), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    reviewed_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)
    
    # Reviewer relationship
    reviewer = db.relationship('User', foreign_keys=[reviewed_by_id])
    messages = db.relationship('Message', backref='claim', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Claim #{self.id} on Item #{self.item_id} by User #{self.claimant_id}>'


class Message(db.Model):
    __tablename__ = 'messages'
    
    id = db.Column(db.Integer, primary_key=True)
    claim_id = db.Column(db.Integer, db.ForeignKey('claims.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)
    
    sender = db.relationship('User', foreign_keys=[sender_id])
    
    def __repr__(self):
        return f'<Message #{self.id} on Claim #{self.claim_id}>'


class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    link = db.Column(db.String(255), nullable=True)
    type = db.Column(db.String(50), default='info')  # 'match_found', 'claim_received', 'claim_approved', 'claim_rejected', 'handover_complete'
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Notification #{self.id} for User #{self.user_id}>'


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(100), nullable=False)  # 'ITEM_REPORTED', 'CLAIM_SUBMITTED', 'CLAIM_APPROVED', 'HANDOVER_VERIFIED'
    details = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    item_id = db.Column(db.Integer, db.ForeignKey('items.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User')
    item = db.relationship('Item')
    
    def __repr__(self):
        return f'<AuditLog #{self.id} {self.action}>'
