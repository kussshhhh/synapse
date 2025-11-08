import React, { useState, useEffect } from 'react';
import { getItems, searchItems, semanticSearchItems, type SemanticSearchResult } from '../api';
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
  const [searchMode, setSearchMode] = useState<'hybrid' | 'semantic' | 'text'>('hybrid');
  const [currentPage, setCurrentPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const itemsPerPage = 10;

  const loadItems = async (query = '', mode = searchMode, page = 1, append = false) => {
    setLoading(true);
    setError('');
    
    try {
      const skip = (page - 1) * itemsPerPage;
      let data;
      
      if (!query) {
        data = await getItems(skip, itemsPerPage);
      } else if (mode === 'semantic') {
        data = await semanticSearchItems(query, skip, itemsPerPage);
      } else if (mode === 'text') {
        data = await searchItems(query, skip, itemsPerPage, false); // semantic=false
      } else {
        // hybrid (default)
        data = await searchItems(query, skip, itemsPerPage, true); // semantic=true
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
      loadItems(searchQuery, searchMode, 1);
      onRefreshComplete?.();
    }
  }, [refresh]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setCurrentPage(1);
    loadItems(searchQuery, searchMode, 1);
  };

  const handleNextPage = () => {
    if (hasMore && !loading) {
      const nextPage = currentPage + 1;
      loadItems(searchQuery, searchMode, nextPage);
    }
  };

  const handlePrevPage = () => {
    if (currentPage > 1 && !loading) {
      const prevPage = currentPage - 1;
      loadItems(searchQuery, searchMode, prevPage);
    }
  };

  const handleLoadMore = () => {
    if (hasMore && !loading) {
      const nextPage = currentPage + 1;
      loadItems(searchQuery, searchMode, nextPage, true);
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
                loadItems('', searchMode, 1);
              }}
            >
              Clear
            </button>
          )}
        </form>

        {searchQuery && (
          <div className="search-mode-selector">
            <label>Search mode:</label>
            <select 
              value={searchMode} 
              onChange={(e) => {
                const mode = e.target.value as 'hybrid' | 'semantic' | 'text';
                setSearchMode(mode);
                setCurrentPage(1);
                loadItems(searchQuery, mode, 1);
              }}
              className="search-mode-select"
            >
              <option value="hybrid">🧠 Hybrid (Text + AI)</option>
              <option value="semantic">🎯 Semantic (AI Only)</option>
              <option value="text">📝 Text Only</option>
            </select>
          </div>
        )}
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
              
              {item.url && (
                <a 
                  href={item.url} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="item-url"
                >
                  {item.url}
                </a>
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