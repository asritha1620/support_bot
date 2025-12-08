from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
import os, logging, datetime, json, uvicorn
from dotenv import load_dotenv
from schemas import ChatRequest, ChatResponse, ResolutionRequest, HealthResponse, FeedbackRequest
from rag import RAGProcessor
from collections import defaultdict
from typing import Dict, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="Support Ticket Assistant API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global RAG processor
rag_processor = RAGProcessor()

session_memories: Dict[str, List[Dict]] = defaultdict(list)
MAX_MEMORY_MESSAGES = 20  # Keep last 20 messages per session
cleanup_counter = 0  # Counter for periodic cleanup

def add_to_session_memory(session_id: str, message: Dict):
    """Add a message to session memory, maintaining max limit"""
    if session_id not in session_memories:
        session_memories[session_id] = []
    
    session_memories[session_id].append(message)
    
    # Keep only the most recent messages
    if len(session_memories[session_id]) > MAX_MEMORY_MESSAGES:
        session_memories[session_id] = session_memories[session_id][-MAX_MEMORY_MESSAGES:]
    
    logger.debug(f"Added message to session {session_id} memory. Total messages: {len(session_memories[session_id])}")

def get_session_memory(session_id: str) -> List[Dict]:
    """Get conversation history for a session"""
    return session_memories.get(session_id, [])

def cleanup_old_sessions(max_age_hours: int = 24):
    """Clean up sessions that haven't been active for max_age_hours"""
    current_time = datetime.datetime.now()
    sessions_to_remove = []
    
    for session_id, messages in session_memories.items():
        if messages:
            last_message_time = datetime.datetime.fromisoformat(messages[-1]["timestamp"])
            age = current_time - last_message_time
            if age.total_seconds() > max_age_hours * 3600:
                sessions_to_remove.append(session_id)
    
    for session_id in sessions_to_remove:
        del session_memories[session_id]
        logger.info(f"Cleaned up old session: {session_id}")
    
    if sessions_to_remove:
        logger.info(f"Cleaned up {len(sessions_to_remove)} old sessions")

# Initialize models
def initialize_models():
    api_key1 = os.getenv('GEMINI_API_KEY1')
    api_key2 = os.getenv('GEMINI_API_KEY2')
    
    if not api_key1:
        logger.error("GEMINI_API_KEY1 is required but not found in environment variables")
        raise ValueError("GEMINI_API_KEY1 is required")
    
    if not api_key2:
        logger.warning("GEMINI_API_KEY2 not found - fallback functionality will not be available")
    
    logger.info("Initializing RAG processor with API keys")
    rag_processor.initialize_models(api_key1, api_key2)
    logger.info("RAG processor initialized successfully")

# Initialize on startup
@app.on_event("startup")
async def startup_event():
    try:
        logger.info("Starting application initialization")
        initialize_models()
        
        if not rag_processor.load_vectorstore():
            # Try to load default data
            default_file = "L2_L3Tickets.xlsx"
            if os.path.exists(default_file):
                logger.info(f"Loading default data from {default_file}")
                try:
                    rag_processor.process_excel_file(default_file, os.path.basename(default_file), "default_file")
                    logger.info("Default data loaded successfully")
                except Exception as e:
                    logger.error(f"Error loading default data: {e}")
                    raise
            else:
                logger.warning(f"Default file {default_file} not found - starting with empty knowledge base")
        else:
            logger.info("Existing vectorstore loaded successfully")
            
        # Clean up old sessions on startup
        cleanup_old_sessions()
        
        logger.info("Application initialization completed")
        
    except Exception as e:
        logger.error(f"Failed to initialize application: {e}")
        raise

# Health check endpoint
@app.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(vectorstore_loaded=rag_processor.vectorstore is not None and len(rag_processor.documents) > 0)

