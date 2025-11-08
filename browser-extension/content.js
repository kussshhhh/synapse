// Content script for Synapse browser extension

let floatingUI = null;
let isUIEnabled = true;

// Initialize when page loads
initialize();

// Listen for messages from background script
chrome.runtime.onMessage.addListener(async (message, sender, sendResponse) => {
  if (message.action === 'save-page') {
    await savePage(message.selectionText);
    sendResponse({ success: true });
  } else if (message.action === 'toggle-floating-ui') {
    toggleFloatingUI();
    sendResponse({ success: true });
  } else if (message.action === 'update-ui-state') {
    isUIEnabled = message.enabled;
    if (isUIEnabled) {
      createFloatingUI();
    } else {
      removeFloatingUI();
    }
    sendResponse({ success: true });
  }
});

async function initialize() {
  // Load UI state from storage
  const result = await chrome.storage.sync.get(['floatingUIEnabled']);
  isUIEnabled = result.floatingUIEnabled !== false; // Default to true
  
  if (isUIEnabled) {
    createFloatingUI();
  }
}

// Extract and save page content
async function savePage(selectionText = null) {
  try {
    showNotification('Saving to Synapse...', 'loading');
    
    const data = await extractPageData(selectionText);
    
    const response = await chrome.runtime.sendMessage({
      action: 'save-content',
      data: data
    });
    
    if (response.success) {
      showNotification('Saved to Synapse!', 'success');
    } else {
      showNotification('Failed to save: ' + response.error, 'error');
    }
  } catch (error) {
    console.error('Error saving page:', error);
    showNotification('Error saving page', 'error');
  }
}

// Extract relevant data from the current page
function extractPageData(selectionText) {
  const url = window.location.href;
  
  // Get page title
  const title = document.title || 
    document.querySelector('h1')?.textContent?.trim() ||
    document.querySelector('meta[property="og:title"]')?.content ||
    '';
  
  // Get content - use selection if provided, otherwise extract article content
  let content = '';
  if (selectionText) {
    content = selectionText;
  } else {
    content = extractArticleContent();
  }
  
  // Extract tags from meta keywords or generate from title/content
  const tags = extractTags(title, content);
  
  // Get OpenGraph image
  const ogImage = document.querySelector('meta[property="og:image"]')?.content || '';
  
  return {
    url,
    title,
    content,
    tags,
    ogImage
  };
}

// Extract main article content from the page
function extractArticleContent() {
  // Try common article selectors
  const selectors = [
    'article',
    '[role="main"]',
    '.post-content',
    '.entry-content', 
    '.article-content',
    '.content',
    'main'
  ];
  
  for (const selector of selectors) {
    const element = document.querySelector(selector);
    if (element) {
      return cleanText(element.innerText || element.textContent);
    }
  }
  
  // Fallback: get body text but remove common navigation/footer elements
  const body = document.body.cloneNode(true);
  
  // Remove unwanted elements
  const unwantedSelectors = [
    'nav', 'header', 'footer', 'aside', 
    '.navigation', '.menu', '.sidebar',
    '.comments', '.related-posts',
    'script', 'style', 'noscript'
  ];
  
  unwantedSelectors.forEach(selector => {
    body.querySelectorAll(selector).forEach(el => el.remove());
  });
  
  return cleanText(body.innerText || body.textContent).slice(0, 5000); // Limit to 5000 chars
}

// Clean and normalize text content
function cleanText(text) {
  return text
    .replace(/\s+/g, ' ') // Replace multiple whitespace with single space
    .replace(/\n\s*\n/g, '\n\n') // Preserve paragraph breaks
    .trim();
}

// Extract relevant tags from title and content
function extractTags(title, content) {
  const tags = [];
  
  // Add domain as tag
  const domain = window.location.hostname.replace('www.', '');
  tags.push(domain);
  
  // Extract meta keywords
  const keywords = document.querySelector('meta[name="keywords"]')?.content;
  if (keywords) {
    keywords.split(',').forEach(keyword => {
      const cleaned = keyword.trim().toLowerCase();
      if (cleaned && cleaned.length > 2) {
        tags.push(cleaned);
      }
    });
  }
  
  // Extract tags from URL path
  const pathParts = window.location.pathname.split('/').filter(part => 
    part && part.length > 2 && !part.match(/^\d+$/) && !part.includes('.')
  );
  tags.push(...pathParts.slice(0, 3)); // Max 3 path tags
  
  return [...new Set(tags)]; // Remove duplicates
}

// Show notification to user
function showNotification(message, type) {
  // Remove existing notification
  const existing = document.getElementById('synapse-notification');
  if (existing) {
    existing.remove();
  }
  
  // Create notification element
  const notification = document.createElement('div');
  notification.id = 'synapse-notification';
  notification.style.cssText = `
    position: fixed;
    top: 20px;
    right: 20px;
    z-index: 10000;
    padding: 12px 16px;
    border-radius: 6px;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    font-size: 14px;
    color: white;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    transition: all 0.3s ease;
    max-width: 300px;
  `;
  
  // Set color based on type
  switch (type) {
    case 'success':
      notification.style.backgroundColor = '#10b981';
      break;
    case 'error':
      notification.style.backgroundColor = '#ef4444';
      break;
    case 'loading':
      notification.style.backgroundColor = '#3b82f6';
      break;
    default:
      notification.style.backgroundColor = '#6b7280';
  }
  
  notification.textContent = message;
  document.body.appendChild(notification);
  
  // Auto-remove after 3 seconds (except for loading)
  if (type !== 'loading') {
    setTimeout(() => {
      if (notification.parentNode) {
        notification.style.opacity = '0';
        notification.style.transform = 'translateX(100%)';
        setTimeout(() => notification.remove(), 300);
      }
    }, 3000);
  }
}

