// Google Login
function loginWithGoogle() {
    const googleOAuthUrl = "https://accounts.google.com/o/oauth2/v2/auth?" +
      "client_id= TEMP CILENT ID - Google" +
      "&redirect_uri=http://localhost:8000" + // Temp placeholder 
      "&response_type=token" +
      "&scope=email profile";
  
    window.location.href = googleOAuthUrl;
  }
  
  // Facebook Login
  function loginWithFacebook() {
    const facebookOAuthUrl = "https://www.facebook.com/v15.0/dialog/oauth?" +
      "client_id= TEMP CILENT ID - Facebook" +
      "&redirect_uri=http://localhost:8000" + 
      "&response_type=token" +
      "&scope=email,public_profile";
  
    window.location.href = facebookOAuthUrl;
  }
  
  // Apple Login
  function loginWithApple() {
    const appleOAuthUrl = "https://appleid.apple.com/auth/authorize?" +
      "client_id= TEMP CILENT ID - Apple" +
      "&redirect_uri=http://localhost:8000" + 
      "&response_type=code" +
      "&scope=email name";
  
    window.location.href = appleOAuthUrl;
  }
  
  
  // Validate Form
  function validateForm(event) {
    event.preventDefault();
  
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
  
    // Example Validation
    if (password.length < 8) {
      alert('Password must be at least 8 characters long.');
      return false;
    }
  
    alert(`Logged in with email: ${email}`);
    return true;
  }