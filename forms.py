from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, IntegerField, FloatField, SelectField, TextAreaField
from wtforms.validators import DataRequired, Email, EqualTo, Length, NumberRange, Optional

class ResetPasswordRequestForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Request Password Reset')

class ResetPasswordForm(FlaskForm):
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=8, message='Password must be at least 8 characters long')
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match')
    ])
    submit = SubmitField('Reset Password')


class ChangeEmailForm(FlaskForm):
    new_email = StringField('New Email', validators=[DataRequired(), Email()])
    password = PasswordField('Current Password', validators=[DataRequired()], description="Enter your current password to confirm.")
    submit_email = SubmitField('Change Email')

class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[
        DataRequired(),
        Length(min=8, message='New password must be at least 8 characters long')
    ])
    confirm_new_password = PasswordField('Confirm New Password', validators=[
        DataRequired(),
        EqualTo('new_password', message='New passwords must match')
    ])
    submit_password = SubmitField('Change Password')

class EditProfileForm(FlaskForm):
    age = IntegerField('Age', validators=[DataRequired(), NumberRange(min=13, max=120)])
    height = FloatField('Height (cm)', validators=[DataRequired(), NumberRange(min=100, max=250)], description="Enter height in centimeters.")
    weight = FloatField('Weight (kg)', validators=[DataRequired(), NumberRange(min=30, max=300)], description="Enter weight in kilograms.")
    fitness_level = SelectField('Fitness Level', choices=[
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced')
    ], validators=[DataRequired()])
    submit_profile = SubmitField('Update Profile Info')

class EditGoalsForm(FlaskForm):
    goals = TextAreaField('Fitness Goals', validators=[Optional(), Length(max=500)], render_kw={"rows": 4, "placeholder": "e.g., Run a 5k, gain muscle, improve endurance..."})
    submit_goals = SubmitField('Update Goals')
