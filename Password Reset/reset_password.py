import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, render_template_string, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash
import secrets

# ── Blueprint & DB ────────────────────────────────────────────────────────────
reset_bp = Blueprint("reset_password", __name__)
db = None  # injected via init_reset_module()

# ── Config (load from environment variables) ──────────────────────────────────
SMTP_HOST     = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT     = int(os.environ.get("SMTP_PORT", 587))
SMTP_USER     = os.environ.get("SMTP_USER", "")         # your@gmail.com
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")     # app password
EMAIL_FROM    = os.environ.get("EMAIL_FROM", SMTP_USER)
APP_BASE_URL  = os.environ.get("APP_BASE_URL", "http://localhost:5000")
TOKEN_EXPIRY_HOURS = int(os.environ.get("TOKEN_EXPIRY_HOURS", 1))


# ── Model ─────────────────────────────────────────────────────────────────────
class PasswordResetToken(db.Model):  # type: ignore[name-defined]  (db set at runtime)
    __tablename__ = "password_reset_tokens"

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    token      = db.Column(db.String(128), unique=True, nullable=False, index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    used       = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def is_valid(self):
        return not self.used and datetime.utcnow() < self.expires_at


# ── Email sender ──────────────────────────────────────────────────────────────
def _send_reset_email(to_email: str, reset_link: str):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Reset your password"
    msg["From"]    = EMAIL_FROM
    msg["To"]      = to_email

    plain = f"Click the link to reset your password (valid for {TOKEN_EXPIRY_HOURS}h):\n{reset_link}"
    html  = _render_email_html(reset_link)

    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html,  "html"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(EMAIL_FROM, to_email, msg.as_string())


# ── Routes ────────────────────────────────────────────────────────────────────
@reset_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "GET":
        return render_template_string(FORGOT_TEMPLATE)

    email = (request.form.get("email") or "").strip().lower()
    if not email:
        flash("Please enter your email address.", "error")
        return render_template_string(FORGOT_TEMPLATE)

    # Import your User model here; adjust the import to match your project layout
    from app import User  # ← change this to wherever your User model lives

    user = User.query.filter_by(email=email).first()

    # Always respond with success to prevent user enumeration attacks
    if user:
        # Invalidate any existing unused tokens for this user
        PasswordResetToken.query.filter_by(user_id=user.id, used=False).update({"used": True})
        db.session.commit()

        token     = secrets.token_urlsafe(48)
        reset_tok = PasswordResetToken(
            user_id    = user.id,
            token      = token,
            expires_at = datetime.utcnow() + timedelta(hours=TOKEN_EXPIRY_HOURS),
        )
        db.session.add(reset_tok)
        db.session.commit()

        reset_link = f"{APP_BASE_URL}/reset-password/{token}"
        try:
            _send_reset_email(user.email, reset_link)
        except Exception as e:
            # Log the error but don't reveal it to the user
            print(f"[reset_password] Email send error: {e}")

    return render_template_string(EMAIL_SENT_TEMPLATE)


@reset_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token: str):
    tok = PasswordResetToken.query.filter_by(token=token).first()

    if not tok or not tok.is_valid():
        return render_template_string(INVALID_TOKEN_TEMPLATE)

    if request.method == "GET":
        return render_template_string(RESET_FORM_TEMPLATE, token=token)

    password  = request.form.get("password", "")
    password2 = request.form.get("password2", "")

    errors = _validate_password(password, password2)
    if errors:
        return render_template_string(RESET_FORM_TEMPLATE, token=token, errors=errors)

    from app import User  # ← same import as above

    user = User.query.get(tok.user_id)
    if not user:
        return render_template_string(INVALID_TOKEN_TEMPLATE)

    user.password_hash = generate_password_hash(password)
    tok.used = True
    db.session.commit()

    return render_template_string(SUCCESS_TEMPLATE)


# ── Helpers ───────────────────────────────────────────────────────────────────
def _validate_password(pw: str, pw2: str) -> list:
    errors = []
    if len(pw) < 8:
        errors.append("Password must be at least 8 characters.")
    if pw != pw2:
        errors.append("Passwords do not match.")
    if not any(c.isupper() for c in pw):
        errors.append("Password must contain at least one uppercase letter.")
    if not any(c.isdigit() for c in pw):
        errors.append("Password must contain at least one number.")
    return errors


def init_reset_module(app, sqlalchemy_db):
    """
    Call this in your app factory:

        from reset_password import reset_bp, init_reset_module
        init_reset_module(app, db)
        app.register_blueprint(reset_bp)
    """
    global db
    db = sqlalchemy_db
    # Patch the model so it can reference db at runtime
    PasswordResetToken.__table_args__ = getattr(PasswordResetToken, "__table_args__", {})
    with app.app_context():
        sqlalchemy_db.create_all()


