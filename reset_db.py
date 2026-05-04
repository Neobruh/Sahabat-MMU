from app2 import app
from db import db

with app.app_context():
    db.drop_all()
    db.create_all()

print("Database reset complete!")