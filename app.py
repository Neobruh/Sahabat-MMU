import os
from datetime import datetime
from flask import Flask, render_template, url_for, flash, redirect, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, current_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'mmu_sahabat_2026_key'

# Absolute path for the database to prevent errors
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'instance', 'sahabat.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- DATABASE MODELS ---
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    major = db.Column(db.String(100), default="Creative Multimedia")
    campus = db.Column(db.String(50), default="Cyberjaya")
    bio = db.Column(db.Text, nullable=True)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    sender = db.relationship('User', foreign_keys=[sender_id])
    receiver = db.relationship('User', foreign_keys=[receiver_id])

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- AUTHENTICATION ROUTES ---
@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        if not email.endswith('@student.mmu.edu.my'):
            flash('Must use a valid MMU Student Email!', 'danger')
            return redirect(url_for('register'))
        
        hashed_pw = generate_password_hash(request.form.get('password'))
        user = User(
            username=request.form.get('username'), email=email, password=hashed_pw,
            major=request.form.get('major'), campus=request.form.get('campus'),
            bio=f"Hey! I'm a {request.form.get('major')} student."
        )
        db.session.add(user)
        db.session.commit()
        flash('Account created! You can now login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form.get('email')).first()
        if user and check_password_hash(user.password, request.form.get('password')):
            login_user(user)
            return redirect(url_for('discovery'))
        flash('Login Unsuccessful. Check email and password', 'danger')
    return render_template('login.html')

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# --- CORE APP ROUTES ---
@app.route("/")
@app.route("/discovery")
@login_required
def discovery():
    major_filter = request.args.get('major', 'All')
    campus_filter = request.args.get('campus', 'All')
    
    query = User.query.filter(User.id != current_user.id)
    if major_filter != 'All':
        query = query.filter_by(major=major_filter)
    if campus_filter != 'All':
        query = query.filter_by(campus=campus_filter)
        
    students = query.all()
    return render_template('discovery.html', students=students)

@app.route("/inbox")
@login_required
def inbox():
    # Show all users to chat with (simplified for now)
    users = User.query.filter(User.id != current_user.id).all()
    return render_template('inbox.html', users=users)

@app.route("/chat/<int:user_id>")
@login_required
def chat(user_id):
    receiver = User.query.get_or_404(user_id)
    # Fetch conversation history
    messages = Message.query.filter(
        ((Message.sender_id == current_user.id) & (Message.receiver_id == user_id)) |
        ((Message.sender_id == user_id) & (Message.receiver_id == current_user.id))
    ).order_by(Message.timestamp.asc()).all()
    return render_template('chat.html', receiver=receiver, messages=messages)

@app.route("/send_message/<int:receiver_id>", methods=['POST'])
@login_required
def send_message(receiver_id):
    content = request.form.get('message')
    if content:
        msg = Message(sender_id=current_user.id, receiver_id=receiver_id, content=content)
        db.session.add(msg)
        db.session.commit()
    return redirect(url_for('chat', user_id=receiver_id))

if __name__ == '__main__':
    with app.app_context():
        instance_path = os.path.join(basedir, 'instance')
        if not os.path.exists(instance_path):
            os.makedirs(instance_path)
        db.create_all()
    app.run(debug=True)