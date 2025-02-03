const API_URL = 'http://localhost:5000/api';

async function validateForm(event) {
    event.preventDefault();

    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    const errorMessage = document.getElementById('error-message');

    const passwordRegex = /^(?=.*[A-Z])(?=.*[0-9])(?=.*[!@#$%^&*])[a-zA-Z0-9!@#$%^&*]{8,}$/;
    if (!passwordRegex.test(password)) {
        showError('Password must be at least 8 characters long, include an uppercase letter, a number, and a special character.');
        return false;
    }

    try {
        const response = await fetch(`${API_URL}/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
                email, 
                password,
                remember: document.getElementById('remember').checked
            })
        });

        const data = await response.json();
        if (data.success) {
            localStorage.setItem('user', JSON.stringify(data.user));
            window.location.href = '/workout';
        } else {
            showError(data.message || 'Login failed');
        }
    } catch (error) {
        showError('Login failed: ' + error.message);
    }
}

function showError(message) {
    const errorMessage = document.getElementById('error-message');
    errorMessage.textContent = message;
    errorMessage.style.display = 'block';

    setTimeout(() => {
        errorMessage.style.display = 'none';
    }, 5000);
}

function loginWithGoogle() {
    const googleOAuthUrl = "https://accounts.google.com/o/oauth2/v2/auth?" +
        "client_id=YOUR_GOOGLE_CLIENT_ID" +
        "&redirect_uri=http://localhost:5000/auth/google/callback" +
        "&response_type=code" +
        "&scope=email profile";

    window.location.href = googleOAuthUrl;
}

function loginWithFacebook() {
    const facebookOAuthUrl = "https://www.facebook.com/v15.0/dialog/oauth?" +
        "client_id=YOUR_FACEBOOK_APP_ID" +
        "&redirect_uri=http://localhost:5000/auth/facebook/callback" +
        "&response_type=code" +
        "&scope=email,public_profile";

    window.location.href = facebookOAuthUrl;
}

function loginWithApple() {
    const appleOAuthUrl = "https://appleid.apple.com/auth/authorize?" +
        "client_id=YOUR_APPLE_CLIENT_ID" +
        "&redirect_uri=http://localhost:5000/auth/apple/callback" +
        "&response_type=code" +
        "&scope=email name";

    window.location.href = appleOAuthUrl;
}

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.input-box input').forEach(input => {
        input.addEventListener('focus', () => {
            input.parentElement.classList.add('focused');
        });
        
        input.addEventListener('blur', () => {
            if (!input.value) {
                input.parentElement.classList.remove('focused');
            }
        });
    });
});