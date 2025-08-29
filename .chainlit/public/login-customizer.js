// Script to hide the logo on the login page
document.addEventListener('DOMContentLoaded', function() {
  // Check if we're on the login page
  if (document.body.classList.contains('login-page') || 
      window.location.pathname === '/login' || 
      document.querySelector('form button[type="submit"]')) {
    
    // Find all potential logo elements
    const possibleLogoContainers = [
      // By class
      document.querySelector('.logo'),
      // By position (usually first element in the first container)
      document.querySelector('.MuiBox-root > .MuiBox-root'),
      // By image alt attribute
      document.querySelector('img[alt="logo"]'),
      // Any image at the top of the login page
      document.querySelector('.login-page img')
    ];

    // Hide any found logo elements
    possibleLogoContainers.forEach(element => {
      if (element) {
        element.style.display = 'none';
        console.log('Hidden logo element:', element);
      }
    });
  }
});
