# =============================================================
# SAHABAT
# =============================================================

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit, join_room

from dotenv import load_dotenv

from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from datetime import datetime
import os
import random
import requests

# =============================================================
# CONFIGURATION
# =============================================================

app = Flask(__name__)
socketio = SocketIO(app, async_mode='threading', cors_allowed_origins='*')
app.secret_key = "SAHABATMMU_26_MINIIT"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///sahabat.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*")

UPLOAD_FOLDER = os.path.join("static", "images", "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK_URL")

# =============================================================
# DATABASE MODELS
# =============================================================

club_memberships = db.Table(
    "club_memberships",
    db.Column("user_id", db.Integer, db.ForeignKey("users.id"), primary_key=True),
    db.Column("club_id", db.Integer, db.ForeignKey("users.id"), primary_key=True),
)

class User(db.Model):
    __tablename__ = "users"

    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(50), unique=True, nullable=False)
    email         = db.Column(db.String(120), unique=True, nullable=False, default="")
    password_hash = db.Column(db.String(255), nullable=False)
    bio           = db.Column(db.String(255), default="")
    profile_pic   = db.Column(db.String(255), default="/static/images/profile-placeholder.png")
    interests     = db.Column(db.String(255), default="")
    faculty       = db.Column(db.String(100), default="")
    course        = db.Column(db.String(100), default="")
    is_admin      = db.Column(db.Boolean, default=False)   # can access admin panel
    is_club       = db.Column(db.Boolean, default=False)   # can post in club page
    is_banned     = db.Column(db.Boolean, default=False)   # blocked from logging in
    clubs = db.relationship(
        "User",
        secondary=club_memberships,
        primaryjoin=id == club_memberships.c.user_id,
        secondaryjoin=id == club_memberships.c.club_id,
        backref="members"
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def interest_list(self):
        if not self.interests:
            return []
        return [i.strip() for i in self.interests.split(",") if i.strip()]


class Post(db.Model):
    __tablename__ = "posts"

    id          = db.Column(db.Integer, primary_key=True)
    type        = db.Column(db.String(10), nullable=False)   # "main" or "club"
    author_id   = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    author_name = db.Column(db.String(50), nullable=False)
    content     = db.Column(db.Text, nullable=False)
    image_url   = db.Column(db.String(255), nullable=True)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    is_visible  = db.Column(db.Boolean, default=True)        # False = hidden by admin

    author   = db.relationship("User", backref="posts")
    likes    = db.relationship("Like", backref="post", cascade="all, delete-orphan")
    comments = db.relationship("Comment", backref="post", cascade="all, delete-orphan",
                               order_by="Comment.created_at")

    def liked_by(self, username):
        return any(like.username == username for like in self.likes)


class Like(db.Model):
    __tablename__ = "likes"

    id       = db.Column(db.Integer, primary_key=True)
    post_id  = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=False)
    username = db.Column(db.String(50), nullable=False)

    __table_args__ = (db.UniqueConstraint("post_id", "username", name="uq_post_user_like"),)


class Comment(db.Model):
    __tablename__ = "comments"

    id         = db.Column(db.Integer, primary_key=True)
    post_id    = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=False)
    username   = db.Column(db.String(50), nullable=False)
    content    = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class DiscoveryLike(db.Model):
    __tablename__ = "discovery_likes"

    id          = db.Column(db.Integer, primary_key=True)
    from_user   = db.Column(db.String(50), nullable=False)   # who clicked ♥
    to_user     = db.Column(db.String(50), nullable=False)   # who received it
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    seen        = db.Column(db.Boolean, default=False)       # for notification badge

    __table_args__ = (db.UniqueConstraint("from_user", "to_user", name="uq_disc_like"),)


class DiscoveryMatch(db.Model):
    __tablename__ = "discovery_matches"

    id         = db.Column(db.Integer, primary_key=True)
    user_a     = db.Column(db.String(50), nullable=False)
    user_b     = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    seen_by_a  = db.Column(db.Boolean, default=False)
    seen_by_b  = db.Column(db.Boolean, default=False)

class CommentNotif(db.Model):
    __tablename__ = "comment_notifs"
 
    id              = db.Column(db.Integer, primary_key=True)
    post_author     = db.Column(db.String(50), nullable=False)   # who owns the post
    commenter       = db.Column(db.String(50), nullable=False)   # who left the comment
    post_id         = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=False)
    comment_content = db.Column(db.String(300), nullable=False)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)
    seen            = db.Column(db.Boolean, default=False)


class LikeNotif(db.Model):
    __tablename__ = "like_notifs"

    id          = db.Column(db.Integer, primary_key=True)
    post_author = db.Column(db.String(50), nullable=False)   # who owns the post
    liker       = db.Column(db.String(50), nullable=False)   # who liked it
    post_id     = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=False)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    seen        = db.Column(db.Boolean, default=False)

    __table_args__ = (db.UniqueConstraint("post_id", "liker", name="uq_post_liker_notif"),)

class FriendRequestNotif(db.Model):
    __tablename__ = "friend_request_notifs"

    id          = db.Column(db.Integer, primary_key=True)
    to_user     = db.Column(db.String(50), nullable=False)   # who receives the notif
    from_user   = db.Column(db.String(50), nullable=False)   # who sent the request
    notif_type  = db.Column(db.String(10), nullable=False)   # "request" or "accepted"
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    seen        = db.Column(db.Boolean, default=False)

