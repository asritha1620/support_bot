from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn, os, tempfile, json
import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import datetime
from rag_service_simple import RAGService, Document
from models import ChatRequest, ChatResponse, FileUploadResponse

# Persistence configuration
PERSISTENCE_DIR = os.path.join(os.path.dirname(__file__), "data")
SHARED_DOCUMENTS_FILE = os.path.join(PERSISTENCE_DIR, "shared_documents.json")
SHARED_SESSION_FILE = os.path.join(PERSISTENCE_DIR, "shared_session.json")

def save_shared_documents(documents: List[Dict[str, Any]], session_id: str):
    """Save shared documents to persistent storage"""
    try:
        os.makedirs(PERSISTENCE_DIR, exist_ok=True)
        
        # Convert documents to serializable format
        serializable_docs = []
        for doc in documents:
            serializable_docs.append({
                "page_content": doc.page_content,
                "metadata": doc.metadata
            })
        
        data = {
            "session_id": session_id,
            "documents": serializable_docs,
            "last_updated": datetime.now().isoformat()
        }
        
        with open(SHARED_DOCUMENTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"Saved {len(documents)} shared documents to {SHARED_DOCUMENTS_FILE}")
        
    except Exception as e:
        print(f"Error saving shared documents: {str(e)}")

def load_shared_documents() -> tuple[List[Dict[str, Any]], str]:
    """Load shared documents from persistent storage"""
    try:
        if not os.path.exists(SHARED_DOCUMENTS_FILE):
            return [], ""
        
        with open(SHARED_DOCUMENTS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Convert back to Document objects
        documents = []
        for doc_data in data.get("documents", []):
            documents.append(Document(
                page_content=doc_data["page_content"],
                metadata=doc_data["metadata"]
            ))
        
        session_id = data.get("session_id", "")
        print(f"Loaded {len(documents)} shared documents from {SHARED_DOCUMENTS_FILE}")
        
        return documents, session_id
        
    except Exception as e:
        print(f"Error loading shared documents: {str(e)}")
        return [], ""

def save_shared_session(session_data: Dict[str, Any]):
    """Save shared session metadata to persistent storage"""
    try:
        os.makedirs(PERSISTENCE_DIR, exist_ok=True)
        
        data = {
            "session_data": session_data,
            "last_updated": datetime.now().isoformat()
        }
        
        with open(SHARED_SESSION_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"Saved shared session data to {SHARED_SESSION_FILE}")
        
    except Exception as e:
        print(f"Error saving shared session: {str(e)}")

def load_shared_session() -> Dict[str, Any]:
    """Load shared session metadata from persistent storage"""
    try:
        if not os.path.exists(SHARED_SESSION_FILE):
            return {}
        
        with open(SHARED_SESSION_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        session_data = data.get("session_data", {})
        print(f"Loaded shared session data from {SHARED_SESSION_FILE}")
        
        return session_data
        
    except Exception as e:
        print(f"Error loading shared session: {str(e)}")
        return {}

# Initialize FastAPI app
app = FastAPI(
    title="Support bot",
    description="A powerful RAG-based chatbot using Gemini AI",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Load default data on application startup"""
    await load_default_data()

# Global RAG service instance
rag_service = RAGService()

# Store session data
sessions = {}

# Default session configuration
DEFAULT_SESSION_ID = "default_support_tickets"
DEFAULT_EXCEL_FILE = os.path.join(os.path.dirname(__file__), "L2_L3Tickets.xlsx")

async def load_default_data():
    """Load the default support ticket data on startup - try persisted data first, then default Excel"""
    try:
        # First, try to load persisted shared data
        persisted_documents, persisted_session_id = load_shared_documents()
        persisted_session_data = load_shared_session()
        
        if persisted_documents and persisted_session_data:
            print("Loading persisted shared knowledge base...")
            
            # Restore the documents in RAG service
            rag_service.sessions[DEFAULT_SESSION_ID] = {
                "documents": persisted_documents,
                "file_path": persisted_session_data.get("file_info", {}).get("filename", "persisted_data")
            }
            
            # Try to load the FAISS vectorstore from disk
            loaded_vectorstore = rag_service.load_vectorstore(DEFAULT_SESSION_ID)
            if loaded_vectorstore:
                rag_service.sessions[DEFAULT_SESSION_ID]["vectorstore"] = loaded_vectorstore
                print("Loaded FAISS vectorstore from disk")
            else:
                print(" No saved vectorstore found, will create on first use")
            
            # Restore the session metadata
            sessions[DEFAULT_SESSION_ID] = persisted_session_data
            sessions[DEFAULT_SESSION_ID]["is_default"] = True
            
            print(f" Restored shared knowledge base with {len(persisted_documents)} documents")
            return True
        
        # If no persisted data, fall back to loading default Excel file
        if os.path.exists(DEFAULT_EXCEL_FILE):
            print(f"Loading default support ticket data from: {DEFAULT_EXCEL_FILE}")
            
            # Process the default file
            success = await rag_service.process_file(DEFAULT_EXCEL_FILE, DEFAULT_SESSION_ID)
            
            if success:
                # Get file info
                df = pd.read_excel(DEFAULT_EXCEL_FILE)
                file_info = {
                    "filename": os.path.basename(DEFAULT_EXCEL_FILE),
                    "rows": len(df),
                    "columns": len(df.columns),
                    "column_names": df.columns.tolist()
                }
                
                # Store default session info
                sessions[DEFAULT_SESSION_ID] = {
                    "file_info": file_info,
                    "upload_time": datetime.now().isoformat(),
                    "chat_history": [],
                    "is_default": True
                }
                
                # Save this as the initial persisted state
                save_shared_documents(rag_service.sessions[DEFAULT_SESSION_ID]["documents"], DEFAULT_SESSION_ID)
                save_shared_session(sessions[DEFAULT_SESSION_ID])
                
                print(f" Default support ticket data loaded successfully!")
                print(f"   {len(df)} tickets loaded with {len(df.columns)} columns")
                return True
            else:
                print(" Failed to process default file")
                return False
        else:
            print(f" Default file not found: {DEFAULT_EXCEL_FILE}")
            return False
            
    except Exception as e:
        print(f"Error loading default data: {str(e)}")
        return False

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "message": "Excel RAG Chatbot API is running!",
        "timestamp": datetime.now().isoformat(),
        "default_session_loaded": DEFAULT_SESSION_ID in sessions
    }

@app.get("/default-session")
async def get_default_session():
    """Get information about the default session"""
    if DEFAULT_SESSION_ID not in sessions:
        return {
            "available": False,
            "message": "Default session not loaded"
        }
    
    session_data = sessions[DEFAULT_SESSION_ID]
    return {
        "available": True,
        "session_id": DEFAULT_SESSION_ID,
        "file_info": session_data.get("file_info"),
        "loaded_at": session_data.get("upload_time"),
        "ticket_count": session_data.get("file_info", {}).get("rows", 0)
    }

@app.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    session_id: str = Form(...)  # Keep for tracking who uploaded
):
    """Upload and add Excel file to shared knowledge base"""
    try:
        # Validate file type
        if not file.filename.endswith(('.xlsx', '.xls')):
            raise HTTPException(
                status_code=400, 
                detail="Only Excel files (.xlsx, .xls) are supported"
            )
        
        # Check if shared session exists
        if DEFAULT_SESSION_ID not in sessions:
            raise HTTPException(status_code=404, detail="Shared knowledge base not available")
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        try:
            # Get current document count for logging
            current_docs = len(rag_service.sessions.get(DEFAULT_SESSION_ID, {}).get("documents", []))
            
            # Add file to existing shared session
            success = await rag_service.append_file(tmp_file_path, DEFAULT_SESSION_ID)
            
            if success:
                # Get new file info
                df = pd.read_excel(tmp_file_path)
                added_rows = len(df)
                
                # Update shared session info
                shared_session_data = sessions[DEFAULT_SESSION_ID]
                current_file_info = shared_session_data.get("file_info", {})
                current_rows = current_file_info.get("rows", 0)
                
                # Update file info to reflect combined data
                updated_file_info = current_file_info.copy()
                updated_file_info["rows"] = current_rows + added_rows
                updated_file_info["filename"] += f" + {file.filename} (uploaded by {session_id[:8]}...)"
                
                shared_session_data["file_info"] = updated_file_info
                
                # Add to shared session chat history
                shared_session_data["chat_history"].append({
                    "timestamp": datetime.now().isoformat(),
                    "type": "file_uploaded",
                    "filename": file.filename,
                    "added_rows": added_rows,
                    "uploaded_by": session_id
                })
                
                # Persist the updated shared knowledge base
                save_shared_documents(rag_service.sessions[DEFAULT_SESSION_ID]["documents"], DEFAULT_SESSION_ID)
                save_shared_session(shared_session_data)
                
                return FileUploadResponse(
                    success=True,
                    message=f"File '{file.filename}' added to shared knowledge base successfully! All users can now access this data.",
                    file_info=updated_file_info,
                    session_id=DEFAULT_SESSION_ID
                )
            else:
                raise HTTPException(status_code=500, detail="Failed to add file to shared knowledge base")
                
        finally:
            # Clean up temporary file
            os.unlink(tmp_file_path)
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding file to shared knowledge base: {str(e)}")

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Chat with the RAG system"""
    try:
        session_id = request.session_id
        
        # Always prefer user's session if provided and exists, otherwise use default
        if not session_id or session_id not in sessions:
            if DEFAULT_SESSION_ID in sessions:
                session_id = DEFAULT_SESSION_ID
                print(f"Using default session for chat: {session_id}")
            else:
                raise HTTPException(status_code=404, detail="No active sessions available. Please wait for the system to initialize.")
        
        # Handle data addition mode
        if request.mode == "add_resolution" or "add resolution" in request.message.lower() or "add data" in request.message.lower():
            return await handle_data_addition(request, session_id)
        
        # Check if we're in the middle of data collection
        session_data = sessions[session_id]
        if "pending_resolution" in session_data:
            return await continue_data_collection(request, session_id)
        
        # Normal chat query
        response = await rag_service.query(request.message, session_id)
        
        if "error" in response:
            raise HTTPException(status_code=500, detail=response["error"])
        
        # Add option to add new resolution
        enhanced_response = response["answer"]
        
        # Store chat history
        chat_entry = {
            "timestamp": datetime.now().isoformat(),
            "user_message": request.message,
            "bot_response": enhanced_response,
            "sources": response.get("sources", [])
        }
        session_data["chat_history"].append(chat_entry)
        
        return ChatResponse(
            success=True,
            response=enhanced_response,
            sources=response.get("sources", []),
            session_id=session_id,
            actions=[{"type": "button", "label": "Add Resolution", "action": "add_resolution"}]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in chat: {str(e)}")

async def handle_data_addition(request: ChatRequest, session_id: str) -> ChatResponse:
    """Handle the start of data addition process"""
    session_data = sessions[session_id]
    
    # Initialize pending resolution data
    session_data["pending_resolution"] = {
        "step": "ticket_level",
        "data": {}
    }
    
    response_text = """**Add New Resolution**

I'll help you add a new ticket resolution to the knowledge base. Please provide the following information:

**Ticket Level** (L2 or L3): """
    
    return ChatResponse(
        success=True,
        response=response_text,
        sources=[],
        session_id=session_id
    )

async def continue_data_collection(request: ChatRequest, session_id: str) -> ChatResponse:
    """Continue collecting data for resolution addition"""
    session_data = sessions[session_id]
    pending = session_data["pending_resolution"]
    user_input = request.message.strip()
    
    if pending["step"] == "ticket_level":
        if user_input.upper() in ["L2", "L3"]:
            pending["data"]["Ticket Level"] = user_input.upper()
            pending["step"] = "category"
            response_text = "**Category** (e.g., Shipping, Payment, API, etc.): "
        else:
            response_text = "Please enter L2 or L3 for the ticket level."
    
    elif pending["step"] == "category":
        pending["data"]["Category"] = user_input
        pending["step"] = "problem"
        response_text = "**Problem Statement** (describe the issue): "
    
    elif pending["step"] == "problem":
        pending["data"]["Problem Statement"] = user_input
        pending["step"] = "resolution"
        response_text = "**Resolution Steps** (describe how to fix it): "
    
    elif pending["step"] == "resolution":
        pending["data"]["Resolution Steps"] = user_input
        
        # Map the collected data to the format expected by add_resolution
        resolution_data = {
            "error_code": f"{pending['data']['Category']} Issue",  # Use category as error code
            "module": pending["data"]["Category"],
            "description": pending["data"]["Problem Statement"],
            "resolution_steps": pending["data"]["Resolution Steps"],
            "ticket_level": pending["data"]["Ticket Level"]
        }
        
        # Add the data to the session using the add_resolution method
        # Always add to the default/shared session so everyone can access new resolutions
        result = await rag_service.add_resolution(DEFAULT_SESSION_ID, resolution_data)
        
        if "success" in result and result["success"]:
            # Update session info for the default session
            default_session_data = sessions[DEFAULT_SESSION_ID]
            current_file_info = default_session_data.get("file_info", {})
            current_rows = current_file_info.get("rows", 0)
            current_file_info["rows"] = current_rows + 1
            current_file_info["filename"] += " + manual resolution"
            default_session_data["file_info"] = current_file_info
            
            # Add to chat history for both the user's session and default session
            default_session_data["chat_history"].append({
                "timestamp": datetime.now().isoformat(),
                "type": "resolution_added",
                "data": pending["data"],
                "added_by_session": session_id
            })
            
            # Also add to user's session chat history
            session_data["chat_history"].append({
                "timestamp": datetime.now().isoformat(),
                "type": "resolution_added",
                "data": pending["data"]
            })
            
            # Save the updated shared knowledge base to persistent storage
            save_shared_documents(rag_service.sessions[DEFAULT_SESSION_ID]["documents"], DEFAULT_SESSION_ID)
            save_shared_session(default_session_data)
            
            response_text = "**Resolution Added Successfully!**\n\n" + \
                           f"**Ticket Level:** {pending['data']['Ticket Level']}\n" + \
                           f"**Category:** {pending['data']['Category']}\n" + \
                           f"**Problem:** {pending['data']['Problem Statement']}\n" + \
                           f"**Resolution:** {pending['data']['Resolution Steps']}\n\n" + \
                           "This resolution has been added to the **shared knowledge base** and will be available for all users to access."
        else:
            error_msg = result.get("error", "Unknown error")
            response_text = f" Sorry, there was an error adding the resolution: {error_msg}. Please try again."
        
        # Clear pending data
        del session_data["pending_resolution"]
    
    return ChatResponse(
        success=True,
        response=response_text,
        sources=[],
        session_id=session_id
    )

@app.post("/add-resolution")
async def add_resolution(resolution_data: Dict[str, Any], session_id: str):
    """Add a new resolution to the shared ticket data"""
    try:
        # Always add to the default/shared session so everyone can access new resolutions
        shared_session_id = DEFAULT_SESSION_ID
        
        if shared_session_id not in sessions:
            raise HTTPException(status_code=404, detail="Shared session not available")
        
        # Add the resolution using the RAG service to the shared session
        result = await rag_service.add_resolution(shared_session_id, resolution_data)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        # Update shared session info
        shared_session_data = sessions[shared_session_id]
        current_file_info = shared_session_data.get("file_info", {})
        current_rows = current_file_info.get("rows", 0)
        current_file_info["rows"] = current_rows + 1
        current_file_info["filename"] += " + manual resolution"
        shared_session_data["file_info"] = current_file_info
        
        # Add to shared session chat history
        shared_session_data["chat_history"].append({
            "timestamp": datetime.now().isoformat(),
            "type": "resolution_added",
            "data": resolution_data,
            "added_by_session": session_id
        })
        
        # Save the updated shared knowledge base to persistent storage
        save_shared_documents(rag_service.sessions[shared_session_id]["documents"], shared_session_id)
        save_shared_session(shared_session_data)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding resolution: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"

    )
