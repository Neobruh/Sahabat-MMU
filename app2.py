from flask import Flask, render_template_string, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
import re

from db import db, User   # 👈 import database from db.py

# -----------------------
# App setup
# -----------------------
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# -----------------------
# Helper function
# -----------------------
def is_mmu_email(email):
    return bool(re.match(r"^[a-zA-Z0-9._%+-]+@mmu\.edu\.my$", email))

# -----------------------
# Routes
# -----------------------

@app.route('/')
def home():
    if 'user_id' in session:
        return render_template_string("""
            <h2>Welcome!</h2>
            <p>You are logged in.</p>
            <a href="/logout">Logout</a>
        """)
    return render_template_string("""
        <h2>Home</h2>
        <a href="/login">Login</a> |
        <a href="/register">Register</a>
    """)

# -----------------------
# USERS (CRUD)
# -----------------------

@app.route('/users', methods=['GET'])
def get_users():
    users = User.query.all()
    return [{"id": u.id, "username": u.username} for u in users]

@app.route('/users/<int:id>', methods=['GET'])
def get_user(id):
    user = User.query.get(id)
    if not user:
        return {"message": "User not found"}, 404
    return {"id": user.id, "username": user.username}

@app.route('/users/<int:id>', methods=['PUT'])
def update_user(id):
    user = User.query.get(id)
    if not user:
        return {"message": "User not found"}, 404

    data = request.get_json()
    user.username = data.get("username", user.username)

    if "password" in data:
        user.password = generate_password_hash(data["password"])

    db.session.commit()
    return {"message": "User updated"}

@app.route('/users/<int:id>', methods=['DELETE'])
def delete_user(id):
    user = User.query.get(id)
    if not user:
        return {"message": "User not found"}, 404

    db.session.delete(user)
    db.session.commit()
    return {"message": "User deleted"}

# -----------------------
# REGISTER
# -----------------------

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form.get('email')
        password = generate_password_hash(request.form['password'])

        if not is_mmu_email(email):
            return "Please use your official MMU student email."

        user = User(username=username, email=email, password=password)
        db.session.add(user)
        db.session.commit()

        return redirect(url_for('login'))

    return render_template_string("""
        <h2>Register</h2>
        <form method="POST">
            <input name="username" placeholder="Username" required><br>
            <input name="email" placeholder="MMU Email" required><br>
            <input name="password" type="password" placeholder="Password" required><br>
            <button type="submit">Register</button>
        </form>
    """)

# -----------------------
# LOGIN
# -----------------------

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            return redirect(url_for('home'))

        return "Invalid credentials"

    return render_template_string("""
        <h2>Login</h2>
        <form method="POST">
            <input name="username" placeholder="Username" required><br>
            <input name="password" type="password" required><br>
            <button type="submit">Login</button>
        </form>
    """)

# -----------------------
# LOGOUT
# -----------------------

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# -----------------------
# DISCOVERY
# -----------------------

@app.route('/discovery')
def discovery():
    return render_template_string("""
        <h2>Discovery Page</h2>
        <p>Find other MMU students here.</p>
    """)

# -----------------------
# RUN APP
# -----------------------

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)