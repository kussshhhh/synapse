# Synapse

Your intelligent second brain - store, search, and discover content across images, URLs, documents, and notes with AI-powered multimodal search.

the fundamental idea is to create a core service with apis and postgres db and expose those apis to interact with many interfaces (website, browser extension, llm, mobile app)

## Features

- **Multimodal Storage**: Images, URLs, PDFs, videos, notes, products.
- **AI-Powered Search**: Claude analyzes your queries and suggests optimal search strategies
- **Smart Content Types**: Automatic filtering based on what you're looking for
- **Semantic + Text Search**: CLIP embeddings + traditional text matching
- **Browser Extension**: One-click saving with floating UI
- **Auto-Tagging**: Claude generates smart tags for uploaded content in the background so when you upload smth it gets saved instantaneously but the tags are processed in the background and later added for better search.

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

### HLD (high level design)

```mermaid
graph TB
    subgraph CLIENT["CLIENT LAYER"]
        EXT[Browser Extension]
        WEB[Web Application]
        MOB[Mobile Apps Future]
    end

    subgraph API["API LAYER - FastAPI Backend"]
        UPLOAD[POST /api/items - Upload Content]
        SEARCH[GET /api/search - Main Search]
        SEMANTIC[GET /api/semantic-search - Vector Only]
        ANALYZE[POST /api/search/analyze - Claude Query Analysis]
        ITEMS[GET /api/items - List Items]
        USERS[User Management APIs]
    end

    subgraph MODES["SEARCH MODES"]
        TMODE[Text Mode - SQL ILIKE matching]
        SMODE[Semantic Mode - Vector similarity only]
        HMODE[Hybrid Mode - Text + Vector combined]
        SMARTMODE[Smart Mode - Claude powered decision]
    end

    subgraph INTEL["INTELLIGENCE LAYER"]
        direction TB
        
        subgraph CLAUDE["Claude Integration via LiteLLM"]
            QUERY_ANALYSIS[Query Analysis Function]
            TAG_GEN[Tag Generation Function]
        end
        
        subgraph PROCESS["Processing Services"]
            CLIP[CLIP Embeddings Service]
            EXTRACT[Content Extractors OCR PDF Web]
        end
    end

    subgraph DATA["DATA LAYER"]
        POSTGRES[PostgreSQL with pgvector]
        S3[S3 Storage LocalStack]
    end

    subgraph TABLES["Database Tables"]
        TUSERS[users]
        TITEMS[items - with tags array]
        TEMBED[embeddings - vector 512]
    end

    %% Client to API
    EXT --> UPLOAD
    EXT --> SEARCH
    WEB --> UPLOAD
    WEB --> SEARCH
    WEB --> ITEMS
    
    %% Search Flow
    SEARCH --> SMARTMODE
    SEARCH --> HMODE
    SEARCH --> TMODE
    SEMANTIC --> SMODE
    
    %% Smart Mode Flow - Claude stays in backend
    SMARTMODE --> QUERY_ANALYSIS
    QUERY_ANALYSIS --> HMODE
    
    %% Upload Flow
    UPLOAD --> EXTRACT
    EXTRACT --> S3
    EXTRACT --> CLIP
    CLIP --> TEMBED
    UPLOAD --> TITEMS
    
    %% Background Enhancement
    TITEMS -.-> TAG_GEN
    TAG_GEN -.-> TITEMS
    
    %% Search Modes to Data
    TMODE --> TITEMS
    SMODE --> TEMBED
    HMODE --> TITEMS
    HMODE --> TEMBED
    
    %% Database relationships
    POSTGRES --> TUSERS
    POSTGRES --> TITEMS
    POSTGRES --> TEMBED
    S3 --> TITEMS

    classDef clientStyle fill:#DBEAFE,stroke:#3B82F6,stroke-width:3px
    classDef apiStyle fill:#D1FAE5,stroke:#10B981,stroke-width:3px
    classDef modeStyle fill:#FEF3C7,stroke:#F59E0B,stroke-width:3px
    classDef claudeStyle fill:#FECACA,stroke:#EF4444,stroke-width:4px
    classDef processStyle fill:#E9D5FF,stroke:#A855F7,stroke-width:3px
    classDef dataStyle fill:#FFEDD5,stroke:#F97316,stroke-width:3px

    class EXT,WEB,MOB clientStyle
    class UPLOAD,SEARCH,SEMANTIC,ANALYZE,ITEMS,USERS apiStyle
    class TMODE,SMODE,HMODE,SMARTMODE modeStyle
    class QUERY_ANALYSIS,TAG_GEN claudeStyle
    class CLIP,EXTRACT processStyle
    class POSTGRES,S3,TUSERS,TITEMS,TEMBED dataStyle
```

## Search Modes

- **Smart (Claude AI)**: Claude analyzes your query and chooses the best approach
- **Hybrid**: Combines text matching with semantic similarity  
- **Semantic**: Pure AI similarity search using CLIP embeddings
- **Text**: Traditional keyword matching

## Tech Stack

- **Backend**: FastAPI + PostgreSQL + pgvector
- **Frontend**: React + TypeScript + Vite
- **AI**: Claude + CLIP embeddings
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

Built for speed, intelligence, and discovery.
