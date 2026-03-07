from flask import session

def get_current_user():
    """Return the currently logged-in username (or None).

    Uses session data set during `/login`. This keeps all login checks
    consistent in one place.
    """
    if not session.get("logged_in"):
        return None
    return session.get("username")
