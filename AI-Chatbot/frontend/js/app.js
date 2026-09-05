/* ============================================================
   Nova AI — Unified App Script  (v3 — Debugged & Stabilized)
   All modules merged to avoid ES module circular dependency issues.
   Organised into clearly labelled sections.
   ============================================================ */

// ╔══════════════════════════════════════════════════════════╗
// ║  1. LIBRARIES INIT                                        ║
// ╚══════════════════════════════════════════════════════════╝

if (window.marked) {
  const renderer = new marked.Renderer();
  renderer.code = (tokenOrCode, languageOrUndefined) => {
    let codeText = typeof tokenOrCode === 'object' ? tokenOrCode.text : tokenOrCode;
    let langRaw = typeof tokenOrCode === 'object' ? tokenOrCode.lang : languageOrUndefined;
    const lang = (langRaw || 'plaintext').trim();
    let highlighted = '';
    try {
      highlighted = (lang && hljs.getLanguage(lang))
        ? hljs.highlight(codeText, { language: lang }).value
        : hljs.highlightAuto(codeText).value;
    } catch (_) {
      highlighted = escapeHtml(codeText);
    }
    return `<div class="code-block-wrap">
      <div class="code-block-header">
        <span class="code-block-lang">${escapeHtml(lang)}</span>
        <button class="code-copy-btn" onclick="copyCodeBlock(this)">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
          </svg>
          Copy
        </button>
      </div>
      <pre><code class="hljs language-${escapeHtml(lang)}">${highlighted}</code></pre>
    </div>`;
  };
  marked.use({ renderer, breaks: true, gfm: true });
}

function copyCodeBlock(btn) {
  const code = btn.closest('.code-block-wrap').querySelector('code').innerText;
  navigator.clipboard.writeText(code).then(() => {
    const orig = btn.innerHTML;
    btn.innerHTML = `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg> Copied!`;
    btn.classList.add('copied');
    setTimeout(() => { btn.innerHTML = orig; btn.classList.remove('copied'); }, 2000);
  }).catch(() => {});
}

// ╔══════════════════════════════════════════════════════════╗
// ║  2. SHARED STATE                                          ║
// ╚══════════════════════════════════════════════════════════╝

const state = {
  activeConversationId: null,
  activeModel: null,
  isStreaming: false,
};

// ╔══════════════════════════════════════════════════════════╗
// ║  3. DOM ELEMENT REFERENCES                               ║
// ╚══════════════════════════════════════════════════════════╝

const els = {
  // Sidebar
  sidebar:          document.getElementById('sidebar'),
  sidebarToggle:    document.getElementById('sidebarToggle'),
  sidebarOverlay:   document.getElementById('sidebarOverlay'),
  sidebarCollapseBtn: document.getElementById('sidebarCollapseBtn'),
  conversationList: document.getElementById('conversationList'),
  searchInput:      document.getElementById('searchInput'),
  newChatBtn:       document.getElementById('newChatBtn'),

  // Topbar
  topbarTitle:      document.getElementById('topbar-title'),
  topbarNewChatBtn: document.getElementById('topbarNewChatBtn'),
  modelSelect:      document.getElementById('modelSelect'),
  topbarDivider:    document.getElementById('topbarDivider'),
  shareBtn:      document.getElementById('shareBtn'),
  exportPdfBtn:  document.getElementById('exportPdfBtn'),
  exportTxtBtn:  document.getElementById('exportTxtBtn'),
  deleteChatBtn: document.getElementById('deleteChatBtn'),
  themeBtn:      document.getElementById('themeBtn'),

  // Chat
  chat:            document.getElementById('chat'),
  chatInner:       document.getElementById('chatInner'),
  welcomeScreen:   document.getElementById('welcomeScreen'),
  typingIndicator: document.getElementById('typingIndicator'),
  skeletonWrap:    document.getElementById('skeletonWrap'),

  // Composer
  messageInput:  document.getElementById('messageInput'),
  sendBtn:       document.getElementById('sendBtn'),
  stopBtn:       document.getElementById('stopBtn'),
  regenerateBtn: document.getElementById('regenerateBtn'),
  attachBtn:     document.getElementById('attachBtn'),
  pdfInput:      document.getElementById('pdfInput'),
  imageBtn:      document.getElementById('imageBtn'),
  imageInput:    document.getElementById('imageInput'),
  micBtn:        document.getElementById('micBtn'),

  // Toast
  toastContainer: document.getElementById('toastContainer'),
};

// ╔══════════════════════════════════════════════════════════╗
// ║  4. UTILITIES                                            ║
// ╚══════════════════════════════════════════════════════════╝

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function renderMarkdown(text) {
  try {
    return DOMPurify.sanitize(marked.parse(text));
  } catch {
    return `<p>${escapeHtml(text)}</p>`;
  }
}

function autoResize(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 240) + 'px';
}

/** Smart auto-scroll: only scroll if user is already near the bottom */
function scrollToBottom(force = false) {
  const el = els.chat;
  const threshold = 120; // px from bottom
  const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < threshold;
  if (force || nearBottom) {
    el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' });
  }
}

