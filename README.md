# Sahabat

A Flask-based Facebook/Tinder hybrid web app for university students.

## Features
- Login (`/login`) and Sign Up (`/signup`)
- Topbar navigation: Main Page, Club, Discovery
- Main Page / Club — post feeds with profile pictures, images, likes, and comments
- Click any profile picture or username to view that user's profile
- Top-right dropdown menu: View Profile, Customize Profile, Settings, Toggle Dark Mode, Sign Out
- Dark mode (persisted via browser localStorage)
- Discovery — swipe-style Like/Pass with a basic similarity score algorithm
- SQLite database (via Flask-SQLAlchemy) for users and posts

## Setup
1. Create a virtual environment (optional but recommended):
   ```
   python -m venv venv
   venv\Scripts\activate      (Windows)
   source venv/bin/activate   (Mac/Linux)
   ```
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Run the app:
   ```
   python app.py
   ```
   On first run, this creates `instance/sahabat.db` and seeds demo data.
4. Open http://127.0.0.1:5000 in your browser.

## Demo login
- Username: `demo`
- Password: `password123`

(Other seeded accounts: `Aisyah`, `Daniel`, `Photography Club`, `Debate Society` — all use password `password123`.)

## File Structure
```
sahabat/
├── app.py
├── requirements.txt
├── README.md
├── instance/
│   └── sahabat.db          # created automatically on first run
├── static/
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   └── main.js          # dropdown + dark mode logic
│   └── images/
│       ├── logo-placeholder.png
│       ├── profile-placeholder.png
│       └── post-placeholder.jpg
└── templates/
    ├── base.html             # topbar, dropdown, dark mode hook
    ├── login.html
    ├── signup.html
    ├── main.html
    ├── club.html
    ├── discovery.html
    ├── profile.html          # view a user's profile + their posts
    ├── edit_profile.html      # customize bio, interests, profile pic
    ├── settings.html          # change password (placeholder for more)
    └── _post_card.html        # shared post card (pic, image, like, comments)
```

## Database Schema (SQLite via SQLAlchemy)

```sql
-- users
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    bio TEXT DEFAULT '',
    profile_pic TEXT DEFAULT '/static/images/profile-placeholder.png',
    interests TEXT DEFAULT ''   -- comma-separated
);

-- posts (used for both Main Page and Club posts via `type`)
CREATE TABLE posts (
    id INTEGER PRIMARY KEY,
    type TEXT NOT NULL,           -- 'main' or 'club'
    author_id INTEGER REFERENCES users(id),
    author_name TEXT NOT NULL,
    content TEXT NOT NULL,
    image_url TEXT,
    created_at DATETIME
);

-- likes
CREATE TABLE likes (
    id INTEGER PRIMARY KEY,
    post_id INTEGER REFERENCES posts(id),
    username TEXT NOT NULL,
    UNIQUE(post_id, username)
);

-- comments
CREATE TABLE comments (
    id INTEGER PRIMARY KEY,
    post_id INTEGER REFERENCES posts(id),
    username TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at DATETIME
);
```

## Notes / Placeholders
- Passwords are hashed with Werkzeug's `generate_password_hash`/`check_password_hash`.
- Profile pictures and post images are referenced by URL/path (text field) —
  add a file upload route later to let users upload real images.
- `DISCOVERY_PROFILES` and `calculate_similarity()` are still placeholders;
  wire up real candidate users + matching against `interests` later.
- Settings page only supports password change — extend with notification
  preferences, privacy, account deletion, etc.
- Dark mode preference is stored in the browser (`localStorage`), not the DB.
- To reset the database, stop the server and delete `instance/sahabat.db`,
  then restart — it will be recreated and reseeded.
