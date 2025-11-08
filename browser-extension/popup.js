// Popup script for Synapse browser extension

document.addEventListener('DOMContentLoaded', async () => {
  const saveBtn = document.getElementById('saveBtn');
  const pageTitle = document.getElementById('pageTitle');
  const pageUrl = document.getElementById('pageUrl');
  const apiUrlInput = document.getElementById('apiUrl');
  const floatingUIToggle = document.getElementById('floatingUIToggle');
  const status = document.getElementById('status');

  // Load current tab info
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (tab) {
    pageTitle.textContent = tab.title || 'No title';
    pageUrl.textContent = tab.url;
  }

  // Load saved settings
  const storage = await chrome.storage.sync.get(['synapseApiUrl', 'floatingUIEnabled']);
  apiUrlInput.value = storage.synapseApiUrl || 'http://localhost:8000';
  floatingUIToggle.checked = storage.floatingUIEnabled !== false; // Default to true

  // Save API URL when changed
  apiUrlInput.addEventListener('change', async () => {
    await chrome.storage.sync.set({ synapseApiUrl: apiUrlInput.value });
    showStatus('API URL saved', 'success');
  });

  // Handle floating UI toggle
  floatingUIToggle.addEventListener('change', async () => {
    const enabled = floatingUIToggle.checked;
    await chrome.storage.sync.set({ floatingUIEnabled: enabled });
    
    // Send message to content script to update UI
    try {
      await chrome.tabs.sendMessage(tab.id, {
        action: 'update-ui-state',
        enabled: enabled
      });
      showStatus(enabled ? 'Floating UI enabled' : 'Floating UI disabled', 'success');
    } catch (error) {
      console.log('Could not update floating UI (page may need refresh)');
    }
  });

  // Handle save button click
  saveBtn.addEventListener('click', async () => {
    await savePage();
  });

  async function savePage() {
    try {
      saveBtn.disabled = true;
      saveBtn.textContent = 'Saving...';
      showStatus('Saving to Synapse...', 'loading');

      // Send message to content script
      const response = await chrome.tabs.sendMessage(tab.id, {
        action: 'save-page'
      });

      if (response && response.success) {
        showStatus('Saved to Synapse!', 'success');
        saveBtn.textContent = 'Saved ✓';
        setTimeout(() => {
          saveBtn.textContent = 'Save Current Page';
          saveBtn.disabled = false;
        }, 2000);
      } else {
        throw new Error('Failed to save page');
      }
    } catch (error) {
      console.error('Error saving page:', error);
      showStatus('Error saving page', 'error');
      saveBtn.textContent = 'Save Current Page';
      saveBtn.disabled = false;
    }
  }

  function showStatus(message, type) {
    status.textContent = message;
    status.className = `status ${type}`;
    status.style.display = 'block';
    
    if (type !== 'loading') {
      setTimeout(() => {
        status.style.display = 'none';
      }, 3000);
    }
  }

  // Handle keyboard shortcuts in popup
  document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'S') {
      e.preventDefault();
      savePage();
    }
  });
});