function formatTime(date) {
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

// ╔══════════════════════════════════════════════════════════╗
// ║  5. TOAST NOTIFICATIONS                                  ║
// ╚══════════════════════════════════════════════════════════╝

const TOAST_ICONS = {
  success: `<svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>`,
  error:   `<svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>`,
  info:    `<svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`,
  warning: `<svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`,
};

function showToast(message, type = 'info', duration = 3500) {
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `
    ${TOAST_ICONS[type] || TOAST_ICONS.info}
    <div class="toast-message">${message}</div>
    <button class="toast-close" aria-label="Dismiss">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
        <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
      </svg>
    </button>`;
  els.toastContainer.appendChild(toast);

  const dismiss = () => {
    if (!toast.parentNode) return;
    toast.classList.add('toast-exit');
    toast.addEventListener('animationend', () => toast.remove(), { once: true });
  };

  toast.querySelector('.toast-close').addEventListener('click', dismiss);
  setTimeout(dismiss, duration);
}

// ╔══════════════════════════════════════════════════════════╗
// ║  6. THEME                                                ║
// ╚══════════════════════════════════════════════════════════╝

const SVG_SUN  = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>`;
const SVG_MOON = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3a7 7 0 0 0 9.79 9.79z"/></svg>`;

function getTheme() { return localStorage.getItem('nova-theme') || localStorage.getItem('dai-theme') || 'light'; }

function setTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem('nova-theme', theme);
  els.themeBtn.innerHTML   = theme === 'dark' ? SVG_SUN : SVG_MOON;
  els.themeBtn.title       = theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode';
}

els.themeBtn.addEventListener('click', () => setTheme(getTheme() === 'dark' ? 'light' : 'dark'));

// ╔══════════════════════════════════════════════════════════╗
// ║  7. SIDEBAR                                              ║
// ╚══════════════════════════════════════════════════════════╝

let allConversations = [];

function openSidebar() {
  els.sidebar.classList.add('open');
  els.sidebarOverlay.classList.add('visible');
}
function closeSidebar() {
  els.sidebar.classList.remove('open');
  els.sidebarOverlay.classList.remove('visible');
}
function toggleSidebar() {
  if (window.innerWidth <= 768) {
    els.sidebar.classList.contains('open') ? closeSidebar() : openSidebar();
  } else {
    els.sidebar.classList.toggle('collapsed');
  }
}

els.sidebarToggle.addEventListener('click', toggleSidebar);
els.sidebarOverlay.addEventListener('click', closeSidebar);

// Fix F2: sidebar collapse button handler
if (els.sidebarCollapseBtn) {
  els.sidebarCollapseBtn.addEventListener('click', () => {
    els.sidebar.classList.toggle('collapsed');
  });
}

els.searchInput.addEventListener('input', () => {
  const q = els.searchInput.value.toLowerCase().trim();
  renderConversations(q ? allConversations.filter(c => (c.title || '').toLowerCase().includes(q)) : allConversations);
});

els.newChatBtn.addEventListener('click', () => {
  clearChat();
  if (window.innerWidth <= 768) closeSidebar();
});

if (els.topbarNewChatBtn) {
  els.topbarNewChatBtn.addEventListener('click', () => {
    clearChat();
    if (window.innerWidth <= 768) closeSidebar();
  });
}

async function refreshConversations() {
  try {
    const res  = await fetch('/api/history/conversations');
    const list = await res.json();
    allConversations = Array.isArray(list) ? list : [];
    renderConversations(allConversations);
  } catch (e) {
    console.error('Failed to refresh conversations', e);
  }
}
window.refreshConversations = refreshConversations;


function renderConversations(list) {
  els.conversationList.innerHTML = '';

  if (!list.length) {
    els.conversationList.innerHTML = `
      <div class="conv-empty">
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
        </svg>
        <p>No conversations yet.<br>Start a new chat!</p>
      </div>`;
    return;
  }

  const groups = groupByDate(list);
  for (const [label, items] of Object.entries(groups)) {
    if (!items.length) continue;
    const labelEl = document.createElement('div');
    labelEl.className   = 'section-label';
    labelEl.textContent = label;
    els.conversationList.appendChild(labelEl);
    items.forEach(c => els.conversationList.appendChild(buildConvItem(c)));
  }
}

function buildConvItem(c) {
  const item = document.createElement('div');
  item.className = 'conv-item' + (c.id === state.activeConversationId ? ' active' : '');
  item.dataset.id = c.id;
  item.setAttribute('role', 'listitem');
  item.setAttribute('tabindex', '0');

  item.innerHTML = `
    <div class="conv-icon">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
      </svg>
    </div>
    <div class="conv-text">
      <div class="conv-title">${escapeHtml(c.title || 'New conversation')}</div>
      <div class="conv-meta">${formatRelativeTime(c.updated_at)}${c.message_count ? ` · ${c.message_count} msg` : ''}</div>
    </div>
    <div class="conv-actions">
      <button class="conv-action-btn delete-btn" title="Delete" aria-label="Delete conversation">
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="3 6 5 6 21 6"/>
          <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>
          <path d="M10 11v6"/><path d="M14 11v6"/>
          <path d="M9 6V4h6v2"/>
        </svg>
      </button>
    </div>`;

  item.addEventListener('click', async (e) => {
    if (e.target.closest('.delete-btn')) return;
    await selectConversation(c);
  });

  item.addEventListener('keydown', async (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      await selectConversation(c);
    }
  });

  item.querySelector('.delete-btn').addEventListener('click', async (e) => {
    e.stopPropagation();
    await deleteConversation(c.id);
  });

  return item;
}

async function selectConversation(c) {
  state.activeConversationId = c.id;
  state.activeModel          = c.model;
  if (c.model) setModelValue(c.model);
  await loadConversation(c.id);
  highlightActiveConv(c.id);
  if (window.innerWidth <= 768) closeSidebar();
}

