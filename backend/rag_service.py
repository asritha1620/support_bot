import os
import pandas as pd
from typing import List, Dict, Any
from dotenv import load_dotenv
from datetime import datetime
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import FAISS
from langchain.schema import Document
from langchain_google_genai import ChatGoogleGenerativeAI
import google.generativeai as genai
from sentence_transformers import SentenceTransformer
import numpy as np

# Load environment variables
load_dotenv()


class SentenceTransformerEmbeddings:
    """Custom embeddings class using sentence-transformers directly"""
    
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of documents"""
        embeddings = self.model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()
    
    def embed_query(self, text: str) -> List[float]:
        """Embed a single query"""
        embedding = self.model.encode([text], convert_to_numpy=True)[0]
        return embedding.tolist()


class RAGService:
    def __init__(self):
        self.sessions = {}  # Store session-specific data
        self.embeddings = None
        self.llm = None
        self.system_prompt = ("""
You are a Support Engineer Helper AI. Your role is to assist the human Support Engineer (me) in diagnosing, troubleshooting, and suggesting fixes for support tickets in our eCommerce platform. I will use your guidance to actually perform the fixes.

Instructions:
--Be friendly, patient, and professional.
--Ask relevant follow-up questions in a short and crisp way, using no more than 3 bullet points.
--Explain technical solutions clearly, step-by-step, without assuming prior technical knowledge. Use 3 bullet points or fewer for resolution steps whenever possible.
--Use a polite, conversational tone but remain focused and precise.
--Always consider the user's previous messages in the thread.
--If a previous ticket or error has been discussed, use that context to tailor your suggestions.
--If a ticket ID or customer name is given, keep that reference until the issue is resolved.
--Retain category-specific history (like "PAY502" errors being payment gateway timeouts).
--Use historical ticket data, known error code mappings, resolution playbooks, and escalation paths to provide solutions.
--If the exact error code is detected, respond with:
    --"As per existing history tickets, here are the resolution steps you can try to fix the problem:"
--Then provide no more than 3 bullet points outlining the steps from the documented history.
--When the user provides resolution steps, respond with:
    --"Thank you for providing the resolution steps, I learnt a new thing today."
--If an issue is unknown or requires human intervention, say so clearly and recommend escalation.
--When referring to logs, files, or configurations, use realistic paths (e.g., /var/logs/payment/, /config/orders.yaml).
--Ask clarifying questions briefly, for example:
    --"Can you share the full error message?"
    --"Did this happen at checkout or order confirmation?"
    --"Any recent changes to config or server?"
--Provide options concisely:
    --"Do you want to check logs or restart the service?"
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
    --"I'm designed to assist with technical support issues. Please let me know how I can help you with a support-related question."
