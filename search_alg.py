from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
import os

app = Flask(__name__)
CORS(app)

# --- DB Config ---
DB_CONFIG = {
    "host":     os.getenv("DB_HOST", "localhost"),
    "user":     os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "campus_db"),
}

def get_db():
    return mysql.connector.connect(**DB_CONFIG)


# ---------------------------------------------------------------------------
# GET /api/search?q=<keyword>
#
# Searches tags (location, subject, course) using a simple LIKE match.
# Returns all posts that have at least one matching tag.
#
# Query params:
#   q        — search keyword (required)
#   type     — optional tag type filter: 'location' | 'subject' | 'course'
#   page     — page number (default 1)
#   per_page — results per page (default 20, max 100)
#
# Example calls:
#   /api/search?q=lib
#   /api/search?q=math&type=subject
#   /api/search?q=hb&type=location&page=2
# ---------------------------------------------------------------------------
@app.route("/api/search", methods=["GET"])
def search_posts():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"error": "Query parameter 'q' is required"}), 400

    tag_type = request.args.get("type", "").strip().lower()
    valid_types = {"location", "subject", "course"}

    try:
        page     = max(1, int(request.args.get("page", 1)))
        per_page = min(100, max(1, int(request.args.get("per_page", 20))))
    except ValueError:
        return jsonify({"error": "page and per_page must be integers"}), 400

    offset  = (page - 1) * per_page
    keyword = f"%{q}%"           # wrap for LIKE
    params  = [keyword]

    # Optionally restrict to a specific tag type
    type_clause = ""
    if tag_type in valid_types:
        type_clause = "AND t.type = %s"
        params.append(tag_type)

    where = f"""
        WHERE EXISTS (
            SELECT 1
            FROM post_tags pt
            JOIN tags t ON pt.tag_id = t.id
            WHERE pt.post_id = p.id
              AND t.name LIKE %s
              {type_clause}
        )
    """

    count_sql = f"SELECT COUNT(*) AS total FROM posts p {where}"

    data_sql = f"""
        SELECT
            p.id,
            p.title,
            p.body,
            p.created_at,
            -- Aggregate all tags on the post (not just matching ones)
            JSON_ARRAYAGG(
                JSON_OBJECT('id', t.id, 'name', t.name, 'type', t.type)
            ) AS tags
        FROM posts p
        LEFT JOIN post_tags pt ON pt.post_id = p.id
        LEFT JOIN tags t       ON t.id = pt.tag_id
        {where}
        GROUP BY p.id, p.title, p.body, p.created_at
        ORDER BY p.created_at DESC
        LIMIT %s OFFSET %s
    """

    try:
        conn   = get_db()
        cursor = conn.cursor(dictionary=True)

        # Count
        cursor.execute(count_sql, params)
        total = cursor.fetchone()["total"]

        # Data
        cursor.execute(data_sql, params + [per_page, offset])
        posts = cursor.fetchall()

        import json
        for post in posts:
            if isinstance(post.get("tags"), str):
                post["tags"] = json.loads(post["tags"])
            if post["tags"]:
                post["tags"] = [t for t in post["tags"] if t and t.get("id")]
            if post.get("created_at"):
                post["created_at"] = post["created_at"].isoformat()

        cursor.close()
        conn.close()

        return jsonify({
            "query":    q,
            "posts":    posts,
            "total":    total,
            "page":     page,
            "per_page": per_page,
            "pages":    (total + per_page - 1) // per_page,
        })

    except mysql.connector.Error as e:
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# GET /api/search/suggestions?q=<keyword>
#
# Returns matching tag names only — lightweight, ideal for
# powering a live dropdown as the user types.
# ---------------------------------------------------------------------------
@app.route("/api/search/suggestions", methods=["GET"])
def search_suggestions():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify([])

    tag_type   = request.args.get("type", "").strip().lower()
    valid_types = {"location", "subject", "course"}
    keyword    = f"%{q}%"
    params     = [keyword]

    type_clause = ""
    if tag_type in valid_types:
        type_clause = "AND type = %s"
        params.append(tag_type)

    sql = f"""
        SELECT name, type, COUNT(pt.post_id) AS post_count
        FROM tags t
        LEFT JOIN post_tags pt ON pt.tag_id = t.id
        WHERE t.name LIKE %s
          {type_clause}
        GROUP BY t.id, t.name, t.type
        ORDER BY post_count DESC, t.name
        LIMIT 10
    """

    try:
        conn   = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(sql, params)
        suggestions = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(suggestions)

    except mysql.connector.Error as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)