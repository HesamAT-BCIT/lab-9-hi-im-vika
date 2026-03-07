from flask import request, jsonify, render_template, session, redirect, url_for
from . import auth_bp
import requests
from config import Config

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Login page. Supports both web form and JSON API login."""
    if request.method == "GET":
        return render_template("login.html")

    # Handle JSON API login
    if request.is_json:
        return api_login()

    # Handle web form login
    email = request.form.get("email")
    password = request.form.get("password")

    if not email or not password:
        return render_template("login.html", error="Email and password are required")

    # Use Firebase Identity REST API to authenticate
    try:
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={Config.WEB_API_KEY}"
        payload = {
            "email": email,
            "password": password,
            "returnSecureToken": True
        }

        res = requests.post(url, json=payload, timeout=10)

        if res.status_code == 200:
            token_data = res.json()
            # For web sessions, we'll use the uid from the response
            uid = token_data.get("localId")
            session["logged_in"] = True
            session["username"] = uid
            session["email"] = email
            session["jwt_token"] = token_data.get("idToken")
            return redirect(url_for("dashboard.home"))

        error_data = res.json().get("error", {})
        error_message = error_data.get("message", "Invalid credentials")
        if "INVALID_LOGIN_CREDENTIALS" in error_message:
            error_message = "Invalid email or password"
        return render_template("login.html", error=error_message)
    except requests.RequestException:
        return render_template("login.html", error="Authentication service unavailable")

@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    """Signup page for creating new user accounts."""
    if request.method == "GET":
        return render_template("signup.html")

    # Handle form submission (web)
    if request.content_type and "application/json" in request.content_type:
        return api_signup()

    email = request.form.get("email")
    password = request.form.get("password")
    confirm_password = request.form.get("confirm_password")

    # Validate passwords match
    if password != confirm_password:
        return render_template("signup.html", error="Passwords do not match")

    # Validate required fields
    if not email or not password:
        return render_template("signup.html", error="Email and password are required")

    try:
        # Create user with Firebase Admin SDK
        user = auth.create_user(email=email, password=password)

        # Initialize profile in Firestore
        db.collection("profiles").document(user.uid).set({
            "email": email,
            "role": "user"
        })

        return redirect(url_for("auth.login"))
    except Exception as e:
        error_message = str(e)
        if "email-already-exists" in error_message:
            error_message = "An account with this email already exists"
        elif "invalid-email" in error_message:
            error_message = "Invalid email address"
        elif "weak-password" in error_message:
            error_message = "Password is too weak. Please use a stronger password"
        return render_template("signup.html", error=error_message)

@auth_bp.route("/logout")
def logout():
    """Clear the session and return to login."""
    session.clear()
    return redirect(url_for("auth.login"))

def api_signup():
    """JSON API endpoint for user registration."""
    data = request.get_json(silent=True) or {}

    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    try:
        # Create user with Firebase Admin SDK
        user = auth.create_user(email=email, password=password)

        # Initialize profile in Firestore
        db.collection("profiles").document(user.uid).set({
            "email": email,
            "role": "user"
        })

        return jsonify({"message": "User created successfully", "uid": user.uid}), 201
    except Exception as e:
        error_message = str(e)
        if "email-already-exists" in error_message:
            return jsonify({"error": "An account with this email already exists"}), 400
        elif "invalid-email" in error_message:
            return jsonify({"error": "Invalid email address"}), 400
        elif "weak-password" in error_message:
            return jsonify({"error": "Password is too weak"}), 400
        return jsonify({"error": "Failed to create user"}), 400

def api_login():
    """JSON API endpoint for login. Returns a JWT token."""
    data = request.get_json(silent=True) or {}

    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={Config.WEB_API_KEY}"
    payload = {
        "email": email,
        "password": password,
        "returnSecureToken": True
    }

    try:
        res = requests.post(url, json=payload, timeout=10)

        if res.status_code == 200:
            return jsonify({"token": res.json()["idToken"]}), 200

        return jsonify({"error": "Invalid credentials"}), 401
    except requests.RequestException:
        return jsonify({"error": "Authentication service unavailable"}), 503