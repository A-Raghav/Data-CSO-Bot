// Script to customize the login page with proper branding
document.addEventListener('DOMContentLoaded', function() {
  // Check if we're on the login page
  if (document.body.classList.contains('login-page') || 
      window.location.pathname === '/login' || 
      document.querySelector('form button[type="submit"]')) {
    
    // Add StatsEye branding to the login page
    const loginContainer = document.querySelector('.login-page') || document.querySelector('form').parentElement;
    
    if (loginContainer) {
      // Create branding element
      const brandingDiv = document.createElement('div');
      brandingDiv.className = 'statsEye-branding';
      brandingDiv.style.textAlign = 'center';
      brandingDiv.style.marginBottom = '20px';
      
      // Add StatsEye logo image
      const logoImg = document.createElement('img');
      logoImg.src = '/public/data-cso-app-logo.png';
      logoImg.alt = 'StatsEye Logo';
      logoImg.style.maxHeight = '80px';
      logoImg.style.marginBottom = '10px';
      
      // Add title
      const titleEl = document.createElement('h1');
      titleEl.textContent = 'StatsEye';
      titleEl.style.fontSize = '24px';
      titleEl.style.margin = '10px 0';
      
      // Add subtitle
      const subtitleEl = document.createElement('p');
      subtitleEl.textContent = 'Your Data Research Assistant for CSO Statistics';
      subtitleEl.style.fontSize = '16px';
      subtitleEl.style.margin = '0 0 20px 0';
      
      // Assemble and insert at the top of the login form
      brandingDiv.appendChild(logoImg);
      brandingDiv.appendChild(titleEl);
      brandingDiv.appendChild(subtitleEl);
      
      const formElement = document.querySelector('form');
      if (formElement && formElement.parentElement) {
        formElement.parentElement.insertBefore(brandingDiv, formElement);
      }
    }
  }
});
