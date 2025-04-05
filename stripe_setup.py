# Setting up the subscription tier
import stripe
import os
from dotenv import load_dotenv

load_dotenv()
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

basic_product = stripe.Product.create(
    name="Pump Chest Basic",
    description="Basic fitness tracking subscription"
)

premium_product = stripe.Product.create(
    name="Pump Chest Premium",
    description="Premium fitness tracking subscription with advanced features"
)

basic_price = stripe.Price.create(
    product=basic_product.id,
    unit_amount=500,  # $5.00
    currency="usd",
    recurring={"interval": "month"}
)

premium_price = stripe.Price.create(
    product=premium_product.id,
    unit_amount=1500,  # $15.00
    currency="usd",
    recurring={"interval": "month"}
)

print(f"Basic price ID: {basic_price.id}")
print(f"Premium price ID: {premium_price.id}")