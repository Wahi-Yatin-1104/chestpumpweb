from flask import Flask, render_template, Response, jsonify, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import secrets
from models import db, User, PasswordReset,BMIHistory, OneRepMax, MealLog
import cv2  
import mediapipe as mp  
import numpy as np
import time
from flask_socketio import SocketIO, emit
from forms import ResetPasswordRequestForm, ResetPasswordForm

# Load environment variables
load_dotenv()

# Initialize Flask and existing configurations
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Mail configuration
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True') == 'True'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')

# Initialize extensions
db.init_app(app)
mail = Mail(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Initialize SocketIO
socketio = SocketIO(app)

# Initialize MediaPipe
mp_pose = mp.solutions.pose
mp_draw = mp.solutions.drawing_utils

# Global variables for workout tracking
mode = "sq"
cnt = 0
pos = None
total_reps = {"sq": 0, "cu": 0, "pu": 0, "lu": 0, "pl": 0, "cr": 0}
cal_burnt = 0
workout_start = None

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
        return redirect(url_for('profile_setup'))
    
    try:
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        sessions = WorkoutSession.query.filter(
            WorkoutSession.user_id == current_user.id,
            WorkoutSession.date >= thirty_days_ago,
            WorkoutSession.is_completed == True
        ).order_by(WorkoutSession.date.desc()).all()
        
        current_month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        monthly_sessions = [s for s in sessions if s.date >= current_month_start]
        
        print(f"Found {len(monthly_sessions)} workouts for current month")
        for session in monthly_sessions:
            print(f"Workout: {session.date}, Calories: {session.calories_burned}, Duration: {session.duration}s")
        
        total_calories = 0
        total_duration = 0
        
        for session in monthly_sessions:
            if session.calories_burned is not None:
                total_calories += float(session.calories_burned)
            if session.duration is not None:
                total_duration += int(session.duration)
        
        total_duration_minutes = total_duration // 60
        
        stats = {
            'total_calories': round(total_calories, 1),
            'total_duration': total_duration_minutes,
            'workouts_count': len(monthly_sessions),
            'streak': current_user.streak_count or 0
        }
        
        print(f"Dashboard stats: {stats}")
        
        workout_data = {
            'dates': [s.date.strftime('%Y-%m-%d') for s in sessions],
            'calories': [round(float(s.calories_burned or 0), 1) for s in sessions],
            'durations': [round(float(s.duration or 0) / 60, 1) if s.duration else 0 for s in sessions]
        }
        
        calendar_data = {s.date.strftime('%Y-%m-%d'): s.to_calendar_dict() for s in sessions}
        
        return render_template('dashboard.html', 
                             user=current_user, 
                             stats=stats,
                             workout_data=workout_data,
                             calendar_data=calendar_data)
                             
    except Exception as e:
        print(f"Dashboard error: {e}")
        flash('Error loading dashboard data')
        return redirect(url_for('home'))

@app.route('/workout')
def workout():
    return render_template('workout.html')

@app.route('/workout/video_feed')
def video_feed():
    return Response(gen_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/workout/change_mode/<new_mode>')
def change_mode(new_mode):
    global mode, cnt, pos
    if new_mode in ['sq', 'pu', 'cu']:
        mode = new_mode
        cnt = 0
        pos = None
        return jsonify({'success': True})
    return jsonify({'success': False})

@app.route('/workout/start')
def start_exercise():
    global workout_start
    workout_start = time.time()
    return jsonify({'success': True})

@app.route('/workout/stop')
def stop_exercise():
    global cnt, pos, cal_burnt, workout_start
    cnt = 0
    pos = None
    cal_burnt = 0
    workout_start = time.time()
    return jsonify({'success': True})

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        name = request.form.get('name')

        if User.query.filter_by(email=email).first():
            flash('Email already registered')
            return redirect(url_for('register'))

        user = User(email=email, name=name)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        login_user(user)
        return redirect(url_for('workout'))

    return render_template('register.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        # Get form data
        name = request.form.get('name')
        email = request.form.get('email')
        message = request.form.get('message')
        
        try:
            # Create and send email
            msg = Message(
                subject=f"Contact Form Submission from {name}",
                sender=app.config['MAIL_USERNAME'],
                recipients=[app.config['MAIL_USERNAME']]  # Send to your support email
            )
            msg.body = f"""
            Name: {name}
            Email: {email}

            Message:
            {message}
            """
            
            mail.send(msg)
            
            flash('Your message has been sent successfully!', 'success')
            return redirect(url_for('contact'))
        
        except Exception as e:
            print(f"Error sending contact form: {e}")
            flash('An error occurred. Please try again later.', 'error')
    
    return render_template('contact.html')

@app.route('/privacy-policy')
def privacy_policy():
    return render_template('privacy_policy.html')

@app.route('/get-started')
def get_started():
    if current_user.is_authenticated:
        return redirect(url_for('workout'))
    else:
        return redirect(url_for('login'))
        
with app.app_context():
    db.create_all()

@app.route('/api/save-bmi', methods=['POST'])
@login_required
def save_bmi():
    try:
        data = request.get_json()
        height = float(data.get('height'))
        weight = float(data.get('weight'))
        bmi = float(data.get('bmi'))
        
        bmi_record = BMIHistory(
            user_id=current_user.id,
            height=height,
            weight=weight,
            bmi=bmi
        )
        db.session.add(bmi_record)
        
        if current_user.profile:
            current_user.profile.height = height
            current_user.profile.weight = weight
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'BMI data saved successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'Failed to save BMI data'
        }), 500

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
        return jsonify({
            'success': False,
            'message': 'Failed to fetch BMI history'
        }), 500
    
@app.route('/api/save_one_rep_max', methods=['POST'])
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
        return jsonify({
            'success': False,
            'message': 'Failed to fetch meals'
        }), 500

@app.route('/api/meals/add', methods=['POST'])
@login_required
def add_meal():
    try:
        data = request.get_json()
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
        
        db.session.add(meal)
        db.session.commit()    
        return jsonify({
            'success': True,
            'message': 'Meal added successfully',
            'meal': meal.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Failed to add meal: {str(e)}'
        }), 500

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@socketio.on("send_heart_rate")
def handle_heart_rate(data):
    try:
        if current_workout_session:
            current_workout_session.avg_heart_rate = data.get('heartRate', 0)
            db.session.commit()
        emit("update_heart_rate", data, broadcast=True)
    except Exception as e:
        db.session.rollback()

if __name__ == '__main__':
    socketio.run(app, debug=True)
