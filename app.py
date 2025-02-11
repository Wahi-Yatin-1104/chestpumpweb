from flask import Flask, render_template, Response, jsonify, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import secrets
from models import db, User, PasswordReset
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
total_reps = {"sq": 0, "cu": 0, "pu": 0}
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

def check_exercise(pts):
    global cnt, pos, total_reps, cal_burnt, mode
    
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
            cal_burnt += {"sq": 0.32, "cu": 0.15, "pu": 0.28}[mode]
        pos = new_pos
        if pos == "up" and good:
            cnt += 1
            total_reps[mode] += 1
        
        socketio.emit("update_stats", {
            "mode": mode,
            "reps": cnt,
            "calories": cal_burnt
        })
        
    return issues


def gen_frames():
    global mode, cnt, pos, cal_burnt, workout_start

    cap = cv2.VideoCapture(0)
    workout_start = time.time()
    font = cv2.FONT_HERSHEY_SIMPLEX

    with mp_pose.Pose(
        min_detection_confidence=0.7,
        min_tracking_confidence=0.7,
        model_complexity=2
    ) as pose:
        while True:
            success, frame = cap.read()
            if not success: break

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

                issues = check_exercise(results.pose_landmarks.landmark)
                msg = f"form: {'good' if not issues else ' & '.join(issues)}"
            else:
                msg = "no pose"

            duration = int(time.time() - workout_start)
            mins, secs = divmod(duration, 60)

            cv2.putText(frame, f'MODE:{mode}', (10, 30), font, 0.7, (0, 255, 0), 2)
            cv2.putText(frame, f'CNT:{cnt}', (10, 60), font, 0.7, (0, 255, 0), 2)
            cv2.putText(frame, msg, (10, 90), font, 0.7, (0, 255, 0) if "good" in msg else (0, 0, 255), 2)
            cv2.putText(frame, f'TIME:{mins:02d}:{secs:02d}', (10, 120), font, 0.7, (0, 255, 0), 2)
            cv2.putText(frame, f'CAL:{int(cal_burnt)}', (10, 150), font, 0.7, (0, 255, 0), 2)

            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

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



@app.route('/get-started')
def get_started():
    if current_user.is_authenticated:
        return redirect(url_for('workout'))
    else:
        return redirect(url_for('login'))
        
with app.app_context():
    db.create_all()

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@socketio.on("send_heart_rate")
def handle_heart_rate(data):
    print(f"Received Heart Rate Data: {data}")
    emit("update_heart_rate", data, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, debug=True)
