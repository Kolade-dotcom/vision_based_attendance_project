from flask import Blueprint, request, session, jsonify
from api.routes.dashboard_routes import dashboard_login_required
import db_helper

dashboard_api_bp = Blueprint("dashboard_api", __name__, url_prefix="/api/dashboard")


@dashboard_api_bp.route("/analytics/trend")
@dashboard_login_required
def attendance_trend():
    course = request.args.get("course")
    user_id = session["user_id"]
    data = db_helper.get_attendance_trend(user_id, course)
    return jsonify(data)


@dashboard_api_bp.route("/analytics/leaderboard")
@dashboard_login_required
def student_leaderboard():
    course = request.args.get("course")
    user_id = session["user_id"]
    data = db_helper.get_student_leaderboard(user_id, course)
    return jsonify(data)


@dashboard_api_bp.route("/courses")
@dashboard_login_required
def courses():
    user_id = session["user_id"]
    all_courses = db_helper.get_lecturer_courses(user_id)
    recent = db_helper.get_recent_session_courses(user_id, limit=2)
    return jsonify({"courses": all_courses, "recent": recent})


@dashboard_api_bp.route("/settings", methods=["GET"])
@dashboard_login_required
def get_settings():
    return jsonify(db_helper.get_user_settings(session["user_id"]))


@dashboard_api_bp.route("/settings", methods=["PUT"])
@dashboard_login_required
def update_settings():
    db_helper.update_user_settings(session["user_id"], request.json)
    return jsonify({"status": "success"})


@dashboard_api_bp.route("/account", methods=["PUT"])
@dashboard_login_required
def update_account():
    data = request.json
    db_helper.update_user_account(
        session["user_id"], name=data.get("name"), email=data.get("email")
    )
    if data.get("name"):
        session["user_name"] = data["name"]
    if data.get("email"):
        session["user_email"] = data["email"]
    return jsonify({"status": "success"})


@dashboard_api_bp.route("/password", methods=["PUT"])
@dashboard_login_required
def change_password():
    from werkzeug.security import check_password_hash, generate_password_hash

    data = request.json
    user = db_helper.get_user_by_email(session["user_email"])
    if not user or not check_password_hash(
        user["password_hash"], data.get("current_password", "")
    ):
        return jsonify({"error": "Current password is incorrect"}), 401
    if len(data.get("new_password", "")) < 6:
        return jsonify({"error": "New password must be at least 6 characters"}), 400
    db_helper.update_user_password(
        session["user_id"], generate_password_hash(data["new_password"])
    )
    return jsonify({"status": "success"})


@dashboard_api_bp.route("/courses/search")
@dashboard_login_required
def search_courses():
    q = request.args.get("q", "")
    results = db_helper.search_all_course_codes(q)
    return jsonify(results)
