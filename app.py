import os
import secrets
import time
import json
import traceback
import csv
import io
from io import BytesIO
import base64 
from datetime import datetime, timedelta
from functools import wraps


from flask import (
    Flask, render_template, Response, jsonify, request,
    redirect, url_for, flash, session, make_response, send_file
)
from flask_sqlalchemy import SQLAlchemy 
from flask_login import (
    LoginManager, login_user, logout_user, login_required, current_user
)
from flask_mail import Mail, Message
from flask_migrate import Migrate
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from flask_wtf import FlaskForm 

from werkzeug.security import generate_password_hash, check_password_hash

from models import (
    db, User, UserProfile, WorkoutSession, PasswordReset,
    BMIHistory, MealLog, Subscription, OneRepMax, ShareableLink 
)

from forms import (
    ResetPasswordRequestForm, ResetPasswordForm,
    ChangeEmailForm, ChangePasswordForm, EditProfileForm, EditGoalsForm 
)

from subscription_routes import subscription_bp
from subscription_middleware import premium_required

import cv2
import mediapipe as mp
import numpy as np
import stripe
from dotenv import load_dotenv
from dateutil.relativedelta import relativedelta 
from weasyprint import HTML, CSS 
from weasyprint.text.fonts import FontConfiguration 
import matplotlib 
matplotlib.use('Agg') 
import matplotlib.pyplot as plt 
import matplotlib.dates as mdates 

from sqlalchemy import func, desc


load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True') == 'True'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')

db.init_app(app)
mail = Mail(app) 
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
migrate = Migrate(app, db)
socketio = SocketIO(app) 
stripe.api_key = os.getenv('STRIPE_SECRET_KEY') 


socketio = SocketIO(app)

mp_pose = mp.solutions.pose
mp_draw = mp.solutions.drawing_utils

app.register_blueprint(subscription_bp, url_prefix='/subscription')
CORS(app)

mode = "sq"
cnt = 0
pos = None
total_reps = {
    "sq": 0, "cu": 0, "pu": 0, "lu": 0, "pl": 0, "cr": 0, "mc": 0, "jj": 0, "bp": 0, "dl": 0, "bp": 0, "op": 0, "br": 0, "fs": 0
}
cal_burnt = 0
workout_start = None
current_workout_session = None

def workout_session_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        global current_workout_session
        if current_workout_session is None:
            return jsonify({'success': False, 'error': 'No active workout session'}), 400
        return f(*args, **kwargs)
    return decorated_function

@login_manager.user_loader
def load_user(user_id):
    try:
        return db.session.get(User, int(user_id))
    except Exception as e:
        print(f"Error loading user: {e}")
        return None

def get_ang(a, b, c):
    if not all([a, b, c]): return 0
    a = np.array([a.x, a.y])
    b = np.array([b.x, b.y])
    c = np.array([c.x, c.y])
    rad = np.arctan2(c[1] - b[1], c[0] - b[0]) - np.arctan2(a[1] - b[1], a[0] - b[0])
    ang = np.abs(rad * 180.0 / np.pi)
    if ang > 180.0: ang = 360 - ang
    return ang

def check_sq(pts):
    hip = pts[mp_pose.PoseLandmark.LEFT_HIP.value]
    knee = pts[mp_pose.PoseLandmark.LEFT_KNEE.value]
    ankle = pts[mp_pose.PoseLandmark.LEFT_ANKLE.value]
    shoulder = pts[mp_pose.PoseLandmark.LEFT_SHOULDER.value]

    k_ang = get_ang(hip, knee, ankle)
    b_ang = get_ang(shoulder, hip, knee)
    knee_dist = np.sqrt((knee.x - ankle.x) ** 2 + (knee.y - ankle.y) ** 2)

    issues = []
    if b_ang < 160:
        issues.append("back not straight")
    if k_ang < 90:
        issues.append("squat too deep")
    if knee_dist > 0.3:
        issues.append("knees over toes")
    if k_ang > 170:
        return "up", not bool(issues), issues
    elif k_ang < 100:
        return "down", not bool(issues), issues
    return None, True, issues

def check_pu(pts):
   shoulder = pts[mp_pose.PoseLandmark.LEFT_SHOULDER.value]
   elbow = pts[mp_pose.PoseLandmark.LEFT_ELBOW.value]
   wrist = pts[mp_pose.PoseLandmark.LEFT_WRIST.value]
   hip = pts[mp_pose.PoseLandmark.LEFT_HIP.value]
   ankle = pts[mp_pose.PoseLandmark.LEFT_ANKLE.value]

   a_ang = get_ang(shoulder, elbow, wrist)
   b_ang = get_ang(shoulder, hip, ankle)
   hip_sag = abs(hip.y - shoulder.y)

   issues = []
   if not 160 < b_ang < 200: issues.append("body not straight")
   if hip_sag > 0.1: issues.append("hips sagging")
   if a_ang > 160: issues.append("go lower")

   if a_ang > 150:
       return "up", not bool(issues), issues
   elif a_ang < 90:
       return "down", not bool(issues), issues
   return None, True, issues

def check_cu(pts):
    shoulder = pts[mp_pose.PoseLandmark.RIGHT_SHOULDER.value]
    elbow = pts[mp_pose.PoseLandmark.RIGHT_ELBOW.value]
    wrist = pts[mp_pose.PoseLandmark.RIGHT_WRIST.value]

    ang = get_ang(shoulder, elbow, wrist)
    drift = abs(elbow.x - shoulder.x)
    wrist_mov = abs(wrist.x - elbow.x)

    issues = []
    if drift > 0.1: issues.append("elbows out")
    if wrist_mov > 0.15: issues.append("wrist not stable")
    if ang > 160: issues.append("extend fully")

    if ang > 150:
        return "down", not bool(issues), issues
    elif ang < 60:
        return "up", not bool(issues), issues
    return None, True, issues

def check_lunge(pts):
    left_hip = pts[mp_pose.PoseLandmark.LEFT_HIP.value]
    left_knee = pts[mp_pose.PoseLandmark.LEFT_KNEE.value]
    left_ankle = pts[mp_pose.PoseLandmark.LEFT_ANKLE.value]
    right_knee = pts[mp_pose.PoseLandmark.RIGHT_KNEE.value]
    right_ankle = pts[mp_pose.PoseLandmark.RIGHT_ANKLE.value]
    shoulder = pts[mp_pose.PoseLandmark.LEFT_SHOULDER.value]

    front_knee_angle = get_ang(left_hip, left_knee, left_ankle)
    back_knee_angle = get_ang(left_hip, right_knee, right_ankle)
    torso_angle = get_ang(shoulder, left_hip, left_knee)

    issues = []
    if front_knee_angle > 100:
        issues.append("bend front knee more")
    if back_knee_angle > 100:
        issues.append("lower back knee")
    if torso_angle < 160:
        issues.append("keep torso upright")
    if front_knee_angle > 150 and back_knee_angle > 150:
        return "up", not bool(issues), issues
    elif front_knee_angle < 100 and back_knee_angle < 100:
        return "down", not bool(issues), issues
    return None, True, issues

def check_plank(pts):
    shoulder = pts[mp_pose.PoseLandmark.LEFT_SHOULDER.value]
    elbow = pts[mp_pose.PoseLandmark.LEFT_ELBOW.value]
    hip = pts[mp_pose.PoseLandmark.LEFT_HIP.value]
    knee = pts[mp_pose.PoseLandmark.LEFT_KNEE.value]
    ankle = pts[mp_pose.PoseLandmark.LEFT_ANKLE.value]
    
    arm_angle = get_ang(shoulder, elbow, hip)
    body_angle = get_ang(shoulder, hip, ankle)
    leg_angle = get_ang(hip, knee, ankle)

    issues = []
    if arm_angle < 75 or arm_angle > 105:
        issues.append("align shoulders over elbows")
    if body_angle < 160:
        issues.append("straighten body")
    if leg_angle < 160:
        issues.append("straighten legs")
    if arm_angle >= 75 and arm_angle <= 105 and body_angle >= 160 and leg_angle >= 160:
        return "hold", not bool(issues), issues
    return None, True, issues

def check_crunch(pts):
    shoulder = pts[mp_pose.PoseLandmark.LEFT_SHOULDER.value]
    hip = pts[mp_pose.PoseLandmark.LEFT_HIP.value]
    knee = pts[mp_pose.PoseLandmark.LEFT_KNEE.value]
    ankle = pts[mp_pose.PoseLandmark.LEFT_ANKLE.value]

    trunk_angle = get_ang(shoulder, hip, knee)
    leg_angle = get_ang(hip, knee, ankle)

    issues = []
    if leg_angle > 100:
        issues.append("keep knees bent")
    if trunk_angle > 130:
        issues.append("crunch higher")
    if trunk_angle > 150:
        return "down", not bool(issues), issues
    elif trunk_angle < 110:
        return "up", not bool(issues), issues
    return None, True, issues

