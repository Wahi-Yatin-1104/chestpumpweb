from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    name = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    subscription_tier = db.Column(db.String(20), default='basic')  # 'basic' or 'premium'
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class PasswordReset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    token = db.Column(db.String(100), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)

    def __init__(self, user_id, token):
        self.user_id = user_id
        self.token = token
        self.expires_at = datetime.utcnow() + timedelta(hours=24)
        
class OneRepMax(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    exercise = db.Column(db.String(20), nullable=False)
    weight = db.Column(db.Float, nullable=False)
    reps = db.Column(db.Integer, nullable=False)
    estimated_one_rep_max = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref=db.backref('one_rep_maxes', lazy=True))
    
    def to_dict(self):
        return {
            'id': self.id,
            'exercise': self.exercise,
            'weight': self.weight,
            'reps': self.reps,
            'estimated_one_rep_max': self.estimated_one_rep_max,
            'date': self.date.strftime('%Y-%m-%d %H:%M:%S')
        }
    
class MealLog(db.Model):
    __tablename__ = 'meal_log'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    meal_type = db.Column(db.String(20), nullable=False)
    food_name = db.Column(db.String(100), nullable=False)
    calories = db.Column(db.Float, nullable=False)
    proteins = db.Column(db.Float, default=0)
    carbs = db.Column(db.Float, default=0)
    fats = db.Column(db.Float, default=0)
    
    user = db.relationship('User', backref=db.backref('meal_logs', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'date': self.date.strftime('%Y-%m-%d %H:%M:%S'),
            'meal_type': self.meal_type,
            'food_name': self.food_name,
            'calories': float(self.calories),
            'proteins': float(self.proteins) if self.proteins is not None else None,
            'carbs': float(self.carbs) if self.carbs is not None else None,
            'fats': float(self.fats) if self.fats is not None else None
        }
    
class WorkoutSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    duration = db.Column(db.Integer, default=0)
    calories_burned = db.Column(db.Float, default=0.0)
    avg_heart_rate = db.Column(db.Float, default=0.0)
    exercise_data = db.Column(db.JSON, default=lambda: {})
    is_completed = db.Column(db.Boolean, default=False)
    
    user = db.relationship('User', backref='workout_sessions')

    def to_dict(self):
        return {
            'id': self.id,
            'date': self.date.isoformat(),
            'duration': self.duration,
            'calories_burned': self.calories_burned,
            'avg_heart_rate': self.avg_heart_rate,
            'exercise_data': self.exercise_data,
            'is_completed': self.is_completed
        }