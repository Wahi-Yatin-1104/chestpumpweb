from flask import Blueprint, request, jsonify, redirect, url_for, render_template, flash
from models import db, User, Subscription 
import stripe
import os
from flask_login import login_required, current_user
from datetime import datetime, timedelta
import traceback 

try:
    from app import app
except ImportError:
    print("Error importing Flask app instance. Ensure 'app' variable exists in app.py for webhook context.")
    app = None 

subscription_bp = Blueprint('subscription', __name__)

stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

@subscription_bp.route('/create-checkout-session', methods=['POST'])
@login_required
def create_checkout_session():
    plan_id = request.json.get('plan_id')

    if plan_id != 'premium':
        print(f"Error: Invalid or non-premium plan_id '{plan_id}' received for checkout.")
        return jsonify({'error': 'Invalid plan selected for checkout'}), 400

    stripe_price_id = os.getenv('STRIPE_PREMIUM_PRICE_ID')

    if not stripe_price_id:
        print("CRITICAL Error: STRIPE_PREMIUM_PRICE_ID not set in .env")
        return jsonify({'error': 'Server configuration error.'}), 500

    print(f"Attempting checkout for plan '{plan_id}' using Price ID: {stripe_price_id}")
    try:
        checkout_session = stripe.checkout.Session.create(
            customer_email=current_user.email,
            payment_method_types=['card'],
            line_items=[{'price': stripe_price_id, 'quantity': 1}],
            mode='subscription',
            success_url=url_for('subscription.subscription_success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('subscription.subscription_cancel', _external=True),
            client_reference_id=str(current_user.id) 
        )
        return jsonify({'checkoutUrl': checkout_session.url})
    except stripe.error.StripeError as e:
        print(f"Stripe Error creating checkout session: {e}")
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        print(f"General Error during checkout creation: {e}")
        traceback.print_exc()
        return jsonify({'error': 'An unexpected error occurred.'}), 500


@subscription_bp.route('/success')
@login_required
def subscription_success():
    session_id = request.args.get('session_id')
    if not session_id:
        print("Subscription Success: No session_id provided.")
        flash('Subscription confirmation session ID missing.', 'warning')
        return redirect(url_for('dashboard'))
    try:
        print(f"Processing subscription success for session_id: {session_id}")
        checkout_session = stripe.checkout.Session.retrieve(session_id)
        subscription_id = checkout_session.subscription
        customer_id = checkout_session.customer

        if not subscription_id or not customer_id:
             print("Error: Missing subscription_id or customer_id in checkout session.")
             flash('Could not retrieve subscription details from Stripe.', 'error')
             return redirect(url_for('dashboard'))

        retrieved_price_id = None
        try:
            line_items = stripe.checkout.Session.list_line_items(session_id, limit=1)
            if line_items and line_items.data:
                retrieved_price_id = line_items.data[0].price.id
        except Exception as li_error:
             print(f"Error retrieving line items in /success: {li_error}")

        plan_type = 'premium' if retrieved_price_id == os.getenv('STRIPE_PREMIUM_PRICE_ID') else 'free'
        if plan_type == 'free' and retrieved_price_id is not None:
             print(f"Warning: Checkout session {session_id} succeeded but price ID {retrieved_price_id} doesn't match premium. Setting user to free.")

        print(f"Subscription Success: session_id={session_id}, Determined plan={plan_type}")

        current_user.subscription_tier = plan_type
        print(f"Set user {current_user.id} subscription_tier to '{plan_type}'")

        subscription = Subscription.query.filter_by(user_id=current_user.id).first()
        if subscription:
            print(f"Updating existing subscription record for user {current_user.id}")
            subscription.stripe_customer_id = customer_id
            subscription.stripe_subscription_id = subscription_id
            subscription.plan_type = plan_type 
            subscription.status = 'active' 
            subscription.cancel_at_period_end = False 
            subscription.updated_at = datetime.utcnow()
        else:
            print(f"Creating new subscription record for user {current_user.id}")
            subscription = Subscription(
                user_id=current_user.id,
                stripe_customer_id=customer_id,
                stripe_subscription_id=subscription_id,
                plan_type=plan_type, 
                status='active', 
                cancel_at_period_end=False
            )
            db.session.add(subscription)

        db.session.commit()
        print(f"Committed initial subscription info (status='active') and tier update for user {current_user.id}.")
        flash('Your premium access is now active!' if plan_type == 'premium' else 'Subscription updated.', 'success')

        return redirect(url_for('subscription.thank_you'))

    except Exception as e:
        print(f"Error processing subscription success: {e}")
        traceback.print_exc()
        db.session.rollback()
        flash('There was an issue confirming your subscription update. Please check your dashboard or contact support.', 'error')
        return redirect(url_for('dashboard'))

@subscription_bp.route('/cancel')
def subscription_cancel():
    return render_template('subscription_cancel.html')

@subscription_bp.route('/thank-you')
@login_required
def thank_you():
    db.session.refresh(current_user)
    _ = current_user.subscription 
    subscription = current_user.subscription
    return render_template('subscription_thank_you.html', subscription=subscription)

@subscription_bp.route('/manage')
@login_required
def manage_subscription():
    subscription = Subscription.query.filter_by(user_id=current_user.id).first()
    if not subscription or not subscription.stripe_customer_id:
        flash('No active subscription found to manage.', 'warning')
        return redirect(url_for('membership'))
    try:
        return_url = url_for('membership', _external=True)
        portal_session = stripe.billing_portal.Session.create(
            customer=subscription.stripe_customer_id,
            return_url=return_url,
        )
        return redirect(portal_session.url)
    except Exception as e:
        print(f"Error creating portal session: {e}")
        traceback.print_exc()
        flash('Could not access the subscription management portal. Please try again later or contact support.', 'error')
        return redirect(url_for('dashboard'))

@subscription_bp.route('/plans')
def subscription_plans():
    return render_template('subscription_plans.html')

@subscription_bp.route('/cancel-request', methods=['POST'])
@login_required
def cancel_subscription_request():
    subscription = Subscription.query.filter_by(user_id=current_user.id).first()
    if not subscription or not subscription.stripe_subscription_id or not subscription.is_active():
        flash('No active subscription found to cancel.', 'warning')
        return redirect(url_for('membership'))
    try:
        stripe.Subscription.modify(subscription.stripe_subscription_id, cancel_at_period_end=True)
        subscription.cancel_at_period_end = True
        subscription.updated_at = datetime.utcnow()
        db.session.commit()
        flash('Your subscription cancellation is scheduled for the end of your current billing period.', 'success')
        print(f"User {current_user.id} scheduled subscription {subscription.stripe_subscription_id} for cancellation.")
    except stripe.error.StripeError as e:
        print(f"Stripe Error cancelling subscription {subscription.stripe_subscription_id}: {e}")
        flash(f"Could not schedule cancellation with Stripe: {e}", 'error')
        db.session.rollback()
    except Exception as e:
        print(f"Error scheduling subscription cancellation: {e}")
        traceback.print_exc()
        flash('An unexpected error occurred while trying to cancel.', 'error')
        db.session.rollback()
    return redirect(url_for('membership'))

@subscription_bp.route('/reactivate-request', methods=['POST'])
@login_required
def reactivate_subscription_request():
    subscription = Subscription.query.filter_by(user_id=current_user.id).first()
    if not subscription or not subscription.stripe_subscription_id:
        flash('No subscription found to reactivate.', 'warning')
        return redirect(url_for('membership'))
    try:
        stripe_sub = stripe.Subscription.retrieve(subscription.stripe_subscription_id)
        if not stripe_sub.cancel_at_period_end:
             if stripe_sub.status == 'active': flash('Subscription is already active.', 'info')
             else: flash('Subscription cannot be reactivated in its current state.', 'warning')
             return redirect(url_for('membership'))
        stripe.Subscription.modify(subscription.stripe_subscription_id, cancel_at_period_end=False)
        subscription.cancel_at_period_end = False
        subscription.status = 'active'
        subscription.updated_at = datetime.utcnow()
        user = db.session.get(User, subscription.user_id) # Use session.get if possible
        if user: user.subscription_tier = subscription.plan_type
        db.session.commit()
        flash('Your subscription has been reactivated.', 'success')
        print(f"User {current_user.id} reactivated subscription {subscription.stripe_subscription_id}.")
    except stripe.error.StripeError as e:
        print(f"Stripe Error reactivating subscription {subscription.stripe_subscription_id}: {e}")
        flash(f"Could not reactivate subscription with Stripe: {e}", 'error')
        db.session.rollback()
    except Exception as e:
        print(f"Error reactivating subscription: {e}")
        traceback.print_exc()
        flash('An unexpected error occurred while trying to reactivate.', 'error')
        db.session.rollback()
    return redirect(url_for('membership'))

@subscription_bp.route('/webhook', methods=['POST'])
def webhook():
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    endpoint_secret = os.getenv('STRIPE_WEBHOOK_SECRET')
    if not endpoint_secret:
        print("CRITICAL Error: STRIPE_WEBHOOK_SECRET not configured.")
        return jsonify(error={"message": "Webhook secret not configured"}), 500
    event = None
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except ValueError as e:
        print(f"Webhook Error (400): Invalid payload - {e}")
        return jsonify(error={"message": "Invalid payload"}), 400
    except stripe.error.SignatureVerificationError as e:
        print(f"Webhook Error (400): Invalid signature - {e}.")
        return jsonify(error={"message": "Invalid signature"}), 400
    except Exception as e:
        print(f"Webhook Error (500): General exception - {e}")
        traceback.print_exc()
        return jsonify(error={"message": "Webhook processing error"}), 500

    event_type = event['type']
    event_data = event['data']['object']
    print(f"Received Verified Stripe webhook event: {event_type}")

    try:
        if event_type == 'checkout.session.completed':
            handle_checkout_session_completed(event_data)
        elif event_type == 'customer.subscription.updated':
            subscription_updated(event_data)
        elif event_type == 'customer.subscription.deleted':
            subscription_canceled(event_data)
        elif event_type == 'invoice.payment_succeeded':
            payment_succeeded(event_data)
        elif event_type == 'invoice.payment_failed':
            payment_failed(event_data)
        else:
            print(f"Unhandled verified event type {event_type}")
    except Exception as e:
        print(f"Error handling verified webhook event {event_type}: {e}")
        traceback.print_exc()
        return jsonify(error={"message": f"Error handling {event_type}"}), 500

    return jsonify({'status': 'success'})


def handle_checkout_session_completed(session_data):
    customer_id = session_data.get('customer')
    subscription_id = session_data.get('subscription')
    client_reference_id = session_data.get('client_reference_id')

    if not all([customer_id, subscription_id, client_reference_id]):
        print("Webhook Error: checkout.session.completed missing required data."); return
    try: user_id = int(client_reference_id)
    except (ValueError, TypeError): print(f"Webhook Error: Invalid user_id: {client_reference_id}"); return

    if not app: print("Webhook Error: Flask app context not available."); return
    with app.app_context():
        user = db.session.get(User, user_id)
        if not user: print(f"Webhook Error: User not found for ID {user_id}"); return

        try:
            stripe_sub = stripe.Subscription.retrieve(subscription_id)
            line_items = stripe.SubscriptionItem.list(subscription=subscription_id, limit=1)
            price_id = line_items.data[0].price.id if line_items and line_items.data else None
            plan_type = 'premium' if price_id == os.getenv('STRIPE_PREMIUM_PRICE_ID') else 'free'
            if plan_type == 'free' and price_id: print(f"Webhook Warning: checkout used unknown price ID {price_id}.")

            status = stripe_sub.get('status', 'incomplete')
            period_end_ts = stripe_sub.get('current_period_end')
            current_period_end_dt = datetime.fromtimestamp(period_end_ts) if period_end_ts else None
            cancel_at_period_end = stripe_sub.get('cancel_at_period_end', False)

            subscription = Subscription.query.filter_by(user_id=user_id).first()
            if subscription:
                print(f"Webhook: Updating subscription for user {user_id} from checkout")
                subscription.stripe_customer_id=customer_id; subscription.stripe_subscription_id=subscription_id
                subscription.status=status; subscription.plan_type=plan_type
                if current_period_end_dt: subscription.current_period_end = current_period_end_dt
                subscription.cancel_at_period_end=cancel_at_period_end; subscription.updated_at=datetime.utcnow()
            else:
                print(f"Webhook: Creating subscription for user {user_id} from checkout")
                subscription = Subscription(
                    user_id=user_id, stripe_customer_id=customer_id, stripe_subscription_id=subscription_id,
                    status=status, plan_type=plan_type, current_period_end=current_period_end_dt,
                    cancel_at_period_end = cancel_at_period_end
                ); db.session.add(subscription)

            user.subscription_tier = plan_type
            db.session.commit()
            print(f"Webhook: User {user_id} subscription finalized. Tier:{plan_type}, Status:{status}, End:{current_period_end_dt}, Cancel@End:{cancel_at_period_end}")
        except Exception as e:
            print(f"Webhook Error processing checkout.session.completed for user {user_id}: {e}")
            traceback.print_exc(); db.session.rollback(); raise

def subscription_updated(subscription_data):
    stripe_subscription_id = subscription_data['id']

    if not app: print("Webhook Error: Flask app context not available."); return
    with app.app_context():
        subscription = Subscription.query.filter_by(stripe_subscription_id=stripe_subscription_id).first()

        if subscription:
            user = db.session.get(User, subscription.user_id) 
            if not user:
                print(f"Webhook Error: User {subscription.user_id} not found for subscription {stripe_subscription_id}")
                return

            new_status = subscription_data.get('status', subscription.status)
            new_cancel_at_period_end = subscription_data.get('cancel_at_period_end', subscription.cancel_at_period_end)

            new_period_end_ts = subscription_data.get('current_period_end')
            new_period_end = subscription.current_period_end 

            if new_period_end_ts:
                 try:
                     new_period_end = datetime.fromtimestamp(new_period_end_ts)
                 except Exception as date_err:
                      print(f"Webhook Warning: Error converting period end TS {new_period_end_ts} in sub.updated for {stripe_subscription_id}: {date_err}")
            else:
                 print(f"Webhook Info: 'current_period_end' not in event data for {stripe_subscription_id}. Keeping existing: {new_period_end}")
                 if new_period_end is None:
                    try:
                        print(f"Webhook Info: Refetching subscription {stripe_subscription_id} to get current_period_end...")
                        stripe_sub_refetched = stripe.Subscription.retrieve(stripe_subscription_id)
                        refetched_ts = stripe_sub_refetched.get('current_period_end')
                        if refetched_ts:
                            new_period_end = datetime.fromtimestamp(refetched_ts)
                            print(f"Webhook Info: Got period end {new_period_end} via refetch.")
                        else:
                            print(f"Webhook Error: Could not get current_period_end even after refetch for sub {stripe_subscription_id}.")
                    except Exception as refetch_err:
                        print(f"Webhook Error: Failed to refetch subscription {stripe_subscription_id}: {refetch_err}")

            # get plan type
            new_plan_type = 'free' #
            new_price_id = None
            if subscription_data.get('items') and subscription_data['items'].get('data'):
                try:
                    new_price_id = subscription_data['items']['data'][0]['price']['id']
                    if new_price_id == os.getenv('STRIPE_PREMIUM_PRICE_ID'):
                        new_plan_type = 'premium'
                except (IndexError, KeyError, TypeError): pass 

            print(f"Webhook: Updating subscription {stripe_subscription_id} -> Status:{new_status}, Plan:{new_plan_type}, Cancel@End:{new_cancel_at_period_end}, PeriodEnd:{new_period_end}")

            # Update the local database record
            subscription.status = new_status
            subscription.current_period_end = new_period_end
            subscription.plan_type = new_plan_type
            subscription.cancel_at_period_end = new_cancel_at_period_end
            subscription.updated_at = datetime.utcnow()

            # Update tier
            if new_status == 'active' and not new_cancel_at_period_end and new_plan_type == 'premium':
                user.subscription_tier = 'premium'
            else:
                if user.subscription_tier != 'free':
                     user.subscription_tier = 'free'
                     print(f"Webhook: Set user {subscription.user_id} tier to free.")

            db.session.commit()
            print(f"Webhook: Subscription {stripe_subscription_id} DB record updated.")
        else:
            print(f"Webhook Warning: Received update for unknown subscription ID: {stripe_subscription_id}")


def subscription_canceled(subscription_data):
    stripe_subscription_id = subscription_data['id']
    if not app: print("Webhook Error: Flask app context not available."); return
    with app.app_context():
        subscription = Subscription.query.filter_by(stripe_subscription_id=stripe_subscription_id).first()
        if subscription:
            print(f"Webhook: Processing deletion for subscription {stripe_subscription_id}")
            subscription.status = 'cancelled'; subscription.cancel_at_period_end = False
            subscription.plan_type = 'free'; subscription.updated_at = datetime.utcnow()
            user = db.session.get(User, subscription.user_id)
            if user and user.subscription_tier != 'free':
                user.subscription_tier = 'free'; print(f"Webhook: Set user {subscription.user_id} tier to free.")
            db.session.commit(); print(f"Webhook: Subscription {stripe_subscription_id} marked cancelled.")
        else: print(f"Webhook Warning: Received delete for unknown subscription ID: {stripe_subscription_id}")


def payment_succeeded(invoice_data):
    stripe_subscription_id = invoice_data.get('subscription')
    if not stripe_subscription_id: print(f"Webhook Info: payment_succeeded invoice {invoice_data.get('id')} lacks subscription ID."); return
    print(f"Webhook: Processing payment_succeeded for sub {stripe_subscription_id}")
    if not app: print("Webhook Error: Flask app context not available."); return
    with app.app_context():
        subscription = Subscription.query.filter_by(stripe_subscription_id=stripe_subscription_id).first()
        if subscription:
            try:
                stripe_sub = stripe.Subscription.retrieve(stripe_subscription_id)
                new_period_end = datetime.fromtimestamp(stripe_sub.current_period_end)
                new_status = stripe_sub.status; new_cancel_at_period_end = stripe_sub.cancel_at_period_end
                new_plan_type = 'free'
                if stripe_sub.items and stripe_sub.items.data:
                    price_id = stripe_sub.items.data[0].price.id
                    if price_id == os.getenv('STRIPE_PREMIUM_PRICE_ID'): new_plan_type = 'premium'
                subscription.current_period_end = new_period_end; subscription.status = new_status
                subscription.plan_type = new_plan_type; subscription.cancel_at_period_end = new_cancel_at_period_end
                subscription.updated_at = datetime.utcnow(); db.session.commit()
                print(f"Webhook: Updated subscription {stripe_subscription_id} after payment. Status:{new_status}, End:{new_period_end}")
                user = db.session.get(User, subscription.user_id)
                if user and new_status == 'active' and not new_cancel_at_period_end and new_plan_type == 'premium':
                    if user.subscription_tier != 'premium': user.subscription_tier = 'premium'; db.session.commit(); print(f"Webhook: Updated user {user.id} tier to premium.")
                elif user and user.subscription_tier != 'free':
                    user.subscription_tier = 'free'; db.session.commit(); print(f"Webhook: Set user {user.id} tier to free.")
            except Exception as e: print(f"Webhook Error updating after payment for {stripe_subscription_id}: {e}"); traceback.print_exc(); db.session.rollback(); raise
        else: print(f"Webhook Warning: Payment success for unknown subscription ID: {stripe_subscription_id}")


def payment_failed(invoice_data):
    stripe_subscription_id = invoice_data.get('subscription')
    if not stripe_subscription_id: print("Webhook: payment_failed event missing subscription ID."); return
    if not app: print("Webhook Error: Flask app context not available."); return
    with app.app_context():
        subscription = Subscription.query.filter_by(stripe_subscription_id=stripe_subscription_id).first()
        if subscription:
            new_status = 'past_due';
            if invoice_data.get('status') == 'uncollectible': new_status = 'unpaid'
            subscription.status = new_status; subscription.updated_at = datetime.utcnow()
            print(f"Webhook: Marked subscription {stripe_subscription_id} as {new_status}.")
            user = db.session.get(User, subscription.user_id)
            if user and user.subscription_tier != 'free':
                user.subscription_tier = 'free'; print(f"Webhook: Set user {subscription.user_id} tier to free.")
            db.session.commit()
        else: print(f"Webhook Warning: Payment failure for unknown subscription ID: {stripe_subscription_id}")