# ── HTML email template ───────────────────────────────────────────────────────
def _render_email_html(reset_link: str) -> str:
    return f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    body {{ margin:0; padding:0; background:#f4f4f5; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }}
    .wrapper {{ max-width:520px; margin:40px auto; background:#ffffff; border-radius:12px; overflow:hidden; border:1px solid #e4e4e7; }}
    .header {{ background:#18181b; padding:32px 40px 28px; text-align:center; }}
    .header h1 {{ margin:0; color:#ffffff; font-size:20px; font-weight:600; letter-spacing:-0.3px; }}
    .body {{ padding:36px 40px; }}
    .body p {{ color:#52525b; font-size:15px; line-height:1.7; margin:0 0 20px; }}
    .btn {{ display:block; width:fit-content; margin:28px auto; background:#18181b; color:#ffffff !important;
            text-decoration:none; padding:14px 32px; border-radius:8px; font-size:15px; font-weight:500; }}
    .link-fallback {{ font-size:12px; color:#a1a1aa; word-break:break-all; text-align:center; margin-top:24px; }}
    .footer {{ border-top:1px solid #f4f4f5; padding:20px 40px; text-align:center; font-size:12px; color:#a1a1aa; }}
  </style>
</head>
<body>
  <div class="wrapper">
    <div class="header"><h1>Reset your password</h1></div>
    <div class="body">
      <p>Hi there,</p>
      <p>We received a request to reset the password for your account. Click the button below — this link expires in <strong>{TOKEN_EXPIRY_HOURS} hour(s)</strong>.</p>
      <a class="btn" href="{reset_link}">Reset my password</a>
      <p>If you didn't request this, you can safely ignore this email. Your password won't change.</p>
      <p class="link-fallback">Or copy this link into your browser:<br>{reset_link}</p>
    </div>
    <div class="footer">This link expires in {TOKEN_EXPIRY_HOURS} hour(s) and can only be used once.</div>
  </div>
</body>
</html>
"""


# ── Flask page templates ──────────────────────────────────────────────────────
_BASE = """
<!DOCTYPE html><html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f4f4f5;
        display:flex;align-items:center;justify-content:center;min-height:100vh;padding:1rem}}
  .card{{background:#fff;border:1px solid #e4e4e7;border-radius:12px;padding:40px;max-width:420px;width:100%}}
  h2{{font-size:20px;font-weight:600;color:#18181b;margin-bottom:8px}}
  p{{font-size:14px;color:#52525b;line-height:1.6;margin-bottom:20px}}
  label{{display:block;font-size:13px;font-weight:500;color:#3f3f46;margin-bottom:6px}}
  input{{width:100%;padding:10px 12px;border:1px solid #d4d4d8;border-radius:8px;font-size:14px;
         color:#18181b;outline:none;transition:border .2s}}
  input:focus{{border-color:#18181b}}
  .field{{margin-bottom:16px}}
  .btn{{width:100%;padding:11px;background:#18181b;color:#fff;border:none;border-radius:8px;
         font-size:14px;font-weight:500;cursor:pointer;margin-top:4px}}
  .btn:hover{{background:#27272a}}
  .errors{{background:#fef2f2;border:1px solid #fecaca;border-radius:8px;padding:12px 16px;margin-bottom:16px}}
  .errors li{{font-size:13px;color:#dc2626;list-style:none;padding:2px 0}}
  .icon{{font-size:40px;margin-bottom:16px}}
  a.back{{display:inline-block;margin-top:16px;font-size:13px;color:#71717a;text-decoration:none}}
  a.back:hover{{color:#18181b}}
</style></head><body><div class="card">{body}</div></body></html>
"""

FORGOT_TEMPLATE = _BASE.format(title="Forgot password", body="""
<div class="icon">🔐</div>
<h2>Forgot your password?</h2>
<p>Enter the email address on your account and we'll send you a reset link.</p>
{% with messages = get_flashed_messages(with_categories=true) %}
  {% for cat, msg in messages %}<div class="errors"><li>{{ msg }}</li></div>{% endfor %}
{% endwith %}
<form method="POST">
  <div class="field">
    <label for="email">Email address</label>
    <input id="email" name="email" type="email" required placeholder="you@example.com" autofocus>
  </div>
  <button class="btn" type="submit">Send reset link</button>
</form>
""")

EMAIL_SENT_TEMPLATE = _BASE.format(title="Check your email", body="""
<div class="icon">📬</div>
<h2>Check your inbox</h2>
<p>If that email address is registered, you'll receive a reset link shortly. It will expire in """ + str(TOKEN_EXPIRY_HOURS) + """ hour(s).</p>
<p>Don't forget to check your spam folder.</p>
<a class="back" href="/forgot-password">← Send again</a>
""")

RESET_FORM_TEMPLATE = _BASE.format(title="Reset password", body="""
<div class="icon">🔑</div>
<h2>Choose a new password</h2>
<p>Must be at least 8 characters with one uppercase letter and one number.</p>
{% if errors %}
<div class="errors">{% for e in errors %}<li>{{ e }}</li>{% endfor %}</div>
{% endif %}
<form method="POST">
  <div class="field">
    <label for="password">New password</label>
    <input id="password" name="password" type="password" required autofocus>
  </div>
  <div class="field">
    <label for="password2">Confirm new password</label>
    <input id="password2" name="password2" type="password" required>
  </div>
  <button class="btn" type="submit">Update password</button>
</form>
""")

SUCCESS_TEMPLATE = _BASE.format(title="Password updated", body="""
<div class="icon">✅</div>
<h2>Password updated!</h2>
<p>Your password has been changed successfully. You can now log in with your new password.</p>
<a class="back" href="/login">← Back to login</a>
""")

INVALID_TOKEN_TEMPLATE = _BASE.format(title="Link expired", body="""
<div class="icon">⚠️</div>
<h2>Link invalid or expired</h2>
<p>This reset link has already been used or has expired. Please request a new one.</p>
<a class="back" href="/forgot-password">← Request new link</a>
""")