async function deleteConversation(id) {
  try {
    await fetch(`/api/history/conversations/${id}`, { method: 'DELETE' });
    if (state.activeConversationId === id) clearChat();
    allConversations = allConversations.filter(c => c.id !== id);
    renderConversations(allConversations);
    showToast('Conversation deleted', 'success');
  } catch (e) {
    showToast('Failed to delete conversation', 'error');
  }
}

function highlightActiveConv(id) {
  document.querySelectorAll('.conv-item').forEach(el => {
    el.classList.toggle('active', el.dataset.id == id);
  });
}

/** Live-update sidebar title without full refresh */
function updateSidebarTitle(conversationId, title) {
  const item = els.conversationList.querySelector(`.conv-item[data-id="${conversationId}"]`);
  if (item) {
    const titleEl = item.querySelector('.conv-title');
    if (titleEl) titleEl.textContent = title;
  }
  const cached = allConversations.find(c => c.id === conversationId);
  if (cached) cached.title = title;
}

function groupByDate(list) {
  const now  = new Date();
  const sod  = (d) => new Date(d.getFullYear(), d.getMonth(), d.getDate());
  const today     = sod(now);
  const yesterday = new Date(today); yesterday.setDate(yesterday.getDate() - 1);
  const last7     = new Date(today); last7.setDate(last7.getDate() - 7);
  const last30    = new Date(today); last30.setDate(last30.getDate() - 30);

  const g = { Today: [], Yesterday: [], 'Last 7 days': [], 'Last 30 days': [], Older: [] };
  for (const c of list) {
    const d = sod(new Date(c.updated_at || Date.now()));
    if      (d >= today)     g['Today'].push(c);
    else if (d >= yesterday) g['Yesterday'].push(c);
    else if (d >= last7)     g['Last 7 days'].push(c);
    else if (d >= last30)    g['Last 30 days'].push(c);
    else                     g['Older'].push(c);
  }
  return g;
}

function formatRelativeTime(ts) {
  if (!ts) return '';
  const diff = Date.now() - new Date(ts).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1)  return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24)  return `${hrs}h ago`;
  return new Date(ts).toLocaleDateString();
}

// ╔══════════════════════════════════════════════════════════╗
// ║  8. SETTINGS (models, export, share)                     ║
// ╚══════════════════════════════════════════════════════════╝

async function fetchModels() {
  try {
    const res  = await fetch('/api/chat/models');
    const data = await res.json();
    els.modelSelect.innerHTML = '';
    for (const m of (data.models || [])) {
      const opt = document.createElement('option');
      opt.value       = m;
      opt.textContent = (data.labels && data.labels[m]) ? data.labels[m] : m;
      els.modelSelect.appendChild(opt);
    }
    // Restore persisted model selection
    const saved = localStorage.getItem('nova-model');
    if (saved) setModelValue(saved);
    else if (data.default) setModelValue(data.default);
  } catch (e) {
    console.error('Failed to fetch models', e);
    const opt = document.createElement('option');
    opt.value = opt.textContent = 'openai/gpt-oss-120b';
    els.modelSelect.appendChild(opt);
  }
}

function getSelectedModel() { return els.modelSelect.value; }

function setModelValue(model) {
  if (!model) return;
  const opt = Array.from(els.modelSelect.options).find(o => o.value === model);
  if (opt) els.modelSelect.value = model;
}

// Persist model selection across sessions
els.modelSelect.addEventListener('change', () => {
  localStorage.setItem('nova-model', els.modelSelect.value);
});

function setTopbarChatButtons(visible) {
  [els.shareBtn, els.exportPdfBtn, els.exportTxtBtn, els.deleteChatBtn, els.topbarDivider]
    .forEach(el => el && el.classList.toggle('hidden', !visible));
}

els.shareBtn.addEventListener('click', async () => {
  if (!state.activeConversationId) return;
  const orig = els.shareBtn.innerHTML;
  els.shareBtn.disabled = true;
  try {
    const res  = await fetch('/api/share/', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ conversation_id: state.activeConversationId }),
    });
    const data = await res.json();
    if (data.share_url) {
      await navigator.clipboard.writeText(data.share_url);
      showToast('Share link copied to clipboard!', 'success');
    } else {
      showToast('Failed to create share link', 'error');
    }
  } catch (e) {
    showToast('Error sharing conversation', 'error');
  } finally {
    els.shareBtn.innerHTML = orig;
    els.shareBtn.disabled  = false;
  }
});

els.exportPdfBtn.addEventListener('click', () => {
  if (!state.activeConversationId) return;
  window.open(`/api/export/pdf/${state.activeConversationId}`);
  showToast('Downloading PDF…', 'info');
});

els.exportTxtBtn.addEventListener('click', () => {
  if (!state.activeConversationId) return;
  window.open(`/api/export/txt/${state.activeConversationId}`);
  showToast('Downloading transcript…', 'info');
});

els.deleteChatBtn.addEventListener('click', async () => {
  if (!state.activeConversationId) return;
  if (!confirm('Delete this conversation?')) return;
  try {
    await fetch(`/api/history/conversations/${state.activeConversationId}`, { method: 'DELETE' });
    clearChat();
    allConversations = allConversations.filter(c => c.id !== state.activeConversationId);
    state.activeConversationId = null;
    renderConversations(allConversations);
    setTopbarChatButtons(false);
    showToast('Conversation deleted', 'success');
  } catch (e) {
    showToast('Failed to delete conversation', 'error');
  }
});

// ╔══════════════════════════════════════════════════════════╗
// ║  9. CHAT — MESSAGES                                      ║
// ╚══════════════════════════════════════════════════════════╝

