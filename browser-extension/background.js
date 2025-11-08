// Background script for Synapse browser extension

// Create context menu on installation
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: 'save-to-synapse',
    title: 'Save to Synapse',
    contexts: ['page', 'selection']
  });
});

// Handle context menu clicks
chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId === 'save-to-synapse') {
    try {
      await chrome.tabs.sendMessage(tab.id, {
        action: 'save-page',
        selectionText: info.selectionText
      });
    } catch (error) {
      console.error('Failed to send message to content script:', error);
    }
  }
});

// Handle keyboard shortcuts
chrome.commands.onCommand.addListener(async (command) => {
  if (command === 'save-page') {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    try {
      await chrome.tabs.sendMessage(tab.id, {
        action: 'save-page'
      });
    } catch (error) {
      console.error('Failed to send message to content script:', error);
    }
  }
});

// Handle messages from content script
chrome.runtime.onMessage.addListener(async (message, sender, sendResponse) => {
  if (message.action === 'save-content') {
    try {
      const response = await saveToSynapse(message.data);
      sendResponse({ success: true, data: response });
    } catch (error) {
      console.error('Error saving to Synapse:', error);
      sendResponse({ success: false, error: error.message });
    }
    return true; // Keep message channel open for async response
  }
});

// Save content to Synapse API
async function saveToSynapse(data) {
  // Get API URL from storage or use default
  const storage = await chrome.storage.sync.get(['synapseApiUrl']);
  const apiUrl = storage.synapseApiUrl || 'http://localhost:8000';
  
  const formData = new FormData();
  formData.append('type', 'url');
  formData.append('title', data.title || '');
  formData.append('url', data.url);
  formData.append('raw_content', data.content || '');
  formData.append('tags', JSON.stringify(data.tags || []));

  const response = await fetch(`${apiUrl}/api/items`, {
    method: 'POST',
    body: formData
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`);
  }

  const result = await response.json();
  console.log('API response:', result); // Debug logging
  return result;
}