import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import google.generativeai as genai
import pandas as pd
import json
import os
import logging
from pathlib import Path
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class RAGProcessor:
    def __init__(self):
        self.vectorstore = None
        self.documents = []
        self.embeddings_model = None
        self.llm = None
        self.api_key1 = None
        self.api_key2 = None
        self.current_key = None
        
    def initialize_models(self, api_key1: str, api_key2: str):
        """Initialize embeddings model and LLM with fallback keys"""
        self.api_key1 = api_key1
        self.api_key2 = api_key2
        self.current_key = api_key1
        
        logger.info("Initializing sentence transformer model")
        self.embeddings_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        logger.info("Configuring Google Generative AI with primary key")
        genai.configure(api_key=self.current_key)
        self.llm = genai.GenerativeModel('gemini-2.5-flash')
        logger.info("RAG processor models initialized successfully")
    
    def switch_to_fallback_key(self):
        """Switch to the fallback API key if available"""
        if self.current_key == self.api_key1 and self.api_key2:
            logger.warning("Switching to fallback API key due to primary key issues")
            self.current_key = self.api_key2
            genai.configure(api_key=self.current_key)
            self.llm = genai.GenerativeModel('gemini-2.5-flash')
            logger.info("Successfully switched to fallback API key")
            return True
        logger.error("Cannot switch to fallback key - either already using it or no fallback available")
        return False
    
    def load_vectorstore(self) -> bool:
        """Load existing vectorstore from disk"""
        index_path = Path("faiss_index/index.faiss")
        docs_path = Path("faiss_index/documents.json")
        
        if index_path.exists() and docs_path.exists():
            try:
                logger.info("Loading existing FAISS index")
                self.vectorstore = faiss.read_index(str(index_path))
                
                logger.info("Loading documents metadata")
                with open(docs_path, 'r') as f:
                    self.documents = json.load(f)
                
                logger.info(f"Successfully loaded vectorstore with {len(self.documents)} documents")
                
                # Debug: Check metadata of first few documents
                if self.documents:
                    logger.debug(f"Sample document metadata: {self.documents[0].get('metadata', {})}")
                    logger.debug(f"Sample document keys: {list(self.documents[0].keys())}")
                
                return True
            except Exception as e:
                logger.error(f"Error loading vectorstore: {e}")
                return False
        else:
            logger.info("No existing vectorstore found")
            return False
    
    def save_vectorstore(self):
        """Save vectorstore to disk"""
        try:
            os.makedirs("faiss_index", exist_ok=True)
            
            if self.vectorstore is not None:
                logger.debug("Saving FAISS index to disk")
                faiss.write_index(self.vectorstore, "faiss_index/index.faiss")
            
            logger.debug("Saving documents metadata to disk")
            with open("faiss_index/documents.json", 'w') as f:
                json.dump(self.documents, f)
            
            logger.debug("Vectorstore saved successfully")
        except Exception as e:
            logger.error(f"Error saving vectorstore: {e}")
            raise
    
    def process_excel_file(self, file_path: str, filename: str = None, source_type: str = "uploaded_file") -> int:
        """Process Excel file and add to vectorstore"""
        try:
            logger.info(f"Processing Excel file: {file_path}")
            df = pd.read_excel(file_path)
            logger.info(f"Loaded Excel file with {len(df)} rows and {len(df.columns)} columns")
            
            # Use filename from parameter or extract from path
            if filename is None:
                filename = os.path.basename(file_path)
            
            # Convert each row to text
            texts = []
            for idx, row in df.iterrows():
                text = f"Row {idx}: " + " | ".join([f"{col}: {val}" for col, val in row.items() if pd.notna(val)])
                texts.append(text)
            
            logger.info(f"Generated {len(texts)} text documents from Excel rows")
            
            # Generate embeddings
            logger.debug("Generating embeddings for documents")
            embeddings = self.embeddings_model.encode(texts)
            
            # Initialize or update FAISS index
            if self.vectorstore is None:
                dimension = embeddings.shape[1]
                self.vectorstore = faiss.IndexFlatL2(dimension)
                logger.info(f"Created new FAISS index with dimension {dimension}")
            
            # Add to index
            self.vectorstore.add(np.array(embeddings).astype('float32'))
            
            # Store documents with metadata
            for i, text in enumerate(texts):
                self.documents.append({
                    "id": len(self.documents) + i,
                    "content": text,
                    "metadata": {
                        "row_index": len(self.documents) + i,
                        "filename": filename,
                        "source_type": source_type
                    }
                })
            
            self.save_vectorstore()
            logger.info(f"Successfully processed {len(texts)} documents from Excel file")
            return len(texts)
            
        except Exception as e:
            logger.error(f"Error processing Excel file {file_path}: {e}")
            raise Exception(f"Error processing file: {str(e)}")
    
    def search_documents(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Search vectorstore for relevant documents"""
        if self.vectorstore is None or len(self.documents) == 0:
            logger.warning("Vectorstore is empty or not initialized - no documents to search")
            return []
        
        try:
            logger.debug(f"Searching for query: '{query[:50]}...' with k={k}")
            
            # Generate query embedding
            query_embedding = self.embeddings_model.encode([query])[0]
            
            # Search
            distances, indices = self.vectorstore.search(np.array([query_embedding]).astype('float32'), k)
            
            results = []
            for i, idx in enumerate(indices[0]):
                if idx < len(self.documents):
                    results.append({
                        "content": self.documents[idx]["content"],
                        "metadata": self.documents[idx]["metadata"],
                        "score": float(distances[0][i])
                    })
            
            logger.debug(f"Found {len(results)} relevant documents")
            return results
            
        except Exception as e:
            logger.error(f"Error searching documents: {e}")
            return []
    
    def generate_response_with_context(self, query: str, context_docs: List[Dict[str, Any]], conversation_history: List[Dict[str, Any]]) -> str:
        """Generate response using LLM with conversation context and fallback key support"""
        if not context_docs:
            logger.warning("No context documents provided for response generation")
            return "I don't have enough information to answer this question."
        
        # Prepare context from documents
        context = "\n\n".join([doc["content"] for doc in context_docs])
        
        # Prepare conversation history (exclude the current query which is already in conversation_history)
        history_text = ""
        if conversation_history:
            # Get the last few messages for context (avoid too long context)
            recent_history = conversation_history[-10:]  # Last 10 messages
            history_lines = []
            for msg in recent_history[:-1]:  # Exclude the current user message
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                if role == "user":
                    history_lines.append(f"User: {content}")
                elif role == "assistant":
                    history_lines.append(f"Assistant: {content}")
            
            if history_lines:
                history_text = "\n\nPrevious conversation:\n" + "\n".join(history_lines)
                logger.debug(f"Including {len(history_lines)} messages from conversation history in prompt")
        
        prompt = f"""You are a Support Engineer Helper AI. Your role is to assist the human Support Engineer (me) in diagnosing, troubleshooting, and suggesting fixes for support tickets in our eCommerce platform. I will use your guidance to actually perform the fixes.
Context from support tickets:
{context}{history_text}
Current user question: {query}
Instructions:
--Be friendly, patient, and professional.
--Ask relevant follow-up questions in a short and crisp way, using no more than 3 bullet points.
--Explain technical solutions clearly, step-by-step, without assuming prior technical knowledge. Use 3 bullet points or fewer for resolution steps whenever possible.
--Use a polite, conversational tone but remain focused and precise.
--Always consider the user's previous messages in the thread.
--If a previous ticket or error has been discussed, use that context to tailor your suggestions.
--If a ticket ID or customer name is given, keep that reference until the issue is resolved.
--Retain category-specific history (like “PAY502” errors being payment gateway timeouts).
--Use historical ticket data, known error code mappings, resolution playbooks, and escalation paths to provide solutions.
--If the exact error code is detected, respond with:
    --“As per existing history tickets, here are the resolution steps you can try to fix the problem:”
--Then provide no more than 3 bullet points outlining the steps from the documented history.
--When the user provides resolution steps, respond with:
    --“Thank you for providing the resolution steps, I learnt a new thing today.”
--If an issue is unknown or requires human intervention, say so clearly and recommend escalation.
--When referring to logs, files, or configurations, use realistic paths (e.g., /var/logs/payment/, /config/orders.yaml).
--Ask clarifying questions briefly, for example:
    --“Can you share the full error message?”
    --“Did this happen at checkout or order confirmation?”
    --“Any recent changes to config or server?”
--Provide options concisely:
    --“Do you want to check logs or restart the service?”
--Summarize steps clearly, with no more than 3 bullet points:
    --Example:
        --Check logs in /var/logs/payment/
        --Update config file payment.yaml
        --Restart payment service
--For L1 issues: Focus on quick fixes like cache clear, network reset, retry, UI checks.
--For L2 issues: Guide through deeper analysis like log checks, config edits, API testing.
--For known L3 tickets: Mention backend/dev team involvement.
--Use bold or code style to highlight file paths, config keys, or API endpoints.
--If the solution is lengthy, provide a brief summary at the end.
--Strictly avoid answering:
    --General knowledge questions (geography, history, etc.)
    --Jokes, trivia, or personal questions
    --Anything unrelated to support engineering
--If an unrelated query is detected, respond with:
    --“I'm designed to assist with technical support issues. Please let me know how I can help you with a support-related question.”
--Do not provide unrelated information even if the user insists.
"""

        # Try with current key first
        try:
            logger.debug("Generating response with conversation context")
            response = self.llm.generate_content(prompt)
            logger.debug("Response generated successfully")
            return response.text
        except Exception as e:
            error_str = str(e).lower()
            logger.warning(f"API call failed with current key: {e}")
            
            # Check if it's a quota/rate limit error
            if any(keyword in error_str for keyword in ['quota', 'rate limit', '429', 'resource exhausted']):
                logger.info("Detected quota/rate limit error - attempting to switch to fallback key")
                # Try switching to fallback key
                if self.switch_to_fallback_key():
                    try:
                        logger.debug("Retrying with fallback API key")
                        response = self.llm.generate_content(prompt)
                        logger.info("Response generated successfully with fallback key")
                        return response.text
                    except Exception as e2:
                        logger.error(f"Response generation failed with fallback key: {e2}")
                        return f"Error generating response with fallback key: {str(e2)}"
                else:
                    logger.error("No fallback key available and primary key has quota issues")
                    return f"Error: Primary API key quota exceeded and no fallback key available: {str(e)}"
            else:
                logger.error(f"Non-quota API error: {e}")
                return f"Error generating response: {str(e)}"
    
    def add_resolution(self, resolution_data: Dict[str, Any]):
        """Add a resolution to the knowledge base"""
        try:
            logger.info(f"Adding resolution - error_code: {resolution_data.get('error_code', 'N/A')}, module: {resolution_data.get('module', 'N/A')}")
            
            resolution_text = f"Resolution - Error Code: {resolution_data.get('error_code', 'N/A')}, Module: {resolution_data.get('module', 'N/A')}, Level: {resolution_data['ticket_level']}\nDescription: {resolution_data['description']}\nResolution: {resolution_data['resolution']}"
            
            # Generate embedding
            logger.debug("Generating embedding for resolution")
            embedding = self.embeddings_model.encode([resolution_text])[0]
            
            # Initialize vectorstore if needed
            if self.vectorstore is None:
                dimension = len(embedding)
                self.vectorstore = faiss.IndexFlatL2(dimension)
                logger.info(f"Created new FAISS index for resolution with dimension {dimension}")
            
            # Add to index
            self.vectorstore.add(np.array([embedding]).astype('float32'))
            
            # Add to documents
            self.documents.append({
                "id": len(self.documents),
                "content": resolution_text,
                "metadata": {
                    "type": "resolution",
                    "row_index": len(self.documents),
                    "error_code": resolution_data.get('error_code'),
                    "module": resolution_data.get('module'),
                    "ticket_level": resolution_data['ticket_level'],
                    "source_type": "user_resolution"
                }
            })
            
            self.save_vectorstore()
            logger.info("Resolution added successfully to knowledge base")
            
        except Exception as e:
            logger.error(f"Error adding resolution: {e}")

            raise
