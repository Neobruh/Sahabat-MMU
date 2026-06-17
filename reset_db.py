"""
Drops ALL tables and recreates the database from scratch.
Creates two starter accounts: 'demo' and 'admin_demo'.

Usage: python reset_db.py
Place in the same folder as app.py before running.
"""

from app import app, db, User

with app.app_context():
    print("⚠️  Dropping all tables...")
    db.drop_all()

    print("🔨 Recreating tables...")
    db.create_all()

    print("👤 Creating starter accounts...")

    demo = User(username="demo")
    demo.set_password("password123")
    # Set email if the model requires it
    if hasattr(demo, 'email'):
        demo.email = "demo@sahabat.mmu"

    admin = User(username="admin_demo", is_admin=True)
    admin.set_password("admin123")
    if hasattr(admin, 'email'):
        admin.email = "admin@sahabat.mmu"

    db.session.add_all([demo, admin])
    db.session.commit()

    print("\n✅ Fresh database ready!")
    print("   • demo        / password123")
    print("   • admin_demo  / admin123  (admin)")