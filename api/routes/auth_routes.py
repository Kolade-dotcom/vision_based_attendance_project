from flask import Blueprint, request
from api.controllers.auth_controller import login_logic, signup_logic, logout_logic

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    return login_logic(data)

@auth_bp.route('/auth/signup', methods=['POST'])
def signup():
    data = request.get_json()
    return signup_logic(data)

@auth_bp.route('/auth/logout', methods=['GET'])
def logout():
    return logout_logic()