--Do not provide unrelated information even if the user insists.
{context}
    """)
        self.setup_models()
    
    def setup_models(self):
        """Initialize the embeddings and LLM models"""
        try:
            # Setup sentence-transformers embeddings for FAISS
            try:
                self.embeddings = SentenceTransformerEmbeddings(
                    model_name="sentence-transformers/all-MiniLM-L6-v2"
                )
                print("Embeddings model initialized successfully")
            except Exception as e:
                print(f"Failed to initialize embeddings: {e}")
                self.embeddings = None
            
            # Setup Gemini LLM
            gemini_api_key = os.getenv("GEMINI_API_KEY")
            if not gemini_api_key:
                print("Warning: GEMINI_API_KEY not found. LLM functionality will be limited.")
                self.llm = None
            else:
                if ChatGoogleGenerativeAI is None:
                    print("Warning: ChatGoogleGenerativeAI not installed. LLM functionality will be limited.")
                    self.llm = None
                else:
                    genai.configure(api_key=gemini_api_key)
                    self.llm = ChatGoogleGenerativeAI(
                        model="gemini-2.0-flash-exp",
                        google_api_key=gemini_api_key,
                        temperature=0.7,
                        convert_system_message_to_human=True
                    )

            print("RAG Service initialized successfully")
            
        except Exception as e:
            print(f"Error initializing RAG service: {str(e)}")
            raise
    
    def load_excel_data(self, file_path: str) -> List[Document]:
        """Load and process Excel file into documents"""
        try:
            # Read Excel file
            df = pd.read_excel(file_path)
            documents = []
            file_name = os.path.basename(file_path)
            
            # Convert each row to a document
            for idx, row in df.iterrows():
                content = ""
                metadata = {"row_index": idx, "source": file_name}
                
                for col in df.columns:
                    if pd.notna(row[col]):
                        content += f"{col}: {row[col]}\n"
                        metadata[col] = str(row[col])
                
                if content.strip():
                    documents.append(Document(
                        page_content=content.strip(),
                        metadata=metadata
                    ))
            
            # Create column summaries
            for col in df.columns:
                col_data = df[col].dropna()
                if not col_data.empty:
                    content = f"Column: {col}\n"
                    content += f"Data type: {col_data.dtype}\n"
                    content += f"Sample values: {', '.join(map(str, col_data.head(10).tolist()))}\n"
                    content += f"Total non-null values: {len(col_data)}"
                    
                    documents.append(Document(
                        page_content=content,
                        metadata={"column": col, "source": file_name, "type": "column_summary"}
                    ))
            
            return documents
            
        except Exception as e:
            print(f"Error loading Excel file: {str(e)}")
            return []
    
    def _fallback_keyword_search(self, question: str, documents: List[Document], limit: int = 5) -> List[Dict]:
        """Fallback keyword search when semantic search is unavailable"""
        question_words = question.lower().split()
        relevant_tickets = []
        
        for doc in documents[:20]:  # Search first 20 documents
            if doc.metadata.get('type') == 'column_summary':
                continue
            content_lower = doc.page_content.lower()
            score = sum(1 for word in question_words if len(word) > 2 and word in content_lower)
            if score > 0:
                relevant_tickets.append({
                    'document': doc,
                    'score': score,
                    'reasons': ['Keyword match']
                })
        
        relevant_tickets.sort(key=lambda x: x['score'], reverse=True)
        return relevant_tickets[:limit]
    
    def create_vectorstore(self, documents: List[Document]) -> FAISS:
        """Create FAISS vectorstore from documents"""
        try:
            if not documents:
                raise ValueError("No documents to process")
            
            # Split documents into smaller chunks
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=500,
                chunk_overlap=50,
                length_function=len
            )
            
            split_docs = text_splitter.split_documents(documents)
            
            # Create vectorstore
            vectorstore = FAISS.from_documents(split_docs, self.embeddings)
            
            return vectorstore
        except Exception as e:
            print(f"Error creating vectorstore: {str(e)}")
            raise
    
    def save_vectorstore(self, vectorstore: FAISS, session_id: str) -> bool:
        """Save FAISS vectorstore to disk for persistence"""
        try:
            persist_dir = f"vectorstores/{session_id}"
            os.makedirs(persist_dir, exist_ok=True)
            vectorstore.save_local(persist_dir)
            print(f"Saved vectorstore for session {session_id}")
            return True
        except Exception as e:
            print(f"Error saving vectorstore: {e}")
            return False
    
    def load_vectorstore(self, session_id: str) -> FAISS:
        """Load FAISS vectorstore from disk"""
        try:
            persist_dir = f"vectorstores/{session_id}"
            if os.path.exists(persist_dir):
                vectorstore = FAISS.load_local(persist_dir, self.embeddings, allow_dangerous_deserialization=True)
                print(f"Loaded vectorstore for session {session_id}")
                return vectorstore
            else:
                print(f"No saved vectorstore found for session {session_id}")
                return None
        except Exception as e:
            print(f"Error loading vectorstore: {e}")
            return None
    
    async def process_file(self, file_path: str, session_id: str) -> bool:
        """Process Excel file and setup RAG for session with FAISS vectorstore"""
        try:
            # Check if vectorstore already exists for this session
            existing_vectorstore = self.load_vectorstore(session_id)
            if existing_vectorstore:
                print(f"Found existing vectorstore for session {session_id}")
                # Load documents from file and add to existing vectorstore
                documents = self.load_excel_data(file_path)
                if not documents:
                    return False
                
                try:
                    existing_vectorstore.add_documents(documents)
                    self.save_vectorstore(existing_vectorstore, session_id)
                    print(f"Updated existing vectorstore with {len(documents)} new documents")
                except Exception as e:
                    print(f"Failed to update existing vectorstore: {e}, creating new one")
                    existing_vectorstore = self.create_vectorstore(documents)
                    self.save_vectorstore(existing_vectorstore, session_id)
                
                # Store in session
                self.sessions[session_id] = {
                    "documents": documents,
                    "vectorstore": existing_vectorstore,
                    "file_path": file_path
                }
                return True
            
            # Load documents
            documents = self.load_excel_data(file_path)
            if not documents:
                return False
            
            # Create FAISS vectorstore for semantic search
            try:
                vectorstore = self.create_vectorstore(documents)
                self.save_vectorstore(vectorstore, session_id)
                print(f"Created and saved FAISS vectorstore with {len(documents)} documents")
            except Exception as e:
                print(f"Failed to create vectorstore: {e}, falling back to document storage only")
                vectorstore = None
            
            # Store in session
            self.sessions[session_id] = {
                "documents": documents,
                "vectorstore": vectorstore,
                "file_path": file_path
            }
            
            return True
            
        except Exception as e:
            print(f"Error processing file: {str(e)}")
            return False
    
    async def append_file(self, file_path: str, session_id: str) -> bool:
        """Append Excel file data to an existing session with FAISS update"""
        try:
            if session_id not in self.sessions:
                return False
            
            # Load new documents
            new_documents = self.load_excel_data(file_path)
            if not new_documents:
                return False
            
            # Append to existing documents
            self.sessions[session_id]["documents"].extend(new_documents)
            
            # Update FAISS vectorstore if it exists
            if self.sessions[session_id].get("vectorstore"):
                try:
                    # Add new documents to existing vectorstore
                    self.sessions[session_id]["vectorstore"].add_documents(new_documents)
                    self.save_vectorstore(self.sessions[session_id]["vectorstore"], session_id)
                    print(f"Updated FAISS vectorstore with {len(new_documents)} new documents")
                except Exception as e:
                    print(f"Failed to update vectorstore: {e}, recreating...")
                    try:
                        # Recreate vectorstore with all documents
                        all_documents = self.sessions[session_id]["documents"]
                        self.sessions[session_id]["vectorstore"] = self.create_vectorstore(all_documents)
                        self.save_vectorstore(self.sessions[session_id]["vectorstore"], session_id)
                        print(f"Recreated FAISS vectorstore with {len(all_documents)} total documents")
                    except Exception as e2:
                        print(f"Failed to recreate vectorstore: {e2}")
                        self.sessions[session_id]["vectorstore"] = None
            else:
                # Try to create vectorstore if it doesn't exist
                try:
                    all_documents = self.sessions[session_id]["documents"]
                    self.sessions[session_id]["vectorstore"] = self.create_vectorstore(all_documents)
                    self.save_vectorstore(self.sessions[session_id]["vectorstore"], session_id)
                    print(f"Created FAISS vectorstore for existing session with {len(all_documents)} documents")
                except Exception as e:
                    print(f"Failed to create vectorstore for existing session: {e}")
            
            # Update file path to indicate multiple files
            current_path = self.sessions[session_id].get("file_path", "")
            if isinstance(current_path, str) and current_path:
                self.sessions[session_id]["file_paths"] = [current_path, file_path]
            elif isinstance(current_path, list):
                current_path.append(file_path)
                self.sessions[session_id]["file_paths"] = current_path
            else:
                self.sessions[session_id]["file_paths"] = [file_path]
            
            print(f"Appended {len(new_documents)} documents to session {session_id}")
            return True
            
        except Exception as e:
            print(f"Error appending file: {str(e)}")
            return False
    
    async def query(self, question: str, session_id: str) -> Dict[str, Any]:
        """Query the RAG system for support ticket resolution"""
        try:
            if session_id not in self.sessions:
                return {"error": "Session not found"}

            documents = self.sessions[session_id]["documents"]

            # Single comprehensive LLM call to handle everything
            if self.llm is not None:
                # Create comprehensive context from all tickets for analysis
                all_ticket_context = ""
                ticket_count = 0
                for doc in documents:
                    if doc.metadata.get('type') != 'column_summary':
                        ticket_count += 1
                        all_ticket_context += f"\n--- Ticket {ticket_count} ---\n{doc.page_content}\n"

                comprehensive_prompt = f"""{self.system_prompt}

