import React, { useState, useEffect } from 'react';
import { getItems, searchItems, semanticSearchItems, smartSearch, type SemanticSearchResult } from '../api';
import type { Item } from '../types';

interface ItemListProps {
  refresh?: boolean;
  onRefreshComplete?: () => void;
}

export default function ItemList({ refresh, onRefreshComplete }: ItemListProps) {
  const [items, setItems] = useState<(Item | SemanticSearchResult)[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [searchMode, setSearchMode] = useState<'smart' | 'hybrid' | 'semantic' | 'text'>('smart');
  const [contentTypeFilters, setContentTypeFilters] = useState<string[]>(['any']);
  const [currentPage, setCurrentPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const itemsPerPage = 10;

  const loadItems = async (query = '', mode = searchMode, contentTypes = contentTypeFilters, page = 1, append = false) => {
    setLoading(true);
    setError('');
    
    try {
      const skip = (page - 1) * itemsPerPage;
      let data;
      
      if (!query) {
        data = await getItems(skip, itemsPerPage);
      } else if (mode === 'smart') {
        // Claude-powered intelligent search with content type influence
        data = await smartSearch(query, skip, itemsPerPage, contentTypes);
      } else if (mode === 'semantic') {
        // Pure semantic search - use user's selected content types only
        data = await semanticSearchItems(query, skip, itemsPerPage, 0.2, contentTypes);
      } else if (mode === 'text') {
        // Pure text search - use user's selected content types only
        data = await searchItems(query, skip, itemsPerPage, false, contentTypes); // semantic=false
      } else {
        // hybrid (default) - use user's selected content types only
        data = await searchItems(query, skip, itemsPerPage, true, contentTypes); // semantic=true
      }
      
      setHasMore(data.length === itemsPerPage);
      
      if (append) {
        setItems(prev => [...prev, ...data]);
      } else {
        setItems(data);
        setCurrentPage(page);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load items');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadItems();
  }, []);

  useEffect(() => {
    if (refresh) {
      setCurrentPage(1);
      // Always refresh to latest items (page 1, no append)
      loadItems(searchQuery, searchMode, contentTypeFilters, 1, false);
      onRefreshComplete?.();
    }
  }, [refresh]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setCurrentPage(1);
    loadItems(searchQuery, searchMode, contentTypeFilters, 1);
  };

  const handleNextPage = () => {
    if (hasMore && !loading) {
      const nextPage = currentPage + 1;
      loadItems(searchQuery, searchMode, contentTypeFilters, nextPage);
    }
  };

  const handlePrevPage = () => {
    if (currentPage > 1 && !loading) {
      const prevPage = currentPage - 1;
      loadItems(searchQuery, searchMode, contentTypeFilters, prevPage);
    }
  };

  const handleLoadMore = () => {
    if (hasMore && !loading) {
      const nextPage = currentPage + 1;
      loadItems(searchQuery, searchMode, contentTypeFilters, nextPage, true);
      setCurrentPage(nextPage);
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
              onClick={() => {
                setSearchQuery('');
                setCurrentPage(1);
                loadItems('', searchMode, contentTypeFilters, 1);
              }}
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
                onChange={(e) => {
                  const mode = e.target.value as 'smart' | 'hybrid' | 'semantic' | 'text';
                  setSearchMode(mode);
                  setCurrentPage(1);
                  loadItems(searchQuery, mode, contentTypeFilters, 1);
                }}
                className="search-mode-select"
              >
                <option value="smart">🤖 Smart (Claude AI)</option>
                <option value="hybrid">🧠 Hybrid (Text + AI)</option>
                <option value="semantic">🎯 Semantic (AI Only)</option>
                <option value="text">📝 Text Only</option>
              </select>
            </div>
          )}
          
          <div className="content-type-selector">
            <label>
              Content types:
              {searchMode === 'smart' && searchQuery && (
                <span className="claude-influence-indicator"> 🤖 (Claude can influence these)</span>
              )}
            </label>
            <div className="content-type-checkboxes">
              {[
                { value: 'any', label: '📂 All Types', exclusive: true },
                { value: 'image', label: '🖼️ Images' },
                { value: 'url', label: '🔗 URLs' },
                { value: 'pdf', label: '📄 PDFs' },
                { value: 'video', label: '🎥 Videos' },
                { value: 'note', label: '📝 Notes' },
                { value: 'product', label: '🛒 Products' }
              ].map((type) => (
                <label key={type.value} className="content-type-checkbox">
                  <input
                    type="checkbox"
                    checked={contentTypeFilters.includes(type.value)}
                    onChange={(e) => {
                      let newFilters;
                      if (type.exclusive) {
                        // "All Types" is exclusive - if selected, clear others
                        newFilters = e.target.checked ? ['any'] : [];
                      } else {
                        // Regular type - add/remove from list
                        if (e.target.checked) {
                          // Remove "any" if selecting specific types
                          newFilters = [...contentTypeFilters.filter(f => f !== 'any'), type.value];
                        } else {
                          newFilters = contentTypeFilters.filter(f => f !== type.value);
                        }
                        // If no types selected, default to "any"
                        if (newFilters.length === 0) {
                          newFilters = ['any'];
                        }
                      }
                      setContentTypeFilters(newFilters);
                      setCurrentPage(1);
                      loadItems(searchQuery, searchMode, newFilters, 1);
                    }}
                  />
                  <span>{type.label}</span>
                </label>
              ))}
            </div>
          </div>
        </div>
      </div>

      {loading && <div className="loading">Loading...</div>}
      {error && <div className="error">{error}</div>}

      <div className="items-grid">
        {items.length === 0 && !loading && (
          <div className="no-items">
            {searchQuery ? 'No items found' : 'No items yet. Add your first item above!'}
          </div>
        )}
        
        {items.map((item) => (
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
              {item.type === 'image' && item.s3_key && (
                <div className="item-image">
                  <img 
                    src={`http://localhost:4566/synapse-storage/${item.s3_key}`}
                    alt={item.title || 'Uploaded image'}
                    className="image-preview"
                    onError={(e) => {
                      // If direct access fails, show a placeholder
                      e.currentTarget.style.display = 'none';
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
        ))}
      </div>

      {/* Pagination Controls */}
      {items.length > 0 && (
        <div className="pagination">
          <div className="pagination-info">
            Page {currentPage} • {items.length} items
          </div>
          
          <div className="pagination-controls">
            <button 
              onClick={handlePrevPage} 
              disabled={currentPage <= 1 || loading}
              className="pagination-btn"
            >
              ← Previous
            </button>
            
            <span className="pagination-current">
              {currentPage}
            </span>
            
            <button 
              onClick={handleNextPage} 
              disabled={!hasMore || loading}
              className="pagination-btn"
            >
              Next →
            </button>
          </div>

          {/* Alternative: Load More button */}
          {hasMore && (
            <button 
              onClick={handleLoadMore} 
              disabled={loading}
              className="load-more-btn"
            >
              {loading ? 'Loading...' : 'Load More'}
            </button>
          )}
        </div>
      )}
    </div>
  );
}