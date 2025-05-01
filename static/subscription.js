document.addEventListener('DOMContentLoaded', function() {

    const basicPlanBtn = document.getElementById('basicPlanBtn');
    const premiumPlanBtn = document.getElementById('premiumPlanBtn');
    
    if (basicPlanBtn) {
        basicPlanBtn.addEventListener('click', function() {
            selectPlan('basic');
        });
    }
    
    if (premiumPlanBtn) {
        premiumPlanBtn.addEventListener('click', function() {
            selectPlan('premium');
        });
    }
});

async function selectPlan(planId) {
    try {
        const isLoggedIn = document.body.classList.contains('logged-in') || 
                          document.querySelector('.btn:contains("Dashboard")') !== null;
        
        if (!isLoggedIn) {
            sessionStorage.setItem('selectedPlanId', planId);
            
            window.location.href = `/register?plan=${planId}`;
            return;
        }
        
        if (planId === 'basic') {
            window.location.href = '/dashboard';
            return;
        }
        
        const response = await fetch('/subscription/create-checkout-session', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ plan_id: planId })
        });

        const data = await response.json();
        
        if (data.error) {
            console.error('Error creating checkout session:', data.error);
            alert(`Error: ${data.error}`);
            return;
        }
        
        window.location.href = data.checkoutUrl;
        
    } catch (error) {
        console.error('Error selecting plan:', error);
        alert('An error occurred. Please try again.');
    }
}

if (document.location.pathname === '/dashboard' && sessionStorage.getItem('selectedPlanId')) {
    const planId = sessionStorage.getItem('selectedPlanId');
    
    if (planId === 'premium') {
        sessionStorage.removeItem('selectedPlanId');
        
        setTimeout(() => {
            selectPlan(planId);
        }, 500);
    } else {
        sessionStorage.removeItem('selectedPlanId');
    }
}