AVAILABLE TICKET DATA ({ticket_count} total tickets):
{all_ticket_context}

USER QUERY: "{question}"

INSTRUCTIONS:
1. If this is NOT a support-related query (greetings, casual chat, unrelated topics), respond directly with an appropriate message following your behavioral guidelines.

2. If this IS a support-related query:
   - First, determine if it's ANALYTICAL (asking for statistics, summaries, trends, analysis of ticket data) or SUPPORT (asking for troubleshooting help, error resolution, specific solutions)
   - For ANALYTICAL queries: Provide statistical analysis, summaries, and insights based on the ticket data
   - For SUPPORT queries: Find similar past tickets and provide step-by-step resolution guidance

3. Format your response professionally using the guidelines in your system prompt.

4. If no relevant tickets are found for support queries, suggest what additional information would help.

Your response:"""

                try:
                    result = self.llm.invoke(comprehensive_prompt)
                    response = result.content if hasattr(result, 'content') else str(result)

                    # For support queries, we still want to provide sources
                    # Check if this looks like a support response (contains ticket references or technical content)
                    is_support_response = any(keyword in response.lower() for keyword in [
                        'ticket', 'error', 'resolution', 'step', 'check', 'fix', 'issue', 'similar'
                    ])

                    if is_support_response:
                        # Extract relevant sources (simplified - just return top matches)
                        relevant_docs = []
                        for doc in documents[:5]:  # Sample first 5 tickets as sources
                            if doc.metadata.get('type') != 'column_summary':
                                relevant_docs.append({
                                    "content": doc.page_content[:300] + "..." if len(doc.page_content) > 300 else doc.page_content,
                                    "metadata": doc.metadata,
                                    "relevance_score": 5,  # Default moderate score
                                    "match_reasons": ["Included in comprehensive analysis"]
                                })

                        return {
                            "answer": f"**Confidence: Medium**\n\n{response}",
                            "sources": relevant_docs
                        }
                    else:
                        # Non-support response (greetings, etc.)
                        return {
                            "answer": response,
                            "sources": []
                        }

                except Exception as e:
                    print(f"LLM query failed: {e}")
                    # Fallback to basic search
            
        except Exception as e:
            return {"error": f"Error during query: {str(e)}"}
    
    async def add_resolution(self, session_id: str, resolution_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add a new resolution to the session's ticket data"""
        try:
            if session_id not in self.sessions:
                return {"error": "Session not found"}

            # Normalize the data
            normalized_data = {
                'error_code': resolution_data.get('error_code', 'N/A'),
                'module': resolution_data.get('module', 'General'),
                'ticket_level': resolution_data.get('ticket_level', 'L2'),
                'description': resolution_data.get('description', '').strip(),
                'resolution': resolution_data.get('resolution', resolution_data.get('resolution_steps', '')).strip()
            }

            # Validate required fields
            if not normalized_data['description'] or not normalized_data['resolution']:
                return {"error": "Missing required fields: description and resolution are required"}

            # Create a new document from the resolution data
            new_document = Document(
                page_content=f"""
Ticket Level: {normalized_data['ticket_level']}
Module: {normalized_data['module']}
Error Code: {normalized_data['error_code']}
Description: {normalized_data['description']}
Resolution: {normalized_data['resolution']}
Added: {datetime.now().isoformat()}
""".strip(),
                metadata={
                    "row_index": len(self.sessions[session_id]["documents"]),  # Next available index
                    "source": "user_added_resolution",
                    "type": "manual_entry",
                    "ticket_level": normalized_data['ticket_level'],
                    "module": normalized_data['module'],
                    "error_code": normalized_data['error_code'],
                    "added_at": datetime.now().isoformat()
                }
            )

            # Add to session documents
            self.sessions[session_id]["documents"].append(new_document)

            print(f"Added new resolution to session {session_id}: {normalized_data['description'][:50]}...")

            return {
                "success": True,
                "message": "Resolution added successfully",
                "document_count": len(self.sessions[session_id]["documents"])
            }

        except Exception as e:
            print(f"Error adding resolution: {str(e)}")
            return {"error": f"Error adding resolution: {str(e)}"}
    
    async def cleanup_session(self, session_id: str):
        """Clean up session data"""
        if session_id in self.sessions:
            del self.sessions[session_id]