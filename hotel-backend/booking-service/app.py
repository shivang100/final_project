# bookings-service app.py
import os
import requests
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity, get_jwt
from models import db, Booking

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI', 'sqlite:///bookings.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'Shivang100@')

db.init_app(app)
jwt = JWTManager(app)
CORS(app)

ROOMS_BASE_URL = os.getenv('ROOMS_BASE_URL', 'http://localhost:5002')




with app.app_context():
    db.create_all()


@app.route('/')
def index():
    return jsonify({"message": "Booking Service running"})

def fetch_room(room_id: int):
    try:
        headers = {}
        auth_header = request.headers.get("Authorization")
        if auth_header:
            headers["Authorization"] = auth_header
        r = requests.get(f"{ROOMS_BASE_URL}/api/rooms/{room_id}", headers=headers, timeout=5)
        if r.status_code == 200:
            return r.json()
        return None
    except Exception:
        return None

def enrich_booking_dict(b_dict: dict) -> dict:
    room_id = b_dict.get("room_id")
    if not room_id:
        return b_dict
    room = fetch_room(room_id)
    if room:
        b_dict["room_name"] = room.get("name")
        b_dict["room_type"] = room.get("room_type")
        b_dict["room_main_image"] = room.get("main_image")
    return b_dict

@app.post('/api/bookings')
@jwt_required()
def create_booking():
    data = request.get_json() or {}
    user_id = get_jwt_identity()
    claims = get_jwt()
    user_role = claims.get('role')
    if user_role not in ['customer', 'admin']:
        return jsonify({"error": "Insufficient permissions"}), 403
    booking_mode = data.get('booking_mode')
    if booking_mode not in ['hourly', 'daily']:
        return jsonify({"error": "Invalid booking mode"}), 400

    billing = data.get('billing') or {}
    required_billing = ['fullName','email','phone','address1','city','state','postalCode','country']
    missing_b = [k for k in required_billing if not billing.get(k)]
    if missing_b:
        return jsonify({"error": f"Missing billing fields: {', '.join(missing_b)}"}), 400

    required_fields = ['room_id']
    if booking_mode == 'hourly':
        required_fields += ['start_time', 'duration_hours']
    else:
        required_fields += ['check_in_date', 'check_out_date']
    missing = [field for field in required_fields if field not in data]
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400

    try:
        check_in = check_out = None
        start_time = None
        duration_hours = None

        if booking_mode == 'daily':
            check_in = datetime.strptime(data['check_in_date'], "%Y-%m-%d").date()
            check_out = datetime.strptime(data['check_out_date'], "%Y-%m-%d").date()
            if check_in >= check_out:
                return jsonify({"error": "Check-in date must be before check-out date"}), 400
            conflicting_booking = Booking.query.filter(
                Booking.room_id == int(data['room_id']),
                Booking.check_out_date > check_in,
                Booking.check_in_date < check_out,
            ).first()
            if conflicting_booking:
                return jsonify({"error": "Booking dates overlap with existing booking"}), 409

        if booking_mode == 'hourly':
            start_time = datetime.strptime(data['start_time'], "%H:%M").time()
            try:
                duration_hours = int(data['duration_hours'])
            except ValueError:
                return jsonify({"error": "Invalid duration_hours, must be integer"}), 400

        booking = Booking(
            customer_id=int(user_id),
            room_id=int(data['room_id']),
            booking_mode=booking_mode,
            check_in_date=check_in if booking_mode == 'daily' else None,
            check_out_date=check_out if booking_mode == 'daily' else None,
            booking_date=datetime.utcnow().date(),
            start_time=start_time if booking_mode == 'hourly' else None,
            duration_hours=duration_hours if booking_mode == 'hourly' else None,
            status=data.get('status', 'pending'),
            bill_full_name=billing.get('fullName'),
            bill_email=billing.get('email'),
            bill_phone=billing.get('phone'),
            bill_gstin=billing.get('gstin'),
            bill_address1=billing.get('address1'),
            bill_address2=billing.get('address2'),
            bill_city=billing.get('city'),
            bill_state=billing.get('state'),
            bill_postal_code=billing.get('postalCode'),
            bill_country=billing.get('country') or 'India',
        )
        db.session.add(booking)
        db.session.commit()
        created = enrich_booking_dict(booking.to_dict())
        return jsonify(created), 201

    except ValueError:
        return jsonify({"error": "Invalid date or time format"}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.get('/api/bookings')
@jwt_required()
def list_bookings():
    user_id = get_jwt_identity()
    claims = get_jwt()
    user_role = claims.get('role')
    bookings = Booking.query.all() if user_role == 'admin' else Booking.query.filter_by(customer_id=int(user_id)).all()
    result = [enrich_booking_dict(b.to_dict()) for b in bookings]
    return jsonify(result), 200

@app.get('/api/bookings/<int:booking_id>')
@jwt_required()
def get_booking(booking_id):
    user_id = int(get_jwt_identity())
    claims = get_jwt()
    user_role = claims.get('role')
    booking = Booking.query.get_or_404(booking_id)
    if user_role != 'admin' and booking.customer_id != user_id:
        return jsonify({"error": "Insufficient permissions"}), 403
    b = enrich_booking_dict(booking.to_dict())
    return jsonify(b), 200

@app.put('/api/bookings/<int:booking_id>')
@jwt_required()
def update_booking(booking_id):
    data = request.get_json()
    user_id = int(get_jwt_identity())
    claims = get_jwt()
    user_role = claims.get('role')
    booking = Booking.query.get_or_404(booking_id)

    if user_role == 'customer' and booking.customer_id != user_id:
        return jsonify({"error": "Insufficient permissions"}), 403

    if user_role == 'customer' and 'status' in data:
        if data['status'] != 'cancellation_requested':
            return jsonify({"error": "Insufficient permissions to update status"}), 403

    if 'check_in_date' in data and 'check_out_date' in data:
        try:
            check_in = datetime.strptime(data['check_in_date'], '%Y-%m-%d').date()
            check_out = datetime.strptime(data['check_out_date'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({"error": "Invalid date format, expected YYYY-MM-DD"}), 400
        if check_in >= check_out:
            return jsonify({"error": "Check-in date must be before check-out date"}), 400
        conflicting_booking = Booking.query.filter(
            Booking.room_id == booking.room_id,
            Booking.id != booking.id,
            Booking.check_out_date > check_in,
            Booking.check_in_date < check_out,
        ).first()
        if conflicting_booking:
            return jsonify({"error": "Booking dates overlap with existing booking"}), 409

    for key in ['status', 'check_in_date', 'check_out_date', 'start_time', 'duration_hours']:
        if key in data:
            if 'date' in key:
                booking_date = datetime.strptime(data[key], '%Y-%m-%d').date()
                setattr(booking, key, booking_date)
            elif key == 'start_time':
                setattr(booking, key, datetime.strptime(data[key], '%H:%M').time())
            elif key == 'duration_hours':
                try:
                    setattr(booking, key, int(data[key]))
                except ValueError:
                    return jsonify({"error": "Invalid duration_hours, must be integer"}), 400
            else:
                setattr(booking, key, data[key])

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Database error: " + str(e)}), 500

    b = enrich_booking_dict(booking.to_dict())
    return jsonify(b), 200

@app.delete('/api/bookings/<int:booking_id>')
@jwt_required()
def delete_booking(booking_id):
    claims = get_jwt()
    user_role = claims.get('role')
    if user_role != 'admin':
        return jsonify({"error": "Admin privileges required"}), 403
    booking = Booking.query.get_or_404(booking_id)
    try:
        db.session.delete(booking)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Database error: " + str(e)}), 500
    return '', 204

@app.get('/healthz')
def healthz():
    return {"ok": True}, 200

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(port=5003, debug=True)
