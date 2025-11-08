# Synapse Browser Extension

A browser extension to save articles and web content to your Synapse second brain.

## Features

- **One-click saving**: Save current page with extension popup
- **Context menu**: Right-click anywhere and select "Save to Synapse"
- **Keyboard shortcut**: `Ctrl+Shift+S` (or `Cmd+Shift+S` on Mac)
- **Smart content extraction**: Automatically extracts article content and metadata
- **Tag generation**: Auto-generates relevant tags from page content
- **Selection support**: Save selected text instead of full page

## Installation

### Development Installation

1. Open Chrome and go to `chrome://extensions/`
2. Enable "Developer mode" in the top right
3. Click "Load unpacked" and select the `browser-extension` folder
4. The Synapse extension should now appear in your extensions

### Usage

1. **Configure API URL**: Click the extension icon and set your Synapse API URL (default: `http://localhost:8000`)
2. **Save a page**: 
   - Click the extension icon and click "Save Current Page"
   - Use keyboard shortcut `Ctrl+Shift+S`
   - Right-click and select "Save to Synapse"
3. **Save selection**: Select text on a page, then right-click and choose "Save to Synapse"

## Content Extraction

The extension intelligently extracts content using:

1. **Article detection**: Looks for `<article>`, `[role="main"]`, `.content` elements
2. **Metadata extraction**: Gets title, OpenGraph data, meta keywords
3. **Tag generation**: Creates tags from domain, URL path, and keywords
4. **Clean text**: Removes navigation, ads, and other non-content elements

## API Integration

The extension sends data to your Synapse API endpoint (`/api/items`) with:

```json
{
  "type": "url",
  "title": "Article Title",
  "url": "https://example.com/article",
  "raw_content": "Article content...",
  "tags": ["domain.com", "technology", "ai"]
}
```

## Requirements

- Chrome/Chromium browser (Manifest V3)
- Running Synapse backend API
- CORS enabled on Synapse API for browser requests

## Files

- `manifest.json` - Extension configuration
- `background.js` - Service worker for context menus and shortcuts
- `content.js` - Content script for page extraction
- `popup.html/js` - Extension popup interface
- `icons/` - Extension icons