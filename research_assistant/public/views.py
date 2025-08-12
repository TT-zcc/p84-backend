# -*- coding: utf-8 -*-
"""Public section, including homepage and signup (API version)."""

import random
import string

from flask import Blueprint, current_app, jsonify, request
from flask_login import login_required, login_user, logout_user
from flask_mail import Message
from flask_jwt_extended import create_access_token

from research_assistant.extensions import bcrypt, csrf_protect, db, login_manager, mail
from research_assistant.user.models import EmailCaptcha, User

blueprint = Blueprint("public", __name__, static_folder="../static")

@blueprint.route("/logout/", methods=["POST"])
@login_required
def logout():
    """
    API endpoint for logging out the current user.
    """
    logout_user()
    return jsonify({
        "code": 0,
        "msg": "Logout successful"
    })


@csrf_protect.exempt
@blueprint.route("/captcha/email/", methods=["GET", "POST"])
def send_email_captcha():
    """
    Request an email verification code.
    Expected JSON body or query: {"email": "user@example.com"}
    """
    email = (request.args.get("email")
             if request.method == "GET"
             else (request.get_json() or {}).get("email"))
    if not email:
        return jsonify({"code": 400, "message": "Email is required"}), 400

    code = "".join(random.choices(string.digits, k=6))
    try:
        msg = Message(
            subject="[Research Assistant] Verification Code",
            recipients=[email],
            body=f"Your code is: {code}. Valid for 10 minutes."
        )
        mail.send(msg)
    except Exception as e:
        current_app.logger.error(f"Failed to send email: {e}")
        return jsonify({"code": 500, "message": "Failed to send email"}), 500

    cap = EmailCaptcha(email=email, captcha=code)
    db.session.add(cap)
    db.session.commit()
    return jsonify({"code": 200, "message": "Verification code sent successfully"})


@csrf_protect.exempt
@blueprint.route("/password/reset/", methods=["POST"])
def reset_password():
    """
    Reset user password.
    Expected JSON body:
    {
      "email": "...",
      "captcha": "...",
      "new_password": "..."
    }
    """
    data = request.get_json() or {}
    email = data.get("email")
    captcha = data.get("captcha")
    new_password = data.get("new_password")

    if not all([email, captcha, new_password]):
        return jsonify({
            "code": 400,
            "message": "Email, captcha, and new_password are all required"
        }), 400

    record = (
        EmailCaptcha.query
                    .filter_by(email=email, captcha=captcha)
                    .order_by(EmailCaptcha.created_at.desc())
                    .first()
    )
    if not record:
        return jsonify({"code": 400, "message": "Invalid or expired captcha"}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"code": 404, "message": "Email not registered"}), 404

    user.password = new_password  # or bcrypt.generate_password_hash(...)
    db.session.commit()
    return jsonify({"code": 200, "message": "Password reset successfully"})
