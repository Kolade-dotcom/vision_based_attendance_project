from flask import Blueprint, request
from api.controllers.student_controller import enroll_student_logic, get_students_logic, update_student_logic, delete_student_logic

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
