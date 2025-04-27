from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import json

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    name = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    subscription_tier = db.Column(db.String(20), default='free')
    last_login = db.Column(db.DateTime, nullable=True)
    streak_count = db.Column(db.Integer, default=0)
    last_workout = db.Column(db.DateTime, nullable=True)

    bmi_records = db.relationship('BMIHistory', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def update_streak(self):
        try:
            if not self.last_workout:
                self.streak_count = 1
            else:
                days_difference = (datetime.utcnow() - self.last_workout).days
                if days_difference <= 1:
                    self.streak_count += 1
                elif days_difference > 1:
                    self.streak_count = 1
            self.last_workout = datetime.utcnow()
        except Exception as e:
            print(f"Error updating streak: {e}")
            self.streak_count = 1
            self.last_workout = datetime.utcnow()

class UserProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    age = db.Column(db.Integer)
    height = db.Column(db.Float)
    weight = db.Column(db.Float)
    fitness_level = db.Column(db.String(20))
    goals = db.Column(db.String(200))
    calorie_goal = db.Column(db.Integer, default=2000)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('profile', uselist=False))

class BMIHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    height = db.Column(db.Float, nullable=False)
    weight = db.Column(db.Float, nullable=False)
    bmi = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'height': self.height,
            'weight': self.weight,
            'bmi': self.bmi,
            'date': self.date.strftime('%Y-%m-%d %H:%M:%S')
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

    def to_calendar_dict(self):
        duration_minutes = round(self.duration / 60) if self.duration else 0
        return {
            'id': self.id,
            'date': self.date.strftime('%Y-%m-%d'),
            'time': self.date.strftime('%I:%M %p'),
            'duration': duration_minutes,
            'calories_burned': round(self.calories_burned, 1) if self.calories_burned else 0,
            'avg_heart_rate': round(self.avg_heart_rate, 1) if self.avg_heart_rate else None,
            'exercise_data': self.exercise_data or {},
            'is_completed': self.is_completed
        }

class PasswordReset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    token = db.Column(db.String(100), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)

    def __init__(self, user_id, token):
        self.user_id = user_id
        self.token = token
        self.expires_at = datetime.utcnow() + timedelta(hours=24)

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

class Subscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    stripe_customer_id = db.Column(db.String(255), unique=True)
    stripe_subscription_id = db.Column(db.String(255), unique=True)
    plan_type = db.Column(db.String(50), default='free')
    status = db.Column(db.String(50))
    current_period_end = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    cancel_at_period_end = db.Column(db.Boolean, default=False)

    user = db.relationship('User', backref=db.backref('subscription', uselist=False))

    def is_active(self):
        return self.status == 'active' and (self.current_period_end is None or self.current_period_end > datetime.utcnow())

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

def to_calendar_dict(self):
    return {
        'id': self.id,
        'date': self.date.strftime('%Y-%m-%d'),
        'time': self.date.strftime('%I:%M %p'),
        'duration': int(self.duration or 0) // 60,
        'calories_burned': round(float(self.calories_burned or 0), 1),
        'avg_heart_rate': round(float(self.avg_heart_rate or 0), 1) if self.avg_heart_rate else None,
        'exercise_data': self.exercise_data,
        'is_completed': self.is_completed
    }

class ShareableLink(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    token = db.Column(db.String(64), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True)

    from_date = db.Column(db.DateTime, nullable=True)
    to_date = db.Column(db.DateTime, nullable=True)

    user = db.relationship('User', backref='share_links')

    def is_valid(self):
        if self.expires_at and self.expires_at < datetime.utcnow():
            return False
        return True