function showWelcome() {
  els.welcomeScreen.classList.remove('hidden');
  els.chatInner.classList.add('hidden');

  document.querySelectorAll('#chatInner .message-row:not(#typingIndicator), #chatInner .skeleton-wrap').forEach(el => el.remove());

  if (!document.getElementById('typingIndicator')) {
    els.chatInner.innerHTML = `
      <div class="skeleton-wrap" id="skeletonWrap" aria-hidden="true">
        <div class="msg-avatar ai-avatar" aria-hidden="true">✦</div>
        <div class="skeleton-content">
          <div class="skeleton-line w-full"></div>
          <div class="skeleton-line w-3q"></div>
          <div class="skeleton-line w-1h"></div>
        </div>
      </div>
      <div class="message-row ai" id="typingIndicator" aria-label="Nova AI is typing" role="status">
        <div class="msg-avatar ai-avatar" aria-hidden="true">✦</div>
        <div class="typing-dots" aria-hidden="true">
          <div class="typing-dot"></div>
          <div class="typing-dot"></div>
          <div class="typing-dot"></div>
        </div>
      </div>`;
  }

  els.typingIndicator = document.getElementById('typingIndicator');
  els.skeletonWrap    = document.getElementById('skeletonWrap');
  els.topbarTitle.textContent = 'Nova AI';
  setTopbarChatButtons(false);
}

function hideWelcome() {
  els.welcomeScreen.classList.add('hidden');
  els.chatInner.classList.remove('hidden');
}

function showTypingIndicator() {
  if (els.typingIndicator) els.typingIndicator.classList.add('visible');
  if (els.skeletonWrap)    els.skeletonWrap.classList.add('visible');
  scrollToBottom(true);
}

function hideTypingIndicator() {
  if (els.typingIndicator) els.typingIndicator.classList.remove('visible');
  if (els.skeletonWrap)    els.skeletonWrap.classList.remove('visible');
}

function addMessage(role, text, timestamp) {
  hideWelcome();
  const { row, bubble } = createMessageRow(role, text, timestamp);
  insertBeforeTyping(row);
  scrollToBottom();
  return bubble;
}

function addSystemMessage(text) {
  addMessage('system', text);
}

function createMessageRow(role, text, timestamp) {
  const now = timestamp ? new Date(timestamp) : new Date();
  const row = document.createElement('div');
  row.className = `message-row ${role}`;

  const avatarContent = {
    user:   `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>`,
    ai:     `✦`,
    system: `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`,
  };

  const avatar    = document.createElement('div');
  avatar.className = `msg-avatar ${role}-avatar`;
  avatar.innerHTML = avatarContent[role] || '?';
  avatar.setAttribute('aria-hidden', 'true');

  const content   = document.createElement('div');
  content.className = 'msg-content';

  if (role !== 'system') {
    const label         = document.createElement('div');
    label.className     = 'msg-role-label';
    label.textContent   = role === 'user' ? 'You' : 'Nova AI';
    content.appendChild(label);
  }

  const bubble       = document.createElement('div');
  bubble.className   = 'msg-bubble' + (role !== 'system' ? ' markdown-body' : '');

  if (role === 'user' || role === 'system') {
    bubble.textContent = text;
  } else {
    bubble.innerHTML = renderMarkdown(text);
    const actions  = document.createElement('div');
    actions.className = 'msg-actions';

    const copyBtn  = makeActionBtn(
      `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>`,
      'Copy response'
    );
    copyBtn.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(bubble.innerText);
        const orig = copyBtn.innerHTML;
        copyBtn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>`;
        showToast('Copied to clipboard', 'success');
        setTimeout(() => { copyBtn.innerHTML = orig; }, 2000);
      } catch (e) {
        showToast('Copy failed', 'error');
      }
    });

    const speakBtn = makeActionBtn(
      `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M15.54 8.46a5 5 0 0 1 0 7.07"/></svg>`,
      'Speak response'
    );
    // Fix F5: use bubble.innerText not raw text to avoid double-escaping
    speakBtn.addEventListener('click', () => speakText(bubble.innerText, speakBtn));

    actions.appendChild(copyBtn);
    actions.appendChild(speakBtn);
    content.appendChild(bubble);
    content.appendChild(actions);
    row.appendChild(avatar);
    row.appendChild(content);
    const tsEl = buildTimestamp(now);
    content.appendChild(tsEl);
    return { row, bubble };
  }

  content.appendChild(bubble);
  if (role === 'user') {
    const tsEl = buildTimestamp(now);
    content.appendChild(tsEl);
  }
  row.appendChild(avatar);
  row.appendChild(content);
  return { row, bubble };
}

function buildTimestamp(date) {
  const ts = document.createElement('div');
  ts.className = 'msg-timestamp';
  ts.textContent = formatTime(date);
  ts.setAttribute('title', date.toLocaleString());
  return ts;
}

function makeActionBtn(svgHtml, title) {
  const btn     = document.createElement('button');
  btn.className = 'msg-action-btn';
  btn.title     = title;
  btn.innerHTML = svgHtml;
  return btn;
}

function insertBeforeTyping(row) {
  const ti = document.getElementById('typingIndicator');
  if (ti && ti.parentNode === els.chatInner) {
    els.chatInner.insertBefore(row, ti);
  } else {
    els.chatInner.appendChild(row);
  }
}

// ── Streaming ─────────────────────────────────────────────────
let streamBuffer  = '';
let streamBubble  = null;
let streamActions = null;
let streamSpeakBtn = null;
// Raw text buffer for efficient streaming (avoid re-parsing markdown on each delta)
let _rawStreamText = '';

