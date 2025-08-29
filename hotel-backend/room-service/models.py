from flask_sqlalchemy import SQLAlchemy
import json

db = SQLAlchemy()

class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    room_type = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    price_per_day = db.Column(db.Float, nullable=False)
    price_per_hour = db.Column(db.Float, default=0)
    main_image = db.Column(db.String(250))
    secondary_images = db.Column(db.Text)  # JSON string list

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'room_type': self.room_type,
            'description': self.description,
            'price_per_day': self.price_per_day,
            'price_per_hour': self.price_per_hour,
            'main_image': self.main_image,
            'secondary_images': json.loads(self.secondary_images) if self.secondary_images else []
        }
