"""
reset_db.py — run once from your project root:
    python reset_db.py

What it does:
  - Deletes ALL data from every table
  - Re-creates demo and admin_demo users with email addresses
  - Leaves the schema intact (no need to delete sahabat.db)
"""

from app import app, db
from app import User, Post, Like, Comment, DiscoveryLike, DiscoveryMatch, CommentNotif, LikeNotif

with app.app_context():

    # ── 1. Wipe all tables in safe order (children before parents) ──
    LikeNotif.query.delete()
    CommentNotif.query.delete()
    DiscoveryMatch.query.delete()
    DiscoveryLike.query.delete()
    Like.query.delete()
    Comment.query.delete()
    Post.query.delete()

    # club_memberships is an association table — clear it via raw SQL
    db.session.execute(db.text("DELETE FROM club_memberships"))

    User.query.delete()
    db.session.commit()
    print("✓ All tables cleared.")

    # ── 2. Re-create demo user ──
    demo = User(
        username    = "demo",
        email       = "demo@student.mmu.edu.my",
        bio         = "Just a demo student exploring Sahabat.",
        profile_pic = "/static/images/profile-placeholder.png",
        interests   = "music, coding, hiking",
    )
    demo.set_password("password123")
    db.session.add(demo)

    # ── 3. Re-create admin_demo user ──
    admin = User(
        username    = "admin_demo",
        email       = "admin@student.mmu.edu.my",
        profile_pic = "/static/images/profile-placeholder.png",
        is_admin    = True,
    )
    admin.set_password("adminpass123")
    db.session.add(admin)

    db.session.commit()
    print("✓ demo and admin_demo recreated with email fields.")
    print("\nDone! You can now start the app normally.")