function startStreamMessage() {
  hideWelcome();
  streamBuffer   = '';
  _rawStreamText = '';

  const row     = document.createElement('div');
  row.className = 'message-row ai';

  const avatar  = document.createElement('div');
  avatar.className = 'msg-avatar ai-avatar';
  avatar.innerHTML = '✦';
  avatar.setAttribute('aria-hidden', 'true');

  const content   = document.createElement('div');
  content.className = 'msg-content';

  const label   = document.createElement('div');
  label.className  = 'msg-role-label';
  label.textContent = 'Nova AI';

  streamBubble  = document.createElement('div');
  // Use a <pre>-like container during streaming for performance;
  // finalizeStream renders proper markdown
  streamBubble.className = 'msg-bubble markdown-body stream-cursor';

  streamActions  = document.createElement('div');
  streamActions.className = 'msg-actions';

  const copyBtn  = makeActionBtn(
    `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>`,
    'Copy response'
  );
  copyBtn.addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(_rawStreamText || (streamBubble ? streamBubble.innerText : ''));
      showToast('Copied!', 'success');
    } catch (e) {
      showToast('Copy failed', 'error');
    }
  });

  streamSpeakBtn = makeActionBtn(
    `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M15.54 8.46a5 5 0 0 1 0 7.07"/></svg>`,
    'Speak response'
  );

  streamActions.appendChild(copyBtn);
  streamActions.appendChild(streamSpeakBtn);

  const streamTs = buildTimestamp(new Date());
  streamTs.id = 'stream-timestamp';

  content.appendChild(label);
  content.appendChild(streamBubble);
  content.appendChild(streamActions);
  content.appendChild(streamTs);
  row.appendChild(avatar);
  row.appendChild(content);

  insertBeforeTyping(row);
  scrollToBottom(true);
}

// Performance fix S4/P6: only re-render markdown every ~300ms, not every delta
let _renderTimer = null;

function appendStreamDelta(delta) {
  if (!streamBubble) return;
  _rawStreamText += delta;
  streamBuffer   += delta;

  // Show raw text immediately for perceived speed, debounce full markdown render
  // This gives instant visual feedback without re-parsing on every token
  if (!_renderTimer) {
    _renderTimer = setTimeout(() => {
      _renderTimer = null;
      if (streamBubble) {
        streamBubble.innerHTML = renderMarkdown(_rawStreamText);
        scrollToBottom();
      }
    }, 80);
  }
}

function finalizeStream() {
  if (_renderTimer) { clearTimeout(_renderTimer); _renderTimer = null; }
  if (!streamBubble) return;
  streamBubble.classList.remove('stream-cursor');
  streamBubble.innerHTML = renderMarkdown(_rawStreamText);
  // Wire speak button to final text
  if (streamSpeakBtn) {
    const finalText = _rawStreamText;
    streamSpeakBtn.addEventListener('click', () => speakText(finalText, streamSpeakBtn));
  }
  streamBubble   = null;
  streamActions  = null;
  streamSpeakBtn = null;
  scrollToBottom();
}

function clearChat() {
  // Cancel any active stream
  if (abortController && state.isStreaming) {
    abortController.abort();
  }
  if (_renderTimer) { clearTimeout(_renderTimer); _renderTimer = null; }
  streamBuffer   = '';
  _rawStreamText = '';
  streamBubble   = null;
  streamActions  = null;
  streamSpeakBtn = null;
  state.activeConversationId = null;
  state.activeModel          = null;
  state.isStreaming           = false;
  highlightActiveConv(null);
  els.messageInput.value = '';
  autoResize(els.messageInput);
  updateCharCounter();
  showWelcome();
  setSendingState(false);
  els.messageInput.focus();
}

// ── Load conversation ─────────────────────────────────────────
async function loadConversation(id) {
  hideWelcome();
  document.querySelectorAll('.message-row:not(#typingIndicator)').forEach(el => el.remove());
  hideTypingIndicator();
  setTopbarChatButtons(true);

  try {
    const res  = await fetch(`/api/history/conversations/${id}`);
    const data = await res.json();
    if (data.error) return;

    setModelValue(data.model);
    els.topbarTitle.textContent = data.title || 'Conversation';

    for (const m of (data.messages || [])) {
      addMessage(m.role === 'assistant' ? 'ai' : m.role, m.content, m.created_at);
    }
    scrollToBottom(true);
  } catch (e) {
    console.error('Failed to load conversation', e);
    showToast('Failed to load conversation', 'error');
  }
}

// ╔══════════════════════════════════════════════════════════╗
// ║  10. CHARACTER COUNTER                                   ║
// ╚══════════════════════════════════════════════════════════╝

const CHAR_WARN_THRESHOLD = 3000;
const CHAR_MAX = 8000;

function getOrCreateCharCounter() {
  let counter = document.getElementById('charCounter');
  if (!counter) {
    counter = document.createElement('div');
    counter.id = 'charCounter';
    counter.className = 'char-counter hidden';
    const composerInner = document.querySelector('.composer-inner');
    if (composerInner) {
      const hint = composerInner.querySelector('.composer-hint');
      if (hint) composerInner.insertBefore(counter, hint);
      else composerInner.appendChild(counter);
    }
  }
  return counter;
}

function updateCharCounter() {
  const counter = getOrCreateCharCounter();
  const len = els.messageInput.value.length;
  if (len >= CHAR_WARN_THRESHOLD) {
    const remaining = CHAR_MAX - len;
    counter.textContent = `${len.toLocaleString()} / ${CHAR_MAX.toLocaleString()} characters${remaining < 500 ? ' — approaching limit' : ''}`;
    counter.className = `char-counter ${remaining < 200 ? 'danger' : remaining < 1000 ? 'warn' : ''}`;
    counter.classList.remove('hidden');
  } else {
    counter.className = 'char-counter hidden';
  }
}