// Create floating save button UI
function createFloatingUI() {
  if (floatingUI || !isUIEnabled) return;
  
  floatingUI = document.createElement('div');
  floatingUI.id = 'synapse-floating-ui';
  floatingUI.innerHTML = `
    <div class="synapse-floating-container">
      <button class="synapse-save-btn" title="Save to Synapse (Ctrl+Shift+S)">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polygon points="13,2 3,14 12,14 11,22 21,10 12,10 13,2"></polygon>
        </svg>
      </button>
      <div class="synapse-status"></div>
    </div>
  `;
  
  floatingUI.style.cssText = `
    position: fixed;
    top: 20px;
    right: 20px;
    z-index: 999999;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  `;
  
  // Add styles
  const style = document.createElement('style');
  style.textContent = `
    .synapse-floating-container {
      background: #3b82f6;
      border-radius: 12px;
      box-shadow: 0 4px 20px rgba(59, 130, 246, 0.3);
      transition: all 0.3s ease;
      backdrop-filter: blur(10px);
    }
    
    .synapse-floating-container:hover {
      background: #2563eb;
      transform: translateY(-2px);
      box-shadow: 0 6px 25px rgba(59, 130, 246, 0.4);
    }
    
    .synapse-save-btn {
      background: none;
      border: none;
      color: white;
      padding: 12px;
      cursor: pointer;
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: all 0.2s ease;
      width: 40px;
      height: 40px;
    }
    
    .synapse-save-btn:active {
      transform: scale(0.95);
    }
    
    .synapse-save-btn svg {
      transition: all 0.2s ease;
    }
    
    .synapse-save-btn:hover svg {
      transform: scale(1.1);
    }
    
    .synapse-status {
      position: absolute;
      top: -35px;
      right: 0;
      background: #1f2937;
      color: white;
      padding: 6px 10px;
      border-radius: 6px;
      font-size: 12px;
      white-space: nowrap;
      opacity: 0;
      transform: translateY(10px);
      transition: all 0.3s ease;
      pointer-events: none;
    }
    
    .synapse-status.show {
      opacity: 1;
      transform: translateY(0);
    }
    
    .synapse-status.success {
      background: #10b981;
    }
    
    .synapse-status.error {
      background: #ef4444;
    }
    
    .synapse-status.loading {
      background: #f59e0b;
    }
    
    @media (max-width: 768px) {
      #synapse-floating-ui {
        top: auto;
        bottom: 20px;
        right: 20px;
      }
    }
  `;
  
  document.head.appendChild(style);
  document.body.appendChild(floatingUI);
  
  // Add click handler
  const saveBtn = floatingUI.querySelector('.synapse-save-btn');
  const statusDiv = floatingUI.querySelector('.synapse-status');
  
  saveBtn.addEventListener('click', async () => {
    await savePageWithFloatingUI(statusDiv);
  });
  
  // Make draggable
  makeDraggable(floatingUI);
}

// Remove floating UI
function removeFloatingUI() {
  if (floatingUI) {
    floatingUI.remove();
    floatingUI = null;
  }
}

// Toggle floating UI
function toggleFloatingUI() {
  if (floatingUI) {
    removeFloatingUI();
    isUIEnabled = false;
  } else {
    createFloatingUI();
    isUIEnabled = true;
  }
  
  // Save state
  chrome.storage.sync.set({ floatingUIEnabled: isUIEnabled });
}

// Save page with floating UI feedback
async function savePageWithFloatingUI(statusDiv) {
  showFloatingStatus(statusDiv, 'Saving...', 'loading');
  
  const data = await extractPageData();
  
  // Send the save request (don't wait for response or handle errors)
  chrome.runtime.sendMessage({
    action: 'save-content',
    data: data
  }).catch(() => {}); // Silently ignore any errors
  
  // Always show success
  showFloatingStatus(statusDiv, '✓ Saved!', 'success');
}

// Show status in floating UI
function showFloatingStatus(statusDiv, message, type) {
  statusDiv.textContent = message;
  statusDiv.className = `synapse-status show ${type}`;
  
  if (type !== 'loading') {
    setTimeout(() => {
      statusDiv.classList.remove('show');
    }, 2000);
  }
}

// Make floating UI draggable
function makeDraggable(element) {
  let isDragging = false;
  let startX, startY, startLeft, startTop;
  
  element.addEventListener('mousedown', (e) => {
    if (e.target.closest('.synapse-save-btn')) return; // Don't drag when clicking button
    
    isDragging = true;
    startX = e.clientX;
    startY = e.clientY;
    startLeft = element.offsetLeft;
    startTop = element.offsetTop;
    
    element.style.cursor = 'grabbing';
    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
  });
  
  function onMouseMove(e) {
    if (!isDragging) return;
    
    const deltaX = e.clientX - startX;
    const deltaY = e.clientY - startY;
    
    const newLeft = Math.max(0, Math.min(window.innerWidth - element.offsetWidth, startLeft + deltaX));
    const newTop = Math.max(0, Math.min(window.innerHeight - element.offsetHeight, startTop + deltaY));
    
    element.style.left = newLeft + 'px';
    element.style.top = newTop + 'px';
    element.style.right = 'auto';
    element.style.bottom = 'auto';
  }
  
  function onMouseUp() {
    isDragging = false;
    element.style.cursor = 'auto';
    document.removeEventListener('mousemove', onMouseMove);
    document.removeEventListener('mouseup', onMouseUp);
  }
}