class FriendRequest(db.Model):
    __tablename__ = "friend_requests"

    id         = db.Column(db.Integer, primary_key=True)
    from_user  = db.Column(db.String(50), nullable=False)
    to_user    = db.Column(db.String(50), nullable=False)
    status     = db.Column(db.String(10), default="pending")  # pending, accepted, declined
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    seen       = db.Column(db.Boolean, default=False)

    __table_args__ = (db.UniqueConstraint("from_user", "to_user", name="uq_friend_request"),)


class Friendship(db.Model):
    __tablename__ = "friendships"

    id         = db.Column(db.Integer, primary_key=True)
    user_a     = db.Column(db.String(50), nullable=False)
    user_b     = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint("user_a", "user_b", name="uq_friendship"),)

    @staticmethod
    def exists_between(u1, u2):
        return Friendship.query.filter(
            ((Friendship.user_a == u1) & (Friendship.user_b == u2)) |
            ((Friendship.user_a == u2) & (Friendship.user_b == u1))
        ).first()

    @staticmethod
    def create(u1, u2):
        if not Friendship.exists_between(u1, u2):
            db.session.add(Friendship(user_a=u1, user_b=u2))


class Message(db.Model):
    __tablename__ = "messages"

    id         = db.Column(db.Integer, primary_key=True)
    sender     = db.Column(db.String(50), nullable=False)
    recipient  = db.Column(db.String(50), nullable=False)
    content    = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    read       = db.Column(db.Boolean, default=False)

# =============================================================
# HELPERS & UTILITIES
# =============================================================

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def current_user():
    if "username" not in session:
        return None
    return User.query.filter_by(username=session["username"]).first()


def login_required_redirect():
    if "username" not in session:
        return redirect(url_for("login"))
    return None


def save_uploaded_image(file):
    if file and file.filename and allowed_file(file.filename):
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        filename = secure_filename(file.filename)
        file.save(os.path.join(UPLOAD_FOLDER, filename))
        return f"/static/images/uploads/{filename}"
    return None

def get_friends(username):
    rows = Friendship.query.filter(
        (Friendship.user_a == username) | (Friendship.user_b == username)
    ).all()
    return [r.user_b if r.user_a == username else r.user_a for r in rows]

@app.context_processor
def inject_current_user():
    return {"current_user_obj": current_user()}

# =============================================================
# DISCOVERY DATA
# =============================================================

PREDEFINED_INTERESTS = [
    "Music", "Coding", "Hiking", "Gaming", "Photography",
    "Art", "Reading", "Football", "Basketball", "Badminton",
    "Cooking", "Fitness", "Dance", "Film", "Travel",
    "Debate", "Volunteering", "Entrepreneurship", "Design", "Anime",
]

FACULTY_COURSES = {
    "Faculty of Computing & Informatics": [
        "Foundation in Computing",
        "Diploma in Information Technology",
        "Bachelor of Computer Science (Hons.)",
        "Bachelor of Information Technology (Honours)",
        "Master of Computing (By Research)",
        "Doctor of Philosophy in Computing (By Research)",
        "Master in Computer Science (By Coursework)",
        "Master in Computer Science – ODL (By Coursework)",
    ],

    "Faculty of Artificial Intelligence & Engineering": [
        "Foundation in Engineering",
        "Bachelor of Science (Honours) in Applied Artificial Intelligence",
        "Bachelor of Science (Honours) in Intelligent Robotics",
        "Bachelor of Electrical and Electronics Engineering with Honours",
        "Bachelor of Engineering (Hons.) (Electronics)",
        "Bachelor of Engineering (Hons.) (Electronics majoring in Telecommunications)",
        "Bachelor of Engineering (Hons.) (Electronics majoring in Computer)",
        "Master of Engineering Science (By Research)",
        "Doctor of Philosophy in Engineering (By Research)",
        "Master of Science in Engineering Business Management (By Coursework)",
        "Master of Engineering in Telecommunications (By Coursework)",
    ],

    "Faculty of Management": [
        "Foundation in Management",
        "Diploma in Management",
        "Diploma in Finance",
        "Bachelor in Accounting (Hons.)",
        "Bachelor in Analytical Economics (Honours)",
        "Bachelor in Finance (Honours)",
        "Bachelor in Business Management (Honours)",
        "Bachelor in Marketing (Honours)",
        "Bachelor in Digital Enterprise Management (Honours)",
        "Master of Philosophy in Management (By Research)",
        "Doctor of Philosophy in Management (By Research)",
        "Master in Business Administration (By Coursework)",
        "Executive Master in Business Administration – ODL (By Coursework)",
    ],

    "Faculty of Creative Multimedia": [
        "Foundation in Creative Multimedia",
        "Diploma in Creative Multimedia",
        "Diploma in 3D Modelling & Animation",
        "Diploma in Creative Audio",
        "Bachelor of Multimedia (Hons.) Advertising Design",
        "Bachelor in Animation (Honours)",
        "Bachelor in Immersive Media Design (Honours)",
        "Bachelor in Visual Effects (Honours)",
        "Master of Science in Creative Multimedia (By Research)",
        "Doctor of Philosophy in Creative Multimedia (By Research)",
        "Master in Creative Multimedia (By Coursework)",
    ],

    "Faculty of Applied Communication": [
        "Foundation in Communication",
        "Diploma in Applied Communication",
        "Bachelor in Communication (Honours) (Strategic Communication)",
        "Master of Philosophy in Communication (By Research)",
        "Doctor of Philosophy (Communication) (By Research)",
    ],

    "Faculty of Cinematic Arts": [
        "Diploma in Cinematography",
        "Bachelor in Cinematic Arts (Honours)",
    ],
}

