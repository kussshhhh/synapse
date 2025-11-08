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

export async function searchItems(query: string, skip = 0, limit = 10, semantic = true, contentTypes?: string[]): Promise<Item[]> {
  const params = new URLSearchParams({
    q: query,
    skip: skip.toString(),
    limit: limit.toString(),
    semantic: semantic.toString()
  });
  
  if (contentTypes && contentTypes.length > 0 && !contentTypes.includes('any')) {
    contentTypes.forEach(type => {
      params.append('content_types', type);
    });
  }
  
  const response = await fetch(`${API_BASE}/api/search?${params}`);
  if (!response.ok) throw new Error('Failed to search items');
  return response.json();
}

export interface SemanticSearchResult extends Item {
  similarity_score: number;
}

export async function semanticSearchItems(query: string, skip = 0, limit = 10, threshold = 0.2, contentTypes?: string[]): Promise<SemanticSearchResult[]> {
  const params = new URLSearchParams({
    q: query,
    skip: skip.toString(),
    limit: limit.toString(),
    threshold: threshold.toString()
  });
  
  if (contentTypes && contentTypes.length > 0 && !contentTypes.includes('any')) {
    contentTypes.forEach(type => {
      params.append('content_types', type);
    });
  }
  
  const response = await fetch(`${API_BASE}/api/semantic-search?${params}`);
  if (!response.ok) throw new Error('Failed to perform semantic search');
  return response.json();
}

// Claude-powered search analysis
export interface SearchAnalysis {
  searchMode: 'hybrid' | 'semantic' | 'text';
  contentType: 'image' | 'url' | 'pdf' | 'video' | 'any';
  enhancedTerms: string[];
  reasoning: string;
}

export async function analyzeSearchQuery(query: string): Promise<SearchAnalysis> {
  const response = await fetch(`${API_BASE}/api/search/analyze?query=${encodeURIComponent(query)}`, {
    method: 'POST'
  });
  if (!response.ok) throw new Error('Failed to analyze search query');
  return response.json();
}

// Smart search that uses Claude analysis for content type suggestions
export async function smartSearch(query: string, skip = 0, limit = 10, contentTypes?: string[]): Promise<(Item | SemanticSearchResult)[]> {
  try {
    // Step 1: Analyze query with Claude to get content type suggestions
    const analysis = await analyzeSearchQuery(query);
    console.log('Claude analysis:', analysis);
    
    // Step 2: Use Claude's suggestions if no user selection, otherwise respect user choice
    let finalContentTypes = contentTypes;
    if (!contentTypes || contentTypes.length === 0 || contentTypes.includes('any')) {
      // Claude suggests multiple content types to include
      finalContentTypes = analysis.contentTypes && analysis.contentTypes.length > 0 ? analysis.contentTypes : ['any'];
    }
    
    // Step 3: Execute search with content type filtering  
    // Try each enhanced term individually and combine results
    let allResults: (Item | SemanticSearchResult)[] = [];
    
    for (const term of analysis.enhancedTerms) {
      let termResults: (Item | SemanticSearchResult)[] = [];
      
      if (analysis.searchMode === 'semantic') {
        termResults = await semanticSearchItems(term, 0, limit, 0.2, finalContentTypes);
      } else if (analysis.searchMode === 'text') {
        termResults = await searchItems(term, 0, limit, false, finalContentTypes);
      } else {
        // hybrid
        termResults = await searchItems(term, 0, limit, true, finalContentTypes);
      }
      
      // Add results, avoiding duplicates
      for (const result of termResults) {
        if (!allResults.find(r => r.id === result.id)) {
          allResults.push(result);
        }
      }
      
      // Stop if we have enough results
      if (allResults.length >= limit) break;
    }
    
    // Apply skip and limit to final results
    return allResults.slice(skip, skip + limit);
  } catch (error) {
    console.error('Smart search failed, falling back to hybrid:', error);
    // Fallback to regular hybrid search
    return await searchItems(query, skip, limit, true, contentTypes);
  }
}