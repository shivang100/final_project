# api-gateway app.py
import os
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from flask_jwt_extended import JWTManager, verify_jwt_in_request
import requests

app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'Shivang100@')
jwt = JWTManager(app)
CORS(app)

# Use env so this works in Docker/K8s
SERVICES = {
    'auth':    os.getenv('AUTH_URL',    'http://localhost:5001'),
    'room':    os.getenv('ROOM_URL',    'http://localhost:5002'),
    'booking': os.getenv('BOOKING_URL', 'http://localhost:5003'),
}

def proxy_request(service_url, path):
    method = request.method
    url = f"{service_url}{path}"
    headers = {key: value for key, value in request.headers if key.lower() != 'host'}
    data = request.get_data()
    params = request.args

    resp = requests.request(
        method, url,
        headers=headers,
        params=params,
        data=data,
        cookies=request.cookies,
        allow_redirects=False,
    )

    excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
    # using resp.headers is fine; your original used resp.raw.headers – both work
    response_headers = [(name, value) for (name, value) in resp.headers.items()
                        if name.lower() not in excluded_headers]
    return Response(resp.content, resp.status_code, response_headers)

@app.before_request
def verify_token():
    if request.path.startswith('/healthz'):
        return
    if request.path.startswith('/api/auth'):
        return
    if request.path.startswith('/api/'):
        print("Authorization header:", request.headers.get('Authorization'))
        try:
            verify_jwt_in_request()
        except Exception as e:
            print("JWT verification error:", str(e))
            return jsonify({"msg": "Missing or invalid token"}), 401

# Auth service routes
@app.route('/api/auth/register', methods=['POST'])
def auth_register():
    return proxy_request(SERVICES['auth'], '/api/auth/register')

@app.route('/api/auth/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
def auth_route(path):
    return proxy_request(SERVICES['auth'], f'/api/auth/{path}')

# Room service routes
@app.route('/api/rooms', methods=['GET', 'POST'])
def room_root():
    return proxy_request(SERVICES['room'], '/api/rooms')

@app.route('/api/rooms/<int:room_id>', methods=['GET', 'PUT', 'DELETE'])
def room_id_route(room_id):
    return proxy_request(SERVICES['room'], f'/api/rooms/{room_id}')

# Booking service routes
@app.route('/api/bookings', methods=['GET', 'POST'])
def booking_root():
    return proxy_request(SERVICES['booking'], '/api/bookings')

@app.route('/api/bookings/<int:booking_id>', methods=['GET', 'PUT', 'DELETE'])
def booking_id_route(booking_id):
    return proxy_request(SERVICES['booking'], f'/api/bookings/{booking_id}')

@app.get('/healthz')
def healthz():
    return {"ok": True}, 200

if __name__ == '__main__':
    app.run(port=5000, debug=True)
