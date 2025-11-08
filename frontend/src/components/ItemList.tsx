import React, { useState, useEffect } from 'react';
import { getItems, searchItems } from '../api';
import type { Item } from '../types';

interface ItemListProps {
  refresh?: boolean;
  onRefreshComplete?: () => void;
}

export default function ItemList({ refresh, onRefreshComplete }: ItemListProps) {
  const [items, setItems] = useState<Item[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [searchQuery, setSearchQuery] = useState('');

  const loadItems = async (query = '') => {
    setLoading(true);
    setError('');
    
    try {
      const data = query ? await searchItems(query) : await getItems();
      setItems(data);
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
      loadItems(searchQuery);
      onRefreshComplete?.();
    }
  }, [refresh]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    loadItems(searchQuery);
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
                loadItems();
              }}
            >
              Clear
            </button>
          )}
        </form>
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
              <span className="item-date">{formatDate(item.created_at)}</span>
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
    </div>
  );
}