# Upload file endpoint
@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    session_id: str = Form(...)
):
    logger.info(f"Upload request received for file: {file.filename}, session: {session_id}")
    
    if not file.filename.endswith(('.xlsx', '.xls')):
        logger.warning(f"Invalid file type uploaded: {file.filename}")
        raise HTTPException(status_code=400, detail="Only Excel files (.xlsx, .xls) are supported")
    
    # Save uploaded file temporarily
    temp_path = f"temp_{session_id}_{file.filename}"
    try:
        with open(temp_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        logger.info(f"Processing uploaded file: {file.filename}")
        # Process the file
        num_rows = rag_processor.process_excel_file(temp_path, file.filename)
        logger.info(f"Successfully processed {num_rows} rows from {file.filename}")
        
        return {
            "message": f"Successfully processed {num_rows} rows from {file.filename}",
            "rows": num_rows
        }
        
    except Exception as e:
        logger.error(f"Error processing uploaded file {file.filename}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up temp file
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
                logger.debug(f"Cleaned up temporary file: {temp_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up temporary file {temp_path}: {e}")

# Chat endpoint
@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    global cleanup_counter
    logger.info(f"Chat request received - session: {request.session_id}, message length: {len(request.message)}")
    
    try:
        # Periodic cleanup of old sessions (every 100 requests)
        cleanup_counter += 1
        if cleanup_counter >= 100:
            cleanup_old_sessions()
            cleanup_counter = 0
        
        # Add user message to session memory
        user_message = {
            "role": "user",
            "content": request.message,
            "timestamp": datetime.datetime.now().isoformat()
        }
        add_to_session_memory(request.session_id, user_message)
        
        # Get conversation history
        conversation_history = get_session_memory(request.session_id)
        logger.debug(f"Retrieved {len(conversation_history)} messages from session memory")
        
        # Search for relevant documents
        relevant_docs = rag_processor.search_documents(request.message, k=5)
        logger.debug(f"Found {len(relevant_docs)} relevant documents for query")
        
        # Generate response with conversation context
        response_text = rag_processor.generate_response_with_context(
            request.message, 
            relevant_docs, 
            conversation_history
        )
        logger.info(f"Generated response for session {request.session_id}")
        
        # Add assistant response to session memory
        assistant_message = {
            "role": "assistant",
            "content": response_text,
            "timestamp": datetime.datetime.now().isoformat()
        }
        add_to_session_memory(request.session_id, assistant_message)
        
        # Prepare sources
        sources = []
        for doc in relevant_docs:
            metadata = doc["metadata"]
            logger.debug(f"Processing source metadata: {metadata}")
            
            # Determine source info based on available metadata
            source_type = metadata.get("source_type")
            filename = metadata.get("filename")
            
            if source_type == "user_resolution":
                source_info = f"Resolution: {metadata.get('error_code', 'N/A')} ({metadata.get('module', 'N/A')})"
            elif source_type in ["uploaded_file", "default_file"]:
                source_info = filename or f"{source_type.replace('_', ' ').title()}"
            elif filename:
                source_info = filename
            else:
                # Fallback for documents with incomplete metadata
                source_info = "Ticket Data"
            
            sources.append({
                "content": doc["content"],
                "metadata": {
                    "source": source_info
                }
            })
        
        return ChatResponse(
            response=response_text,
            sources=sources
        )
        
    except Exception as e:
        logger.error(f"Error processing chat request for session {request.session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Add resolution endpoint
@app.post("/add-resolution")
async def add_resolution(resolution: ResolutionRequest):
    logger.info(f"Add resolution request received - error_code: {resolution.error_code}, module: {resolution.module}")
    
    try:
        rag_processor.add_resolution(resolution.dict())
        logger.info("Resolution added successfully to knowledge base")
        return {"message": "Resolution added successfully to the knowledge base"}
    except Exception as e:
        logger.error(f"Error adding resolution: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Feedback endpoint
@app.post("/feedback")
async def submit_feedback(feedback: FeedbackRequest):
    logger.info(f"Feedback received - type: {feedback.type}, messageId: {feedback.messageId}")
    
    try:
        # For negative feedback, save to file
        if feedback.type == "negative":
            feedback_entry = {
                "timestamp": datetime.datetime.now().isoformat(),
                "message_id": feedback.messageId,
                "type": feedback.type,
                "suggestions": feedback.suggestions
            }
            
            # Save to feedback.json file
            feedback_file = "feedback.json"
            try:
                # Load existing feedback if file exists
                if os.path.exists(feedback_file):
                    with open(feedback_file, 'r') as f:
                        existing_feedback = json.load(f)
                else:
                    existing_feedback = []
                
                # Add new feedback
                existing_feedback.append(feedback_entry)
                
                # Save back to file
                with open(feedback_file, 'w') as f:
                    json.dump(existing_feedback, f, indent=2)
                
                logger.info(f"Negative feedback saved to {feedback_file}")
            except Exception as e:
                logger.error(f"Error saving feedback to file: {e}")
                raise HTTPException(status_code=500, detail="Failed to save feedback")
        
        return {"message": "Feedback submitted successfully"}
    except Exception as e:
        logger.error(f"Error processing feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Clear chat endpoint
@app.post("/clear-chat")
async def clear_chat(session_id: str = Form(...)):
    logger.info(f"Clear chat request received for session: {session_id}")

    try:
        if session_id in session_memories:
            del session_memories[session_id]
            logger.info(f"Session {session_id} cleared successfully")
            return {"message": f"Chat history cleared for session {session_id}"}
        else:
            logger.warning(f"Clear request for non-existent session: {session_id}")
            return {"message": f"No chat history found for session {session_id}"}

    except Exception as e:
        logger.error(f"Error clearing chat for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear chat history")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

