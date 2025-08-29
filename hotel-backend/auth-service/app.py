# auth-service app.py
import os
from datetime import timedelta
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import (
    JWTManager, create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity, get_jwt
)
from models import db, User  # assumes models.py defines SQLAlchemy db and User

app = Flask(__name__)

# --- Core config (now env-driven) ---
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI', 'sqlite:///auth.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'Shivang100@')

# --- Token expirations ---
app.config['JWT_ACCESS_TOKEN_EXPIRES']  = timedelta(minutes=30)
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=7)

db.init_app(app)
jwt = JWTManager(app)
CORS(app, resources={r"/api/*": {"origins": "*"}})


with app.app_context():
    db.create_all()


@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    username = data.get('username', '').strip().lower()
    email    = data.get('email', '').strip().lower()
    password = data.get('password', '')
    if not username or not email or not password:
        return jsonify({'msg': 'username, email, and password are required'}), 400
    if User.query.filter_by(username=username).first():
        return jsonify({'msg': 'Username already exists'}), 400
    user = User(username=username, email=email, role=data.get('role', 'customer'))
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    access_token  = create_access_token(identity=str(user.id),
                                        additional_claims={"role": user.role, "email": user.email})
    refresh_token = create_refresh_token(identity=str(user.id),
                                         additional_claims={"role": user.role, "email": user.email})
    return jsonify({
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": {
            "id": user.id, "username": user.username, "email": user.email, "role": user.role
        }
    }), 201

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    username = (data.get('username') or '').strip().lower()
    password = data.get('password') or ''
    user = User.query.filter_by(username=username).first()
    if user and user.check_password(password):
        access_token  = create_access_token(identity=str(user.id),
                                            additional_claims={"role": user.role, "email": user.email})
        refresh_token = create_refresh_token(identity=str(user.id),
                                             additional_claims={"role": user.role, "email": user.email})
        return jsonify({
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": {"id": user.id, "username": user.username, "email": user.email, "role": user.role}
        }), 200
    return jsonify({'msg': 'Invalid username or password'}), 401

@app.route('/api/auth/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    user_id = get_jwt_identity()
    claims  = get_jwt()
    new_access = create_access_token(
        identity=user_id,
        additional_claims={"role": claims.get("role"), "email": claims.get("email")}
    )
    return jsonify(access_token=new_access), 200

@app.route('/api/protected/me', methods=['GET'])
@jwt_required()
def me():
    user_id = get_jwt_identity()
    claims  = get_jwt()
    return jsonify({"id": user_id, "role": claims.get('role'), "email": claims.get('email')}), 200

@app.get('/healthz')
def healthz():
    return {"ok": True}, 200

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(port=5001, debug=True)