// ╔══════════════════════════════════════════════════════════╗
// ║  11. SEND / STREAMING / STOP                             ║
// ╚══════════════════════════════════════════════════════════╝

let abortController  = null;
let lastUserMessage  = '';

/** Toggle UI between idle and streaming state */
function setSendingState(sending) {
  state.isStreaming        = sending;
  els.sendBtn.disabled     = sending;
  if (els.stopBtn) {
    els.stopBtn.disabled   = !sending;
    els.stopBtn.classList.toggle('visible', sending);
  }
  els.regenerateBtn.disabled = sending;
}

async function sendMessage() {
  const text = els.messageInput.value.trim();
  if (!text || state.isStreaming) return;

  lastUserMessage        = text;
  els.messageInput.value = '';
  autoResize(els.messageInput);
  updateCharCounter();

  setSendingState(true);
  hideTypingIndicator();

  addMessage('user', text);
  showTypingIndicator();
  startStreamMessage();

  abortController = new AbortController();

  const payload = {
    conversation_id: state.activeConversationId,
    message:         text,
    model:           getSelectedModel(),
    temperature:     0.7,
    top_p:           1.0,
    max_tokens:      1024,
  };

  try {
    const res = await fetch('/api/chat/stream', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(payload),
      signal:  abortController.signal,
    });

    if (!res.ok) {
      throw new Error(`Server error: ${res.status} ${res.statusText}`);
    }

    hideTypingIndicator();

    const reader  = res.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buf = '';
    let streamDone = false;
    // Track if we got a new conversation ID this session
    let isNewConv = !state.activeConversationId;

    while (!streamDone) {
      let readResult;
      try {
        readResult = await reader.read();
      } catch (readErr) {
        // AbortError from reader.cancel() — stream was stopped
        if (readErr.name === 'AbortError') break;
        throw readErr;
      }

      const { value, done } = readResult;

      // Fix S2: reader.done is the fallback end-of-stream signal
      if (done) {
        finalizeStream();
        streamDone = true;
        break;
      }

      buf += decoder.decode(value, { stream: true });
      const lines = buf.split('\n');
      buf = lines.pop(); // keep incomplete line in buffer

      for (const line of lines) {
        if (!line.trim()) continue;
        try {
          const evt = JSON.parse(line);

          // ── Bind conversation ID ──────────────────────────────
          if (evt.conversation_id && !state.activeConversationId) {
            state.activeConversationId = evt.conversation_id;
            setTopbarChatButtons(true);
            els.topbarTitle.textContent = text.slice(0, 50) + (text.length > 50 ? '…' : '');
            // Defer sidebar refresh until after stream to avoid jank (fix S3)
            highlightActiveConv(evt.conversation_id);
          } else if (evt.conversation_id) {
            state.activeConversationId = evt.conversation_id;
          }

          // ── Live title update ─────────────────────────────────
          if (evt.title) {
            els.topbarTitle.textContent = evt.title;
            updateSidebarTitle(evt.conversation_id || state.activeConversationId, evt.title);
          }

          if (evt.delta) appendStreamDelta(evt.delta);
          if (evt.error) {
            appendStreamDelta(`\n\n**Error:** ${evt.error}`);
            showToast('Generation error: ' + evt.error, 'error');
          }

          if (evt.done) {
            finalizeStream();
            streamDone = true;
            // Refresh sidebar after stream done (fix S3 - no jank during streaming)
            refreshConversations().then(() => {
              highlightActiveConv(state.activeConversationId);
            });
            break;
          }
        } catch (err) {
          console.warn('SSE parse error:', err, 'line:', line);
        }
      }
    }
  } catch (e) {
    hideTypingIndicator();
    if (e.name === 'AbortError') {
      appendStreamDelta('\n\n*[Stopped by user]*');
      finalizeStream();
      showToast('Generation stopped', 'info');
    } else {
      console.error('Stream error:', e);
      appendStreamDelta(`\n\n**Connection error:** ${e.message}`);
      finalizeStream();
      showToast('Connection error — please try again', 'error');
    }
  } finally {
    setSendingState(false);
    abortController = null;
    hideTypingIndicator();
    els.messageInput.focus();
  }
}

// ── Stop button (S1/F1) ───────────────────────────────────────
if (els.stopBtn) {
  els.stopBtn.addEventListener('click', () => {
    if (abortController) {
      abortController.abort();
    }
  });
}

els.sendBtn.addEventListener('click', sendMessage);

els.messageInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
});

els.messageInput.addEventListener('input', () => {
  autoResize(els.messageInput);
  updateCharCounter();
});

els.regenerateBtn.addEventListener('click', async () => {
  if (!lastUserMessage || state.isStreaming) return;
  els.messageInput.value = lastUserMessage;
  autoResize(els.messageInput);
  await sendMessage();
});

// ╔══════════════════════════════════════════════════════════╗
// ║  12. KEYBOARD SHORTCUTS                                  ║
// ╚══════════════════════════════════════════════════════════╝

document.addEventListener('keydown', (e) => {
  const tag = document.activeElement?.tagName;

  // Ctrl+K — focus search
  if (e.ctrlKey && e.key === 'k') {
    e.preventDefault();
    els.searchInput.focus();
    els.searchInput.select();
  }

  // Ctrl+N — new chat
  if (e.ctrlKey && e.key === 'n') {
    e.preventDefault();
    clearChat();
  }

  // Escape — stop generation or close sidebar
  if (e.key === 'Escape') {
    if (state.isStreaming && abortController) {
      abortController.abort();
    } else if (window.innerWidth <= 768 && els.sidebar.classList.contains('open')) {
      closeSidebar();
    }
  }
});

