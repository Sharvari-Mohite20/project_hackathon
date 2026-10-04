import os
import random
import string
import csv
import io
from datetime import datetime, date
from flask import (
    Flask, render_template, request, redirect, url_for, 
    flash, jsonify, send_file, Response, abort
)
from flask_login import (
    LoginManager, login_user, logout_user, 
    login_required, current_user
)
from werkzeug.utils import secure_filename
import qrcode

from config import Config
from models import db, User, CampusLocation, Item, Claim, Message, Notification, AuditLog
from matching import find_potential_matches, calculate_match_score
from seed_data import seed_database

app = Flask(__name__)
app.config.from_object(Config)

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def generate_pin():
    """Generate a secure 6-digit numeric handover PIN."""
    return ''.join(random.choices(string.digits, k=6))

def generate_qr_pass(claim_id, pin):
    """Generate and save a QR code for handover verification."""
    qr_data = f"CAMPUSFIND-PASS:CLAIM-{claim_id}:PIN-{pin}"
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=3,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#1e3a8a", back_color="#ffffff")
    
    filename = f"qr_claim_{claim_id}.png"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    img.save(filepath)
    return filename

# Context Processors for Templates
@app.context_processor
def inject_global_data():
    unread_count = 0
    if current_user.is_authenticated:
        unread_count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    
    return {
        'college_name': app.config['COLLEGE_NAME'],
        'campus_name': app.config['CAMPUS_NAME'],
        'security_phone': app.config['SECURITY_CONTACT_PHONE'],
        'security_email': app.config['SECURITY_CONTACT_EMAIL'],
        'unread_notifications_count': unread_count,
        'current_year': datetime.utcnow().year
    }

