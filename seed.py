import random
from datetime import datetime, timedelta
from faker import Faker

# Import your database instance and models
# Adjust these imports based on your actual file structure (e.g., from app import db, User, Post)
from app import db, User, Post, PREDEFINED_INTERESTS, FACULTY_COURSES

fake = Faker()

def seed_database(num_users=20, posts_per_user=3):
    print("Initializing database seeding...")
    
    # 1. Clear existing data
    db.drop_all()
    db.create_all()
    print("Database cleared and rebuilt.")

    # 2. Create the Admin Demo Account
    print("Creating admin demo account...")
    admin_user = User(
        username="admin_demo",
        email="admin@demo.com",
        bio="System Administrator Demo Account.",
        profile_pic="https://api.dicebear.com/7.x/adventurer/svg?seed=admin_demo",
        interests="Coding, Debate",
        faculty="Faculty of Computing & Informatics",
        course="Bachelor of Computer Science (Hons.)",
        is_admin=True,      # Granted admin privileges
        is_club=False,
        is_banned=False
    )
    admin_user.set_password("adminpass123")
    db.session.add(admin_user)
    
    # Separate lists to keep track of regular users and clubs
    created_users = [admin_user]  # Add admin to users list so they can post/join clubs too
    created_clubs = []

    # 3. Create Fake Users & Clubs
    for _ in range(num_users):
        is_club = random.random() < 0.2
        
        if is_club:
            username = fake.company() + " Club"
            faculty = ""
            course = ""
            interests = ""
            bio = f"The official account for {username}. Connecting students through shared passions!"
        else:
            username = fake.user_name()
            # Prevent accidental username collision with our admin account
            if username == "admin_demo":
                username = username + "_1"
                
            faculty = random.choice(list(FACULTY_COURSES.keys()))
            course = random.choice(FACULTY_COURSES[faculty])
            
            user_interests = random.sample(PREDEFINED_INTERESTS, k=random.randint(2, 4))
            interests = ", ".join(user_interests)
            bio = fake.sentence(nb_words=12)

        email = fake.unique.email()
        
        user = User(
            username=username,
            email=email,
            bio=bio,
            profile_pic=f"https://api.dicebear.com/7.x/adventurer/svg?seed={username}",
            interests=interests,
            faculty=faculty,
            course=course,
            is_admin=False,
            is_club=is_club,
            is_banned=False
        )
        user.set_password("password123")
        db.session.add(user)
        
        if is_club:
            created_clubs.append(user)
        else:
            created_users.append(user)

    db.session.commit()
    print(f"Successfully created accounts (including admin_demo) and {len(created_clubs)} clubs.")

    # 4. Create Interconnected Club Memberships
    if created_clubs and created_users:
        for user in created_users:
            joined_clubs = random.sample(created_clubs, k=random.randint(1, min(3, len(created_clubs))))
            user.clubs.extend(joined_clubs)
        db.session.commit()
        print("Generated random club memberships.")

    # 5. Create Fake Posts
    all_accounts = created_users + created_clubs
    
    for account in all_accounts:
        for _ in range(random.randint(1, posts_per_user)):
            post_type = "club" if account.is_club else "main"
            random_days_ago = random.randint(0, 30)
            created_at_time = datetime.utcnow() - timedelta(days=random_days_ago)

            post = Post(
                type=post_type,
                author_id=account.id,
                author_name=account.username,
                content=fake.paragraph(nb_sentences=random.randint(2, 5)),
                image_url=random.choice([None, "https://picsum.photos/600/400"]),
                created_at=created_at_time,
                is_visible=True
            )
            db.session.add(post)

    db.session.commit()
    print("Successfully generated posts.")
    print("-" * 50)
    print("Seeding complete!")
    print("ADMIN LOGIN -> Username: 'admin_demo' | Password: 'adminpass123'")
    print("USER LOGIN  -> Use any fake username | Password: 'password123'")
    print("-" * 50)

    db.session.commit()
    print("Successfully generated posts.")
    print("Seeding complete! You can now log in to any account using password: 'password123'")

if __name__ == "__main__":
    # If executing this inside a standalone script, wrap it in your Flask app context
    from app import app
    with app.app_context():
        seed_database()