// ╔══════════════════════════════════════════════════════════╗
// ║  13. WELCOME SUGGESTIONS                                 ║
// ╚══════════════════════════════════════════════════════════╝

async function loadWelcomeSuggestions() {
  const container = document.querySelector('.welcome-suggestions');
  if (!container) return;

  try {
    const res  = await fetch('/api/suggest/prompts?count=4');
    const data = await res.json();
    const prompts = data.prompts || [];

    if (!prompts.length) return;

    container.innerHTML = '';
    for (const p of prompts) {
      const card = document.createElement('button');
      card.className = 'suggestion-card';
      card.dataset.prompt = p.prompt;
      card.innerHTML = `
        <div class="suggestion-icon">${p.icon || '💡'}</div>
        <div class="suggestion-title">${escapeHtml(p.title)}</div>
        <div class="suggestion-desc">${escapeHtml(p.desc)}</div>`;
      card.addEventListener('click', () => {
        els.messageInput.value = p.prompt;
        autoResize(els.messageInput);
        updateCharCounter();
        els.messageInput.focus();
      });
      container.appendChild(card);
    }
  } catch (e) {
    // Fallback: wire up any static cards in the HTML
    document.querySelectorAll('.suggestion-card').forEach(card => {
      card.addEventListener('click', () => {
        const prompt = card.dataset.prompt;
        if (prompt) {
          els.messageInput.value = prompt;
          autoResize(els.messageInput);
          updateCharCounter();
          els.messageInput.focus();
        }
      });
    });
  }
}

// ╔══════════════════════════════════════════════════════════╗
// ║  14. TTS / MICROPHONE                                    ║
// ╚══════════════════════════════════════════════════════════╝

// Fix T3: MIME type map for audio formats
const AUDIO_MIME_MAP = {
  mp3: 'mpeg',
  wav: 'wav',
  ogg: 'ogg',
  webm: 'webm',
};

async function speakText(text, btn) {
  if (!text || !text.trim()) return;
  const orig = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M21 12a9 9 0 1 1-9-9"/></svg>`;

  // Try server TTS first, fall back to Web Speech API
  let serverTTSSucceeded = false;
  try {
    const fd = new FormData();
    fd.append('text', text);
    const res  = await fetch('/text-to-speech', { method: 'POST', body: fd });
    const data = await res.json();

    if (data.success && data.audio?.audio_base64) {
      const fmt  = data.audio.format || 'wav';
      const mime = AUDIO_MIME_MAP[fmt] || fmt;  // Fix T3: correct MIME type

      // Check if the audio is non-silent (edge-tts actually generated audio)
      // Silent WAV fallback has a very small size; real TTS is much larger
      const audioBytes = atob(data.audio.audio_base64).length;
      if (audioBytes > 2000) {  // threshold: silent WAV is ~1-3KB, real TTS is much more
        const audio = new Audio(`data:audio/${mime};base64,${data.audio.audio_base64}`);
        // Fix T2: handle autoplay restrictions
        try {
          await audio.play();
          serverTTSSucceeded = true;
        } catch (playErr) {
          if (playErr.name === 'NotAllowedError') {
            showToast('Click the page first to enable audio playback', 'warning');
            serverTTSSucceeded = true; // Don't fall through to speech synthesis
          }
        }
      }
    }
  } catch (e) {
    console.warn('Server TTS error:', e);
  }

  // Fallback to browser Web Speech API (always available, no install needed)
  if (!serverTTSSucceeded && 'speechSynthesis' in window) {
    try {
      window.speechSynthesis.cancel(); // Cancel any current speech
      const utterance = new SpeechSynthesisUtterance(text.slice(0, 4000));
      utterance.rate  = 1.0;
      utterance.pitch = 1.0;
      utterance.lang  = 'en-US';
      window.speechSynthesis.speak(utterance);
    } catch (e) {
      showToast('Text-to-speech unavailable', 'warning');
    }
  } else if (!serverTTSSucceeded) {
    showToast('TTS not available in this browser', 'warning');
  }

  btn.innerHTML = orig;
  btn.disabled  = false;
}

// PDF upload
els.attachBtn.addEventListener('click', () => {
  els.pdfInput.click();
});

els.pdfInput.addEventListener('change', async function () {
  const file = this.files[0];
  if (!file) return;

  const orig = els.attachBtn.innerHTML;
  els.attachBtn.disabled = true;
  els.attachBtn.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" class="spin-icon"><path d="M21 12a9 9 0 1 1-9-9"/></svg>`;

  const fd = new FormData();
  fd.append('file', file);
  if (state.activeConversationId) {
    fd.append('conversation_id', state.activeConversationId);
  }

  showToast(`Indexing "${file.name}"…`, 'info');

  try {
    const res  = await fetch('/api/upload/pdf', { method: 'POST', body: fd });
    const data = await res.json();
    if (data.success) {
      if (data.conversation_id && !state.activeConversationId) {
        state.activeConversationId = data.conversation_id;
        els.topbarTitle.textContent = `Doc: ${file.name}`;
        setTopbarChatButtons(true);
        if (typeof window.refreshConversations === 'function') {
          window.refreshConversations();
        }
      }
      hideWelcome();
      addSystemMessage(`📄 **"${file.name}"** successfully indexed (${data.chunks} segments). You can now ask any questions about this document!`);
      showToast(`"${file.name}" indexed successfully!`, 'success');
      els.messageInput.focus();
    } else {
      showToast('Upload failed: ' + (data.detail || data.message || 'unknown error'), 'error');
    }
  } catch (e) {
    console.error('PDF upload error:', e);
    showToast('Error uploading PDF: ' + e.message, 'error');
  } finally {
    els.attachBtn.innerHTML = orig;
    els.attachBtn.disabled  = false;
    this.value = '';
  }
});

