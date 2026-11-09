from pathlib import Path
import os
import sqlite3
from functools import wraps
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import joblib
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "aquaguard.db"
MODEL_PATH = BASE_DIR / "aquaguard_ai_model.joblib"

FEATURES = [
    "ph", "Hardness", "Solids", "Chloramines", "Sulfate",
    "Conductivity", "Organic_carbon", "Trihalomethanes", "Turbidity"
]
DISPLAY_NAMES = {
    "ph": "pH", "Hardness": "Hardness", "Solids": "Solids",
    "Chloramines": "Chloramines", "Sulfate": "Sulfate",
    "Conductivity": "Conductivity", "Organic_carbon": "Organic carbon",
    "Trihalomethanes": "Trihalomethanes", "Turbidity": "Turbidity"
}

app = Flask(__name__)
app.secret_key = os.environ.get("AQUAGUARD_SECRET_KEY", "change-this-local-dev-secret-before-deployment")
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)

_model = None
_model_error = None

def get_db():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection

def init_db():
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                prediction INTEGER NOT NULL,
                probability_0 REAL,
                probability_1 REAL,
                parameters_json TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)

def load_model():
    global _model, _model_error
    if _model is not None:
        return _model
    if not MODEL_PATH.exists():
        _model_error = "Model file nahi mili. aquaguard_ai_model.joblib ko app.py ke same folder mein copy karo."
        return None
    try:
        _model = joblib.load(MODEL_PATH)
        _model_error = None
        return _model
    except Exception as exc:
        _model_error = f"Model load nahi hua: {exc}"
        app.logger.exception("Could not load model")
        return None

def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    with get_db() as db:
        return db.execute("SELECT id, name, email, created_at FROM users WHERE id = ?", (user_id,)).fetchone()

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please login to open your dashboard.", "info")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped

def page_context(active):
    model_ready = load_model() is not None
    return {"active": active, "user": current_user(), "model_ready": model_ready,
            "model_message": "Model connected" if model_ready else (_model_error or "Model offline")}

@app.get("/")
def index():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if len(name) < 2 or len(name) > 80:
            flash("Name 2 se 80 characters ke beech hona chahiye.", "error")
        elif "@" not in email or len(email) > 180:
            flash("Valid email address enter karo.", "error")
        elif len(password) < 8:
            flash("Password kam se kam 8 characters ka rakho.", "error")
        else:
            try:
                with get_db() as db:
                    db.execute(
                        "INSERT INTO users(name,email,password_hash,created_at) VALUES(?,?,?,?)",
                        (name, email, generate_password_hash(password), datetime.now().isoformat(timespec="seconds"))
                    )
                flash("Account ban gaya! Ab login karo.", "success")
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                flash("Is email se account pehle se bana hua hai.", "error")
    return render_template("auth.html", mode="signup")

@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        with get_db() as db:
            user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            flash("Welcome back! Login successful.", "success")
            return redirect(url_for("dashboard"))
        flash("Email ya password sahi nahi hai.", "error")
    return render_template("auth.html", mode="login")

