# 🧠 Synapse

Your intelligent second brain - store, search, and discover content across images, URLs, documents, and notes with AI-powered multimodal search.

## Features

- **Multimodal Storage**: Images, URLs, PDFs, videos, notes, products
- **AI-Powered Search**: Claude analyzes your queries and suggests optimal search strategies
- **Smart Content Types**: Automatic filtering based on what you're looking for
- **Semantic + Text Search**: CLIP embeddings + traditional text matching
- **Browser Extension**: One-click saving with floating UI
- **Auto-Tagging**: Claude generates smart tags for uploaded content

## Quick Start

### Backend
```bash
cd backend
uv run python main.py
```

### Frontend  
```bash
cd frontend
npm install && npm run dev
```

### Browser Extension
1. Load `browser-extension/` as unpacked extension in Chrome
2. Drag images or click the floating save button

## Search Modes

- **🤖 Smart (Claude AI)**: Claude analyzes your query and chooses the best approach
- **🧠 Hybrid**: Combines text matching with semantic similarity  
- **🎯 Semantic**: Pure AI similarity search using CLIP embeddings
- **📝 Text**: Traditional keyword matching

## Tech Stack

- **Backend**: FastAPI + PostgreSQL + pgvector
- **Frontend**: React + TypeScript + Vite
- **AI**: Claude (LiteLLM) + CLIP embeddings
- **Storage**: S3-compatible (LocalStack for dev)

## Environment Setup

Create `backend/.env`:
```
ANTHROPIC_BASE_URL=your_litellm_endpoint
ANTHROPIC_AUTH_TOKEN=your_api_key
DEBUG=true
```

## How It Works

1. **Upload**: Save any content type with automatic CLIP embedding generation
2. **Claude Analysis**: Background tagging and search query optimization  
3. **Smart Search**: Multi-term OR search with intelligent content type filtering
4. **Results**: Ranked by relevance with similarity scores

Built for speed, intelligence, and discovery. 🚀