// Image Upload
if (els.imageBtn && els.imageInput) {
  els.imageBtn.addEventListener('click', () => els.imageInput.click());

  els.imageInput.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const validTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/webp', 'image/gif'];
    if (!validTypes.includes(file.type)) {
      showToast('Please select a PNG, JPG, WEBP, or GIF image.', 'error');
      return;
    }

    const orig = els.imageBtn.innerHTML;
    els.imageBtn.disabled = true;
    els.imageBtn.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" class="spin-icon"><path d="M21 12a9 9 0 1 1-9-9"/></svg>`;

    showToast(`Uploading ${file.name}…`, 'info');
    const fd = new FormData();
    fd.append('file', file);
    if (state.activeConversationId) {
      fd.append('conversation_id', state.activeConversationId);
    }

    try {
      const res = await fetch('/api/upload/image', { method: 'POST', body: fd });
      const data = await res.json();
      if (data.success) {
        if (data.conversation_id && !state.activeConversationId) {
          state.activeConversationId = data.conversation_id;
          setTopbarChatButtons(true);
          if (typeof window.refreshConversations === 'function') {
            window.refreshConversations();
          }
        }
        showToast('Image attached successfully!', 'success');
        els.messageInput.value = (els.messageInput.value + `\n[Image attached: ${file.name}] `).trim();
        autoResize(els.messageInput);
        updateCharCounter();
        els.messageInput.focus();
      } else {
        showToast(data.message || data.detail || 'Image upload failed', 'error');
      }
    } catch (err) {
      console.error('Image upload error:', err);
      showToast('Network error during upload', 'error');
    } finally {
      els.imageBtn.innerHTML = orig;
      els.imageBtn.disabled  = false;
      els.imageInput.value = '';
    }
  });
}

// ── Microphone / Speech-to-Text ───────────────────────────────
let mediaRecorder = null;
let audioChunks   = [];
let isRecording   = false;

const MIC_SVG = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/></svg>`;

els.micBtn.addEventListener('click', async () => {
  if (!isRecording) {
    try {
      const stream  = await navigator.mediaDevices.getUserMedia({ audio: true });

      // Fix ST1: detect the actual supported MIME type
      const mimeType = (() => {
        const types = [
          'audio/webm;codecs=opus',
          'audio/webm',
          'audio/ogg;codecs=opus',
          'audio/mp4',
        ];
        for (const t of types) {
          if (MediaRecorder.isTypeSupported(t)) return t;
        }
        return '';  // browser default
      })();

      mediaRecorder = mimeType
        ? new MediaRecorder(stream, { mimeType })
        : new MediaRecorder(stream);
      audioChunks   = [];

      mediaRecorder.addEventListener('dataavailable', e => { if (e.data.size > 0) audioChunks.push(e.data); });

      mediaRecorder.addEventListener('stop', async () => {
        // Use the actual MIME type from recorder (not hardcoded 'audio/wav')
        const recordedMime = mediaRecorder?.mimeType || mimeType || 'audio/webm';
        const ext = recordedMime.includes('ogg') ? 'ogg'
                  : recordedMime.includes('mp4')  ? 'mp4'
                  : 'webm';

        const blob = new Blob(audioChunks, { type: recordedMime });
        const fd   = new FormData();
        fd.append('file', blob, `recording.${ext}`);

        const origHtml = els.micBtn.innerHTML;
        els.micBtn.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M21 12a9 9 0 1 1-9-9"/></svg>`;
        els.micBtn.disabled  = true;

        try {
          const res  = await fetch('/speech-to-text', { method: 'POST', body: fd });
          const data = await res.json();
          if (data.success && data.text) {
            els.messageInput.value = (els.messageInput.value + ' ' + data.text).trim();
            autoResize(els.messageInput);
            updateCharCounter();
            showToast('Transcription complete', 'success');
          } else {
            showToast(data.message || 'Transcription failed', 'warning');
          }
        } catch (e) {
          showToast('Error transcribing audio', 'error');
        } finally {
          els.micBtn.innerHTML = origHtml;
          els.micBtn.disabled  = false;
          // Fix ST2: clean up mediaRecorder reference
          mediaRecorder = null;
        }
      });

      mediaRecorder.start();
      isRecording = true;
      els.micBtn.classList.add('recording');
      showToast('Recording… click mic again to stop', 'info');
    } catch (err) {
      if (err.name === 'NotAllowedError') {
        showToast('Microphone access denied — please allow it in browser settings', 'error');
      } else {
        showToast('Could not access microphone: ' + err.message, 'error');
      }
    }
  } else {
    // Stop recording
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
      mediaRecorder.stop();
      mediaRecorder.stream.getTracks().forEach(t => t.stop());
    }
    isRecording = false;
    els.micBtn.classList.remove('recording');
  }
});

// ╔══════════════════════════════════════════════════════════╗
// ║  15. INIT                                                ║
// ╚══════════════════════════════════════════════════════════╝

(async function init() {
  setTheme(getTheme());
  setSendingState(false);
  await Promise.all([fetchModels(), refreshConversations(), loadWelcomeSuggestions()]);
  els.messageInput.focus();
})();
