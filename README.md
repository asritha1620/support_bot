# 🤖 Support Ticket Assistant - AI-Powered Chatbot

A modern, full-stack application for intelligent support ticket analysis using RAG (Retrieval Augmented Generation) powered by Google's Gemini 2.0 Flash AI. Features conversational memory, user feedback, and collaborative knowledge base management.

**✨ Key Features:**
- 🧠 **Conversation Memory**: Remembers context across messages for natural, flowing conversations
- 🎫 **Support Ticket Focus**: Specialized AI trained for analyzing support ticket data and patterns
- 👍👎 **Smart Feedback**: User feedback system with detailed improvement suggestions
- 📚 **Collaborative Knowledge**: Shared knowledge base where uploads and resolutions benefit all users
- 🔍 **Source Attribution**: Clear indication of which tickets inform each AI response

## 🏗️ Architecture

```
support_bot/
├── backend/                 # Python FastAPI server
│   ├── main.py             # API endpoints & session management
│   ├── rag.py              # RAG processing with conversation context
│   ├── schemas.py          # Pydantic data models
│   ├── requirements.txt    # Python dependencies
│   └── faiss_index/        # Vector database storage
├── frontend/                # React.js application
│   ├── src/
│   │   ├── components/     # React components (ChatInterface, etc.)
│   │   ├── services/       # API service layer
│   │   └── App.js          # Main application
│   ├── package.json        # Node.js dependencies
│   └── public/
├── feedback.json           # User feedback storage
└── .env                    # Environment variables
```

## ✨ Features

### 🎯 **Core Functionality**
- **🎫 Support Ticket Analysis**: Specialized AI for analyzing support ticket data from Excel files
- **🧠 Conversation Memory**: Remembers previous messages within sessions for contextual responses
- **🤖 AI-Powered Chat**: Natural language queries using Gemini 2.0 Flash with fallback API support
- **🔍 RAG Technology**: Advanced retrieval with vector similarity search across ticket data
- **📱 Modern UI**: Responsive React interface with Material-UI components
- **👍👎 Feedback System**: User feedback collection with detailed suggestions for improvement
- **📚 Collaborative Knowledge Base**: Shared resolutions and uploaded data accessible to all users
- **📊 Source Attribution**: Clear indication of which tickets/data sources inform each response

### 🛠️ **Technical Features**
- **RESTful API**: FastAPI backend with automatic OpenAPI documentation
- **Real-time Chat**: Instant responses with expandable source details
- **Session Management**: Per-session conversation memory with automatic cleanup
- **File Upload**: Excel file processing (.xlsx/.xls) with automatic data indexing
- **Resolution Management**: User-contributed troubleshooting steps added to knowledge base
- **Error Handling**: Comprehensive error handling with graceful API key fallback
- **CORS Support**: Cross-origin requests enabled for seamless frontend integration
- **Type Safety**: Full TypeScript support in frontend with Pydantic validation in backend

## 🚀 Quick Start

