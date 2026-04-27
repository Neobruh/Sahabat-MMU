from flask import Flask, request, jsonify
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User
import re

app = Flask(__name__)
app.config.from_pyfile("config.py")

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)

# Load user for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# MMU Email validation 
def is_valid_mmu_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@student\.mmu\.edu\.my$'
    return re.match(pattern, email)

#  Register
@app.route("/register", methods=["POST"])
def register():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    if not is_valid_mmu_email(email):
        return jsonify({"error": "Only @student.mmu.edu.my emails allowed"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "User already exists"}), 400

    hashed_pw = generate_password_hash(password)

    new_user = User(email=email, password=hashed_pw)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "User registered successfully"})

#  Login
@app.route("/login", methods=["POST"])
def login():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    user = User.query.filter_by(email=email).first()

    if not user or not check_password_hash(user.password, password):
        return jsonify({"error": "Invalid credentials"}), 401

    login_user(user)
    return jsonify({"message": "Logged in successfully"})

#  Logout
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return jsonify({"message": "Logged out successfully"})

#  Protected route example
@app.route("/dashboard")
@login_required
def dashboard():
    return jsonify({"message": f"Welcome {current_user.email}"})

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)