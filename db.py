from flask import Flask, render_template_string, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# -----------------------
# Database Model
# -----------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

# -----------------------
# Routes
# -----------------------

# Home page
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

# Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])

        user = User(username=username, password=password)
        db.session.add(user)
        db.session.commit()

        return redirect(url_for('login'))

    return render_template_string("""
        <h2>Register</h2>
        <form method="POST">
            <input name="username" placeholder="Username" required><br>
            <input name="password" type="password" placeholder="Password" required><br>
            <button type="submit">Register</button>
        </form>
    """)

# Login
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
            <input name="password" type="password" placeholder="Password" required><br>
            <button type="submit">Login</button>
        </form>
    """)

# Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# -----------------------
# Run App
# -----------------------
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
