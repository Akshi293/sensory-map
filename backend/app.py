from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)

app = Flask(__name__,
            static_folder=os.path.join(ROOT_DIR, 'frontend', 'static'),
            static_url_path='/static',
            template_folder=os.path.join(ROOT_DIR, 'frontend', 'templates'))
CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


class Place(db.Model):
    __tablename__ = 'places'

    id               = db.Column(db.Integer, primary_key=True)
    place_name       = db.Column(db.String(200), nullable=False)
    latitude         = db.Column(db.Float, nullable=False)
    longitude        = db.Column(db.Float, nullable=False)
    noise_level      = db.Column(db.Integer, nullable=False)
    crowd_level      = db.Column(db.Integer, nullable=False)
    lighting_level   = db.Column(db.Integer, nullable=False)
    sensory_score    = db.Column(db.Integer, nullable=False)
    sensory_category = db.Column(db.String(20), nullable=False)
    note             = db.Column(db.Text, nullable=True)
    created_at       = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id':               self.id,
            'place_name':       self.place_name,
            'latitude':         self.latitude,
            'longitude':        self.longitude,
            'noise_level':      self.noise_level,
            'crowd_level':      self.crowd_level,
            'lighting_level':   self.lighting_level,
            'sensory_score':    self.sensory_score,
            'sensory_category': self.sensory_category,
            'note':             self.note,
            'created_at':       self.created_at.isoformat(),
        }


def calculate_sensory_score(noise, crowd, lighting):
    return noise + crowd + lighting


def determine_category(score):
    if 3 <= score <= 6:
        return 'Calm'
    elif 7 <= score <= 10:
        return 'Moderate'
    else:
        return 'Overwhelming'


def validate_level(value, name):
    if not isinstance(value, int):
        return f'{name} must be an integer.'
    if not (1 <= value <= 5):
        return f'{name} must be between 1 and 5.'
    return None


@app.route('/')
def index():
    return send_from_directory(app.template_folder, 'index.html')


@app.route('/api/tags', methods=['POST'])
def create_tag():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data received.'}), 400

    place_name     = data.get('place_name', '').strip()
    latitude       = data.get('latitude')
    longitude      = data.get('longitude')
    noise_level    = data.get('noise_level')
    crowd_level    = data.get('crowd_level')
    lighting_level = data.get('lighting_level')
    note           = data.get('note', '').strip()

    if not place_name:
        return jsonify({'error': 'place_name is required.'}), 400
    if latitude is None or longitude is None:
        return jsonify({'error': 'latitude and longitude are required.'}), 400

    for value, name in [(noise_level, 'noise_level'),
                        (crowd_level, 'crowd_level'),
                        (lighting_level, 'lighting_level')]:
        err = validate_level(value, name)
        if err:
            return jsonify({'error': err}), 400

    score    = calculate_sensory_score(noise_level, crowd_level, lighting_level)
    category = determine_category(score)

    place = Place(
        place_name       = place_name,
        latitude         = latitude,
        longitude        = longitude,
        noise_level      = noise_level,
        crowd_level      = crowd_level,
        lighting_level   = lighting_level,
        sensory_score    = score,
        sensory_category = category,
        note             = note or None,
    )
    db.session.add(place)
    db.session.commit()
    return jsonify(place.to_dict()), 201


@app.route('/api/tags', methods=['GET'])
def get_tags():
    places = Place.query.order_by(Place.created_at.desc()).all()
    return jsonify([p.to_dict() for p in places]), 200


@app.route('/api/tags/<int:tag_id>', methods=['DELETE'])
def delete_tag(tag_id):
    place = Place.query.get(tag_id)
    if not place:
        return jsonify({'error': 'Tag not found.'}), 404
    db.session.delete(place)
    db.session.commit()
    return jsonify({'message': 'Deleted successfully.'}), 200


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)