from functools import wraps
from flask import redirect, url_for, flash, current_app 
from flask_login import current_user
from datetime import datetime

def has_active_subscription():
    if not current_user.is_authenticated:
        return False

    subscription = getattr(current_user, 'subscription', None)
    if not subscription:
        return False

    return current_user.subscription_tier == 'premium' and subscription.is_active()

def premium_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("Please log in to access this feature.", "info")
            return redirect(url_for('login', next=request.url)) 

        if not has_active_subscription():
            flash('This feature requires an active Premium subscription.', 'warning')
            return redirect(url_for('subscription.subscription_plans'))

        return f(*args, **kwargs)
    return decorated_function