### Prerequisites
- **Python 3.8+** - [Download here](https://python.org/)
- **Node.js 16+** - [Download here](https://nodejs.org/)
- **Gemini API Key** - [Get from Google AI Studio](https://aistudio.google.com/app/apikey)

### 1. Setup Environment
```bash
# Clone or download the project
cd support_bot

# Ensure your .env file contains:
GEMINI_API_KEY=your_actual_api_key_here
```

### 2. Start Application (Direct Commands - RECOMMENDED)

#### Option A: Simple Batch File (Windows)
```bash
# Just run this - it opens two terminals automatically
run_simple.bat
```

#### Option B: Manual Terminal Commands

**Terminal 1 - Backend:**
```bash
cd backend
.venv\Scripts\activate  # Windows
# or: source .venv/bin/activate  # Linux/Mac
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

### 3. Start Application (Full Automation)
```bash
# Windows (PowerShell)
.\start_fullstack.ps1

# Windows (Command Prompt)
start_fullstack.bat
```

### 3. Manual Setup

#### Backend Setup
```bash
cd backend

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start backend server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

#### Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm start
```

## 🌐 Application URLs

- **Frontend Application**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## 📡 API Endpoints

### Core Endpoints
- `GET /health` - Health check and vectorstore status
- `POST /upload` - Upload Excel file for processing and indexing
- `POST /chat` - Send chat message and get AI response with conversation context
- `POST /add-resolution` - Add user-contributed resolution to shared knowledge base
- `POST /feedback` - Submit user feedback (positive/negative with suggestions)

### Data Management
- **Persistent Storage**: FAISS vector database with document metadata
- **Session Memory**: In-memory conversation history (24h auto-cleanup)
- **Feedback Storage**: JSON file storage for improvement suggestions
- **Knowledge Base**: Shared across all users and sessions

## 💬 Usage

### 1. Upload Support Ticket Data
Upload Excel files containing support ticket data using the drag & drop interface or file selector. The system automatically indexes the data for AI-powered queries.

### 2. Ask Questions About Tickets
Try these example questions:
- "What are the most common shipping errors this month?"
- "Show me tickets related to payment failures"
- "How many high-priority tickets do we have in logistics?"
- "What are the top 5 error codes in the support tickets?"
- "Can you tell me more about tickets from customer ID 12345?"

### 3. Interactive Conversation
- **Context Awareness**: The AI remembers previous questions and answers within your session
- **Follow-up Questions**: Ask "Can you tell me more about the top 3?" and the AI will reference previous context
- **Clarification**: If your question is vague, the AI will ask for clarification

### 4. Provide Feedback
- **Thumbs Up (👍)**: "Thanks for the feedback! 😊"
- **Thumbs Down (👎)**: Opens dialog to provide improvement suggestions
- Your feedback helps improve the AI responses for everyone!

### 5. Add Resolutions
Click "Add Resolution" to contribute troubleshooting steps that become part of the shared knowledge base, helping all users with similar issues.

### 6. Review Sources
Each AI response includes expandable sources showing which ticket data informed the answer, with clear attribution to filenames and resolution entries.

## 🔧 Configuration

### Environment Variables
```env
GEMINI_API_KEY1=your_primary_gemini_api_key
GEMINI_API_KEY2=your_fallback_gemini_api_key  # Optional: for quota handling
REACT_APP_API_URL=http://localhost:8000      # Optional: custom backend URL
```

### Backend Configuration
Key settings in `backend/main.py`:
- **MAX_MEMORY_MESSAGES = 20**: Maximum messages stored per session
- **Session cleanup**: Automatic removal of sessions older than 24 hours

Key settings in `backend/rag.py`:
- **Conversation context**: Last 10 messages included in AI prompts
- **Search results**: Top 5 similar documents retrieved per query
- **Embedding model**: `all-MiniLM-L6-v2` for semantic search

### Knowledge Base Management
- **Default data**: `L2_L3Tickets.xlsx` loaded on startup
- **Uploaded files**: Automatically added to shared knowledge base
- **User resolutions**: Manually added troubleshooting steps
- **Persistence**: All data saved to `faiss_index/` directory

## 🐛 Troubleshooting

### Common Issues

#### Backend Issues
1. **Gemini API Key Errors**
   - Verify both `GEMINI_API_KEY1` and `GEMINI_API_KEY2` (if used) in `.env`
   - Check API quota at Google AI Studio
   - Ensure `.env` file is in the backend directory

2. **Vectorstore Loading Errors**
   - Delete `faiss_index/` directory to rebuild from default data
   - Check file permissions for FAISS index files
   - Ensure `L2_L3Tickets.xlsx` exists in backend directory

3. **Memory Issues**
   - Reduce `MAX_MEMORY_MESSAGES` in `main.py` for lower memory usage
   - Sessions auto-cleanup after 24 hours of inactivity

4. **Import Errors**
   - Activate virtual environment: `.venv\Scripts\activate` (Windows)
   - Reinstall dependencies: `pip install -r requirements.txt`

#### Frontend Issues
1. **Connection Errors**
   - Ensure backend is running on port 8000
   - Check CORS settings in `backend/main.py`
   - Verify API URL in frontend services

2. **File Upload Errors**
   - Check file format (.xlsx or .xls only)
   - Verify file size is reasonable (< 50MB recommended)
   - Check backend logs for processing errors

3. **Feedback System Issues**
   - Positive feedback: Immediate acknowledgment
   - Negative feedback: Requires suggestions in dialog
   - Check `feedback.json` for stored improvement suggestions

### Performance Optimization
- **Large Datasets**: Consider preprocessing or sampling large Excel files
- **Slow Responses**: Reduce retrieval count (k parameter) in RAG search
- **Memory Usage**: Monitor session count and adjust cleanup intervals
- **API Costs**: Use fallback API key to manage quota limits

## 🔒 Security Considerations

- **API Keys**: Never commit `.env` files to version control
- **File Uploads**: Backend validates file types and sizes
- **CORS**: Currently allows localhost only; configure for production
- **Sessions**: In-memory storage; use Redis/database for production

## 🚀 Production Deployment

### Backend (FastAPI)
```bash
# Install production server
pip install gunicorn

# Run with Gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:8000
```

### Frontend (React)
```bash
# Build for production
npm run build

# Serve with nginx or any static file server
# Build files will be in the 'build' directory
```

### Docker Deployment
```dockerfile
# Example Dockerfile for backend
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 📚 Development

### Project Structure
```
backend/
├── main.py          # FastAPI app, session management, API endpoints
├── rag.py           # RAGProcessor class with conversation context
├── schemas.py       # Pydantic models for request/response validation
└── requirements.txt # Python dependencies

frontend/
├── src/
│   ├── components/
│   │   ├── ChatInterface.js    # Main chat UI with feedback system
│   │   └── DataPreview.js      # File upload and data preview
│   ├── services/
│   │   └── ApiService.js       # API client with error handling
│   └── App.js                  # Main React app with session management
└── package.json
```

### Key Components

#### Conversation Memory System
- **Session Storage**: In-memory dictionary with automatic cleanup
- **Context Window**: Last 10 messages included in AI prompts
- **Persistence**: Survives server restarts (24h cleanup)
- **Integration**: Seamlessly integrated into RAG response generation

#### Feedback System
- **Positive Feedback**: Immediate acknowledgment with friendly message
- **Negative Feedback**: Dialog-based suggestions stored in `feedback.json`
- **Analytics**: Data collected for continuous AI improvement

#### Knowledge Base Management
- **Shared Data**: All uploaded files and resolutions accessible to all users
- **Vector Storage**: FAISS index with document metadata persistence
- **Dynamic Updates**: New data immediately available for queries

### Adding New Features
1. **Backend**: Add endpoints in `main.py`, logic in `rag.py`
2. **Frontend**: Create components in `src/components/`
3. **API**: Update `ApiService.js` for new endpoints
4. **Models**: Add Pydantic schemas in `schemas.py`

### Testing Conversation Memory
```python
# Test script included: backend/test_memory.py
python test_memory.py
```

## 📄 License

This project is open source and available under the MIT License.

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

## 📞 Support

For issues and questions:
- Check the troubleshooting section above
- Review backend logs for detailed error information
- Ensure all prerequisites are properly installed