from flask import Blueprint, jsonify, request

from flask_jwt_extended import (
    create_access_token,
    jwt_required,
    get_jwt_identity
)
from research_assistant.extensions import db
from research_assistant.user.models import User

blueprint = Blueprint("user", __name__, url_prefix="/users", static_folder="../static")


@blueprint.route("/register", methods=["POST"])
def register():
    """
    registered user
    """
    data = request.get_json()
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    if not username or not email or not password:
        return jsonify({"msg": "Missing fields"}), 400

    # Check if username already exists
    if User.query.filter_by(username=username).first():
        return jsonify({"msg": "Username already exists"}), 400

    # Check if email already exists
    if User.query.filter_by(email=email).first():
        return jsonify({"msg": "Email already exists"}), 400


    user = User(username=username, email=email)
    user.password = password  # Set password using encryption method
    db.session.add(user)
    db.session.flush()  # Flush to get user.id before committing
    
    return jsonify({"msg": "Registration successful"}), 200


@blueprint.route("/login", methods=["POST"])
def login():
    """
    For logged-in users, return a JWT token
    """
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    user = User.query.filter_by(username=username).first()
    if user and user.check_password(password):
        access_token = create_access_token(identity=str(user.id))
        return jsonify(access_token=access_token), 200

    return jsonify({"msg": "Invalid username or password"}), 401
