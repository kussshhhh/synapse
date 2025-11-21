import React, { useState, useEffect } from 'react';
import { searchItems, semanticSearchItems, type SemanticSearchResult } from '../api';
import type { Item } from '../types';

interface ItemListProps {
  refresh?: boolean;
  onRefreshComplete?: () => void;
}

export default function ItemList({ refresh, onRefreshComplete }: ItemListProps) {
  // Separate state for Images and Text/Other
  const [imageItems, setImageItems] = useState<(Item | SemanticSearchResult)[]>([]);
  const [textItems, setTextItems] = useState<(Item | SemanticSearchResult)[]>([]);

  const [loadingImages, setLoadingImages] = useState(false);
  const [loadingText, setLoadingText] = useState(false);
  const [error, setError] = useState('');

  const [searchQuery, setSearchQuery] = useState('');
  const [searchMode, setSearchMode] = useState<'smart' | 'hybrid' | 'semantic' | 'text'>('smart');

  // Pagination state for each column
  const [imagePage, setImagePage] = useState(1);
  const [textPage, setTextPage] = useState(1);
  const [hasMoreImages, setHasMoreImages] = useState(true);
  const [hasMoreText, setHasMoreText] = useState(true);

  const itemsPerPage = 10;

  // Helper to fetch items based on type
  const fetchItemsByType = async (
    types: string[],
    page: number,
    query: string,
    mode: string
  ) => {
    const skip = (page - 1) * itemsPerPage;

    if (!query) {
      // If no query, use searchItems with empty query to leverage type filtering
      return await searchItems('', skip, itemsPerPage, false, types);
    } else if (mode === 'smart') {
      // For smart search, we want to force the types we are looking for
      // ignoring Claude's type suggestions to ensure we populate both columns.
      // We use hybrid search with the query for the split view when in "Smart" mode.
      return await searchItems(query, skip, itemsPerPage, true, types);
    } else if (mode === 'semantic') {
      return await semanticSearchItems(query, skip, itemsPerPage, 0.2, types);
    } else if (mode === 'text') {
      return await searchItems(query, skip, itemsPerPage, false, types);
    } else {
      // hybrid (default)
      return await searchItems(query, skip, itemsPerPage, true, types);
    }
  };

  const loadImages = async (page = 1, append = false) => {
    setLoadingImages(true);
    try {
      const data = await fetchItemsByType(['image'], page, searchQuery, searchMode);
      setHasMoreImages(data.length === itemsPerPage);
      if (append) {
        setImageItems(prev => [...prev, ...data]);
      } else {
        setImageItems(data);
      }
    } catch (err) {
      console.error("Failed to load images", err);
    } finally {
      setLoadingImages(false);
    }
  };

  const loadText = async (page = 1, append = false) => {
    setLoadingText(true);
    try {
      const data = await fetchItemsByType(['note', 'url', 'pdf', 'video', 'product'], page, searchQuery, searchMode);
      setHasMoreText(data.length === itemsPerPage);
      if (append) {
        setTextItems(prev => [...prev, ...data]);
      } else {
        setTextItems(data);
      }
    } catch (err) {
      console.error("Failed to load text items", err);
      setError('Failed to load some items');
    } finally {
      setLoadingText(false);
    }
  };

  const loadAll = (resetPage = false) => {
    setError('');
    if (resetPage) {
      setImagePage(1);
      setTextPage(1);
      // We need to pass 1 explicitly because state updates are async
      loadImages(1, false);
      loadText(1, false);
    } else {
      loadImages(imagePage, false);
      loadText(textPage, false);
    }
  };

  useEffect(() => {
    loadAll(true);
  }, []);

  useEffect(() => {
    if (refresh) {
      loadAll(true);
      onRefreshComplete?.();
    }
  }, [refresh]);

  // Effect to reload when search mode changes
  useEffect(() => {
    if (searchQuery) {
      loadAll(true);
    }
  }, [searchMode]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    loadAll(true);
  };

  const handleClear = () => {
    setSearchQuery('');
    // We need to wait for state update or just pass empty string manually
    // But loadAll uses state. 
    // Let's just force a reload with empty query logic
    // Actually, if we set query to empty, the effect on searchMode won't trigger (it checks searchQuery)
    // So we need to manually trigger.
    // But state is stale.
    // Let's just reload the page.
    window.location.reload(); // Simplest way to reset everything cleanly
  };

  const handleLoadMoreImages = () => {
    if (hasMoreImages && !loadingImages) {
      const nextPage = imagePage + 1;
      setImagePage(nextPage);
      loadImages(nextPage, true);
    }
  };

  const handleLoadMoreText = () => {
    if (hasMoreText && !loadingText) {
      const nextPage = textPage + 1;
      setTextPage(nextPage);
      loadText(nextPage, true);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString();
  };

  const getTypeColor = (type: string) => {
    const colors: Record<string, string> = {
      note: '#4CAF50',
      url: '#2196F3',
      image: '#FF9800',
      video: '#E91E63',
      pdf: '#9C27B0',
      product: '#FF5722'
    };
    return colors[type] || '#757575';
  };

  const renderItemCard = (item: Item | SemanticSearchResult) => (
    <div key={item.id} className="item-card">
      <div className="item-header">
        <span
          className="item-type"
          style={{ backgroundColor: getTypeColor(item.type) }}
        >
          {item.type}
        </span>
        <div className="item-header-right">
          {'similarity_score' in item && (
            <span className="similarity-score">
              {Math.round(item.similarity_score * 100)}% match
            </span>
          )}
          <span className="item-date">{formatDate(item.created_at)}</span>
        </div>
      </div>

      <div className="item-content">
        {item.title && <h3 className="item-title">{item.title}</h3>}

        {/* Show image preview for image items */}
        {item.type === 'image' && (
          <div className="item-image">
            <img
              src={item.s3_key ? `http://localhost:4566/synapse-storage/${item.s3_key}` : item.url || ''}
              alt={item.title || 'Uploaded image'}
              className="image-preview"
              onError={(e) => {
                // If S3 fails and we haven't tried the URL yet, try the URL
                if (item.s3_key && item.url && e.currentTarget.src.includes('localhost:4566') && !e.currentTarget.src.includes(item.url)) {
                  e.currentTarget.src = item.url;
                } else {
                  e.currentTarget.style.display = 'none';
                }
              }}
            />
          </div>
        )}

        {item.url && item.type !== 'image' && (
          <a
            href={item.url}
            target="_blank"
            rel="noopener noreferrer"
            className="item-url"
          >
            {item.url}
          </a>
        )}

        {/* For images, show source page if URL exists */}
        {item.type === 'image' && item.url && !item.url.startsWith('data:') && (
          <div className="item-source">
            Source: <a
              href={item.url}
              target="_blank"
              rel="noopener noreferrer"
              className="item-source-link"
            >
              {new URL(item.url).hostname}
            </a>
          </div>
        )}

        {item.raw_content && (
          <p className="item-text">
            {item.raw_content.length > 200
              ? `${item.raw_content.slice(0, 200)}...`
              : item.raw_content}
          </p>
        )}

        {item.tags.length > 0 && (
          <div className="item-tags">
            {item.tags.map((tag, index) => (
              <span key={index} className="tag">{tag}</span>
            ))}
          </div>
        )}
      </div>
    </div>
  );

  return (
    <div className="item-list">
      <div className="search-section">
        <h2>Your Items</h2>

        <form onSubmit={handleSearch} className="search-form">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search your items..."
            className="search-input"
          />
          <button type="submit">Search</button>
          {searchQuery && (
            <button
              type="button"
              onClick={handleClear}
            >
              Clear
            </button>
          )}
        </form>

        <div className="search-controls">
          {searchQuery && (
            <div className="search-mode-selector">
              <label>Search mode:</label>
              <select
                value={searchMode}
                onChange={(e) => setSearchMode(e.target.value as any)}
                className="search-mode-select"
              >
                <option value="smart">🤖 Smart (Gemini AI)</option>
                <option value="hybrid">🧠 Hybrid (Text + AI)</option>
                <option value="semantic">🎯 Semantic (AI Only)</option>
                <option value="text">📝 Text Only</option>
              </select>
            </div>
          )}
        </div>
      </div>

      {error && <div className="error">{error}</div>}

      <div className="split-view-container">
        {/* Left Column: Text/Other */}
        <div className="split-column">
          <div className="split-column-header">
            <h3>📄 Text & Notes</h3>
            <span className="count-badge">{textItems.length}</span>
          </div>

          <div className="split-column-content">
            {loadingText && textItems.length === 0 && <div className="loading">Loading...</div>}

            {textItems.length === 0 && !loadingText && (
              <div className="no-items">No text items found</div>
            )}

            <div className="items-grid">
              {textItems.map(renderItemCard)}
            </div>

            {hasMoreText && (
              <div className="load-more-container">
                <button
                  onClick={handleLoadMoreText}
                  disabled={loadingText}
                  className="load-more-btn"
                >
                  {loadingText ? 'Loading...' : 'Load More Text'}
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Images */}
        <div className="split-column">
          <div className="split-column-header">
            <h3>🖼️ Images</h3>
            <span className="count-badge">{imageItems.length}</span>
          </div>

          <div className="split-column-content">
            {loadingImages && imageItems.length === 0 && <div className="loading">Loading...</div>}

            {imageItems.length === 0 && !loadingImages && (
              <div className="no-items">No images found</div>
            )}

            <div className="items-grid">
              {imageItems.map(renderItemCard)}
            </div>

            {hasMoreImages && (
              <div className="load-more-container">
                <button
                  onClick={handleLoadMoreImages}
                  disabled={loadingImages}
                  className="load-more-btn"
                >
                  {loadingImages ? 'Loading...' : 'Load More Images'}
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}