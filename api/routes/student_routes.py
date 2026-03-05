from flask import Blueprint, request
from api.controllers.student_controller import (
    enroll_student_logic, 
    get_students_logic, 
    update_student_logic, 
    delete_student_logic,
    approve_student_logic,
    reject_student_logic,
    get_pending_count_logic
)

student_bp = Blueprint('student', __name__)

@student_bp.route('/students', methods=['GET'])
def get_students():
    return get_students_logic()

@student_bp.route('/enroll', methods=['POST'])
def enroll_student():
    data = request.get_json()
    return enroll_student_logic(data)

@student_bp.route('/students/<path:student_id>', methods=['PUT'])
def update_student(student_id):
    data = request.get_json()
    return update_student_logic(student_id, data)

@student_bp.route('/students/<path:student_id>', methods=['DELETE'])
def delete_student(student_id):
    return delete_student_logic(student_id)


# Approval Workflow Routes
@student_bp.route('/students/<path:student_id>/approve', methods=['POST'])
def approve_student(student_id):
    """Approve a pending student enrollment."""
    return approve_student_logic(student_id)

@student_bp.route('/students/<path:student_id>/reject', methods=['POST'])
def reject_student(student_id):
    """Reject a pending student enrollment."""
    data = request.get_json() or {}
    return reject_student_logic(student_id, data)

@student_bp.route('/students/pending/count', methods=['GET'])
def get_pending_count():
    """Get count of pending student enrollments."""
    return get_pending_count_logic()

