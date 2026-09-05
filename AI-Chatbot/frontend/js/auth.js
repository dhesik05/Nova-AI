document.addEventListener('DOMContentLoaded', () => {
  const loginOverlay = document.getElementById('loginOverlay');
  const nameLoginForm = document.getElementById('nameLoginForm');
  const userNameInput = document.getElementById('userNameInput');
  const nameLoginSubmitBtn = document.getElementById('nameLoginSubmitBtn');
  
  const userAvatar = document.getElementById('userAvatar');
  const defaultAvatar = document.getElementById('defaultAvatar');
  const userName = document.getElementById('userName');
  const userEmail = document.getElementById('userEmail');
  const logoutBtn = document.getElementById('logoutBtn');

  let currentToken = localStorage.getItem('jwt_token');
  let currentUser = JSON.parse(localStorage.getItem('jwt_user') || 'null');

  // Override global fetch to automatically attach JWT token and handle 401s
  const originalFetch = window.fetch;
  window.fetch = async function(...args) {
    let [resource, config] = args;
    
    // Inject token for API routes
    const url = typeof resource === 'string' ? resource : (resource ? resource.url : '');
    if (url && (
      url.startsWith('/api/') ||
      url.startsWith('/new-chat') ||
      url.startsWith('/history') ||
      url.startsWith('/upload/') ||
      url.startsWith('/speech-to-text') ||
      url.startsWith('/text-to-speech')
    )) {
      config = config || {};
      config.headers = config.headers || {};
      
      if (currentToken) {
        if (config.headers instanceof Headers) {
          config.headers.set('Authorization', `Bearer ${currentToken}`);
        } else {
          config.headers['Authorization'] = `Bearer ${currentToken}`;
        }
      }
    }
    
    try {
      const response = await originalFetch(resource, config);
      if (response.status === 401 || response.status === 403) {
        handleLogout();
      }
      return response;
    } catch (error) {
      throw error;
    }
  };

  function updateProfileUI() {
    if (currentUser) {
      const displayName = currentUser.name || 'Nova User';
      if (userName) userName.textContent = displayName;
      if (userEmail) userEmail.textContent = currentUser.email || 'Free Tier';
      
      // Update Initials Avatar
      const initial = displayName.trim().charAt(0).toUpperCase() || 'U';
      if (defaultAvatar) {
        defaultAvatar.textContent = initial;
        defaultAvatar.style.display = 'flex';
      }
      if (userAvatar) {
        userAvatar.style.display = 'none';
      }
    }
  }

  async function handleNameLogin(e) {
    if (e) e.preventDefault();
    
    const nameVal = (userNameInput.value || '').trim();
    if (!nameVal) {
      userNameInput.focus();
      return;
    }

    // Disable button and show progress
    const origBtnContent = nameLoginSubmitBtn.innerHTML;
    nameLoginSubmitBtn.disabled = true;
    nameLoginSubmitBtn.innerHTML = `
      <svg class="spin-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        <line x1="12" y1="2" x2="12" y2="6"></line>
        <line x1="12" y1="18" x2="12" y2="22"></line>
        <line x1="4.93" y1="4.93" x2="7.76" y2="7.76"></line>
        <line x1="16.24" y1="16.24" x2="19.07" y2="19.07"></line>
        <line x1="2" y1="12" x2="6" y2="12"></line>
        <line x1="18" y1="12" x2="22" y2="12"></line>
        <line x1="4.93" y1="19.07" x2="7.76" y2="16.24"></line>
        <line x1="16.24" y1="7.76" x2="19.07" y2="4.93"></line>
      </svg>
      <span>Joining...</span>
    `;

    try {
      const res = await originalFetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: nameVal })
      });
      
      const data = await res.json();
      
      if (data.access_token) {
        currentToken = data.access_token;
        currentUser = data.user;
        localStorage.setItem('jwt_token', currentToken);
        localStorage.setItem('jwt_user', JSON.stringify(currentUser));
        
        loginOverlay.classList.add('fade-out');
        setTimeout(() => {
          loginOverlay.classList.add('hidden');
          loginOverlay.classList.remove('fade-out');
        }, 300);

        updateProfileUI();
        
        if (typeof window.refreshConversations === 'function') {
          window.refreshConversations();
        }
        
        // Focus chat input
        const msgInput = document.getElementById('messageInput');
        if (msgInput) setTimeout(() => msgInput.focus(), 350);
      } else {
        alert('Login failed: ' + (data.detail || data.message || 'Please try again.'));
      }
    } catch (err) {
      console.error('Login error:', err);
      alert('Unable to connect to Nova AI server. Please check connection.');
    } finally {
      nameLoginSubmitBtn.disabled = false;
      nameLoginSubmitBtn.innerHTML = origBtnContent;
    }
  }

  function handleLogout() {
    currentToken = null;
    currentUser = null;
    localStorage.removeItem('jwt_token');
    localStorage.removeItem('jwt_user');
    
    loginOverlay.classList.remove('hidden');
    if (userNameInput) {
      userNameInput.value = '';
      setTimeout(() => userNameInput.focus(), 200);
    }
    
    // Clear conversation list and message feeds
    const chatInner = document.getElementById('chatInner');
    if (chatInner) {
      document.querySelectorAll('#chatInner .message-row:not(#typingIndicator)').forEach(el => el.remove());
    }
    const convList = document.getElementById('conversationList');
    if (convList) convList.innerHTML = '';
  }

  // Event Listeners
  if (nameLoginForm) {
    nameLoginForm.addEventListener('submit', handleNameLogin);
  }

  if (logoutBtn) {
    logoutBtn.addEventListener('click', handleLogout);
  }

  // App initialization
  function initApp() {
    if (currentToken && currentUser) {
      loginOverlay.classList.add('hidden');
      updateProfileUI();
    } else {
      loginOverlay.classList.remove('hidden');
      if (userNameInput) setTimeout(() => userNameInput.focus(), 200);
    }
  }

  initApp();
});
