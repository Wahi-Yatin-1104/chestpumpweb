from functools import wraps
from flask import redirect, url_for, flash
from flask_login import current_user
from datetime import datetime

def premium_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login'))
            
        if current_user.subscription_tier != 'premium' or not has_active_subscription():
            flash('This feature requires a premium subscription', 'warning')
            return redirect(url_for('subscription.plans'))
            
        return f(*args, **kwargs)
    return decorated_function

def has_active_subscription():
    if not current_user.is_authenticated:
        return False
        
    subscription = current_user.subscription
    if not subscription:
        return False
        
    return (subscription.status == 'active' and 
            subscription.current_period_end > datetime.utcnow())