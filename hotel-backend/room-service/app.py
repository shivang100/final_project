# rooms-service app.py
import os
import json
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager, jwt_required, get_jwt
from werkzeug.utils import secure_filename
from models import db, Room

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI', 'sqlite:///rooms.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'Shivang100@')
CORS(app)

# Upload config
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

db.init_app(app)
jwt = JWTManager(app)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS



with app.app_context():
    db.create_all()


@app.route('/api/upload-image', methods=['POST'])
@jwt_required()
def upload_image():
    if 'image' not in request.files:
        return jsonify({'error': 'No image file provided'}), 400
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        url = f'/uploads/{filename}'
        return jsonify({'url': url})
    return jsonify({'error': 'File type not allowed'}), 400

@app.route('/uploads/<path:filename>')
def serve_uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/api/rooms', methods=['GET'])
@jwt_required()
def list_rooms():
    rooms = Room.query.all()
    return jsonify([room.to_dict() for room in rooms])

@app.route('/api/rooms/<int:room_id>', methods=['GET'])
@jwt_required()
def get_room(room_id):
    room = Room.query.get(room_id)
    if not room:
        return jsonify({'error': 'Room not found'}), 404
    return jsonify(room.to_dict())

@app.route('/api/rooms', methods=['POST'])
@jwt_required()
def create_room():
    claims = get_jwt()
    role = claims.get('role')
    if role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    data = request.get_json()
    room = Room(
        name=data['name'],
        room_type=data['room_type'],
        description=data.get('description', ''),
        price_per_day=data['price_per_day'],
        price_per_hour=data.get('price_per_hour', 0),
        main_image=data.get('main_image', ''),
        secondary_images=json.dumps(data.get('secondary_images', []))
    )
    db.session.add(room)
    db.session.commit()
    return jsonify(room.to_dict()), 201

@app.route('/api/rooms/<int:room_id>', methods=['PUT'])
@jwt_required()
def update_room(room_id):
    claims = get_jwt()
    role = claims.get('role')
    if role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    room = Room.query.get_or_404(room_id)
    data = request.get_json()
    for key in ['name', 'room_type', 'description', 'price_per_day', 'price_per_hour', 'main_image', 'secondary_images']:
        if key in data:
            if key == 'secondary_images':
                setattr(room, key, json.dumps(data[key]))
            else:
                setattr(room, key, data[key])
    db.session.commit()
    return jsonify(room.to_dict())

@app.route('/api/rooms/<int:room_id>', methods=['DELETE'])
@jwt_required()
def delete_room(room_id):
    claims = get_jwt()
    role = claims.get('role')
    if role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    room = Room.query.get_or_404(room_id)
    db.session.delete(room)
    db.session.commit()
    return jsonify({'message': 'Room deleted'})

@app.get('/healthz')
def healthz():
    return {"ok": True}, 200

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(port=5002, debug=True)
