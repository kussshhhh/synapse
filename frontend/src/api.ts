import type { User, Item, CreateUserRequest } from './types';

const API_BASE = 'http://localhost:8000';

// Type detection helpers
export function detectContentType(file?: File, url?: string): string {
  if (file) {
    if (file.type.startsWith('image/')) return 'image';
    if (file.type === 'application/pdf') return 'pdf';
    if (file.type.startsWith('video/')) return 'video';
    return 'file';
  }
  
  if (url) {
    if (url.includes('youtube.com') || url.includes('youtu.be')) return 'video';
    if (url.includes('amazon.') || url.includes('ebay.') || url.includes('shop')) return 'product';
    return 'url';
  }
  
  return 'note';
}

// API functions
export async function createUser(userData: CreateUserRequest): Promise<User> {
  const response = await fetch(`${API_BASE}/api/users`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(userData)
  });
  
  if (!response.ok) throw new Error('Failed to create user');
  return response.json();
}

export async function getCurrentUser(): Promise<User> {
  const response = await fetch(`${API_BASE}/api/users/me`);
  if (!response.ok) throw new Error('Failed to get user');
  return response.json();
}

export async function createItem({
  file,
  type,
  title,
  url,
  raw_content,
  tags = []
}: {
  file?: File;
  type: string;
  title?: string;
  url?: string;
  raw_content?: string;
  tags?: string[];
}): Promise<Item> {
  const formData = new FormData();
  
  formData.append('type', type);
  if (file) formData.append('file', file);
  if (title) formData.append('title', title);
  if (url) formData.append('url', url);
  if (raw_content) formData.append('raw_content', raw_content);
  formData.append('tags', JSON.stringify(tags));
  
  const response = await fetch(`${API_BASE}/api/items`, {
    method: 'POST',
    body: formData
  });
  
  if (!response.ok) throw new Error('Failed to create item');
  return response.json();
}

export async function getItems(skip = 0, limit = 10): Promise<Item[]> {
  const response = await fetch(`${API_BASE}/api/items?skip=${skip}&limit=${limit}`);
  if (!response.ok) throw new Error('Failed to get items');
  return response.json();
}

export async function searchItems(query: string, skip = 0, limit = 10, semantic = true): Promise<Item[]> {
  const response = await fetch(`${API_BASE}/api/search?q=${encodeURIComponent(query)}&skip=${skip}&limit=${limit}&semantic=${semantic}`);
  if (!response.ok) throw new Error('Failed to search items');
  return response.json();
}

export interface SemanticSearchResult extends Item {
  similarity_score: number;
}

export async function semanticSearchItems(query: string, skip = 0, limit = 10, threshold = 0.2): Promise<SemanticSearchResult[]> {
  const response = await fetch(`${API_BASE}/api/semantic-search?q=${encodeURIComponent(query)}&skip=${skip}&limit=${limit}&threshold=${threshold}`);
  if (!response.ok) throw new Error('Failed to perform semantic search');
  return response.json();
}