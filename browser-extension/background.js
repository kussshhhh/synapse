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
  } else if (message.action === 'save-image') {
    try {
      const response = await saveImageToSynapse(message.data);
      sendResponse({ success: true, data: response });
    } catch (error) {
      console.error('Error saving image to Synapse:', error);
      sendResponse({ success: false, error: error.message });
    }
    return true;
  }
});

// Save content to Synapse API
async function saveToSynapse(data) {
  // Get API URL from storage or use default
  const storage = await chrome.storage.sync.get(['synapseApiUrl']);
  const apiUrl = storage.synapseApiUrl || 'http://localhost:8000';
  
  const formData = new FormData();
  
  // Determine type based on content
  const type = data.imageUrl ? 'image' : 'url';
  
  formData.append('type', type);
  formData.append('title', data.title || '');
  formData.append('url', data.imageUrl || data.url);
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

// Save image to Synapse API
async function saveImageToSynapse(data) {
  // Get API URL from storage or use default
  const storage = await chrome.storage.sync.get(['synapseApiUrl']);
  const apiUrl = storage.synapseApiUrl || 'http://localhost:8000';
  
  const formData = new FormData();
  
  // Handle image data
  if (data.imageUrl && !data.imageBlob) {
    // If it's a regular URL, download the image first
    try {
      const imageResponse = await fetch(data.imageUrl);
      const blob = await imageResponse.blob();
      formData.append('file', blob, data.filename);
    } catch (error) {
      console.error('Failed to download image:', error);
      // Fallback to saving as URL
      formData.append('type', 'url');
      formData.append('url', data.url);
    }
  } else if (data.imageBlob) {
    // If we already have a blob (from base64), use it directly
    formData.append('file', data.imageBlob, data.filename);
  } else {
    // No image data, just save as URL
    formData.append('type', 'url');
    formData.append('url', data.url);
  }
  
  // Add other metadata
  formData.append('type', 'image');
  formData.append('title', data.title || '');
  formData.append('url', data.url);  // This is the source page URL
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
  console.log('Image save response:', result);
  return result;
}