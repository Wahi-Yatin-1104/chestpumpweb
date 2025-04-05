from flask import Blueprint, request, jsonify, redirect, url_for, render_template
from models import db, User, Subscription
import stripe
import os
from flask_login import login_required, current_user
from datetime import datetime, timedelta

subscription_bp = Blueprint('subscription', __name__)

stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

@subscription_bp.route('/create-checkout-session', methods=['POST'])
@login_required
def create_checkout_session():
    plan_id = request.json.get('plan_id')
    
    if plan_id not in ['price_basic_monthly', 'price_premium_monthly']:
        return jsonify({'error': 'Invalid plan selected'}), 400
    
    try:
        checkout_session = stripe.checkout.Session.create(
            customer_email=current_user.email,
            payment_method_types=['card'],
            line_items=[
                {
                    'price': plan_id,
                    'quantity': 1,
                },
            ],
            mode='subscription',
            success_url=request.host_url + 'subscription/success?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=request.host_url + 'subscription/cancel',
        )
        
        return jsonify({'checkoutUrl': checkout_session.url})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@subscription_bp.route('/success')
@login_required
def subscription_success():
    session_id = request.args.get('session_id')
    
    if not session_id:
        return redirect(url_for('dashboard'))
    
    try:
        # Retrieve the session to get subscription details
        checkout_session = stripe.checkout.Session.retrieve(session_id)
        subscription_id = checkout_session.subscription
        customer_id = checkout_session.customer
        
        # Update user's subscription
        subscription = Subscription.query.filter_by(user_id=current_user.id).first()
        
        if subscription:
            subscription.stripe_customer_id = customer_id
            subscription.stripe_subscription_id = subscription_id
            subscription.status = 'active'
            subscription.plan_type = 'premium' if checkout_session.amount_total >= 1500 else 'basic'
            subscription.current_period_end = datetime.now() + timedelta(days=30)
        else:
            subscription = Subscription(
                user_id=current_user.id,
                stripe_customer_id=customer_id,
                stripe_subscription_id=subscription_id,
                status='active',
                plan_type='premium' if checkout_session.amount_total >= 1500 else 'basic',
                current_period_end=datetime.now() + timedelta(days=30)
            )
            db.session.add(subscription)
        
        # Update user's subscription tier
        current_user.subscription_tier = 'premium' if checkout_session.amount_total >= 1500 else 'basic'
        db.session.commit()
        
        return redirect(url_for('subscription.thank_you'))
    
    except Exception as e:
        print(f"Error processing subscription: {e}")
        return redirect(url_for('dashboard'))

@subscription_bp.route('/cancel')
def subscription_cancel():
    return render_template('subscription_cancel.html')

@subscription_bp.route('/thank-you')
@login_required
def thank_you():
    return render_template('subscription_thank_you.html')

@subscription_bp.route('/manage')
@login_required
def manage_subscription():
    subscription = Subscription.query.filter_by(user_id=current_user.id).first()
    
    if not subscription or subscription.status != 'active':
        return redirect(url_for('subscription.plans'))
    
    try:
        # Create a Stripe portal session
        portal_session = stripe.billing_portal.Session.create(
            customer=subscription.stripe_customer_id,
            return_url=request.host_url + 'dashboard',
        )
        
        return redirect(portal_session.url)
    
    except Exception as e:
        print(f"Error creating portal session: {e}")
        return redirect(url_for('dashboard'))

@subscription_bp.route('/plans')
def subscription_plans():
    return render_template('subscription_plans.html')

# Stripe webhook handler 
@subscription_bp.route('/webhook', methods=['POST'])
def webhook():
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, os.getenv('STRIPE_WEBHOOK_SECRET')
        )
    except ValueError:
        return jsonify({'status': 'error'}), 400
    except stripe.error.SignatureVerificationError:
        return jsonify({'status': 'error'}), 400

    if event['type'] == 'customer.subscription.updated':
        subscription_updated(event['data']['object'])
    elif event['type'] == 'customer.subscription.deleted':
        subscription_canceled(event['data']['object'])
    elif event['type'] == 'invoice.payment_succeeded':
        payment_succeeded(event['data']['object'])
    elif event['type'] == 'invoice.payment_failed':
        payment_failed(event['data']['object'])

    return jsonify({'status': 'success'})

def subscription_updated(subscription_data):
    subscription = Subscription.query.filter_by(
        stripe_subscription_id=subscription_data['id']
    ).first()
    
    if subscription:
        subscription.status = subscription_data['status']
        subscription.current_period_end = datetime.fromtimestamp(subscription_data['current_period_end'])
        db.session.commit()

def subscription_canceled(subscription_data):
    subscription = Subscription.query.filter_by(
        stripe_subscription_id=subscription_data['id']
    ).first()
    
    if subscription:
        subscription.status = 'cancelled'
        
        # Update user's subscription tier
        user = User.query.get(subscription.user_id)
        if user:
            user.subscription_tier = 'basic'
            
        db.session.commit()

def payment_succeeded(invoice_data):
    # Update subscription
    subscription = Subscription.query.filter_by(
        stripe_subscription_id=invoice_data['subscription']
    ).first()
    
    if subscription:
        subscription.current_period_end = datetime.fromtimestamp(invoice_data['lines']['data'][0]['period']['end'])
        db.session.commit()

def payment_failed(invoice_data):
    # Mark subscription past due
    subscription = Subscription.query.filter_by(
        stripe_subscription_id=invoice_data['subscription']
    ).first()
    
    if subscription:
        subscription.status = 'past_due'
        db.session.commit()