@app.get("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))

@app.get("/dashboard")
@login_required
def dashboard():
    ctx = page_context("dashboard")
    with get_db() as db:
        rows = db.execute("SELECT * FROM predictions WHERE user_id=? ORDER BY id DESC LIMIT 5",
                          (session["user_id"],)).fetchall()
        totals = db.execute("""
            SELECT COUNT(*) AS total,
                   SUM(CASE WHEN prediction=1 THEN 1 ELSE 0 END) AS potable,
                   SUM(CASE WHEN prediction=0 THEN 1 ELSE 0 END) AS not_potable
            FROM predictions WHERE user_id=?
        """, (session["user_id"],)).fetchone()
    ctx.update(recent=rows, total=totals["total"] or 0, potable=totals["potable"] or 0,
               not_potable=totals["not_potable"] or 0)
    return render_template("dashboard.html", **ctx)

@app.get("/predict")
@login_required
def predict_page():
    return render_template("predict.html", **page_context("predict"))

@app.post("/api/predict")
@login_required
def api_predict():
    model = load_model()
    if model is None:
        return jsonify({"error": _model_error or "Model unavailable"}), 503
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "Valid JSON data bhejo."}), 400
    try:
        row = {}
        for feature in FEATURES:
            if feature not in payload:
                return jsonify({"error": f"Parameter missing hai: {feature}"}), 400
            value = float(payload[feature])
            if pd.isna(value):
                raise ValueError(f"{DISPLAY_NAMES[feature]} valid number hona chahiye.")
            row[feature] = value
        if not 0 <= row["ph"] <= 14:
            return jsonify({"error": "pH ki value 0 se 14 ke beech honi chahiye."}), 400
        for feature in FEATURES[1:]:
            if row[feature] < 0:
                return jsonify({"error": f"{DISPLAY_NAMES[feature]} negative nahi ho sakta."}), 400

        sample = pd.DataFrame([row], columns=FEATURES)
        prediction = int(model.predict(sample)[0])
        probs = {}
        if hasattr(model, "predict_proba"):
            values = model.predict_proba(sample)[0]
            classes = getattr(model, "classes_", [0, 1])
            probs = {str(int(cls)): float(prob) for cls, prob in zip(classes, values)}
        p0 = probs.get("0")
        p1 = probs.get("1")

        import json
        with get_db() as db:
            cursor = db.execute("""
                INSERT INTO predictions(user_id,created_at,prediction,probability_0,probability_1,parameters_json)
                VALUES(?,?,?,?,?,?)
            """, (session["user_id"], datetime.now().isoformat(timespec="seconds"), prediction,
                  p0, p1, json.dumps(row)))
            prediction_id = cursor.lastrowid

        return jsonify({
            "id": prediction_id,
            "prediction": prediction,
            "label": "Potable class" if prediction == 1 else "Not potable class",
            "probabilities": {key: round(value, 4) for key, value in probs.items()},
            "created_at": datetime.now().strftime("%d %b %Y, %I:%M %p")
        })
    except (TypeError, ValueError) as exc:
        return jsonify({"error": str(exc) or "Har field mein valid number enter karo."}), 400
    except Exception as exc:
        app.logger.exception("Prediction failed")
        return jsonify({"error": f"Prediction nahi ho paya: {exc}"}), 500

@app.get("/history")
@login_required
def history():
    import json
    with get_db() as db:
        rows = db.execute("SELECT * FROM predictions WHERE user_id=? ORDER BY id DESC",
                          (session["user_id"],)).fetchall()
    records = []
    for row in rows:
        item = dict(row)
        try:
            item["parameters"] = json.loads(item["parameters_json"])
        except Exception:
            item["parameters"] = {}
        records.append(item)
    return render_template("history.html", **page_context("history"), records=records)

@app.get("/analytics")
@login_required
def analytics():
    with get_db() as db:
        rows = db.execute("SELECT prediction, created_at FROM predictions WHERE user_id=? ORDER BY id",
                          (session["user_id"],)).fetchall()
    labels = [row["created_at"][:10] for row in rows]
    values = [int(row["prediction"]) for row in rows]
    return render_template("analytics.html", **page_context("analytics"),
                           total=len(rows), potable=sum(values), not_potable=len(values)-sum(values),
                           chart_labels=labels, chart_values=values)

@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user = current_user()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if len(name) < 2 or len(name) > 80:
            flash("Name 2 se 80 characters ke beech hona chahiye.", "error")
        else:
            with get_db() as db:
                db.execute("UPDATE users SET name=? WHERE id=?", (name, session["user_id"]))
            flash("Profile updated.", "success")
            return redirect(url_for("profile"))
    with get_db() as db:
        count = db.execute("SELECT COUNT(*) FROM predictions WHERE user_id=?", (session["user_id"],)).fetchone()[0]
    return render_template("profile.html", **page_context("profile"), prediction_count=count)

@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    if request.method == "POST":
        # Settings page currently stores only browser display preferences locally.
        flash("Settings saved for this session.", "success")
    return render_template("settings.html", **page_context("settings"))

@app.get("/api/health")
def health():
    model = load_model()
    return jsonify({"ok": model is not None, "model_loaded": model is not None,
                    "message": "Model connected" if model is not None else _model_error}), (200 if model is not None else 503)

@app.errorhandler(404)
def not_found(_):
    return render_template("error.html", code=404, message="Page nahi mila.", user=current_user()), 404

init_db()

if __name__ == "__main__":
    # Local development only; use a production WSGI server for deployment.
    app.run(host="127.0.0.1", port=5000, debug=False)
