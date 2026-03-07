from decorators.auth import require_jwt, require_api_key
from utils.profile import get_profile_data, set_profile, get_profile_doc_ref
from utils.validation import require_json_content_type, validate_profile_data, normalize_profile_data
from firebase import db
from firebase_admin import firestore
from flask import request, jsonify
import time
import re
from . import api_bp

@api_bp.get("/profile")
@require_jwt
def api_get_profile(uid: str):
    """Return the current user's profile."""
    profile_data = get_profile_data(uid)
    return jsonify({"uid": uid, "profile": profile_data}), 200


@api_bp.post("/profile")
@require_jwt
def api_create_profile(uid: str):
    """Create/replace the current user's profile from a JSON body."""
    content_error = require_json_content_type()
    if content_error:
        return content_error

    data = request.get_json(silent=True) or {}
    first_name = data.get("first_name", "")
    last_name = data.get("last_name", "")
    student_id = data.get("student_id", "")

    error = validate_profile_data(first_name, last_name, student_id)
    if error:
        return jsonify({"error": error}), 400

    normalized = normalize_profile_data(first_name, last_name, student_id)
    set_profile(uid, normalized, merge=False)
    return jsonify({"message": "Profile saved successfully", "profile": normalized}), 200


@api_bp.put("/profile")
@require_jwt
def api_update_profile(uid: str):
    """Update the current user's profile from a JSON body.

    Implements strict input validation:
    - Whitelist: Only allows first_name, last_name, student_id fields
    - Bounds checking: Names max 50 chars, student_id must be 8-9 alphanumeric
    - Collects all errors before returning
    """
    content_error = require_json_content_type()
    if content_error:
        return content_error

    data = request.get_json(silent=True) or {}
    if not data:
        return jsonify({"error": "Request body cannot be empty"}), 400

    # Whitelist of allowed fields
    allowed_fields = {"first_name", "last_name", "student_id"}

    # Check for invalid fields
    invalid_fields = set(data.keys()) - allowed_fields
    errors = []

    if invalid_fields:
        errors.append(f"Invalid field(s): {', '.join(sorted(invalid_fields))}. Only first_name, last_name, and student_id are allowed.")

    first_name = data.get("first_name")
    last_name = data.get("last_name")
    student_id = data.get("student_id")

    # Validate first_name if provided
    if first_name is not None:
        first_name = first_name.strip() if first_name else ""
        if len(first_name) > 50:
            errors.append("first_name must not exceed 50 characters")

    # Validate last_name if provided
    if last_name is not None:
        last_name = last_name.strip() if last_name else ""
        if len(last_name) > 50:
            errors.append("last_name must not exceed 50 characters")

    # Validate student_id if provided
    if student_id is not None:
        student_id = str(student_id).strip() if student_id else ""
        if student_id:  # Only validate format if not empty
            if not (len(student_id) == 8 or len(student_id) == 9):
                errors.append("student_id must be exactly 8 or 9 characters")
            elif not re.match(r'^[a-zA-Z0-9]+$', student_id):
                errors.append("student_id must contain only alphanumeric characters")

    # Return all errors at once if any
    if errors:
        return jsonify({"errors": errors}), 400

    # Prepare the update data (only include provided fields)
    update_data = {}
    if first_name is not None:
        update_data["first_name"] = first_name
    if last_name is not None:
        update_data["last_name"] = last_name
    if student_id is not None:
        update_data["student_id"] = student_id

    if not update_data:
        return jsonify({"error": "No updatable fields provided"}), 400

    # Merge update into existing document (or create if missing).
    set_profile(uid, update_data, merge=True)

    updated_profile = get_profile_data(uid)
    return jsonify({"message": "Profile updated successfully", "profile": updated_profile}), 200


@api_bp.delete("/profile")
@require_jwt
def api_delete_profile(uid: str):
    """Delete the current user's profile."""
    get_profile_doc_ref(uid).delete()
    return jsonify({"message": "Profile deleted successfully"}), 200


@api_bp.route("/sensor_data", methods=["POST"])
@require_api_key
def api_post_sensor_data(uid: str):
    """Receive sensor data from IoT devices (requires API key authentication)."""
    content_error = require_json_content_type()
    if content_error:
        return content_error

    data = request.get_json(silent=True) or {}

    # Validate that we received some data
    if not data:
        return jsonify({"error": "Request body cannot be empty"}), 400

    # Store sensor data in Firestore (you can customize the collection name)
    # Using a timestamp-based document ID for uniqueness
    doc_id = str(int(time.time() * 1000))
    db.collection("sensor_data").document(doc_id).set({
        "data": data,
        "timestamp": firestore.SERVER_TIMESTAMP
    })

    return jsonify({"message": "Sensor data received successfully", "id": doc_id}), 201