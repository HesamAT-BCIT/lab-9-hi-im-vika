from utils.auth import get_current_user
from utils.profile import get_profile_data
from flask import session, redirect, url_for, render_template
from . import dashboard_bp

@dashboard_bp.route("/")
def home():
    """Home page. Redirects to login if no active session."""
    current_user = get_current_user()
    if current_user:
        profile_data = get_profile_data(current_user)
        return render_template("dashboard.html", first_name=profile_data.get('first_name', ''), jwt_token=session.get('jwt_token'))
    return redirect(url_for("auth.login"))