def calculate_similarity(current_user, other_user):
    """
    0-100 score weighted across three dimensions:
      - Shared interests  → 60%
      - Same faculty      → 25%
      - Shared clubs      → 15%
    """
    score = 0

    # --- Interests (60%) ---
    u_interests = set(i.lower() for i in current_user.interest_list())
    o_interests = set(i.lower() for i in other_user.interest_list())
    union = u_interests | o_interests
    if union:
        score += (len(u_interests & o_interests) / len(union)) * 60

    # --- Faculty (25%) ---
    if (current_user.faculty and other_user.faculty and
            current_user.faculty == other_user.faculty):
        score += 25

    # --- Clubs (15%) ---
    u_clubs = set(c.id for c in current_user.clubs)
    o_clubs = set(c.id for c in other_user.clubs)
    all_clubs = u_clubs | o_clubs
    if all_clubs:
        score += (len(u_clubs & o_clubs) / len(all_clubs)) * 15

    return round(score)


# =============================================================
# AUTH ROUTES
# =============================================================

@app.route("/")
def index():
    """Redirect to login or main page depending on session."""
    if "username" not in session:
        return redirect(url_for("login"))
    return redirect(url_for("main_page"))


@app.route("/login", methods=["GET", "POST"])
def login():
    """Handle user login. Blocks banned accounts."""
    error = None
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            if user.is_banned:
                error = "This account has been banned."
            else:
                session["username"] = user.username
                return redirect(url_for("main_page"))
        else:
            error = "Invalid username or password."

    return render_template("login.html", error=error)


