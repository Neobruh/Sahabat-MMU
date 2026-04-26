from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)  # Must be @mmu.edu.my
    major = db.Column(db.String(100))
    gender = db.Column(db.String(10))
    merit_points = db.Column(db.Integer, default=0)  # Merit points for study sessions [cite: 104]
    is_verified = db.Column(db.Boolean, default=False)
    buddy_mode_enabled = db.Column(db.Boolean, default=False)  # Group interaction toggle [cite: 64]
    
    def __repr__(self):
        return f'<User {self.full_name}>'