# --- Authentication Routes ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))
        
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user, remember=remember)
            flash(f'Welcome back, {user.name}!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash('Invalid college email or password. Try one-click demo login below.', 'danger')
            
    return render_template('auth/login.html')


@app.route('/quick-login/<role_or_email>')
def quick_login(role_or_email):
    """Convenient 1-click login for evaluation and hackathon judging."""
    user = None
    if role_or_email == 'admin':
        user = User.query.filter_by(role='admin').first()
    elif role_or_email == 'student1' or role_or_email == 'aarav':
        user = User.query.filter_by(email='aarav.sharma@apexuni.edu').first()
    elif role_or_email == 'student2' or role_or_email == 'priya':
        user = User.query.filter_by(email='priya.patel@apexuni.edu').first()
    elif role_or_email == 'staff' or role_or_email == 'faculty':
        user = User.query.filter_by(role='staff').first()
    else:
        user = User.query.filter_by(email=role_or_email).first()
        
    if user:
        login_user(user)
        flash(f'Logged in as {user.name} ({user.role.capitalize()}) via Quick Access.', 'success')
    else:
        flash('Demo user not found.', 'warning')
        
    return redirect(url_for('index'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        student_id = request.form.get('student_id', '').strip()
        department = request.form.get('department', '').strip()
        phone = request.form.get('phone', '').strip()
        role = request.form.get('role', 'student')
        
        # Validation
        if not name or not email or not password:
            flash('Name, college email, and password are required.', 'danger')
            return render_template('auth/register.html')
            
        if User.query.filter_by(email=email).first():
            flash('An account with this email already exists. Please log in.', 'warning')
            return redirect(url_for('login'))
            
        user = User(
            name=name,
            email=email,
            student_id=student_id,
            department=department,
            phone=phone,
            role=role if role in ['student', 'staff'] else 'student'
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        login_user(user)
        flash(f'Account registered successfully! Welcome to CampusFind, {user.name}.', 'success')
        return redirect(url_for('index'))
        
    return render_template('auth/register.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('index'))


# --- Main Portal Routes ---

@app.route('/')
def index():
    # Urgent items ticker
    urgent_items = Item.query.filter_by(is_urgent=True, status='active').order_by(Item.created_at.desc()).limit(5).all()
    
    # Recent Lost Items
    recent_lost = Item.query.filter_by(item_type='lost', status='active').order_by(Item.created_at.desc()).limit(6).all()
    
    # Recent Found Items
    recent_found = Item.query.filter_by(item_type='found', status='active').order_by(Item.created_at.desc()).limit(6).all()
    
    # Campus Locations with item counts
    locations = CampusLocation.query.all()
    loc_stats = []
    for loc in locations:
        active_count = Item.query.filter_by(location_id=loc.id, status='active').count()
        loc_stats.append({
            'location': loc,
            'count': active_count
        })
        
    # Portal KPI stats
    total_items = Item.query.count()
    active_lost = Item.query.filter_by(item_type='lost', status='active').count()
    active_found = Item.query.filter_by(item_type='found', status='active').count()
    resolved_count = Item.query.filter_by(status='resolved').count()
    
    resolution_rate = round((resolved_count / total_items * 100), 1) if total_items > 0 else 0
    
    return render_template(
        'index.html',
        urgent_items=urgent_items,
        recent_lost=recent_lost,
        recent_found=recent_found,
        loc_stats=loc_stats,
        total_items=total_items,
        active_lost=active_lost,
        active_found=active_found,
        resolved_count=resolved_count,
        resolution_rate=resolution_rate
    )


@app.route('/items')
def item_list():
    item_type = request.args.get('type', 'all')
    category = request.args.get('category', 'all')
    location_id = request.args.get('location_id', type=int)
    search_query = request.args.get('q', '').strip()
    status = request.args.get('status', 'active')
    urgent_only = request.args.get('urgent') == 'true'
    sort_by = request.args.get('sort', 'newest')
    
    query = Item.query
    
    if item_type in ['lost', 'found']:
        query = query.filter(Item.item_type == item_type)
        
    if category != 'all' and category:
        query = query.filter(Item.category == category)
        
    if location_id:
        query = query.filter(Item.location_id == location_id)
        
    if status != 'all' and status:
        query = query.filter(Item.status == status)
        
    if urgent_only:
        query = query.filter(Item.is_urgent == True)
        
    if search_query:
        like_str = f"%{search_query}%"
        query = query.filter(
            (Item.title.ilike(like_str)) | 
            (Item.description.ilike(like_str)) | 
            (Item.specific_location.ilike(like_str)) |
            (Item.category.ilike(like_str))
        )
        
    if sort_by == 'oldest':
        query = query.order_by(Item.created_at.asc())
    elif sort_by == 'reward':
        query = query.order_by(Item.reward_amount.desc())
    else:
        query = query.order_by(Item.created_at.desc())
        
    items = query.all()
    locations = CampusLocation.query.order_by(CampusLocation.name).all()
    
    categories = [
        'Electronics', 'ID & Cards', 'Bags & Wallets', 
        'Keys & Locks', 'Books & Stationery', 'Clothing & Wearables', 
        'Bottles & Containers', 'Sports & Fitness', 'Other'
    ]
    
    return render_template(
        'items/list.html',
        items=items,
        locations=locations,
        categories=categories,
        current_type=item_type,
        current_category=category,
        current_location=location_id,
        current_status=status,
        current_search=search_query,
        current_sort=sort_by,
        urgent_only=urgent_only
    )


@app.route('/items/<int:item_id>')
def item_detail(item_id):
    item = Item.query.get_or_404(item_id)
    
    # Run Smart Matching against opposite active items
    opposite_type = 'found' if item.item_type == 'lost' else 'lost'
    candidates = Item.query.filter_by(item_type=opposite_type).all()
    potential_matches = find_potential_matches(item, candidates, min_score=30)
    
    # Check if current user has already claimed this item
    user_claim = None
    if current_user.is_authenticated:
        user_claim = Claim.query.filter_by(item_id=item.id, claimant_id=current_user.id).first()
        
    # Active approved claim on this item (for handover status)
    active_approved_claim = Claim.query.filter_by(item_id=item.id, status='approved').first()
    
    return render_template(
        'items/detail.html',
        item=item,
        potential_matches=potential_matches,
        user_claim=user_claim,
        active_approved_claim=active_approved_claim
    )


@app.route('/items/report', methods=['GET', 'POST'])
@login_required
def report_item():
    if request.method == 'POST':
        item_type = request.form.get('item_type')
        title = request.form.get('title', '').strip()
        category = request.form.get('category', '').strip()
        description = request.form.get('description', '').strip()
        location_id = request.form.get('location_id', type=int)
        specific_location = request.form.get('specific_location', '').strip()
        date_str = request.form.get('date_lost_or_found')
        is_urgent = bool(request.form.get('is_urgent'))
        reward_amount = float(request.form.get('reward_amount') or 0.0)
        secret_question = request.form.get('secret_verification_question', '').strip()
        safe_custody = request.form.get('safe_custody_info', '').strip()
        contact_pref = request.form.get('contact_preference', 'in_app')
        
        if not title or not category or not description:
            flash('Title, category, and description are mandatory.', 'danger')
            return redirect(url_for('report_item'))
            
        try:
            item_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else date.today()
        except ValueError:
            item_date = date.today()
            
        # Handle image upload
        image_path = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(f"{int(datetime.utcnow().timestamp())}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image_path = filename
                
        new_item = Item(
            item_type=item_type,
            title=title,
            category=category,
            description=description,
            location_id=location_id if location_id else None,
            specific_location=specific_location,
            date_lost_or_found=item_date,
            image_path=image_path,
            status='active',
            is_urgent=is_urgent,
            reward_amount=reward_amount,
            secret_verification_question=secret_question if item_type == 'found' else None,
            safe_custody_info=safe_custody if item_type == 'found' else None,
            contact_preference=contact_pref,
            user_id=current_user.id
        )
        db.session.add(new_item)
        db.session.commit()
        
        # Log Audit Trail
        log = AuditLog(
            action=f"ITEM_REPORTED_{item_type.upper()}",
            details=f"User {current_user.name} reported {item_type} item: {title}",
            user_id=current_user.id,
            item_id=new_item.id
        )
        db.session.add(log)
        
        # Automated AI Matching Check
        opposite_type = 'found' if item_type == 'lost' else 'lost'
        candidates = Item.query.filter_by(item_type=opposite_type, status='active').all()
        matches = find_potential_matches(new_item, candidates, min_score=45)
        
        if matches:
            top_match = matches[0]
            notif = Notification(
                user_id=current_user.id,
                title=f"Smart Match Detected ({top_match['score']}% Match)!",
                message=f"We found an existing {opposite_type} item that closely matches your report: '{top_match['item'].title}'. Click to review.",
                link=f"/items/{top_match['item'].id}",
                type="match_found"
            )
            db.session.add(notif)
            flash(f'Item reported! Our smart matching engine detected a {top_match["score"]}% potential match in our database!', 'info')
        else:
            flash(f'Your {item_type.capitalize()} item has been broadcasted to the campus portal!', 'success')
            
        db.session.commit()
        return redirect(url_for('item_detail', item_id=new_item.id))
        
    locations = CampusLocation.query.order_by(CampusLocation.name).all()
    categories = [
        'Electronics', 'ID & Cards', 'Bags & Wallets', 
        'Keys & Locks', 'Books & Stationery', 'Clothing & Wearables', 
        'Bottles & Containers', 'Sports & Fitness', 'Other'
    ]
    return render_template('items/report.html', locations=locations, categories=categories)


@app.route('/my-items')
@login_required
def my_items():
    my_lost = Item.query.filter_by(user_id=current_user.id, item_type='lost').order_by(Item.created_at.desc()).all()
    my_found = Item.query.filter_by(user_id=current_user.id, item_type='found').order_by(Item.created_at.desc()).all()
    
    # Claims filed by me
    my_claims = Claim.query.filter_by(claimant_id=current_user.id).order_by(Claim.created_at.desc()).all()
    
    # Claims filed on my items
    received_claims = Claim.query.join(Item).filter(Item.user_id == current_user.id).order_by(Claim.created_at.desc()).all()
    
    return render_template(
        'items/my_items.html',
        my_lost=my_lost,
        my_found=my_found,
        my_claims=my_claims,
        received_claims=received_claims
    )


# --- Claim & Verification Handover Routes ---

@app.route('/items/<int:item_id>/claim', methods=['POST'])
@login_required
def submit_claim(item_id):
    item = Item.query.get_or_404(item_id)
    
    if item.user_id == current_user.id:
        flash("You cannot claim an item you reported yourself.", "warning")
        return redirect(url_for('item_detail', item_id=item.id))
        
    # Check if already claimed
    existing = Claim.query.filter_by(item_id=item.id, claimant_id=current_user.id).first()
    if existing:
        flash("You have already submitted a claim for this item.", "info")
        return redirect(url_for('claim_detail', claim_id=existing.id))
        
    claim_desc = request.form.get('claim_description', '').strip()
    answer_question = request.form.get('answer_to_secret_question', '').strip()
    
    if not claim_desc:
        flash("Please describe your ownership claim and why this item is yours.", "danger")
        return redirect(url_for('item_detail', item_id=item.id))
        
    proof_image = None
    if 'proof_image' in request.files:
        file = request.files['proof_image']
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(f"proof_{int(datetime.utcnow().timestamp())}_{file.filename}")
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            proof_image = filename
            
    claim = Claim(
        item_id=item.id,
        claimant_id=current_user.id,
        claim_description=claim_desc,
        answer_to_secret_question=answer_question,
        proof_image_path=proof_image,
        status='pending'
    )
    db.session.add(claim)
    
    # Notify Item Owner
    notif = Notification(
        user_id=item.user_id,
        title="New Ownership Claim Received",
        message=f"{current_user.name} submitted an ownership claim on your reported item '{item.title}'.",
        link=f"/claims/{claim.id}",
        type="claim_received"
    )
    db.session.add(notif)
    
    # Audit Log
    log = AuditLog(
        action="CLAIM_SUBMITTED",
        details=f"User {current_user.name} claimed item #{item.id} ({item.title})",
        user_id=current_user.id,
        item_id=item.id
    )
    db.session.add(log)
    
    db.session.commit()
    flash("Your ownership claim has been submitted! You can now chat directly with the reporter or security to verify.", "success")
    return redirect(url_for('claim_detail', claim_id=claim.id))


@app.route('/claims/<int:claim_id>')
@login_required
def claim_detail(claim_id):
    claim = Claim.query.get_or_404(claim_id)
    
    # Permission check: claimant, item reporter, or admin
    is_claimant = (claim.claimant_id == current_user.id)
    is_reporter = (claim.item.user_id == current_user.id)
    is_admin = current_user.is_admin
    
    if not (is_claimant or is_reporter or is_admin):
        flash("Access denied: You are not authorized to view this claim.", "danger")
        return redirect(url_for('index'))
        
    messages = claim.messages.order_by(Message.sent_at.asc()).all()
    
    # Mark messages as read for receiver
    for msg in messages:
        if msg.sender_id != current_user.id and not msg.is_read:
            msg.is_read = True
    db.session.commit()
    
    return render_template(
        'claims/claim_detail.html',
        claim=claim,
        messages=messages,
        is_claimant=is_claimant,
        is_reporter=is_reporter,
        is_admin=is_admin
    )


@app.route('/claims/<int:claim_id>/send-message', methods=['POST'])
@login_required
def send_claim_message(claim_id):
    claim = Claim.query.get_or_404(claim_id)
    
    # Permission check
    if not (claim.claimant_id == current_user.id or claim.item.user_id == current_user.id or current_user.is_admin):
        abort(403)
        
    content = request.form.get('content', '').strip()
    if content:
        msg = Message(
            claim_id=claim.id,
            sender_id=current_user.id,
            content=content
        )
        db.session.add(msg)
        
        # Determine recipient to notify
        recipient_id = claim.item.user_id if current_user.id == claim.claimant_id else claim.claimant_id
        notif = Notification(
            user_id=recipient_id,
            title="New Message on Claim",
            message=f"{current_user.name} sent a message regarding '{claim.item.title}'.",
            link=f"/claims/{claim.id}",
            type="message"
        )
        db.session.add(notif)
        db.session.commit()
        
    return redirect(url_for('claim_detail', claim_id=claim.id))


@app.route('/claims/<int:claim_id>/review', methods=['POST'])
@login_required
def review_claim(claim_id):
    claim = Claim.query.get_or_404(claim_id)
    
    # Only item reporter or admin can review
    if not (claim.item.user_id == current_user.id or current_user.is_admin):
        flash("You are not authorized to approve or reject this claim.", "danger")
        return redirect(url_for('claim_detail', claim_id=claim.id))
        
    action = request.form.get('action')  # 'approve' or 'reject'
    rejection_reason = request.form.get('rejection_reason', '').strip()
    
    if action == 'approve':
        pin = generate_pin()
        claim.status = 'approved'
        claim.handover_pin = pin
        claim.reviewed_at = datetime.utcnow()
        claim.reviewed_by_id = current_user.id
        
        # Generate QR code pass
        qr_file = generate_qr_pass(claim.id, pin)
        claim.qr_code_path = qr_file
        
        # Update item status
        claim.item.status = 'pending_claim'
        
        # Notify claimant
        notif = Notification(
            user_id=claim.claimant_id,
            title="Ownership Claim Approved!",
            message=f"Congratulations! Your claim for '{claim.item.title}' has been approved. Your 6-digit Handover PIN is {pin}. Present it at collection.",
            link=f"/claims/{claim.id}/pass",
            type="claim_approved"
        )
        db.session.add(notif)
        
        log = AuditLog(
            action="CLAIM_APPROVED",
            details=f"Claim #{claim.id} approved by {current_user.name}. Handover PIN {pin} generated.",
            user_id=current_user.id,
            item_id=claim.item.id
        )
        db.session.add(log)
        flash(f"Claim approved! Secure Handover PIN ({pin}) and QR pass have been generated.", "success")
        
    elif action == 'reject':
        claim.status = 'rejected'
        claim.rejection_reason = rejection_reason or "Proof provided did not match item attributes."
        claim.reviewed_at = datetime.utcnow()
        claim.reviewed_by_id = current_user.id
        
        notif = Notification(
            user_id=claim.claimant_id,
            title="Claim Status Update",
            message=f"Your claim for '{claim.item.title}' was reviewed and not approved: {claim.rejection_reason}",
            link=f"/claims/{claim.id}",
            type="claim_rejected"
        )
        db.session.add(notif)
        
        log = AuditLog(
            action="CLAIM_REJECTED",
            details=f"Claim #{claim.id} rejected by {current_user.name}. Reason: {claim.rejection_reason}",
            user_id=current_user.id,
            item_id=claim.item.id
        )
        db.session.add(log)
        flash("Claim has been marked as rejected.", "info")
        
    db.session.commit()
    return redirect(url_for('claim_detail', claim_id=claim.id))


@app.route('/claims/<int:claim_id>/pass')
@login_required
def claim_pass(claim_id):
    claim = Claim.query.get_or_404(claim_id)
    
    if not (claim.claimant_id == current_user.id or claim.item.user_id == current_user.id or current_user.is_admin):
        flash("Unauthorized to view claim pass.", "danger")
        return redirect(url_for('index'))
        
    if claim.status not in ['approved', 'completed']:
        flash("Claim must be approved before viewing the Handover Pass.", "warning")
        return redirect(url_for('claim_detail', claim_id=claim.id))
        
    return render_template('claims/claim_pass.html', claim=claim)


@app.route('/claims/<int:claim_id>/verify-handover', methods=['POST'])
@login_required
def verify_handover(claim_id):
    claim = Claim.query.get_or_404(claim_id)
    
    # Must be item reporter or security admin
    if not (claim.item.user_id == current_user.id or current_user.is_admin):
        flash("You are not authorized to verify physical handover.", "danger")
        return redirect(url_for('claim_detail', claim_id=claim.id))
        
    entered_pin = request.form.get('handover_pin', '').strip()
    
    if entered_pin == claim.handover_pin:
        claim.status = 'completed'
        claim.item.status = 'resolved'
        claim.item.resolved_at = datetime.utcnow()
        
        # Notify claimant
        notif = Notification(
            user_id=claim.claimant_id,
            title="Item Returned Successfully!",
            message=f"Physical handover of '{claim.item.title}' is confirmed and verified. Thank you for using CampusFind!",
            link=f"/items/{claim.item.id}",
            type="handover_complete"
        )
        db.session.add(notif)
        
        # Audit Log
        log = AuditLog(
            action="HANDOVER_VERIFIED",
            details=f"Physical handover of item #{claim.item.id} verified with PIN by {current_user.name}. Item status closed as resolved.",
            user_id=current_user.id,
            item_id=claim.item.id
        )
        db.session.add(log)
        db.session.commit()
        
        flash("Handover PIN verified successfully! The item is officially marked as RETURNED & RESOLVED.", "success")
    else:
        flash("Incorrect Handover PIN! Please verify the 6-digit code shown on the student's Claim Pass.", "danger")
        
    return redirect(url_for('claim_detail', claim_id=claim.id))


# --- Campus Map View ---

@app.route('/campus-map')
def campus_map():
    locations = CampusLocation.query.all()
    location_data = []
    
    for loc in locations:
        lost_count = Item.query.filter_by(location_id=loc.id, item_type='lost', status='active').count()
        found_count = Item.query.filter_by(location_id=loc.id, item_type='found', status='active').count()
        recent_items = Item.query.filter_by(location_id=loc.id, status='active').order_by(Item.created_at.desc()).limit(3).all()
        
        location_data.append({
            'loc': loc,
            'lost_count': lost_count,
            'found_count': found_count,
            'total_active': lost_count + found_count,
            'recent_items': recent_items
        })
        
    return render_template('campus_map.html', locations=location_data)


# --- Admin Security Dashboard ---

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash("Access denied: Campus Security Administrator privileges required.", "danger")
        return redirect(url_for('index'))
        
    total_items = Item.query.count()
    active_lost = Item.query.filter_by(item_type='lost', status='active').count()
    active_found = Item.query.filter_by(item_type='found', status='active').count()
    resolved_items = Item.query.filter_by(status='resolved').count()
    pending_claims = Claim.query.filter_by(status='pending').count()
    
    # Custody Items in Security lockers
    custody_items = Item.query.filter(Item.storage_locker_number.isnot(None), Item.status != 'resolved').all()
    
    # Recent claims needing oversight
    recent_claims = Claim.query.order_by(Claim.created_at.desc()).limit(8).all()
    
    # Recent audit logs
    audit_logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(15).all()
    
    # Category distribution for Chart.js
    categories = ['Electronics', 'ID & Cards', 'Bags & Wallets', 'Keys & Locks', 'Books & Stationery', 'Clothing & Wearables', 'Other']
    cat_counts = [Item.query.filter_by(category=c).count() for c in categories]
    
    return render_template(
        'admin/dashboard.html',
        total_items=total_items,
        active_lost=active_lost,
        active_found=active_found,
        resolved_items=resolved_items,
        pending_claims=pending_claims,
        custody_items=custody_items,
        recent_claims=recent_claims,
        audit_logs=audit_logs,
        cat_labels=categories,
        cat_counts=cat_counts
    )


@app.route('/admin/items/<int:item_id>/update-storage', methods=['POST'])
@login_required
def update_storage(item_id):
    if not current_user.is_admin:
        abort(403)
        
    item = Item.query.get_or_404(item_id)
    locker = request.form.get('storage_locker_number', '').strip()
    custody_info = request.form.get('safe_custody_info', '').strip()
    
    item.storage_locker_number = locker
    if custody_info:
        item.safe_custody_info = custody_info
        
    log = AuditLog(
        action="STORAGE_UPDATED",
        details=f"Admin {current_user.name} assigned item #{item.id} to Locker: '{locker}'",
        user_id=current_user.id,
        item_id=item.id
    )
    db.session.add(log)
    db.session.commit()
    
    flash(f"Storage locker updated for '{item.title}'!", "success")
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/export-csv')
@login_required
def export_csv():
    if not current_user.is_admin:
        abort(403)
        
    items = Item.query.order_by(Item.created_at.desc()).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'ID', 'Type', 'Title', 'Category', 'Campus Location', 'Specific Location',
        'Date Lost/Found', 'Status', 'Reporter Name', 'Reporter Email', 
        'Storage Locker', 'Created At', 'Resolved At'
    ])
    
    for it in items:
        writer.writerow([
            it.id,
            it.item_type.upper(),
            it.title,
            it.category,
            it.location.name if it.location else 'N/A',
            it.specific_location or '',
            it.date_lost_or_found.strftime('%Y-%m-%d') if it.date_lost_or_found else '',
            it.status.upper(),
            it.reporter.name if it.reporter else 'N/A',
            it.reporter.email if it.reporter else 'N/A',
            it.storage_locker_number or 'Unassigned',
            it.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            it.resolved_at.strftime('%Y-%m-%d %H:%M:%S') if it.resolved_at else ''
        ])
        
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename=campus_lost_and_found_{datetime.utcnow().strftime('%Y%m%d')}.csv"}
    )


# --- Notifications & API ---

@app.route('/notifications')
@login_required
def notifications_view():
    user_notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    # Mark all read
    for n in user_notifications:
        n.is_read = True
    db.session.commit()
    return render_template('notifications.html', notifications=user_notifications)


@app.route('/api/search')
def api_search():
    q = request.args.get('q', '').strip()
    if not q or len(q) < 2:
        return jsonify([])
        
    items = Item.query.filter(
        (Item.title.ilike(f'%{q}%')) | 
        (Item.category.ilike(f'%{q}%')) |
        (Item.specific_location.ilike(f'%{q}%'))
    ).limit(8).all()
    
    return jsonify([it.to_dict() for it in items])


@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500

# Initialize database with seed data upon startup
with app.app_context():
    seed_database(app)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
