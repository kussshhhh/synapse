import React, { useState } from 'react';
import { createItem, detectContentType } from '../api';

interface UploadFormProps {
  onSuccess?: () => void;
}

export default function UploadForm({ onSuccess }: UploadFormProps) {
  const [file, setFile] = useState<File | null>(null);
  const [url, setUrl] = useState('');
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [tags, setTags] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      // Auto-detect type
      const type = detectContentType(file || undefined, url || undefined);
      
      // Parse tags
      const tagList = tags.split(',').map(tag => tag.trim()).filter(tag => tag);

      await createItem({
        file: file || undefined,
        type,
        title: title || undefined,
        url: url || undefined,
        raw_content: content || undefined,
        tags: tagList
      });

      // Reset form
      setFile(null);
      setUrl('');
      setTitle('');
      setContent('');
      setTags('');
      
      onSuccess?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setLoading(false);
    }
  };

  const detectedType = detectContentType(file || undefined, url || undefined);

  return (
    <div className="upload-form">
      <h2>Add to Synapse</h2>
      
      <form onSubmit={handleSubmit} className="form">
        {/* File Upload */}
        <div className="field">
          <label>Upload File:</label>
          <input
            type="file"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            accept="image/*,application/pdf,text/*,video/*"
          />
        </div>

        {/* URL Input */}
        <div className="field">
          <label>Or enter URL:</label>
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://example.com"
            disabled={!!file}
          />
        </div>

        {/* Title */}
        <div className="field">
          <label>Title:</label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Enter a title"
          />
        </div>

        {/* Content (for notes) */}
        {!file && !url && (
          <div className="field">
            <label>Content:</label>
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="Write your note here..."
              rows={4}
            />
          </div>
        )}

        {/* Tags */}
        <div className="field">
          <label>Tags:</label>
          <input
            type="text"
            value={tags}
            onChange={(e) => setTags(e.target.value)}
            placeholder="tag1, tag2, tag3"
          />
        </div>

        {/* Detected Type Display */}
        <div className="detected-type">
          <strong>Detected type: {detectedType}</strong>
        </div>

        {/* Submit */}
        <button type="submit" disabled={loading || (!file && !url && !content)}>
          {loading ? 'Adding...' : 'Add Item'}
        </button>

        {error && <div className="error">{error}</div>}
      </form>
    </div>
  );
}