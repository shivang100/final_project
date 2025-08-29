# models.py
from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy()

class Booking(db.Model):
    __tablename__ = 'bookings'
    id = db.Column(db.Integer, primary_key=True)


    customer_id = db.Column(db.Integer, nullable=False, index=True)
    room_id = db.Column(db.Integer, nullable=False, index=True)
    booking_mode = db.Column(db.String(10), nullable=False)  
    check_in_date = db.Column(db.Date)
    check_out_date = db.Column(db.Date)
    booking_date = db.Column(db.Date)
    start_time = db.Column(db.Time)
    duration_hours = db.Column(db.Integer)
    status = db.Column(db.String(30), default='pending')

    bill_full_name   = db.Column(db.String(120), nullable=False)
    bill_email       = db.Column(db.String(120), nullable=False)
    bill_phone       = db.Column(db.String(30),  nullable=False)
    bill_gstin       = db.Column(db.String(20))

    bill_address1    = db.Column(db.String(200), nullable=False)
    bill_address2    = db.Column(db.String(200))
    bill_city        = db.Column(db.String(100), nullable=False)
    bill_state       = db.Column(db.String(100), nullable=False)
    bill_postal_code = db.Column(db.String(20),  nullable=False)
    bill_country     = db.Column(db.String(80),  nullable=False, default='India')

    def to_dict(self):
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "room_id": self.room_id,
            "booking_mode": self.booking_mode,
            "check_in_date": self.check_in_date.isoformat() if self.check_in_date else None,
            "check_out_date": self.check_out_date.isoformat() if self.check_out_date else None,
            "booking_date": self.booking_date.isoformat() if self.booking_date else None,
            "start_time": self.start_time.strftime("%H:%M") if self.start_time else None,
            "duration_hours": self.duration_hours,
            "status": self.status,

            "billing": {
                "fullName": self.bill_full_name,
                "email": self.bill_email,
                "phone": self.bill_phone,
                "gstin": self.bill_gstin,
                "address1": self.bill_address1,
                "address2": self.bill_address2,
                "city": self.bill_city,
                "state": self.bill_state,
                "postalCode": self.bill_postal_code,
                "country": self.bill_country,
            }
        }
