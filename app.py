import os
import pickle
import threading
import sqlite3
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, request, render_template, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash

# import your local modules
from chefbot.model import ChefRecommender
from chefbot.nutrition_model import NutritionTrainer

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

# Paths
RECIPE_PKL = "chefbot_model.pkl"
NUTRITION_PKL = "chefbot_nutrition.pkl"
DB_PATH = "chefbot_users.db"

# Globals
MODEL: ChefRecommender = None
nut_trainer: NutritionTrainer | None = None

# ============ DATABASE SETUP ============
def init_db():
    """Initialize SQLite database with users table."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_searches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            ingredients TEXT,
            max_time INTEGER,
            target_calories INTEGER,
            target_protein INTEGER,
            searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    conn.commit()
    conn.close()
    print("✅ Database initialized")

init_db()

# ============ AUTH DECORATOR ============
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({"error": "Authentication required", "redirect": "/login"}), 401
        return f(*args, **kwargs)
    return decorated_function

# ============ MODEL LOADING ============
def load_recipe_model():
    """Load a saved recipe model if present; otherwise return a fresh ChefRecommender."""
    if os.path.exists(RECIPE_PKL):
        try:
            with open(RECIPE_PKL, "rb") as f:
                m = pickle.load(f)
            setattr(m, "fitted", True)
            setattr(m, "_fitting", False)
            print(f"✅ Loaded pre-trained recipe model from {RECIPE_PKL}")
            return m
        except Exception as e:
            print(f"⚠️ Failed to load recipe model from {RECIPE_PKL}: {e}")
    print("⚠️ No saved recipe model loaded — creating a new ChefRecommender instance.")
    m = ChefRecommender()
    m.fitted = False
    m._fitting = False
    return m

def start_recipe_background_fit():
    """Start background fitting of the recipe model if needed."""
    global MODEL
    if MODEL is None or getattr(MODEL, "fitted", False) or getattr(MODEL, "_fitting", False):
        return

    def _fit_and_save():
        try:
            MODEL._fitting = True
            print("🚀 Background recipe model fitting started...")
            MODEL.fit(data_folder="data")
            with open(RECIPE_PKL, "wb") as f:
                pickle.dump(MODEL, f)
            print(f"✅ Recipe model fitted and saved to {RECIPE_PKL}")
            MODEL.fitted = True
        except Exception as e:
            print(f"❌ Background recipe fit failed: {e}")
        finally:
            MODEL._fitting = False

    threading.Thread(target=_fit_and_save, daemon=True).start()

def load_nutrition_model():
    """Try to load nutrition model if present."""
    if os.path.exists(NUTRITION_PKL):
        try:
            nt = NutritionTrainer()
            nt.load(NUTRITION_PKL)
            print(f"✅ Loaded nutrition model from {NUTRITION_PKL}")
            return nt
        except Exception as e:
            print(f"⚠️ Failed to load nutrition model: {e}")
            return None
    print("⚠️ No nutrition model found.")
    return None

MODEL = load_recipe_model()
nut_trainer = load_nutrition_model()

# ============ AUTH ROUTES ============
@app.route("/")
def landing():
    """Landing page - redirects to login or main app."""
    if 'user_id' in session:
        return redirect(url_for('index'))
    return redirect(url_for('login_page'))

@app.route("/login")
def login_page():
    """Render login page."""
    if 'user_id' in session:
        return redirect(url_for('index'))
    return render_template("login.html")

@app.route("/register")
def register_page():
    """Render registration page."""
    if 'user_id' in session:
        return redirect(url_for('index'))
    return render_template("register.html")

@app.route("/api/register", methods=["POST"])
def api_register():
    """Handle user registration."""
    data = request.get_json()
    username = data.get("username", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "").strip()

    if not username or not email or not password:
        return jsonify({"error": "All fields are required"}), 400
    
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        password_hash = generate_password_hash(password)
        cursor.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
            (username, email, password_hash)
        )
        conn.commit()
        user_id = cursor.lastrowid
        
        # Auto-login after registration
        session['user_id'] = user_id
        session['username'] = username
        session.permanent = True
        
        return jsonify({"success": True, "redirect": "/app"})
    except sqlite3.IntegrityError:
        return jsonify({"error": "Username or email already exists"}), 400
    finally:
        conn.close()

@app.route("/api/login", methods=["POST"])
def api_login():
    """Handle user login."""
    data = request.get_json()
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, password_hash FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    
    if user and check_password_hash(user[2], password):
        # Update last login
        cursor.execute("UPDATE users SET last_login = ? WHERE id = ?", (datetime.now(), user[0]))
        conn.commit()
        
        session['user_id'] = user[0]
        session['username'] = user[1]
        session.permanent = True
        
        conn.close()
        return jsonify({"success": True, "redirect": "/app"})
    
    conn.close()
    return jsonify({"error": "Invalid username or password"}), 401

@app.route("/logout")
def logout():
    """Handle user logout."""
    session.clear()
    return redirect(url_for('login_page'))

# ============ MAIN APP ROUTES ============
@app.route("/app")
@login_required
def index():
    """Main application page."""
    start_recipe_background_fit()
    return render_template("index.html", username=session.get('username'))

@app.route("/model_status")
@login_required
def model_status():
    """Check model status."""
    return jsonify({
        "fitted": bool(getattr(MODEL, "fitted", False)),
        "fitting": bool(getattr(MODEL, "_fitting", False)),
        "nutrition_loaded": bool(nut_trainer is not None)
    })

@app.route("/recommend", methods=["POST"])
@login_required
def recommend():
    """Basic recipe recommendations."""
    global MODEL
    if MODEL is None or not getattr(MODEL, "fitted", False):
        return jsonify({"error": "Model is still loading. Please wait.", "results": []}), 503

    data = request.get_json() or request.form
    ingredients = data.get("ingredients", "")
    max_time = data.get("max_time", None)
    is_veg = data.get("is_veg", None)

    # Log search
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO user_searches (user_id, ingredients, max_time) VALUES (?, ?, ?)",
            (session['user_id'], ingredients, max_time)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Failed to log search: {e}")

    filters = {}
    if max_time is not None and str(max_time).strip() != "":
        try:
            filters["max_time"] = float(max_time)
        except:
            pass
    if is_veg is not None:
        if isinstance(is_veg, str):
            filters["is_veg"] = is_veg.lower() in ("1", "true", "yes", "y")
        else:
            filters["is_veg"] = bool(is_veg)

    try:
        results = MODEL.recommend(ingredients, top_k=12, filters=filters)
        return jsonify({"results": results})
    except Exception as e:
        print(f"Error in /recommend: {e}")
        return jsonify({"error": str(e), "results": []}), 500

@app.route("/recommend_with_nutrition", methods=["POST"])
@login_required
def recommend_with_nutrition():
    """Nutrition-aware recommendation."""
    global MODEL, nut_trainer
    if MODEL is None or not getattr(MODEL, "fitted", False):
        return jsonify({"error": "Recipe model is still loading."}), 503

    req = request.get_json() or request.form
    ingredients = req.get("ingredients", "")
    max_time = req.get("max_time", None)
    nutrition_target = req.get("nutrition_target", {}) or {}
    try:
        tolerance = float(req.get("tolerance", 0.2))
    except:
        tolerance = 0.2

    # Log search with nutrition data
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO user_searches (user_id, ingredients, max_time, target_calories, target_protein) VALUES (?, ?, ?, ?, ?)",
            (session['user_id'], ingredients, max_time, 
             nutrition_target.get('calories'), nutrition_target.get('protein'))
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Failed to log search: {e}")

    filters = {}
    if max_time is not None and str(max_time).strip() != "":
        try:
            filters["max_time"] = float(max_time)
        except:
            pass

    candidates = MODEL.recommend(ingredients, top_k=60, filters=filters)
    if not candidates:
        return jsonify({"results": []})

    texts = []
    for c in candidates:
        ing = c.get("ingredients", "") or ""
        instr = c.get("instructions", "") or ""
        title = c.get("title", "") or ""
        texts.append(ing + " " + instr + " " + title)

    preds = None
    target_names = []

    if nut_trainer is not None:
        try:
            preds = nut_trainer.predict_for_texts(texts)
            target_names = list(nut_trainer.targets)
        except Exception as e:
            print(f"⚠️ Nutrition model prediction failed: {e}")
            preds = None

    if preds is None:
        first = candidates[0]
        possible = ["calories", "protein", "fat", "carbs"]
        target_names = [k for k in possible if k in first]
        import numpy as np
        preds_list = []
        for r in candidates:
            row_vals = []
            for tn in target_names:
                try:
                    row_vals.append(float(r.get(tn, 0) or 0))
                except:
                    row_vals.append(0.0)
            preds_list.append(row_vals)
        preds = np.array(preds_list) if preds_list else None

    if preds is None or len(target_names) == 0:
        for r in candidates:
            r["nutrition_pred"] = {}
            r["nutrition_distance"] = None
        return jsonify({"results": candidates[:12]})

    import numpy as np
    def compute_distance(pred_row):
        total = 0.0
        count = 0.0
        for i, tn in enumerate(target_names):
            if tn in nutrition_target:
                try:
                    target_val = float(nutrition_target[tn])
                except:
                    continue
                pred_val = float(pred_row[i])
                if target_val != 0:
                    d = abs(pred_val - target_val) / target_val
                else:
                    d = abs(pred_val - target_val)
                total += d
                count += 1.0
        if count == 0:
            return float("inf")
        return total / count

    scored = []
    for row, pred in zip(candidates, preds):
        dist = compute_distance(pred)
        out = row.copy()
        out["nutrition_pred"] = {tn: float(pred[i]) for i, tn in enumerate(target_names)}
        out["nutrition_distance"] = float(dist) if np.isfinite(dist) else None
        scored.append(out)

    scored_sorted = sorted(scored, key=lambda x: (x["nutrition_distance"] is None, x["nutrition_distance"] or 1e9))
    
    if nutrition_target:
        filtered = [r for r in scored_sorted if (r["nutrition_distance"] is not None and r["nutrition_distance"] <= tolerance)]
        results = filtered if filtered else scored_sorted[:12]
    else:
        results = scored_sorted[:12]

    return jsonify({"results": results})

@app.route("/api/user_stats")
@login_required
def user_stats():
    """Get user search history stats."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM user_searches WHERE user_id = ?",
        (session['user_id'],)
    )
    search_count = cursor.fetchone()[0]
    conn.close()
    
    return jsonify({
        "username": session.get('username'),
        "total_searches": search_count
    })

if __name__ == "__main__":
    start_recipe_background_fit()
    print("🚀 Starting ChefBot server on http://127.0.0.1:5000")
    app.run(debug=True)