def check_exercise(pts):
    global cnt, pos, total_reps, cal_burnt, mode, current_workout_session

    new_pos = None
    good = True
    issues = []

    if mode == "sq":
        new_pos, good, issues = check_sq(pts)
    elif mode == "cu":
        new_pos, good, issues = check_cu(pts)
    elif mode == "pu":
        new_pos, good, issues = check_pu(pts)

    if new_pos != pos:
        if pos and good:
            calories = {"sq": 0.32, "cu": 0.15, "pu": 0.28}[mode]
            cal_burnt += calories
            
            with app.app_context():
                try:
                    if current_workout_session:
                        current_workout_session.calories_burned = round(cal_burnt, 2)
                        
                        if workout_start:
                            current_duration = int(time.time() - workout_start)
                            current_workout_session.duration = current_duration
                        
                        exercise_data = current_workout_session.exercise_data or {}
                        exercise_data[mode] = total_reps[mode]
                        current_workout_session.exercise_data = exercise_data
                        current_workout_session.is_completed = False
                        
                        db.session.commit()
                except Exception as e:
                    db.session.rollback()
                
        pos = new_pos
        if pos == "up" and good:
            cnt += 1
            total_reps[mode] += 1

        duration = int(time.time() - workout_start) if workout_start else 0
        stats_update = {
            "mode": mode,
            "reps": cnt,
            "calories": round(cal_burnt, 2),
            "duration": duration,
            "form_issues": issues
        }
        socketio.emit("update_stats", stats_update)

    return issues

