from flask import Blueprint, jsonify, request
import db_helper
import base64
import os

worker_bp = Blueprint("worker", __name__, url_prefix="/api/worker")

WORKER_API_KEY = os.environ.get("WORKER_API_KEY", "dev-worker-key")


def _check_worker_key():
    key = request.headers.get("X-Worker-Key")
    if key != WORKER_API_KEY:
        return jsonify({"error": "Unauthorized"}), 401
    return None


@worker_bp.route("/faces")
def get_faces():
    """Return all enrolled student face encodings for the worker."""
    auth_err = _check_worker_key()
    if auth_err:
        return auth_err

    students = db_helper.get_all_student_encodings()
    result = []
    for s in students:
        if s["face_encoding"]:
            encoding_data = s["face_encoding"]
            if isinstance(encoding_data, memoryview):
                encoding_data = bytes(encoding_data)
            result.append({
                "student_id": s["student_id"],
                "name": s["name"],
                "face_encoding": base64.b64encode(encoding_data).decode("ascii"),
            })
    return jsonify(result)
