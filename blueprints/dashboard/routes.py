import utils.profile, utils.validation, utils.auth
from . import dashboard_bp
from flask import request, url_for, redirect, render_template

@dashboard_bp.route("/")
def home():
    """Home page. Redirects to login if no active session."""
    current_user = get_current_user()
    if current_user:
        profile_data = get_profile_data(current_user)
        return render_template("dashboard.html", first_name=profile_data.get('first_name', ''), jwt_token=session.get('jwt_token'))
    return redirect(url_for("login"))
