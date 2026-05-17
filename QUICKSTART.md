# Quick Start Guide

Hướng dẫn nhanh để chạy Document Understanding System.

## Prerequisites

- Python 3.10+
- Node.js 18+
- Poppler (for PDF processing)
- CUDA GPU (recommended)

## Installation

### 1. Install Backend

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install Poppler (Windows)
# Download from: https://github.com/oschwartz10612/poppler-windows/releases
# Add bin/ folder to PATH
```

### 2. Install Frontend

```bash
cd frontend
npm install
cd ..
```

### 3. Configure Environment

```bash
# Copy environment file
cp .env.example .env

# Edit .env and set your Google API key if using Gemini
# GOOGLE_API_KEY="your-api-key-here"
```

## Running the System

### Option 1: Manual Start (2 Terminals)

**Terminal 1 - Backend:**
```bash
python -m app.main
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

### Option 2: Using Scripts (Windows)

**Start all services:**
```powershell
.\start.ps1
```

**Stop all services:**
```powershell
.\stop.ps1
```

## Access Points

- **Frontend Chat UI**: http://localhost:3000
- **Backend API**: http://localhost:1201
- **API Documentation**: http://localhost:1201/docs

## First Steps

### 1. Index a Document

Before you can chat, you need to index documents:

```bash
# Using API
curl -X POST "http://localhost:1201/api/v1/index" \
  -H "Content-Type: application/json" \
  -d '{"file_path": "path/to/your/document.pdf"}'
```

Or use Swagger UI at http://localhost:1201/docs

### 2. Start Chatting

1. Open http://localhost:3000
2. Select a model (Qwen or Gemini)
3. Ask questions about your documents
4. View AI thinking process
5. Check source documents

## Troubleshooting

### Backend Issues

**Port 1201 already in use:**
```bash
# Windows
netstat -ano | findstr :1201
taskkill /PID <pid> /F

# Edit app/main.py to change port
```

**CUDA out of memory:**
- Reduce batch sizes in config
- Use CPU mode
- Use smaller models

### Frontend Issues

**Port 3000 already in use:**
```bash
# Edit frontend/vite.config.js
server: { port: 3001 }
```

**API connection failed:**
- Check backend is running on port 1201
- Check CORS settings
- Verify proxy configuration in vite.config.js

## Development Mode

Backend with auto-reload:
```bash
uvicorn app.main:app --reload
```

Frontend with hot-reload:
```bash
cd frontend
npm run dev
```

## Production Build

### Backend
```bash
uvicorn app.main:app --host 0.0.0.0 --port 1201 --workers 4
```

### Frontend
```bash
cd frontend
npm run build
# Serve dist/ folder with any static server
```

## Support

For issues, check:
- README.md in project root
- frontend/README.md for frontend-specific issues
- API docs at /docs endpoint