def gen_frames():
    cap = cv2.VideoCapture(0)
    with mp_pose.Pose(
        min_detection_confidence=0.7,
        min_tracking_confidence=0.7,
        model_complexity=2
    ) as pose:
        while True:
            success, frame = cap.read()
            if not success:
                break

            try:
                frame = cv2.flip(frame, 1)
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = pose.process(rgb)

                if results.pose_landmarks:
                    mp_draw.draw_landmarks(
                        frame,
                        results.pose_landmarks,
                        mp_pose.POSE_CONNECTIONS,
                        mp_draw.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2),
                        mp_draw.DrawingSpec(color=(0, 0, 255), thickness=2, circle_radius=2)
                    )

                    try:
                        issues = check_exercise(results.pose_landmarks.landmark)
                        if issues:
                            overlay = frame.copy()
                            cv2.addWeighted(overlay, 0.3, frame, 0.7, 0, frame)
                            msg = ' & '.join(issues)
                            cv2.putText(frame, f'form: {msg}', (10, 90), 
                                      cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                        else:
                            cv2.putText(frame, 'form: good', (10, 90), 
                                      cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    except Exception as e:
                        print(f"Error processing exercise: {e}")

                cv2.putText(frame, f'MODE:{mode}', (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(frame, f'CNT:{cnt}', (10, 60), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(frame, f'CAL:{cal_burnt:.1f}', (10, 150), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

                duration = int(time.time() - workout_start) if workout_start else 0
                mins, secs = divmod(duration, 60)
                cv2.putText(frame, f'TIME:{mins:02d}:{secs:02d}', (10, 120), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

                ret, buffer = cv2.imencode('.jpg', frame)
                frame = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            except Exception as e:
                continue

@app.route('/')
def home():
    return render_template('index.html')
    
@app.route('/login')
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('workout'))

        flash('Invalid email or password')
    return render_template('login.html')

@app.route('/register')
def register():
    return render_template('register.html')

@app.route('/forgot-password')
def forgot_password():
    return render_template('forgot-password.html')

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    user = users.get(email)
    if user and check_password_hash(user['password'], password):
        return jsonify({
            'success': True,
            'user': {
                'email': email,
                'name': user['name']
            }
        })
    
    return jsonify({
        'success': False,
        'message': 'Invalid email or password'
    }), 401

@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    name = data.get('name')
    
    if email in users:
        return jsonify({
            'success': False,
            'message': 'Email already registered'
        }), 400
    
    users[email] = {
        'name': name,
        'password': generate_password_hash(password)
    }
    
    return jsonify({
        'success': True,
        'message': 'Registration successful'
    })

@app.route('/reset-password-request', methods=['GET', 'POST'])
def reset_password_request():
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        email = form.email.data
        user = User.query.filter_by(email=email).first()

        if user:
            token = secrets.token_urlsafe(32)
            reset_token = PasswordReset(
                user_id=user.id,
                token=token,
                expires_at=datetime.utcnow() + timedelta(hours=24)
            )
            db.session.add(reset_token)
            db.session.commit()

            reset_url = url_for('reset_password', token=token, _external=True)
            msg = Message('Password Reset Request',
                          sender=app.config['MAIL_USERNAME'],
                          recipients=[user.email])
            msg.body = f'To reset your password, visit the following link: {reset_url}'
            mail.send(msg)

            flash('Check your email for password reset instructions')
            return redirect(url_for('login'))

    return render_template('reset_request.html', form=form)

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if request.method == 'POST':
        new_password = request.form.get('password')
        return jsonify({
            'success': True,
            'message': 'Password updated successfully'
        })
    return render_template('reset-password.html')

@app.route('/dashboard')
@login_required
def dashboard():
    if not current_user.profile:
        flash('Please complete your profile first.', 'info')
        return redirect(url_for('profile_setup'))
    try:
        db.session.refresh(current_user)
        _ = current_user.subscription
    except Exception as refresh_err:
         print(f"Error refreshing user session data: {refresh_err}")
    try:
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        sessions_last_30d = WorkoutSession.query.filter(
            WorkoutSession.user_id == current_user.id,
            WorkoutSession.date >= thirty_days_ago,
            WorkoutSession.is_completed == True
        ).order_by(WorkoutSession.date.asc()).all()
        current_month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        monthly_sessions = [s for s in sessions_last_30d if s.date >= current_month_start]
        total_calories = sum(float(s.calories_burned or 0) for s in monthly_sessions)
        total_duration_seconds = sum(int(s.duration or 0) for s in monthly_sessions)
        total_duration_minutes = total_duration_seconds // 60
        stats = {
            'total_calories': round(total_calories, 1),
            'total_duration': total_duration_minutes,
            'workouts_count': len(monthly_sessions),
            'streak': current_user.streak_count or 0
        }
        workout_data = {
            'dates': [s.date.strftime('%Y-%m-%d') for s in sessions_last_30d],
            'calories': [round(float(s.calories_burned or 0), 1) for s in sessions_last_30d],
            'durations': [round(float(s.duration or 0) / 60, 1) if s.duration else 0 for s in sessions_last_30d]
        }
        all_completed_sessions = WorkoutSession.query.filter_by(user_id=current_user.id, is_completed=True).all()
        calendar_data = {s.date.strftime('%Y-%m-%d'): s.to_calendar_dict() for s in all_completed_sessions}
        return render_template('dashboard.html', stats=stats, workout_data=workout_data, calendar_data=calendar_data)
    except Exception as e:
        print(f"Dashboard error: {e}")
        traceback.print_exc()
        flash('Error loading dashboard data', 'error')
        stats = {'total_calories': 0, 'total_duration': 0, 'workouts_count': 0, 'streak': 0}
        workout_data = {'dates':[], 'calories':[], 'durations':[]}
        calendar_data = {}
        return render_template('dashboard.html', stats=stats, workout_data=workout_data, calendar_data=calendar_data)

# Workout routes
@app.route('/workout')
@login_required
def workout():
    return render_template('workout.html')

@app.route('/workout/video_feed')
@login_required
def video_feed():
    return Response(gen_frames(),
                   mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/workout/change_mode/<new_mode>')
@login_required
def change_mode(new_mode):
    global mode, cnt, pos
    valid_modes = ['sq', 'pu', 'cu', 'lu', 'pl', 'cr', 'mc', 'jj', 'bp', 'dl', 'fs', 'br', 'op']
    if new_mode in valid_modes:
        mode = new_mode
        cnt = 0
        pos = None
        return jsonify({'success': True})
    return jsonify({'success': False})

@app.route('/workout/start')
@login_required
def start_exercise():
    global workout_start, current_workout_session, total_reps, cal_burnt, cnt, pos
    
    try:
        total_reps = {"sq": 0, "cu": 0, "pu": 0}
        cal_burnt = 0
        cnt = 0
        pos = None
        workout_start = time.time()
        
        print("Debug - Starting new workout session")
        print(f"Initial state: total_reps={total_reps}, cal_burnt={cal_burnt}")
        current_workout_session = WorkoutSession(
            user_id=current_user.id,
            exercise_data={},
            calories_burned=0.0,
            duration=0,
            avg_heart_rate=0.0,
            date=datetime.utcnow(),
            is_completed=False
        )
        db.session.add(current_workout_session)
        db.session.commit()
        
        print(f"New session created: {current_workout_session.to_dict()}")
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error starting workout: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/workout/stop')
@login_required
def stop_exercise():
    global workout_start, cnt, pos, cal_burnt, current_workout_session
    
    try:
        print("Attempting to stop workout...")
        
        if current_workout_session:
            if workout_start:
                duration = int(time.time() - workout_start)
                current_workout_session.duration = duration
                
            current_workout_session.calories_burned = cal_burnt
            current_workout_session.exercise_data = dict(total_reps)
            
            db.session.commit()
            print("Workout session updated successfully")

        workout_start = None
        cnt = 0
        pos = None
        
        return jsonify({
            'success': True,
            'message': 'Workout stopped successfully'
        })
            
    except Exception as e:
        print(f"Error stopping workout: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/workout/finish', methods=['POST'])
@login_required
def finish_workout():
    global current_workout_session, workout_start, total_reps, cal_burnt
    
    try:
        print("\n===== WORKOUT FINISH =====")
        data = request.get_json()
        print("Received workout data:", data)
        
        if not current_workout_session:
            print("ERROR: No active workout session!")
            return jsonify({
                'success': False,
                'message': 'No active workout session found'
            }), 400

        calories_burned = float(data.get('calories_burned', cal_burnt))
        current_workout_session.calories_burned = calories_burned
        print(f"Set calories_burned to: {calories_burned}")

        if 'duration' in data and data['duration'] is not None:
            try:
                duration_seconds = int(data['duration'])
                print(f"Using exact duration from payload: {duration_seconds} seconds")
                current_workout_session.duration = duration_seconds
            except (ValueError, TypeError) as e:
                print(f"Error with duration: {e}, using fallback calculation")
                if workout_start:
                    duration_seconds = int(time.time() - workout_start)
                    current_workout_session.duration = duration_seconds
                    print(f"Fallback duration set to: {duration_seconds} seconds")
        
        current_workout_session.exercise_data = dict(total_reps)
        current_workout_session.is_completed = True
        current_user.update_streak()
        db.session.add(current_workout_session)
        db.session.commit()
        print(f"Saved workout with duration: {current_workout_session.duration} seconds")
        workout_start = None
        session_id = current_workout_session.id
        current_workout_session = None
        
        return jsonify({
            'success': True,
            'message': 'Workout saved successfully'
        })
            
    except Exception as e:
        print(f"Error finishing workout: {e}")
        import traceback
        traceback.print_exc()
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
        
@app.route('/workout-history')
@login_required
def workout_history():
    try:
        workouts = WorkoutSession.query.filter(
            WorkoutSession.user_id == current_user.id,
            WorkoutSession.is_completed == True
        ).order_by(WorkoutSession.date).all()
        
        print(f"Found {len(workouts)} workouts for user {current_user.id}")
        
        user_data = {
            'name': current_user.name,
            'email': current_user.email,
            'age': current_user.profile.age if current_user.profile else None,
            'height': current_user.profile.height if current_user.profile else None,
            'weight': current_user.profile.weight if current_user.profile else None,
            'fitness_level': current_user.profile.fitness_level if current_user.profile else 'beginner'
        }
        
        workout_data = []
        for workout in workouts:
            workout_dict = {
                'id': workout.id,
                'date': workout.date.strftime('%Y-%m-%d'),
                'duration': workout.duration or 0,
                'calories_burned': workout.calories_burned or 0,
                'exercise_data': workout.exercise_data or {}
            }
            workout_data.append(workout_dict)
        
        try:
            from workout_analytics import WorkoutEfficiencyAnalyzer
            analyzer = WorkoutEfficiencyAnalyzer(user_data, workout_data)
            efficiency_report = analyzer.generate_report()
            print("Analysis completed successfully")
            
            if 'overall_stats' not in efficiency_report:
                efficiency_report['overall_stats'] = {
                    'avg_score': 0, 
                    'trend': 'Stable', 
                    'improvement': 0, 
                    'num_workouts': len(workout_data)
                }
            
            if 'detailed_scores' not in efficiency_report:
                efficiency_report['detailed_scores'] = []
                
            if 'recommendations' not in efficiency_report:
                efficiency_report['recommendations'] = []
                
            if 'exercise_comparison' not in efficiency_report:
                efficiency_report['exercise_comparison'] = {}
            
            return render_template('workout_history.html', efficiency=efficiency_report)
            
        except ImportError as e:
            print(f"Import error: {str(e)}")
            
            efficiency_scores = []
            for workout in workout_data:
                duration_min = max(workout['duration'] / 60, 0.1) 
                calories = workout['calories_burned']
                total_reps = sum(workout['exercise_data'].values())
                
                intensity = calories / duration_min if duration_min > 0 else 0
                efficiency = calories / max(total_reps, 1) if total_reps > 0 else 0
                
                primary_exercise = 'unknown'
                if workout['exercise_data']:
                    primary_exercise = max(workout['exercise_data'].items(), key=lambda x: x[1])[0]
                
                score = (intensity * 0.6 + efficiency * 0.4) / 3
                score = min(max(score, 0), 10)  
                
                category = 'Poor'
                if score >= 8:
                    category = 'Excellent'
                elif score >= 6:
                    category = 'Good'
                elif score >= 4:
                    category = 'Average'
                
                efficiency_scores.append({
                    'date': workout['date'],
                    'score': round(score, 1),
                    'category': category,
                    'primary_exercise': primary_exercise,
                    'efficiency_metrics': {
                        'intensity': round(intensity, 2),
                        'efficiency': round(efficiency, 2)
                    }
                })
            
            avg_score = sum(w['score'] for w in efficiency_scores) / len(efficiency_scores) if efficiency_scores else 0
            
            trend = "Stable"
            improvement = 0
            if len(efficiency_scores) >= 2:
                sorted_scores = sorted(efficiency_scores, key=lambda x: x['date'])
                first_score = sorted_scores[0]['score']
                last_score = sorted_scores[-1]['score']
                
                improvement = round(((last_score - first_score) / max(first_score, 0.1)) * 100, 1)
                
                if improvement > 10:
                    trend = "Improving"
                elif improvement < -10:
                    trend = "Declining"
            
            recommendations = []
            if trend == "Declining":
                recommendations.append("Your workout efficiency is declining. Consider varying your routine or increasing intensity.")
            elif trend == "Improving":
                recommendations.append("Your workout efficiency is improving. Keep up the good work!")
            else:
                recommendations.append("Your workout efficiency is stable. Consider trying new exercises to improve.")
            
            simple_report = {
                'overall_stats': {
                    'avg_score': round(avg_score, 1),
                    'trend': trend,
                    'improvement': improvement,
                    'num_workouts': len(efficiency_scores)
                },
                'detailed_scores': efficiency_scores,
                'recommendations': recommendations,
                'exercise_comparison': {} 
            }
            
            print("Generated simplified efficiency report")
            return render_template('workout_history.html', efficiency=simple_report)
            
    except Exception as e:
        print(f"Error generating efficiency report: {e}")
        import traceback
        traceback.print_exc()
        
        dummy_data = {
            'overall_stats': {
                'avg_score': 7.5,
                'trend': 'Stable',
                'improvement': 0,
                'num_workouts': 0
            },
            'detailed_scores': [],
            'recommendations': ['Error occurred: ' + str(e)],
            'exercise_comparison': {}
        }
        
        return render_template('workout_history.html', efficiency=dummy_data)

def get_ang(a, b, c):
    if not all([a, b, c]):
        return 0
    a = np.array([a.x, a.y])
    b = np.array([b.x, b.y])
    c = np.array([c.x, c.y])
    rad = np.arctan2(c[1] - b[1], c[0] - b[0]) - np.arctan2(a[1] - b[1], a[0] - b[0])
    ang = np.abs(rad * 180.0 / np.pi)
    if ang > 180.0:
        ang = 360 - ang
    return ang

def check_sq(pts):
    hip = pts[mp_pose.PoseLandmark.LEFT_HIP.value]
    knee = pts[mp_pose.PoseLandmark.LEFT_KNEE.value]
    ankle = pts[mp_pose.PoseLandmark.LEFT_ANKLE.value]
    shoulder = pts[mp_pose.PoseLandmark.LEFT_SHOULDER.value]

    k_ang = get_ang(hip, knee, ankle)
    b_ang = get_ang(shoulder, hip, knee)
    knee_dist = np.sqrt((knee.x - ankle.x) ** 2 + (knee.y - ankle.y) ** 2)

    issues = []
    if b_ang < 160:
        issues.append("back not straight")
    if k_ang < 90:
        issues.append("squat too deep")
    if knee_dist > 0.3:
        issues.append("knees over toes")

    if k_ang > 170:
        return "up", not bool(issues), issues
    elif k_ang < 100:
        return "down", not bool(issues), issues
    return None, True, issues

def check_pu(pts):
    shoulder = pts[mp_pose.PoseLandmark.LEFT_SHOULDER.value]
    elbow = pts[mp_pose.PoseLandmark.LEFT_ELBOW.value]
    wrist = pts[mp_pose.PoseLandmark.LEFT_WRIST.value]
    hip = pts[mp_pose.PoseLandmark.LEFT_HIP.value]
    ankle = pts[mp_pose.PoseLandmark.LEFT_ANKLE.value]

    a_ang = get_ang(shoulder, elbow, wrist)
    b_ang = get_ang(shoulder, hip, ankle)
    hip_sag = abs(hip.y - shoulder.y)

    issues = []
    if not 160 < b_ang < 200:
        issues.append("body not straight")
    if hip_sag > 0.1:
        issues.append("hips sagging")
    if a_ang > 160:
        issues.append("go lower")

    if a_ang > 150:
        return "up", not bool(issues), issues
    elif a_ang < 90:
        return "down", not bool(issues), issues
    return None, True, issues

def check_cu(pts):
    shoulder = pts[mp_pose.PoseLandmark.RIGHT_SHOULDER.value]
    elbow = pts[mp_pose.PoseLandmark.RIGHT_ELBOW.value]
    wrist = pts[mp_pose.PoseLandmark.RIGHT_WRIST.value]

    ang = get_ang(shoulder, elbow, wrist)
    drift = abs(elbow.x - shoulder.x)
    wrist_mov = abs(wrist.x - elbow.x)

    issues = []
    if drift > 0.1:
        issues.append("elbows out")
    if wrist_mov > 0.15:
        issues.append("wrist not stable")
    if ang > 160:
        issues.append("extend fully")

    if ang > 150:
        return "down", not bool(issues), issues
    elif ang < 60:
        return "up", not bool(issues), issues
    return None, True, issues
    
def check_lunge(pts):
    left_hip = pts[mp_pose.PoseLandmark.LEFT_HIP.value]
    left_knee = pts[mp_pose.PoseLandmark.LEFT_KNEE.value]
    left_ankle = pts[mp_pose.PoseLandmark.LEFT_ANKLE.value]
    right_knee = pts[mp_pose.PoseLandmark.RIGHT_KNEE.value]
    right_ankle = pts[mp_pose.PoseLandmark.RIGHT_ANKLE.value]
    shoulder = pts[mp_pose.PoseLandmark.LEFT_SHOULDER.value]

    front_knee_angle = get_ang(left_hip, left_knee, left_ankle)
    back_knee_angle = get_ang(left_hip, right_knee, right_ankle)
    torso_angle = get_ang(shoulder, left_hip, left_knee)

    issues = []
    if front_knee_angle > 100:
        issues.append("bend front knee more")
    if back_knee_angle > 100:
        issues.append("lower back knee")
    if torso_angle < 160:
        issues.append("keep torso upright")
    if front_knee_angle > 150 and back_knee_angle > 150:
        return "up", not bool(issues), issues
    elif front_knee_angle < 100 and back_knee_angle < 100:
        return "down", not bool(issues), issues
    return None, True, issues
    
def check_deadlift(pts):
    shoulder = pts[mp_pose.PoseLandmark.LEFT_SHOULDER.value]
    hip = pts[mp_pose.PoseLandmark.LEFT_HIP.value]
    knee = pts[mp_pose.PoseLandmark.LEFT_KNEE.value]
    ankle = pts[mp_pose.PoseLandmark.LEFT_ANKLE.value]
    
    hip_angle = get_ang(shoulder, hip, knee)
    knee_angle = get_ang(hip, knee, ankle)
    back_angle = get_ang(shoulder, hip, ankle)
    
    print(f"Deadlift - hip angle: {hip_angle}, knee angle: {knee_angle}, back angle: {back_angle}")
    
    issues = []
    if back_angle < 150:
        issues.append("straighten back")
    if hip_angle < 45:
        issues.append("hips too low")
    if knee_angle < 140 and hip_angle > 120:
        issues.append("bend knees more")
    if hip_angle > 160 and knee_angle > 160:
        return "up", not bool(issues), issues
    elif hip_angle < 90 and knee_angle < 160:
        return "down", not bool(issues), issues
    return None, True, issues
    
def check_bench_press(pts):
    shoulder = pts[mp_pose.PoseLandmark.LEFT_SHOULDER.value]
    elbow = pts[mp_pose.PoseLandmark.LEFT_ELBOW.value]
    wrist = pts[mp_pose.PoseLandmark.LEFT_WRIST.value]

    arm_angle = get_ang(shoulder, elbow, wrist)
    elbow_position = elbow.y - shoulder.y
    
    print(f"Bench press - arm angle: {arm_angle}, elbow position: {elbow_position}")
    
    issues = []
    if elbow_position > 0.1:
        issues.append("elbows too high")
    if arm_angle < 45:
        issues.append("keep tension")
    if arm_angle > 160:
        return "up", not bool(issues), issues
    elif arm_angle < 90:
        return "down", not bool(issues), issues
    return None, True, issues

def check_overhead_press(pts):
    shoulder = pts[mp_pose.PoseLandmark.LEFT_SHOULDER.value]
    elbow = pts[mp_pose.PoseLandmark.LEFT_ELBOW.value]
    wrist = pts[mp_pose.PoseLandmark.LEFT_WRIST.value]
    hip = pts[mp_pose.PoseLandmark.LEFT_HIP.value]

    arm_angle = get_ang(shoulder, elbow, wrist)
    torso_angle = get_ang(shoulder, hip, pts[mp_pose.PoseLandmark.LEFT_ANKLE.value])
    
    issues = []
    if torso_angle < 160:
        issues.append("maintain upright posture")
    if arm_angle < 150 and wrist.y > shoulder.y:
        issues.append("press fully overhead")
    if wrist.y < shoulder.y and arm_angle > 160:
        return "up", not bool(issues), issues
    elif wrist.y > shoulder.y and arm_angle < 100:
        return "down", not bool(issues), issues
    return None, True, issues

def check_bent_over_row(pts):
    shoulder = pts[mp_pose.PoseLandmark.LEFT_SHOULDER.value]
    hip = pts[mp_pose.PoseLandmark.LEFT_HIP.value]
    knee = pts[mp_pose.PoseLandmark.LEFT_KNEE.value]
    elbow = pts[mp_pose.PoseLandmark.LEFT_ELBOW.value]

    torso_angle = get_ang(shoulder, hip, knee)
    pull_angle = get_ang(shoulder, elbow, hip)
    
    issues = []
    if torso_angle > 135:
        issues.append("hinge more at hips")
    if pull_angle > 100:
        issues.append("pull higher")
    if elbow.y < shoulder.y:
        return "up", not bool(issues), issues
    elif elbow.y > shoulder.y + 0.2:
        return "down", not bool(issues), issues
    return None, True, issues

def check_front_squat(pts):
    shoulder = pts[mp_pose.PoseLandmark.LEFT_SHOULDER.value]
    elbow = pts[mp_pose.PoseLandmark.LEFT_ELBOW.value]
    hip = pts[mp_pose.PoseLandmark.LEFT_HIP.value]
    knee = pts[mp_pose.PoseLandmark.LEFT_KNEE.value]
    ankle = pts[mp_pose.PoseLandmark.LEFT_ANKLE.value]

    knee_angle = get_ang(hip, knee, ankle)
    torso_angle = get_ang(shoulder, hip, knee)
    elbow_height = elbow.y - shoulder.y
    
    issues = []
    if torso_angle < 150:
        issues.append("keep chest up")
    if elbow_height < -0.1:
        issues.append("elbows up")
    if knee_angle < 70:
        issues.append("squat depth good")
    if knee_angle > 160:
        return "up", not bool(issues), issues
    elif knee_angle < 90:
        return "down", not bool(issues), issues
    return None, True, issues

def check_crunch(pts):
    shoulder = pts[mp_pose.PoseLandmark.LEFT_SHOULDER.value]
    hip = pts[mp_pose.PoseLandmark.LEFT_HIP.value]
    knee = pts[mp_pose.PoseLandmark.LEFT_KNEE.value]
    ankle = pts[mp_pose.PoseLandmark.LEFT_ANKLE.value]

    trunk_angle = get_ang(shoulder, hip, knee)
    leg_angle = get_ang(hip, knee, ankle)

    issues = []
    if leg_angle > 100:
        issues.append("keep knees bent")
    if trunk_angle > 130:
        issues.append("crunch higher")
    if trunk_angle > 150:
        return "down", not bool(issues), issues
    elif trunk_angle < 110:
        return "up", not bool(issues), issues
    return None, True, issues

    
def check_plank(pts):
    shoulder = pts[mp_pose.PoseLandmark.LEFT_SHOULDER.value]
    elbow = pts[mp_pose.PoseLandmark.LEFT_ELBOW.value]
    hip = pts[mp_pose.PoseLandmark.LEFT_HIP.value]
    knee = pts[mp_pose.PoseLandmark.LEFT_KNEE.value]
    ankle = pts[mp_pose.PoseLandmark.LEFT_ANKLE.value]

    arm_angle = get_ang(shoulder, elbow, hip)
    body_angle = get_ang(shoulder, hip, ankle)
    leg_angle = get_ang(hip, knee, ankle)

    issues = []
    if arm_angle < 75 or arm_angle > 105:
        issues.append("align shoulders over elbows")
    if body_angle < 160:
        issues.append("straighten body")
    if leg_angle < 160:
        issues.append("straighten legs")
    if arm_angle >= 75 and arm_angle <= 105 and body_angle >= 160 and leg_angle >= 160:
        elapsed = int(time.time() - workout_start) if workout_start else 0
        if elapsed % 10 == 0 and elapsed > 0:
            return "up", not bool(issues), issues
        return "hold", not bool(issues), issues
    return None, True, issues
    
def check_mountain_climber(pts):
    shoulder = pts[mp_pose.PoseLandmark.LEFT_SHOULDER.value]
    hip = pts[mp_pose.PoseLandmark.LEFT_HIP.value]
    left_knee = pts[mp_pose.PoseLandmark.LEFT_KNEE.value]
    right_knee = pts[mp_pose.PoseLandmark.RIGHT_KNEE.value]
    ankle = pts[mp_pose.PoseLandmark.LEFT_ANKLE.value]

    plank_angle = get_ang(shoulder, hip, ankle)
    left_knee_angle = get_ang(hip, left_knee, ankle)
    right_knee_angle = get_ang(hip, right_knee, ankle)

    issues = []
    if plank_angle < 160:
        issues.append("keep body straight")
    if min(left_knee_angle, right_knee_angle) > 100:
        issues.append("drive knees higher")
    if left_knee_angle < 90:
        return "right", not bool(issues), issues
    elif right_knee_angle < 90:
        return "right", not bool(issues), issues
    return None, True, issues
    
def check_jumping_jack(pts):
    left_shoulder = pts[mp_pose.PoseLandmark.LEFT_SHOULDER.value]
    right_shoulder = pts[mp_pose.PoseLandmark.RIGHT_SHOULDER.value]
    left_hip = pts[mp_pose.PoseLandmark.LEFT_HIP.value]
    right_hip = pts[mp_pose.PoseLandmark.RIGHT_HIP.value]
    left_ankle = pts[mp_pose.PoseLandmark.LEFT_ANKLE.value]
    right_ankle = pts[mp_pose.PoseLandmark.RIGHT_ANKLE.value]

    arm_distance = np.sqrt((left_shoulder.x - right_shoulder.x)**2)
    leg_distance = np.sqrt((left_ankle.x - right_ankle.x)**2)

    issues = []
    if arm_distance < 0.3 and leg_distance > 0.3:
        issues.append("raise arms with jump")
    if arm_distance > 0.3 and leg_distance < 0.3:
        issues.append("jump feet out")
    if arm_distance < 0.2 and leg_distance < 0.2:
        return "closed", not bool(issues), issues
    elif arm_distance > 0.4 and leg_distance > 0.3:
        return "open", not bool(issues), issues
    return None, True, issues

def check_burpee(pts):
    shoulder = pts[mp_pose.PoseLandmark.LEFT_SHOULDER.value]
    hip = pts[mp_pose.PoseLandmark.LEFT_HIP.value]
    knee = pts[mp_pose.PoseLandmark.LEFT_KNEE.value]
    ankle = pts[mp_pose.PoseLandmark.LEFT_ANKLE.value]
    wrist = pts[mp_pose.PoseLandmark.LEFT_WRIST.value]

    hip_height = hip.y
    shoulder_height = shoulder.y
    plank_angle = get_ang(shoulder, hip, ankle)
    knee_angle = get_ang(hip, knee, ankle)

    issues = []
    
    if hip_height < 0.4:
        if knee_angle < 160:
            issues.append("jump higher")
        phase = "jump"
    elif hip_height > 0.8:
        if plank_angle < 160:
            issues.append("keep body straight")
        phase = "plank"
    else:
        if knee_angle > 100:
            issues.append("squat lower")
        phase = "squat"

    if phase == "jump":
        return "up", not bool(issues), issues
    elif phase == "plank":
        return "down", not bool(issues), issues
    return None, True, issues
    
def check_exercise(pts):
    global cnt, pos, total_reps, cal_burnt, mode, current_workout_session

    new_pos = None
    good = True
    issues = []

    if mode == "sq":
        new_pos, good, issues = check_sq(pts)
    elif mode == "pu":
        new_pos, good, issues = check_pu(pts)
    elif mode == "cu":
        new_pos, good, issues = check_cu(pts)
    elif mode == "lu":
        new_pos, good, issues = check_lunge(pts)
    elif mode == "pl":
        new_pos, good, issues = check_plank(pts)
    elif mode == "cr":
        new_pos, good, issues = check_crunch(pts)
    elif mode == "mc":
        new_pos, good, issues = check_mountain_climber(pts)
    elif mode == "jj":
        new_pos, good, issues = check_jumping_jack(pts)
    elif mode == "bp":
        new_pos, good, issues = check_bench_press(pts)
    elif mode == "dl":
        new_pos, good, issues = check_deadlift(pts)
    elif mode == "fs":
        new_pos, good, issues = check_front_squat(pts)
    elif mode == "br":
        new_pos, good, issues = check_bent_over_row(pts)
    elif mode == "op":
        new_pos, good, issues = check_overhead_press(pts)

    if new_pos != pos:
        print(f"Exercise: {mode}, Position change: {pos} -> {new_pos}, Good form: {good}")
        
        if pos and good:
            calories = {
                "sq": 0.32,
                "pu": 0.28,
                "cu": 0.15,
                "lu": 0.30,
                "pl": 0.25,
                "cr": 0.20,
                "mc": 0.35,
                "jj": 0.40,
                "bp": 0.50,
                "dl": 0.80,
                "fs": 0.70,
                "br": 0.50,
                "op": 0.55
            }
            cal_burnt += calories.get(mode, 0.30)

            with app.app_context():
                try:
                    if current_workout_session:
                        current_workout_session.calories_burned = round(cal_burnt, 2)
                        if workout_start:
                            current_duration = int(time.time() - workout_start)
                            current_workout_session.duration = current_duration
                        
                        exercise_data = current_workout_session.exercise_data or {}
                        exercise_data[mode] = total_reps[mode]
                        current_workout_session.exercise_data = exercise_data
                        
                        current_workout_session.is_completed = False
                        
                        db.session.commit()
                except Exception as e:
                    print(f"Error updating workout session: {e}")
                    db.session.rollback()
                
        pos = new_pos
        if new_pos in ["up", "right", "open"] and good:
            cnt += 1
            total_reps[mode] += 1
            print(f"Rep counted for {mode}, total reps: {total_reps[mode]}")

        duration = int(time.time() - workout_start) if workout_start else 0
        stats_update = {
            "mode": mode,
            "reps": cnt,
            "calories": round(cal_burnt, 2),
            "duration": duration,
            "form_issues": issues
        }
        socketio.emit("update_stats", stats_update)

    return issues

def gen_frames():
    cap = cv2.VideoCapture(0)
    with mp_pose.Pose(
        min_detection_confidence=0.7,
        min_tracking_confidence=0.7,
        model_complexity=2
    ) as pose:
        while True:
            success, frame = cap.read()
            if not success:
                break

            try:
                frame = cv2.flip(frame, 1)
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = pose.process(rgb)

                if results.pose_landmarks:
                    mp_draw.draw_landmarks(
                        frame,
                        results.pose_landmarks,
                        mp_pose.POSE_CONNECTIONS,
                        mp_draw.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2),
                        mp_draw.DrawingSpec(color=(0, 0, 255), thickness=2, circle_radius=2)
                    )

                    try:
                        issues = check_exercise(results.pose_landmarks.landmark)
                        if issues:
                            overlay = frame.copy()
                            cv2.addWeighted(overlay, 0.3, frame, 0.7, 0, frame)
                            msg = ' & '.join(issues)
                            cv2.putText(frame, f'form: {msg}', (10, 90), 
                                      cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                        else:
                            cv2.putText(frame, 'form: good', (10, 90), 
                                      cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    except Exception as e:
                        print(f"Error processing exercise: {e}")

                cv2.putText(frame, f'MODE:{mode}', (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(frame, f'CNT:{cnt}', (10, 60), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(frame, f'CAL:{cal_burnt:.1f}', (10, 150), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

                duration = int(time.time() - workout_start) if workout_start else 0
                mins, secs = divmod(duration, 60)
                cv2.putText(frame, f'TIME:{mins:02d}:{secs:02d}', (10, 120), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

                ret, buffer = cv2.imencode('.jpg', frame)
                frame = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            except Exception as e:
                print(f"Error in frame generation: {e}")
                continue
            
EXERCISE_THRESHOLDS = {
    'lu': {
        'front_knee': {'min': 80, 'max': 100},
        'back_knee': {'min': 80, 'max': 100},
        'torso': {'min': 160, 'max': 180}
    },
    'pl': {
        'arm': {'min': 75, 'max': 105},
        'body': {'min': 160, 'max': 180},
        'leg': {'min': 160, 'max': 180}
    },
    'cr': {
        'trunk': {'min': 110, 'max': 150},
        'leg': {'min': 70, 'max': 100}
    },
    'mc': {
        'plank': {'min': 160, 'max': 180},
        'knee_drive': {'min': 90, 'max': 180}
    },
    'jj': {
        'arm_spread': {'min': 0.3, 'max': 0.5},
        'leg_spread': {'min': 0.3, 'max': 0.5}
    },
    'bp': {
        'jump': {'min': 160, 'max': 180},
        'plank': {'min': 160, 'max': 180},
        'squat': {'min': 80, 'max': 100}
    },
    'dl': {
        'hip': {'min': 90, 'max': 160},
        'knee': {'min': 140, 'max': 180},
        'back': {'min': 150, 'max': 180}
    },
    'fs': {
        'knee': {'min': 90, 'max': 160},
        'torso': {'min': 150, 'max': 180},
        'elbow': {'min': -0.1, 'max': 0.1}
    },
    'br': {
        'torso': {'min': 45, 'max': 135},
        'pull': {'min': 45, 'max': 100}
    },
    'op': {
        'arm': {'min': 100, 'max': 160},
        'torso': {'min': 160, 'max': 180}
    }
}

def get_vertical_distance(p1, p2):
    return abs(p1.y - p2.y)

def get_horizontal_distance(p1, p2):
    return abs(p1.x - p2.x)

def get_points_distance(p1, p2):
    return np.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2)

def check_range(value, min_val, max_val):
    """Check if a value is within the specified range"""
    return min_val <= value <= max_val

@socketio.on("send_heart_rate")
def handle_heart_rate(data):
    try:
        if current_workout_session:
            current_workout_session.avg_heart_rate = data.get('heartRate', 0)
            db.session.commit()
        emit("update_heart_rate", data, broadcast=True)
    except Exception as e:
        print(f"Heart rate error: {e}")
        db.session.rollback()

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

@app.route('/reset-password-request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        try:
            user = User.query.filter_by(email=form.email.data).first()
            if user:
                token = secrets.token_urlsafe(32)
                reset_token = PasswordReset(
                    user_id=user.id,
                    token=token
                )
                db.session.add(reset_token)
                db.session.commit()
                reset_url = url_for('reset_password', token=token, _external=True)

                html_body = f'''
                <html>
                <body style="font-family: Arial, sans-serif; padding: 20px; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto; background: #f9f9f9; padding: 20px; border-radius: 10px;">
                        <h2 style="color: #45ffca; text-align: center;">Pump Chest Password Reset</h2>
                        <p style="margin: 20px 0;">Hello,</p>
                        <p>You have requested to reset your password for your Pump Chest account.</p>
                        <p>Please click the button below to reset your password:</p>
                        <div style="text-align: center; margin: 30px 0;">
                            <a href="{reset_url}" 
                               style="background: #45ffca; 
                                      color: #000; 
                                      padding: 12px 25px; 
                                      text-decoration: none; 
                                      border-radius: 5px; 
                                      display: inline-block;">
                                Reset Password
                            </a>
                        </div>
                        <p>If you did not request this password reset, please ignore this email.</p>
                        <p>This link will expire in 24 hours.</p>
                        <hr style="border: 1px solid #eee; margin: 20px 0;">
                        <p style="font-size: 12px; color: #666; text-align: center;">
                            &copy; 2025 Pump Chest. All rights reserved.
                        </p>
                    </div>
                </body>
                </html>
                '''

                msg = Message(
                    'Password Reset Request - Pump Chest',
                    sender=('Pump Chest', app.config['MAIL_USERNAME']),
                    recipients=[user.email]
                )

                msg.body = f'To reset your password, visit the following link: {reset_url}'
                msg.html = html_body
                mail.send(msg)
                print(f"Password reset email sent to: {user.email}")

                flash('Password reset instructions have been sent to your email')
                return redirect(url_for('login'))
            else:
                flash('If an account exists with that email, you will receive reset instructions')
                return redirect(url_for('login'))

        except Exception as e:
            print(f"Error sending password reset email: {str(e)}")
            db.session.rollback()
            flash('An error occurred while sending the reset email. Please try again.')

    return render_template('reset_request.html', form=form)

@app.route('/workout-history')
@login_required
def workout_history():
    try:
        workouts = WorkoutSession.query.filter(
            WorkoutSession.user_id == current_user.id,
            WorkoutSession.is_completed == True
        ).order_by(WorkoutSession.date).all()
        
        print(f"Found {len(workouts)} workouts for user {current_user.id}")
        
        user_data = {
            'name': current_user.name,
            'email': current_user.email,
            'age': current_user.profile.age if current_user.profile else None,
            'height': current_user.profile.height if current_user.profile else None,
            'weight': current_user.profile.weight if current_user.profile else None,
            'fitness_level': current_user.profile.fitness_level if current_user.profile else 'beginner'
        }
        
        workout_data = []
        for workout in workouts:
            workout_dict = {
                'id': workout.id,
                'date': workout.date.strftime('%Y-%m-%d'),
                'duration': workout.duration or 0,
                'calories_burned': workout.calories_burned or 0,
                'exercise_data': workout.exercise_data or {}
            }
            workout_data.append(workout_dict)
        
        try:
            from workout_analytics import WorkoutEfficiencyAnalyzer
            analyzer = WorkoutEfficiencyAnalyzer(user_data, workout_data)
            efficiency_report = analyzer.generate_report()
            print("Analysis completed successfully")
            
            if 'overall_stats' not in efficiency_report:
                efficiency_report['overall_stats'] = {
                    'avg_score': 0, 
                    'trend': 'Stable', 
                    'improvement': 0, 
                    'num_workouts': len(workout_data)
                }
            
            if 'detailed_scores' not in efficiency_report:
                efficiency_report['detailed_scores'] = []
                
            if 'recommendations' not in efficiency_report:
                efficiency_report['recommendations'] = []
                
            if 'exercise_comparison' not in efficiency_report:
                efficiency_report['exercise_comparison'] = {}
            
            return render_template('workout_history.html', efficiency=efficiency_report)
            
        except ImportError as e:
            print(f"Import error: {str(e)}")
            
            efficiency_scores = []
            for workout in workout_data:
                duration_min = max(workout['duration'] / 60, 0.1) 
                calories = workout['calories_burned']
                total_reps = sum(workout['exercise_data'].values())
                
                intensity = calories / duration_min if duration_min > 0 else 0
                efficiency = calories / max(total_reps, 1) if total_reps > 0 else 0
                
                primary_exercise = 'unknown'
                if workout['exercise_data']:
                    primary_exercise = max(workout['exercise_data'].items(), key=lambda x: x[1])[0]
                
                score = (intensity * 0.6 + efficiency * 0.4) / 3
                score = min(max(score, 0), 10)  
                
                category = 'Poor'
                if score >= 8:
                    category = 'Excellent'
                elif score >= 6:
                    category = 'Good'
                elif score >= 4:
                    category = 'Average'
                
                efficiency_scores.append({
                    'date': workout['date'],
                    'score': round(score, 1),
                    'category': category,
                    'primary_exercise': primary_exercise,
                    'efficiency_metrics': {
                        'intensity': round(intensity, 2),
                        'efficiency': round(efficiency, 2)
                    }
                })
            
            avg_score = sum(w['score'] for w in efficiency_scores) / len(efficiency_scores) if efficiency_scores else 0
            
            trend = "Stable"
            improvement = 0
            if len(efficiency_scores) >= 2:
                sorted_scores = sorted(efficiency_scores, key=lambda x: x['date'])
                first_score = sorted_scores[0]['score']
                last_score = sorted_scores[-1]['score']
                
                improvement = round(((last_score - first_score) / max(first_score, 0.1)) * 100, 1)
                
                if improvement > 10:
                    trend = "Improving"
                elif improvement < -10:
                    trend = "Declining"
            
            recommendations = []
            if trend == "Declining":
                recommendations.append("Your workout efficiency is declining. Consider varying your routine or increasing intensity.")
            elif trend == "Improving":
                recommendations.append("Your workout efficiency is improving. Keep up the good work!")
            else:
                recommendations.append("Your workout efficiency is stable. Consider trying new exercises to improve.")
            
            simple_report = {
                'overall_stats': {
                    'avg_score': round(avg_score, 1),
                    'trend': trend,
                    'improvement': improvement,
                    'num_workouts': len(efficiency_scores)
                },
                'detailed_scores': efficiency_scores,
                'recommendations': recommendations,
                'exercise_comparison': {} 
            }
            
            print("Generated simplified efficiency report")
            return render_template('workout_history.html', efficiency=simple_report)
            
    except Exception as e:
        print(f"Error generating efficiency report: {e}")
        import traceback
        traceback.print_exc()
        
        dummy_data = {
            'overall_stats': {
                'avg_score': 7.5,
                'trend': 'Stable',
                'improvement': 0,
                'num_workouts': 0
            },
            'detailed_scores': [],
            'recommendations': ['Error occurred: ' + str(e)],
            'exercise_comparison': {}
        }
        
        return render_template('workout_history.html', efficiency=dummy_data)


@app.route('/api/bmi-history')
@login_required
def get_bmi_history():
    try:
        history = BMIHistory.query.filter_by(
            user_id=current_user.id
        ).order_by(BMIHistory.date.desc()).limit(10).all()
        
        history_data = [{
            'date': record.date.strftime('%Y-%m-%d'),
            'bmi': record.bmi,
            'weight': record.weight,
            'height': record.height
        } for record in history]
        
        return jsonify({
            'success': True,
            'data': history_data
        })
        
    except Exception as e:
        print(f"Error fetching BMI history: {e}")
        return jsonify({
            'success': False,
            'message': 'Failed to fetch BMI history'
        }), 500
    
@app.route('/api/meals/today')
@login_required
def get_todays_meals():
    try:
        today = datetime.now().date()
        meals = MealLog.query.filter(
            MealLog.user_id == current_user.id,
            func.date(MealLog.date) == today
        ).order_by(MealLog.date.desc()).all()
        
        calorie_goal = 2000
        if current_user.profile and hasattr(current_user.profile, 'calorie_goal'):
            calorie_goal = current_user.profile.calorie_goal
        
        return jsonify({
            'success': True,
            'meals': [meal.to_dict() for meal in meals],
            'calorie_goal': calorie_goal
        })
    except Exception as e:
        print(f"Error fetching meals: {e}")
        return jsonify({
            'success': False,
            'message': 'Failed to fetch meals'
        }), 500

@app.route('/api/meals/add', methods=['POST'])
@login_required
def add_meal():
    try:
        data = request.get_json()
        print("Received meal data:", data)
        required_fields = ['meal_type', 'food_name', 'calories']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'message': f'Missing required field: {field}'
                }), 400
            
        meal = MealLog(
            user_id=current_user.id,
            meal_type=str(data['meal_type']),
            food_name=str(data['food_name']),
            calories=float(data['calories']),
            proteins=float(data.get('proteins', 0) or 0),
            carbs=float(data.get('carbs', 0) or 0),
            fats=float(data.get('fats', 0) or 0)
        )
        
        print("Created meal object:", meal)
        
        db.session.add(meal)
        db.session.commit()
        
        print("Meal saved successfully")
        
        return jsonify({
            'success': True,
            'message': 'Meal added successfully',
            'meal': meal.to_dict()
        })
        
    except Exception as e:
        print(f"Error adding meal: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Failed to add meal: {str(e)}'
        }), 500
    
@app.route('/export-data')
@login_required
def export_data_page():
    return render_template('export_data.html')
    
    
@app.route('/export-data/download', methods=['GET'])
@login_required
def export_data():
    try:
        format_type = request.args.get('format', 'json')
        date_from = request.args.get('from')
        date_to = request.args.get('to')
        
        from_date = datetime.strptime(date_from, '%Y-%m-%d') if date_from else None
        to_date = datetime.strptime(date_to, '%Y-%m-%d') if date_to else None
        
        filters = [WorkoutSession.user_id == current_user.id, WorkoutSession.is_completed == True]
        if from_date:
            filters.append(WorkoutSession.date >= from_date)
        if to_date:
            filters.append(WorkoutSession.date <= to_date)
        
        workouts = WorkoutSession.query.filter(*filters).order_by(WorkoutSession.date).all()
        
        bmi_history = BMIHistory.query.filter(
            BMIHistory.user_id == current_user.id
        ).order_by(BMIHistory.date).all()
        
        export_data = {
            'user': {
                'name': current_user.name,
                'email': current_user.email,
                'profile': {
                    'age': current_user.profile.age if current_user.profile else None,
                    'height': current_user.profile.height if current_user.profile else None,
                    'weight': current_user.profile.weight if current_user.profile else None,
                    'fitness_level': current_user.profile.fitness_level if current_user.profile else None,
                    'goals': current_user.profile.goals if current_user.profile else None
                },
                'export_date': datetime.utcnow().isoformat()
            },
            'workouts': [workout.to_dict() for workout in workouts],
            'bmi_history': [bmi.to_dict() for bmi in bmi_history]
        }

        from workout_analytics import WorkoutEfficiencyAnalyzer
        analyzer = WorkoutEfficiencyAnalyzer()
        analyzer.load_from_json(export_data)
        efficiency_report = analyzer.generate_report()
        export_data['efficiency_analysis'] = efficiency_report
        
        if format_type == 'json':
            response = jsonify(export_data)
            response.headers['Content-Disposition'] = f'attachment; filename=pump_chest_data_{current_user.id}.json'
            return response
            
        elif format_type == 'csv':
            output = io.StringIO()
            csv_writer = csv.writer(output)
            
            csv_writer.writerow(['User Data'])
            csv_writer.writerow(['Name', 'Email', 'Age', 'Height', 'Weight', 'Fitness Level'])
            csv_writer.writerow([
                current_user.name,
                current_user.email,
                current_user.profile.age if current_user.profile else '',
                current_user.profile.height if current_user.profile else '',
                current_user.profile.weight if current_user.profile else '',
                current_user.profile.fitness_level if current_user.profile else ''
            ])
            csv_writer.writerow([])
            csv_writer.writerow(['Workout History'])
            csv_writer.writerow(['Date', 'Duration (min)', 'Calories Burned', 'Exercise Reps', 'Efficiency Score'])
            for workout in workouts:
                matching_score = next((w['score'] for w in efficiency_report['detailed_scores'] 
                                    if w['workout_id'] == workout.id), 'N/A')
                
                csv_writer.writerow([
                    workout.date.strftime('%Y-%m-%d %H:%M'),
                    round(workout.duration / 60, 1) if workout.duration else 0,
                    round(workout.calories_burned, 1) if workout.calories_burned else 0,
                    ', '.join([f"{ex}: {reps}" for ex, reps in workout.exercise_data.items() if reps > 0]),
                    matching_score
                ])
            
            csv_writer.writerow([])
            csv_writer.writerow(['Efficiency Analysis'])
            csv_writer.writerow(['Overall Score', 'Trend', 'Improvement'])
            csv_writer.writerow([
                efficiency_report['overall_stats']['avg_score'],
                efficiency_report['overall_stats']['trend'],
                f"{efficiency_report['overall_stats']['improvement']}%"
            ])
            
            csv_writer.writerow([])
            csv_writer.writerow(['Exercise Comparison'])
            csv_writer.writerow(['Exercise', 'Average Score', 'Intensity', 'Efficiency', 'Count'])
            for exercise, stats in efficiency_report['exercise_comparison'].items():
                csv_writer.writerow([
                    exercise,
                    stats['avg_score'],
                    stats['avg_intensity'],
                    stats['avg_efficiency'],
                    stats['workout_count']
                ])
            
            csv_writer.writerow([])
            csv_writer.writerow(['Recommendations'])
            for rec in efficiency_report['recommendations']:
                csv_writer.writerow([rec])
            
            response = make_response(output.getvalue())
            response.headers['Content-Disposition'] = f'attachment; filename=pump_chest_data_{current_user.id}.csv'
            response.headers['Content-Type'] = 'text/csv'
            return response
            
        else:
            return jsonify({'error': 'Unsupported format requested'}), 400
            
    except Exception as e:
        print(f"Error exporting data: {e}")
        return jsonify({'error': 'Failed to export data'}), 500


@app.route('/api/share-workout/<int:workout_id>', methods=['POST'])
@login_required
def share_workout(workout_id):
    try:
        workout = WorkoutSession.query.get(workout_id)
        if not workout or workout.user_id != current_user.id:
            return jsonify({'error': 'Workout not found'}), 404

        token = secrets.token_urlsafe(16)
        expires_days = request.json.get('expires', 7)
        
        app.shared_workouts = getattr(app, 'shared_workouts', {})
        app.shared_workouts[token] = {
            'workout_id': workout_id,
            'expires': datetime.utcnow() + timedelta(days=expires_days)
        }

        share_url = url_for('view_shared_workout', token=token, _external=True)
        
        return jsonify({
            'success': True,
            'share_url': share_url,
            'expires': (datetime.utcnow() + timedelta(days=expires_days)).isoformat()
        })
        
    except Exception as e:
        print(f"Error sharing workout: {e}")
        return jsonify({'error': 'Failed to share workout'}), 500

@app.route('/api/save-one-rep-max', methods=['POST'])
@login_required
def save_one_rep_max():
    try:
        data = request.get_json()
        
        required_fields = ['exercise', 'weight', 'reps', 'estimated_one_rep_max']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'message': f'Missing required field: {field}'
                }), 400
        
        orm = OneRepMax(
            user_id=current_user.id,
            exercise=data['exercise'],
            weight=float(data['weight']),
            reps=int(data['reps']),
            estimated_one_rep_max=float(data['estimated_one_rep_max'])
        )
        
        db.session.add(orm)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'One rep max saved successfully',
            'data': orm.to_dict()
        })
        
    except Exception as e:
        print(f"Error saving one rep max: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Failed to save one rep max: {str(e)}'
        }), 500

@app.route('/shared-workout/<token>')
def view_shared_workout(token):
    app.shared_workouts = getattr(app, 'shared_workouts', {})

    if token not in app.shared_workouts:
        return render_template('404.html', message="Shared workout link not found or expired")
    
    share_data = app.shared_workouts[token]
    if share_data['expires'] < datetime.utcnow():
        return render_template('404.html', message="Shared workout link has expired")

    workout = WorkoutSession.query.get(share_data['workout_id'])
    if not workout:
        return render_template('404.html', message="Workout not found")

    user = User.query.get(workout.user_id)
    
    return render_template('shared_workout.html', workout=workout, user=user)

@app.route('/workout-efficiency')
@login_required
def workout_efficiency():
    try:
        print("=== WORKOUT EFFICIENCY ROUTE ACCESSED ===")
        
        workouts = WorkoutSession.query.filter(
            WorkoutSession.user_id == current_user.id,
            WorkoutSession.is_completed == True
        ).order_by(WorkoutSession.date).all()
        
        print(f"Found {len(workouts)} workouts")
        
        user_data = {
            'name': current_user.name,
            'email': current_user.email,
            'age': current_user.profile.age if current_user.profile else None,
            'height': current_user.profile.height if current_user.profile else None,
            'weight': current_user.profile.weight if current_user.profile else None,
            'fitness_level': current_user.profile.fitness_level if current_user.profile else 'beginner'
        }
        
        workout_data = []
        for workout in workouts:
            workout_dict = {
                'id': workout.id,
                'date': workout.date.strftime('%Y-%m-%d'),
                'duration': workout.duration or 0,
                'calories_burned': workout.calories_burned or 0,
                'exercise_data': workout.exercise_data or {}
            }
            workout_data.append(workout_dict)
        
        try:
            from workout_analytics import WorkoutEfficiencyAnalyzer
            analyzer = WorkoutEfficiencyAnalyzer(user_data, workout_data)
            efficiency_report = analyzer.generate_report()
            print("Analysis completed successfully")
            
            if 'overall_stats' not in efficiency_report:
                efficiency_report['overall_stats'] = {
                    'avg_score': 0, 
                    'trend': 'Stable', 
                    'improvement': 0, 
                    'num_workouts': len(workout_data)
                }
            
            if 'detailed_scores' not in efficiency_report:
                efficiency_report['detailed_scores'] = []
                
            if 'recommendations' not in efficiency_report:
                efficiency_report['recommendations'] = []
                
            if 'exercise_comparison' not in efficiency_report:
                efficiency_report['exercise_comparison'] = {}
            
            for workout in efficiency_report.get('detailed_scores', []):
                if 'efficiency_metrics' not in workout:
                    workout['efficiency_metrics'] = {'intensity': 0, 'efficiency': 0}
                if 'category' not in workout:
                    workout['category'] = 'Average'
            
            return render_template('workout_efficiency.html', efficiency=efficiency_report)
            
        except ImportError as e:
            print(f"Import error: {str(e)}")
            
            efficiency_scores = []
            for workout in workout_data:
                duration_min = max(workout['duration'] / 60, 0.1) 
                calories = workout['calories_burned']
                total_reps = sum(workout['exercise_data'].values())
                
                intensity = calories / duration_min if duration_min > 0 else 0
                efficiency = calories / max(total_reps, 1) if total_reps > 0 else 0
                
                primary_exercise = 'unknown'
                if workout['exercise_data']:
                    primary_exercise = max(workout['exercise_data'].items(), key=lambda x: x[1])[0]
                
                score = (intensity * 0.6 + efficiency * 0.4) / 3
                score = min(max(score, 0), 10) 
                
                category = 'Poor'
                if score >= 8:
                    category = 'Excellent'
                elif score >= 6:
                    category = 'Good'
                elif score >= 4:
                    category = 'Average'
                
                efficiency_scores.append({
                    'date': workout['date'],
                    'score': round(score, 1),
                    'category': category,
                    'primary_exercise': primary_exercise,
                    'efficiency_metrics': {
                        'intensity': round(intensity, 2),
                        'efficiency': round(efficiency, 2)
                    }
                })
            
            avg_score = sum(w['score'] for w in efficiency_scores) / len(efficiency_scores) if efficiency_scores else 0
            
            trend = "Stable"
            improvement = 0
            if len(efficiency_scores) >= 2:
                sorted_scores = sorted(efficiency_scores, key=lambda x: x['date'])
                first_score = sorted_scores[0]['score']
                last_score = sorted_scores[-1]['score']
                
                improvement = round(((last_score - first_score) / max(first_score, 0.1)) * 100, 1)
                
                if improvement > 10:
                    trend = "Improving"
                elif improvement < -10:
                    trend = "Declining"
            
            recommendations = []
            if trend == "Declining":
                recommendations.append("Your workout efficiency is declining. Consider varying your routine or increasing intensity.")
            elif trend == "Improving":
                recommendations.append("Your workout efficiency is improving. Keep up the good work!")
            else:
                recommendations.append("Your workout efficiency is stable. Consider trying new exercises to improve.")
            
            simple_report = {
                'overall_stats': {
                    'avg_score': round(avg_score, 1),
                    'trend': trend,
                    'improvement': improvement,
                    'num_workouts': len(efficiency_scores)
                },
                'detailed_scores': efficiency_scores,
                'recommendations': recommendations,
                'exercise_comparison': {} 
            }
            
            print("Generated simplified efficiency report")
            return render_template('workout_efficiency.html', efficiency=simple_report)
            
    except Exception as e:
        print(f"Error generating efficiency report: {e}")
        import traceback
        traceback.print_exc()
        
        dummy_data = {
            'overall_stats': {
                'avg_score': 7.5,
                'trend': 'Stable',
                'improvement': 0,
                'num_workouts': 0
            },
            'detailed_scores': [],
            'recommendations': ['Error occurred: ' + str(e)],
            'exercise_comparison': {}
        }
        
        return render_template('workout_efficiency.html', efficiency=dummy_data)

@app.route('/api/simple-update-goal/<int:goal>', methods=['GET'])
@login_required
def simple_update_goal(goal):
    try:
        if goal < 1200 or goal > 10000:
            return "Error: Goal must be between 1200 and 10000", 400
        
        if not current_user.profile:
            profile = UserProfile(
                user_id=current_user.id,
                calorie_goal=goal
            )
            db.session.add(profile)
            db.session.commit()
            return "Profile created with calorie goal"
        
        current_user.profile.calorie_goal = goal
        db.session.commit()
        return "Calorie goal updated successfully"
        
    except Exception as e:
        print(f"Error in simple calorie goal update: {e}")
        db.session.rollback()
        return "Error updating calorie goal", 500
   


if __name__ == '__main__':
    with app.app_context():
        try:
            db.create_all()
        except Exception as e:
            print(f"Database initialization error: {e}")
    socketio.run(app, debug=True)
    
 
