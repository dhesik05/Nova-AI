document.addEventListener('DOMContentLoaded', () => {
  const loginOverlay = document.getElementById('loginOverlay');
  const googleSignInBtn = document.getElementById('googleSignInBtn');
  const userAvatar = document.getElementById('userAvatar');
  const defaultAvatar = document.getElementById('defaultAvatar');
  const userName = document.getElementById('userName');
  const userEmail = document.getElementById('userEmail');
  const logoutBtn = document.getElementById('logoutBtn');
  const devLoginBtn = document.getElementById('devLoginBtn');

  let currentToken = localStorage.getItem('jwt_token');
  let currentUser = JSON.parse(localStorage.getItem('jwt_user') || 'null');

  // Override global fetch to inject JWT and handle 401s
  const originalFetch = window.fetch;
  window.fetch = async function(...args) {
    let [resource, config] = args;
    
    // Only inject for API routes
    const url = typeof resource === 'string' ? resource : resource.url;
    if (url && (url.startsWith('/api/') || url.startsWith('/new-chat') || url.startsWith('/history') || url.startsWith('/upload/') || url.startsWith('/speech-to-text') || url.startsWith('/text-to-speech'))) {
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
        // Token missing, expired, or invalid
        handleLogout();
      }
      return response;
    } catch (error) {
      throw error;
    }
  };

  function updateProfileUI() {
    if (currentUser) {
      userName.textContent = currentUser.name || 'User';
      userEmail.textContent = currentUser.email || '';
      if (currentUser.profile_picture) {
        userAvatar.src = currentUser.profile_picture;
        userAvatar.style.display = 'block';
        defaultAvatar.style.display = 'none';
      } else {
        userAvatar.style.display = 'none';
        defaultAvatar.style.display = 'flex';
      }
    }
  }

  function handleLoginSuccess(response) {
    const credential = response.credential;
    
    originalFetch('/api/auth/google', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ credential })
    })
    .then(res => res.json())
    .then(data => {
      if (data.access_token) {
        currentToken = data.access_token;
        currentUser = data.user;
        localStorage.setItem('jwt_token', currentToken);
        localStorage.setItem('jwt_user', JSON.stringify(currentUser));
        
        loginOverlay.classList.add('hidden');
        updateProfileUI();
        
        // Refresh conversations if function exists
        if (typeof window.refreshConversations === 'function') {
           window.refreshConversations();
        } else {
           // Reload page to re-initialize app state if needed
           window.location.reload();
        }
      } else {
        alert('Login failed: ' + (data.detail || 'Unknown error'));
      }
    })
    .catch(err => {
      console.error('Auth error:', err);
      alert('Authentication failed.');
    });
  }

  function handleLogout() {
    currentToken = null;
    currentUser = null;
    localStorage.removeItem('jwt_token');
    localStorage.removeItem('jwt_user');
    
    loginOverlay.classList.remove('hidden');
    
    // Clear chat UI
    if (document.getElementById('messages')) {
       document.getElementById('messages').innerHTML = '';
    }
    if (document.getElementById('conversationList')) {
       document.getElementById('conversationList').innerHTML = '';
    }
  }

  // Bind logout
  if (logoutBtn) {
    logoutBtn.addEventListener('click', handleLogout);
  }

  // Bind dev login bypass / guest login
  if (devLoginBtn) {
    devLoginBtn.addEventListener('click', () => {
      originalFetch('/api/auth/guest', {
        method: 'POST'
      })
      .then(res => res.json())
      .then(data => {
        if (data.access_token) {
          currentToken = data.access_token;
          currentUser = data.user;
          localStorage.setItem('jwt_token', currentToken);
          localStorage.setItem('jwt_user', JSON.stringify(currentUser));
          
          loginOverlay.classList.add('hidden');
          updateProfileUI();
          
          if (typeof window.refreshConversations === 'function') {
             window.refreshConversations();
          } else {
             window.location.reload();
          }
        } else {
          alert('Guest login failed: ' + (data.detail || 'Unknown error'));
        }
      })
      .catch(err => {
        console.error('Auth error:', err);
        alert('Authentication failed.');
      });
    });
  }

  // Init Google Login
  function initGoogleAuth() {
    if (window.google && window.google.accounts) {
      google.accounts.id.initialize({
        client_id: '19204177227-etb9mtn1at0kiffv5u4ls0qq2ckt3ik4.apps.googleusercontent.com', // Validated in backend, bypass in dev
        callback: handleLoginSuccess
      });
      google.accounts.id.renderButton(
        googleSignInBtn,
        { theme: 'outline', size: 'large', width: 300 }
      );
    } else {
      setTimeout(initGoogleAuth, 100);
    }
  }

  function initApp() {
    if (currentToken && currentUser) {
      loginOverlay.classList.add('hidden');
      updateProfileUI();
    } else {
      loginOverlay.classList.remove('hidden');
    }
    initGoogleAuth();
  }

  initApp();
});