@app.route("/signup", methods=["GET", "POST"])
def signup():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm  = request.form.get("confirm_password", "")

        if not username or not email or not password:
            error = "All fields are required."
        elif not email.endswith("@student.mmu.edu.my"):
            error = "You must use your @student.mmu.edu.my email."
        elif password != confirm:
            error = "Passwords do not match."
        elif User.query.filter_by(username=username).first():
            error = "Username already taken."
        elif User.query.filter_by(email=email).first():
            error = "An account with that email already exists."
        else:
            user = User(username=username, email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            session["username"] = user.username
            return redirect(url_for("main_page"))

    return render_template("signup.html", error=error)


@app.route("/logout")
def logout():
    """Clear session and redirect to login."""
    session.pop("username", None)
    return redirect(url_for("login"))


# =============================================================
# MAIN FEED
# =============================================================

@app.route("/main")
def main_page():
    """Show visible main posts with sort filter and pagination (50 per page)."""
    redir = login_required_redirect()
    if redir:
        return redir

    from sqlalchemy import func
    from datetime import timedelta

    sort    = request.args.get("sort", "recent")
    page    = max(1, request.args.get("page", 1, type=int))
    per_page = 50

    base_q = Post.query.filter_by(type="main", is_visible=True)

    if sort == "recent":
        query = base_q.order_by(Post.created_at.desc())

    else:
        # Date window for popularity filters
        now = datetime.utcnow()
        if sort == "popular-daily":
            since = now - timedelta(days=1)
        elif sort == "popular-monthly":
            since = now - timedelta(days=30)
        else:  # popular-yearly
            since = now - timedelta(days=365)

        like_count = (
            db.session.query(Like.post_id, func.count(Like.id).label("n"))
            .group_by(Like.post_id)
            .subquery()
        )
        query = (
            base_q
            .filter(Post.created_at >= since)
            .outerjoin(like_count, Post.id == like_count.c.post_id)
            .order_by(func.coalesce(like_count.c.n, 0).desc(), Post.created_at.desc())
        )

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    posts      = pagination.items

    return render_template(
        "main.html",
        posts      = posts,
        pagination = pagination,
        sort       = sort,
        username   = session["username"],
        active_page = "main"
    )


@app.route("/post/create", methods=["POST"])
def create_post():
    """Create a new main feed post."""
    redir = login_required_redirect()
    if redir:
        return redir

    content   = request.form.get("content", "").strip()
    image_url = save_uploaded_image(request.files.get("image"))

    if content:
        user = current_user()
        db.session.add(Post(
            type        = "main",
            author_id   = user.id,
            author_name = user.username,
            content     = content,
            image_url   = image_url
        ))
        db.session.commit()

    return redirect(url_for("main_page"))


@app.route("/post/<int:post_id>")
def post_detail(post_id):
    """Show a single post on its own page."""
    redir = login_required_redirect()
    if redir:
        return redir

    post = Post.query.get_or_404(post_id)

    if not post.is_visible:
        user = current_user()
        if not user or not user.is_admin:
            return redirect(url_for("main_page" if post.type == "main" else "club_page"))

    return render_template(
        "post_detail.html",
        post        = post,
        username    = session["username"],
        active_page = "main" if post.type == "main" else "club"
    )


# =============================================================
# CLUB FEED
# =============================================================

@app.route("/club")
def club_page():
    """Show all visible club posts, newest first."""
    redir = login_required_redirect()
    if redir:
        return redir

    posts = Post.query.filter_by(type="club", is_visible=True).order_by(Post.created_at.desc()).all()
    return render_template("club.html", posts=posts, username=session["username"], active_page="club")


@app.route("/club/post/create", methods=["POST"])
def create_club_post():
    """Create a new club post. Only club accounts can post here."""
    redir = login_required_redirect()
    if redir:
        return redir

    user = current_user()
    if not user.is_club:
        return redirect(url_for("club_page"))

    content   = request.form.get("content", "").strip()
    image_url = save_uploaded_image(request.files.get("image"))

    if content:
        db.session.add(Post(
            type        = "club",
            author_id   = user.id,
            author_name = user.username,
            content     = content,
            image_url   = image_url
        ))
        db.session.commit()

    return redirect(url_for("club_page"))


# =============================================================
# FRIEND REQUESTS
# =============================================================

@app.route("/friend-request/send/<username>", methods=["POST"])
def send_friend_request(username):
    redir = login_required_redirect()
    if redir:
        return jsonify({"error": "unauthorized"}), 401

    me = session["username"]
    if username == me:
        return jsonify({"error": "cannot friend yourself"}), 400
    if Friendship.exists_between(me, username):
        return jsonify({"error": "already friends"}), 400
    if FriendRequest.query.filter_by(from_user=me, to_user=username, status="pending").first():
        return jsonify({"error": "request already sent"}), 400

    # If they already requested you, accept instead of duplicating
    reverse = FriendRequest.query.filter_by(from_user=username, to_user=me, status="pending").first()
    if reverse:
        reverse.status = "accepted"
        Friendship.create(me, username)
        db.session.commit()
        return jsonify({"status": "friends"})

    db.session.add(FriendRequest(from_user=me, to_user=username))
    db.session.add(FriendRequestNotif(to_user=username, from_user=me, notif_type="request"))
    db.session.commit()
    return jsonify({"status": "pending"})


@app.route("/friend-request/<int:request_id>/accept", methods=["POST"])
def accept_friend_request(request_id):
    redir = login_required_redirect()
    if redir:
        return jsonify({"error": "unauthorized"}), 401

    req = FriendRequest.query.get_or_404(request_id)
    if req.to_user != session["username"] or req.status != "pending":
        return jsonify({"error": "invalid request"}), 400

    req.status = "accepted"
    Friendship.create(req.from_user, req.to_user)
    db.session.add(FriendRequestNotif(to_user=req.from_user, from_user=req.to_user, notif_type="accepted"))
    db.session.commit()
    return jsonify({"success": True})


@app.route("/friend-request/<int:request_id>/decline", methods=["POST"])
def decline_friend_request(request_id):
    redir = login_required_redirect()
    if redir:
        return jsonify({"error": "unauthorized"}), 401

    req = FriendRequest.query.get_or_404(request_id)
    if req.to_user != session["username"] or req.status != "pending":
        return jsonify({"error": "invalid request"}), 400

    req.status = "declined"
    db.session.commit()
    return jsonify({"success": True})

@app.route("/unfriend/<username>", methods=["POST"])
def unfriend(username):
    redir = login_required_redirect()
    if redir:
        return jsonify({"error": "unauthorized"}), 401
 
    me = session["username"]
    if username == me:
        return jsonify({"error": "invalid request"}), 400
 
    friendship = Friendship.query.filter(
        db.or_(
            db.and_(Friendship.user_a == me,       Friendship.user_b == username),
            db.and_(Friendship.user_a == username,  Friendship.user_b == me),
        )
    ).first()
 
    if not friendship:
        return jsonify({"error": "not friends"}), 404
 
    db.session.delete(friendship)
    db.session.commit()
    return jsonify({"success": True})

# =============================================================
# MESSAGING 
# =============================================================

@app.route("/messages/<username>")
def get_messages(username):
    redir = login_required_redirect()
    if redir:
        return jsonify({"error": "unauthorized"}), 401

    me = session["username"]
    msgs = Message.query.filter(
        ((Message.sender == me)       & (Message.recipient == username)) |
        ((Message.sender == username) & (Message.recipient == me))
    ).order_by(Message.created_at.asc()).limit(100).all()

    # Mark received messages as read
    Message.query.filter_by(sender=username, recipient=me, read=False).update({"read": True})
    db.session.commit()

    return jsonify([{
        "id":         m.id,
        "sender":     m.sender,
        "recipient":  m.recipient,
        "content":    m.content,
        "created_at": m.created_at.strftime("%H:%M"),
        "read":       m.read,
    } for m in msgs])

@app.route("/messages/friends-list")
def friends_list_api():
    """Return the current user's friends with profile pics for the messenger."""
    if "username" not in session:
        return jsonify([]), 401
 
    me      = session["username"]
    rows    = Friendship.query.filter(
        (Friendship.user_a == me) | (Friendship.user_b == me)
    ).all()
    names   = [r.user_b if r.user_a == me else r.user_a for r in rows]
    users   = User.query.filter(User.username.in_(names)).all()
 
    return jsonify([{
        "username":    u.username,
        "profile_pic": u.profile_pic or "/static/images/profile-placeholder.png",
    } for u in users])

@app.route("/messages/unread-count")
def unread_message_count():
    if "username" not in session:
        return jsonify({"count": 0})
    count = Message.query.filter_by(recipient=session["username"], read=False).count()
    return jsonify({"count": count})

@app.route("/messages/unread-per-friend")
def unread_per_friend():
    if "username" not in session:
        return jsonify({})
    me = session["username"]
    rows = db.session.query(Message.sender, db.func.count(Message.id))\
        .filter_by(recipient=me, read=False)\
        .group_by(Message.sender).all()
    return jsonify({sender: count for sender, count in rows})

@socketio.on("join")
def on_join(data):
    """Client joins a private room keyed by sorted usernames."""
    me    = session.get("username")
    other = data.get("other")
    if not me or not other:
        return
    room = "_".join(sorted([me, other]))
    join_room(room)


@socketio.on("send_message")
def on_send_message(data):
    me        = session.get("username")
    recipient = data.get("recipient")
    content   = data.get("content", "").strip()

    if not me or not recipient or not content:
        return

    # Security: must be friends
    if not Friendship.exists_between(me, recipient):
        return

    msg = Message(sender=me, recipient=recipient, content=content)
    db.session.add(msg)
    db.session.commit()

    room    = "_".join(sorted([me, recipient]))
    payload = {
        "id":         msg.id,
        "sender":     me,
        "recipient":  recipient,
        "content":    content,
        "created_at": msg.created_at.strftime("%H:%M"),
    }
    emit("new_message", payload, to=room)

# =============================================================
# DISCOVERY
# =============================================================

@app.route("/discovery")
def discovery_page():
    """Show the next unrated real user profile with a similarity score."""
    redir = login_required_redirect()
    if redir:
        return redir

    user = current_user()

    # Users already acted on (liked or passed) — exclude them
    already_liked = {dl.to_user for dl in DiscoveryLike.query.filter_by(from_user=user.username).all()}
    passed_key    = f"passed_{user.username}"
    already_passed = set(session.get(passed_key, []))
    seen = already_liked | already_passed

    # Exclude self, clubs, banned, and already-seen users
    candidates = User.query.filter(
        User.username != user.username,
        User.is_club   == False,
        User.is_banned == False,
        ~User.username.in_(seen)
    ).all()

    if not candidates:
        return render_template(
            "discovery.html",
            profile     = None,
            similarity  = 0,
            username    = session["username"],
            active_page = "discovery"
        )

    # Pick the highest-scoring candidate
    scored = sorted(candidates, key=lambda u: calculate_similarity(user, u), reverse=True)
    profile_user = scored[0]
    similarity   = calculate_similarity(user, profile_user)

    return render_template(
        "discovery.html",
        profile     = profile_user,
        similarity  = similarity,
        username    = session["username"],
        active_page = "discovery"
    )


@app.route("/discovery/action", methods=["POST"])
def discovery_action():
    """Handle like/pass. Creates a match if mutual like exists."""
    redir = login_required_redirect()
    if redir:
        return redir

    action      = request.form.get("action")
    target_name = request.form.get("target_username", "").strip()
    me          = session["username"]

    if action == "like" and target_name:
        # Record like (ignore duplicate)
        existing = DiscoveryLike.query.filter_by(from_user=me, to_user=target_name).first()
        if not existing:
            db.session.add(DiscoveryLike(from_user=me, to_user=target_name))
            db.session.commit()

            # Check for mutual like → create match
            mutual = DiscoveryLike.query.filter_by(from_user=target_name, to_user=me).first()
            if mutual:
                already_matched = DiscoveryMatch.query.filter(
                    ((DiscoveryMatch.user_a == me)          & (DiscoveryMatch.user_b == target_name)) |
                    ((DiscoveryMatch.user_a == target_name) & (DiscoveryMatch.user_b == me))
                ).first()
                if not already_matched:
                    db.session.add(DiscoveryMatch(user_a=me, user_b=target_name))
                    Friendship.create(me, target_name) 
                    db.session.commit()

    elif action == "pass" and target_name:
        passed_key = f"passed_{me}"
        passed     = session.get(passed_key, [])
        if target_name not in passed:
            passed.append(target_name)
        session[passed_key] = passed

    return redirect(url_for("discovery_page"))


@app.route("/notifications")
def notifications():
    """Return likes, matches, and comment notifications for the current user."""
    redir = login_required_redirect()
    if redir:
        return redir
 
    me = session["username"]
 
    likes = DiscoveryLike.query.filter_by(to_user=me).order_by(DiscoveryLike.created_at.desc()).limit(10).all()
 
    matches = DiscoveryMatch.query.filter(
        (DiscoveryMatch.user_a == me) | (DiscoveryMatch.user_b == me)
    ).order_by(DiscoveryMatch.created_at.desc()).limit(10).all()
 
    comment_notifs = CommentNotif.query.filter_by(post_author=me).order_by(CommentNotif.created_at.desc()).limit(10).all()

    like_notifs = LikeNotif.query.filter_by(post_author=me).order_by(LikeNotif.created_at.desc()).limit(10).all()

    friend_request_notifs = FriendRequestNotif.query.filter_by(to_user=me).order_by(FriendRequestNotif.created_at.desc()).limit(10).all()
 
    # Mark ALL unseen items as seen (not just the ones displayed)
    DiscoveryLike.query.filter_by(to_user=me, seen=False).update({"seen": True})

    DiscoveryMatch.query.filter(
        (DiscoveryMatch.user_a == me) & (DiscoveryMatch.seen_by_a == False)
    ).update({"seen_by_a": True})

    DiscoveryMatch.query.filter(
        (DiscoveryMatch.user_b == me) & (DiscoveryMatch.seen_by_b == False)
    ).update({"seen_by_b": True})

    CommentNotif.query.filter_by(post_author=me, seen=False).update({"seen": True})

    LikeNotif.query.filter_by(post_author=me, seen=False).update({"seen": True})

    FriendRequestNotif.query.filter_by(to_user=me, seen=False).update({"seen": True})

    db.session.commit()

    return render_template(
        "notifications.html",
        likes                 = likes,
        matches               = matches,
        comment_notifs        = comment_notifs,
        like_notifs           = like_notifs,
        friend_request_notifs = friend_request_notifs,
        username              = me,
        active_page           = None
    )
 
@app.route("/notifications/count")
def notifications_count():
    """Return total unseen notification count as JSON for the badge."""
    if "username" not in session:
        return jsonify({"count": 0})
 
    me = session["username"]
 
    unseen_likes = DiscoveryLike.query.filter_by(to_user=me, seen=False).count()
 
    unseen_matches = DiscoveryMatch.query.filter(
        ((DiscoveryMatch.user_a == me) & (DiscoveryMatch.seen_by_a == False)) |
        ((DiscoveryMatch.user_b == me) & (DiscoveryMatch.seen_by_b == False))
    ).count()
 
    unseen_comments = CommentNotif.query.filter_by(post_author=me, seen=False).count()

    unseen_post_likes = LikeNotif.query.filter_by(post_author=me, seen=False).count()
 
    unseen_friend_requests = FriendRequestNotif.query.filter_by(to_user=me, seen=False).count()

    return jsonify({"count": unseen_likes + unseen_matches + unseen_comments + unseen_post_likes + unseen_friend_requests})


@app.route("/club/join/<int:club_id>", methods=["POST"])
def join_club(club_id):
    """Toggle membership in a club."""
    redir = login_required_redirect()
    if redir:
        return jsonify({"error": "unauthorized"}), 401

    user = current_user()
    club = User.query.filter_by(id=club_id, is_club=True).first_or_404()

    if club in user.clubs:
        user.clubs.remove(club)
        joined = False
    else:
        user.clubs.append(club)
        joined = True

    db.session.commit()
    return jsonify({"joined": joined, "club": club.username})


# =============================================================
# POST INTERACTIONS (likes, comments, reports)
# =============================================================

@app.route("/post/<int:post_id>/like", methods=["POST"])
def like_post(post_id):
    """Toggle like on a post. Returns JSON for JS fetch."""
    redir = login_required_redirect()
    if redir:
        return jsonify({"error": "unauthorized"}), 401

    username = session["username"]
    existing = Like.query.filter_by(post_id=post_id, username=username).first()

    if existing:
        db.session.delete(existing)
        liked = False

        # Remove the notification if it hasn't been seen yet
        notif = LikeNotif.query.filter_by(post_id=post_id, liker=username).first()
        if notif:
            db.session.delete(notif)
    else:
        db.session.add(Like(post_id=post_id, username=username))
        liked = True

        # Notify the post author (but not if they're liking their own post)
        post = Post.query.get(post_id)
        if post and post.author_name != username:
            existing_notif = LikeNotif.query.filter_by(post_id=post_id, liker=username).first()
            if not existing_notif:
                db.session.add(LikeNotif(
                    post_author = post.author_name,
                    liker       = username,
                    post_id     = post_id
                ))

    db.session.commit()
    count = Like.query.filter_by(post_id=post_id).count()
    return jsonify({"liked": liked, "count": count})


@app.route("/post/<int:post_id>/comment", methods=["POST"])
def comment_post(post_id):
    """Add a comment to a post and notify the post author."""
    redir = login_required_redirect()
    if redir:
        return redir
 
    content = request.form.get("comment", "").strip()
    if content:
        commenter = session["username"]
        post = Post.query.get_or_404(post_id)
 
        db.session.add(Comment(
            post_id  = post_id,
            username = commenter,
            content  = content
        ))
 
        # Notify the post author (but not if they're commenting on their own post)
        if post.author_name != commenter:
            db.session.add(CommentNotif(
                post_author     = post.author_name,
                commenter       = commenter,
                post_id         = post_id,
                comment_content = content[:280]
            ))
 
        db.session.commit()
 
    return redirect(request.referrer or url_for("main_page"))


@app.route("/post/<int:post_id>/report", methods=["POST"])
def report_post(post_id):
    """Send a report embed to the Discord webhook."""
    redir = login_required_redirect()
    if redir:
        return jsonify({"error": "unauthorized"}), 401

    post     = Post.query.get_or_404(post_id)
    reporter = session["username"]
    reason   = request.form.get("reason", "No reason given").strip()

    embed = {
        "title": "🚨 Post Reported",
        "color": 0xff5a5a,
        "fields": [
            {"name": "Post ID",      "value": str(post.id),    "inline": True},
            {"name": "Author",       "value": post.author_name,"inline": True},
            {"name": "Reported By",  "value": reporter,        "inline": True},
            {"name": "Reason",       "value": reason},
            {"name": "Content",      "value": post.content[:500]},
        ]
    }

    # Attach post image if available (requires public URL — won't work on localhost)
    if post.image_url:
        host           = request.host_url.rstrip("/")
        full_image_url = host + post.image_url if post.image_url.startswith("/") else post.image_url
        embed["image"] = {"url": full_image_url}

    requests.post(DISCORD_WEBHOOK, json={"embeds": [embed]})
    return jsonify({"success": True})


# =============================================================
# PROFILE & SETTINGS
# =============================================================

@app.route("/profile/<username>")
def profile_page(username):
    redir = login_required_redirect()
    if redir:
        return redir

    user      = User.query.filter_by(username=username).first_or_404()
    posts     = Post.query.filter_by(author_id=user.id).order_by(Post.created_at.desc()).all()
    all_clubs = User.query.filter_by(is_club=True).all()
    viewer    = current_user()

    friend_status     = "self"
    incoming_request  = None
    if viewer.username != user.username:
        if Friendship.exists_between(viewer.username, user.username):
            friend_status = "friends"
        else:
            sent = FriendRequest.query.filter_by(from_user=viewer.username, to_user=user.username, status="pending").first()
            incoming_request = FriendRequest.query.filter_by(from_user=user.username, to_user=viewer.username, status="pending").first()
            if sent:
                friend_status = "pending_sent"
            elif incoming_request:
                friend_status = "pending_received"
            else:
                friend_status = "none"

    return render_template(
        "profile.html",
        profile_user      = user,
        posts             = posts,
        all_clubs         = all_clubs,
        viewer            = viewer,
        friend_status     = friend_status,
        incoming_request  = incoming_request,
        username          = session["username"],
        active_page       = None
    )


@app.route("/profile/edit", methods=["GET", "POST"])
def edit_profile():
    """Edit bio, interests, and profile picture."""
    redir = login_required_redirect()
    if redir:
        return redir

    user = current_user()

    if request.method == "POST":
        user.bio       = request.form.get("bio", "").strip()
        selected       = request.form.getlist("interests")
        user.interests = ", ".join(selected)
        user.faculty   = request.form.get("faculty", "").strip()
        user.course    = request.form.get("course", "").strip()

        # Handle profile picture upload
        file = request.files.get("profile_pic_file")
        uploaded_url = save_uploaded_image(file)
        if uploaded_url:
            user.profile_pic = uploaded_url

        db.session.commit()
        return redirect(url_for("profile_page", username=user.username))

    return render_template(
        "edit_profile.html",
        user                 = user,
        predefined_interests = PREDEFINED_INTERESTS,
        faculty_courses      = FACULTY_COURSES,
        username             = session["username"],
        active_page          = None
    )


@app.route("/settings", methods=["GET", "POST"])
def settings_page():
    """Account settings — currently supports password change."""
    redir = login_required_redirect()
    if redir:
        return redir

    user = current_user()

    if request.method == "POST":
        new_password = request.form.get("new_password", "").strip()
        if new_password:
            user.set_password(new_password)
            db.session.commit()
            flash("Password updated.")

    return render_template(
        "settings.html",
        user        = user,
        username    = session["username"],
        active_page = None
    )


# =============================================================
# SEARCH API
# =============================================================

@app.route("/search/api")
def search_api():
    """Live search endpoint — returns matching clubs and users as JSON."""
    redir = login_required_redirect()
    if redir:
        return jsonify({"error": "unauthorized"}), 401

    q = request.args.get("q", "").strip()
    if not q or len(q) < 2:
        return jsonify({"clubs": [], "users": []})

    pattern = f"%{q}%"

    clubs = User.query.filter(
        User.is_club == True,
        User.is_banned == False,
        User.username.ilike(pattern)
    ).limit(6).all()

    users = User.query.filter(
        User.is_club == False,
        User.is_banned == False,
        User.username.ilike(pattern)
    ).limit(6).all()

    return jsonify({
        "clubs": [
            {
                "username": c.username,
                "profile_pic": c.profile_pic or "/static/images/profile-placeholder.png",
                "bio": c.bio or ""
            }
            for c in clubs
        ],
        "users": [
            {
                "username": u.username,
                "profile_pic": u.profile_pic or "/static/images/profile-placeholder.png",
                "faculty": u.faculty or ""
            }
            for u in users
        ]
    })


# =============================================================
# ADMIN PANEL
# =============================================================

@app.route("/admin")
def admin_panel():
    """Admin dashboard — view users and hidden posts."""
    redir = login_required_redirect()
    if redir:
        return redir

    user = current_user()
    if not user.is_admin:
        return redirect(url_for("main_page"))

    users        = User.query.order_by(User.id).all()
    hidden_posts = Post.query.filter_by(is_visible=False).order_by(Post.created_at.desc()).all()

    return render_template(
        "admin.html",
        users        = users,
        hidden_posts = hidden_posts,
        username     = session["username"],
        active_page  = None
    )


@app.route("/admin/create-club", methods=["POST"])
def create_club():
    """Create a new club account. Admin only."""
    redir = login_required_redirect()
    if redir:
        return jsonify({"error": "unauthorized"}), 401

    if not current_user().is_admin:
        return jsonify({"error": "forbidden"}), 403

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()

    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400
    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username already taken"}), 400

    club = User(username=username, is_club=True)
    club.set_password(password)
    db.session.add(club)
    db.session.commit()

    return jsonify({"success": True, "username": club.username})


@app.route("/admin/ban/<int:user_id>", methods=["POST"])
def ban_user(user_id):
    """Ban a user and hide all their posts. Admin only."""
    redir = login_required_redirect()
    if redir:
        return jsonify({"error": "unauthorized"}), 401

    if not current_user().is_admin:
        return jsonify({"error": "forbidden"}), 403

    target = User.query.get_or_404(user_id)
    target.is_banned = True
    Post.query.filter_by(author_id=target.id).update({"is_visible": False})
    db.session.commit()

    return jsonify({"success": True, "username": target.username})


@app.route("/admin/unban/<int:user_id>", methods=["POST"])
def unban_user(user_id):
    """Unban a user. Admin only."""
    redir = login_required_redirect()
    if redir:
        return jsonify({"error": "unauthorized"}), 401

    if not current_user().is_admin:
        return jsonify({"error": "forbidden"}), 403

    target = User.query.get_or_404(user_id)
    target.is_banned = False
    db.session.commit()

    return jsonify({"success": True})


@app.route("/post/<int:post_id>/delete", methods=["POST"])
def delete_post(post_id):
    """Hide a post (soft delete). Admin only."""
    redir = login_required_redirect()
    if redir:
        return jsonify({"error": "unauthorized"}), 401

    if not current_user().is_admin:
        return jsonify({"error": "forbidden"}), 403

    post = Post.query.get_or_404(post_id)
    post.is_visible = False
    db.session.commit()

    return jsonify({"success": True})


@app.route("/admin/restore-post/<int:post_id>", methods=["POST"])
def restore_post(post_id):
    """Restore a hidden post. Admin only."""
    redir = login_required_redirect()
    if redir:
        return jsonify({"error": "unauthorized"}), 401

    if not current_user().is_admin:
        return jsonify({"error": "forbidden"}), 403

    post = Post.query.get_or_404(post_id)
    post.is_visible = True
    db.session.commit()

    return jsonify({"success": True})


# =============================================================
# DATABASE INIT & SEED DATA
# =============================================================

def init_db():
    """Create tables and seed with demo data if empty."""
    db.create_all()

    if User.query.first() is not None:
        return  # Already seeded

    # --- Seed users ---
    demo = User(
        username    = "demo",
        bio         = "Just a demo student exploring Sahabat.",
        profile_pic = "/static/images/profile-placeholder.png",
        interests   = "music, coding, hiking"
    )
    demo.set_password("password123")

    aisyah = User(username="Aisyah", profile_pic="/static/images/profile-placeholder.png", interests="running, music")
    aisyah.set_password("password123")

    daniel = User(username="Daniel", profile_pic="/static/images/profile-placeholder.png", interests="coding, hiking")
    daniel.set_password("password123")

    photo_club = User(username="Photography Club", profile_pic="/static/images/profile-placeholder.png",
                      interests="photography", is_club=True)
    photo_club.set_password("password123")

    debate_club = User(username="Debate Society", profile_pic="/static/images/profile-placeholder.png",
                       interests="debate", is_club=True)
    debate_club.set_password("password123")

    db.session.add_all([demo, aisyah, daniel, photo_club, debate_club])
    db.session.commit()

    # --- Seed posts ---
    posts = [
        Post(type="main", author_id=aisyah.id, author_name="Aisyah",
             content="Anyone joining the campus run this weekend?",
             image_url="/static/images/post-placeholder.jpg"),
        Post(type="main", author_id=daniel.id, author_name="Daniel",
             content="Lost my student ID near the library, please help!",
             image_url=None),
        Post(type="club", author_id=photo_club.id, author_name="Photography Club",
             content="Photo walk this Saturday, 4PM at the lake.",
             image_url="/static/images/post-placeholder.jpg"),
        Post(type="club", author_id=debate_club.id, author_name="Debate Society",
             content="Sign-ups for the inter-uni debate are open!",
             image_url=None),
    ]
    db.session.add_all(posts)
    db.session.commit()

    # --- Seed likes & comments ---
    db.session.add(Like(post_id=posts[0].id, username="Daniel"))
    db.session.add(Like(post_id=posts[2].id, username="Aisyah"))
    db.session.add(Like(post_id=posts[2].id, username="Daniel"))
    db.session.add(Comment(post_id=posts[0].id, username="Daniel", content="I'm in!"))
    db.session.add(Comment(post_id=posts[2].id, username="Aisyah", content="Can't wait!"))
    db.session.commit()


# =============================================================
# ENTRY POINT
# =============================================================

if __name__ == "__main__":
    with app.app_context():
        init_db()
    socketio.run(app, debug=True)