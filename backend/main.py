"""
FastAPI Backend Server for Multi-User Chat with AI Support
Supports WebSocket for real-time messaging and /bot command to add AI to conversations
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, Body, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Optional
import json
import uuid
from datetime import datetime
from pydantic import BaseModel
import asyncio
import logging
import os
from pathlib import Path
from dotenv import load_dotenv
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
import requests as http_requests

# Configure logging first
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Google OAuth configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

# Gemini AI imports
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
    # Configure Gemini API key from environment variable
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if gemini_api_key:
        genai.configure(api_key=gemini_api_key)
        logger.info("Gemini AI configured successfully")
    else:
        GEMINI_AVAILABLE = False
        logger.warning("GEMINI_API_KEY not found in environment variables. Gemini AI will not be available.")
except ImportError as e:
    GEMINI_AVAILABLE = False
    gemini_api_key = None
    logger.warning(f"Gemini AI not available. Import error: {e}")

# Firebase imports
try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    FIREBASE_AVAILABLE = True
except ImportError as e:
    FIREBASE_AVAILABLE = False
    print(f"Firebase not available, using in-memory storage. Import error: {e}")

# RAG Service imports
try:
    import sys
    # Add rag directory to path
    rag_dir = Path(__file__).parent / "rag"
    sys.path.insert(0, str(rag_dir))
    from rag_service import RAGService
    RAG_AVAILABLE = True
except ImportError as e:
    RAG_AVAILABLE = False
    logger.warning(f"RAG service not available. Import error: {e}")

app = FastAPI(title="IntoTheWild Chat API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your Flutter app's origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage (fallback if Firebase not configured)
active_connections: Dict[str, WebSocket] = {}
conversations: Dict[str, Dict] = {}
messages_store: Dict[str, List[Dict]] = {}
users: Dict[str, Dict] = {}

# Firebase initialization
db = None

# Initialize Firebase if available
if FIREBASE_AVAILABLE:
    try:
        # Check if Firebase is already initialized (prevents error on reload)
        try:
            firebase_admin.get_app()
            logger.info("Firebase already initialized")
        except ValueError:
            # Firebase not initialized yet, so initialize it
            import os
            # Get the directory where this script is located
            script_dir = os.path.dirname(os.path.abspath(__file__))
            cred_path = os.path.join(script_dir, "serviceAccountKey.json")
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            logger.info("Firebase initialized successfully")

        db = firestore.client()
    except Exception as e:
        logger.warning(f"Firebase initialization failed: {e}")
        db = None

# Pydantic models
class User(BaseModel):
    id: str
    username: str
    email: Optional[str] = None
    googleId: Optional[str] = None
    picture: Optional[str] = None
    createdAt: Optional[str] = None
    lastLoginAt: Optional[str] = None


class Message(BaseModel):
    id: str
    text: str
    userId: str
    userName: str
    conversationId: str
    createdAt: str
    isBot: bool = False
    imageUrl: Optional[str] = None
    type: str = "text"


class Conversation(BaseModel):
    id: str
    name: Optional[str] = None
    type: str  # "one_to_one" or "group"
    participants: List[str]
    createdAt: str
    hasBot: bool = False


class CreateConversationRequest(BaseModel):
    name: Optional[str] = None
    type: str  # "one_to_one" or "group"
    participantIds: List[str]


class RegisterUserRequest(BaseModel):
    username: str
    email: Optional[str] = None


# Database helper functions
async def save_message(message: Dict):
    """Save message to database (Firebase or in-memory)"""
    if db:
        # Save to Firebase
        db.collection("messages").add(message)
    else:
        # In-memory storage
        conv_id = message["conversationId"]
        if conv_id not in messages_store:
            messages_store[conv_id] = []
        messages_store[conv_id].append(message)


async def get_messages(conversation_id: str, limit: int = 50) -> List[Dict]:
    """Get messages from database"""
    if db:
        # Get from Firebase
        messages_ref = db.collection("messages").where("conversationId", "==", conversation_id)
        messages_ref = messages_ref.order_by("createdAt", direction=firestore.Query.DESCENDING).limit(limit)
        docs = messages_ref.stream()
        return [doc.to_dict() for doc in docs]
    else:
        # In-memory storage
        return messages_store.get(conversation_id, [])


async def save_conversation(conversation: Dict):
    """Save conversation to database"""
    if db:
        db.collection("conversations").document(conversation["id"]).set(conversation)
    else:
        conversations[conversation["id"]] = conversation


async def get_conversation(conversation_id: str) -> Optional[Dict]:
    """Get conversation from database"""
    if db:
        doc = db.collection("conversations").document(conversation_id).get()
        return doc.to_dict() if doc.exists else None
    else:
        return conversations.get(conversation_id)


async def update_conversation(conversation_id: str, updates: Dict):
    """Update conversation in database"""
    if db:
        db.collection("conversations").document(conversation_id).update(updates)
    else:
        if conversation_id in conversations:
            conversations[conversation_id].update(updates)


async def find_conversation_by_participants(participant_ids: List[str], conversation_type: str = "one_to_one") -> Optional[Dict]:
    """Find existing conversation with exact same participants (for one-to-one conversations)"""
    participant_set = set(participant_ids)

    if db:
        # Query Firebase for conversations with these participants
        convs_ref = db.collection("conversations").where("type", "==", conversation_type)
        docs = convs_ref.stream()
        for doc in docs:
            conv = doc.to_dict()
            if conv and set(conv.get("participants", [])) == participant_set:
                return conv
        return None
    else:
        # In-memory storage
        for conv in conversations.values():
            if conv.get("type") == conversation_type and set(conv.get("participants", [])) == participant_set:
                return conv
        return None


# Initialize RAG Service
rag_service = None
if RAG_AVAILABLE:
    try:
        # Get the path to the plant data JSON file
        script_dir = Path(__file__).parent
        json_file_path = script_dir / "rag" / "all_plants_streaming.json"
        rag_service = RAGService(json_file_path=str(json_file_path) if json_file_path.exists() else None)
        if rag_service.is_available():
            logger.info("RAG service initialized successfully")
        else:
            logger.warning("RAG service initialized but not fully available (missing API keys)")
    except Exception as e:
        logger.error(f"Failed to initialize RAG service: {e}")
        rag_service = None

# AI Service (shared AI for all users)
class AIService:
    """Shared AI service that generates responses using Gemini AI with RAG support"""

    def __init__(self):
        """Initialize the AI service with Gemini model"""
        self.model = None
        self.model_name = None
        self.rag_service = rag_service
        if GEMINI_AVAILABLE and gemini_api_key:
            # Try different model names in order of preference
            # gemini-1.5-flash is faster and more cost-effective
            # gemini-1.5-pro is more capable but slower
            model_names = ['gemini-2.5-flash']

            for model_name in model_names:
                try:
                    logger.info(f"Attempting to initialize Gemini model: {model_name}")
                    self.model = genai.GenerativeModel(model_name)
                    self.model_name = model_name
                    logger.info(f"Gemini AI model '{model_name}' initialized successfully")
                    break
                except Exception as e:
                    logger.warning(f"Failed to initialize Gemini model '{model_name}': {e}")
                    self.model = None
                    continue

            if not self.model:
                logger.error("Failed to initialize any Gemini model. AI will use fallback responses.")

    async def generate_response(self, user_message: str, conversation_context: List[Dict] = None) -> str:
        """
        Generate AI response using Gemini AI.

        Args:
            user_message: The user's message
            conversation_context: List of previous messages for context

        Returns:
            AI-generated response string
        """
        # If Gemini is not available, fall back to mock response
        if not self.model:
            logger.warning("Gemini model not available, using fallback response")
            responses = [
                f"I understand you said: {user_message}. Let me help you with survival guidance.",
                "That's an interesting question about survival. Here's what I think...",
                "Based on your message, I'd recommend considering the following survival tips...",
                "I can help you with that! In survival situations, it's important to...",
            ]
            await asyncio.sleep(0.5)
            return responses[hash(user_message) % len(responses)]

        try:
            # Build conversation history for context
            prompt_parts = []

            # Add system context for plant identification and information
            system_prompt = """You are a helpful AI assistant specialized in plant identification, edibility, medicinal uses, and outdoor plant knowledge.
Your primary role is to help users learn about plants they find in the wild, including:
- Identifying plants by their characteristics
- Determining if plants are edible or poisonous
- Explaining medicinal uses and traditional applications
- Providing safety warnings about toxic plants
- Sharing information about plant habitats, growth patterns, and uses

IMPORTANT SAFETY GUIDELINES:
- Always emphasize that users should NEVER consume plants without 100% certainty of identification
- Warn about lookalike plants that might be toxic
- Recommend consulting with local experts or field guides
- When in doubt, advise users to err on the side of caution

Keep your responses accurate, informative, and safety-focused. Be friendly and educational."""
            prompt_parts.append(system_prompt)

            # Get RAG context if available
            rag_context = ""
            if self.rag_service and self.rag_service.is_available():
                try:
                    rag_context = self.rag_service.get_rag_context(user_message, top_k=3)
                    if rag_context:
                        prompt_parts.append("\n" + rag_context)
                        prompt_parts.append("\nUse the above plant information to answer the user's question. If the information is relevant, cite it. If not, you can provide general guidance but mention that specific information about that plant may not be in the knowledge base.")
                except Exception as e:
                    logger.error(f"Error getting RAG context: {e}")

            # Add conversation context if available
            if conversation_context:
                # Reverse to get chronological order (oldest first)
                context_messages = conversation_context[::-1]
                for msg in context_messages[-10:]:  # Use last 10 messages for context
                    text = msg.get("text", "")
                    is_bot = msg.get("isBot", False)
                    if text:
                        if is_bot:
                            prompt_parts.append(f"Assistant: {text}")
                        else:
                            user_name = msg.get("userName", "User")
                            prompt_parts.append(f"{user_name}: {text}")

            # Add current user message
            prompt_parts.append(f"User: {user_message}")
            prompt_parts.append("Assistant:")

            # Join prompt parts with newlines for better formatting
            full_prompt = "\n".join(prompt_parts)

            # Generate response using Gemini
            # Run in executor to avoid blocking the event loop
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.model.generate_content(full_prompt)
            )

            # Extract text from response
            ai_response = response.text.strip() if response.text else "I'm sorry, I couldn't generate a response. Please try again."

            logger.info(f"Generated AI response for message: {user_message[:50]}...")
            return ai_response

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error generating AI response: {e}")

            # Check if it's a model not found error
            if "404" in error_msg or "not found" in error_msg.lower():
                logger.error(f"Model '{self.model_name}' not available. Please check your API key permissions or try a different model.")
                # Mark model as unavailable for future requests
                self.model = None

            # Fallback response on error
            return f"I apologize, but I encountered an error processing your message. Please try again. Your message was: {user_message[:100]}"


# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_conversations: Dict[str, List[str]] = {}  # userId -> [conversationIds]

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        logger.info(f"User {user_id} connected")

    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            logger.info(f"User {user_id} disconnected")

    async def send_personal_message(self, message: dict, user_id: str):
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].send_json(message)
            except Exception as e:
                logger.error(f"Error sending message to {user_id}: {e}")

    async def broadcast_to_conversation(self, message: dict, conversation_id: str, exclude_user: str = None):
        """Broadcast message to all users in a conversation"""
        conversation = await get_conversation(conversation_id)
        if not conversation:
            return

        participants = conversation.get("participants", [])
        for user_id in participants:
            if user_id != exclude_user and user_id in self.active_connections:
                try:
                    await self.active_connections[user_id].send_json(message)
                except Exception as e:
                    logger.error(f"Error broadcasting to {user_id}: {e}")


manager = ConnectionManager()
ai_service = AIService()  # Initialize with Gemini AI


@app.get("/")
async def root():
    return {"message": "IntoTheWild Chat API", "status": "running"}


@app.post("/api/rag/index-plants")
async def index_plants():
    """Index plant data from JSON into Pinecone vector database"""
    if not RAG_AVAILABLE or not rag_service:
        raise HTTPException(status_code=503, detail="RAG service not available")

    if not rag_service.is_available():
        raise HTTPException(
            status_code=503,
            detail="RAG service not fully configured. Please set AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, and PINECONE_API_KEY environment variables."
        )

    try:
        # Get the path to the plant data JSON file
        script_dir = Path(__file__).parent
        json_file_path = script_dir / "rag" / "all_plants_streaming.json"

        if not json_file_path.exists():
            raise HTTPException(status_code=404, detail=f"Plant data file not found: {json_file_path}")

        logger.info("Starting plant indexing process...")
        success = rag_service.load_and_index_plants(str(json_file_path))

        if success:
            return {
                "message": "Plants indexed successfully",
                "status": "success",
                "plants_cached": len(rag_service.plant_cache)
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to index plants. Check logs for details.")

    except Exception as e:
        logger.error(f"Error indexing plants: {e}")
        raise HTTPException(status_code=500, detail=f"Error indexing plants: {str(e)}")


@app.get("/api/rag/status")
async def rag_status():
    """Get RAG service status"""
    if not RAG_AVAILABLE or not rag_service:
        return {
            "available": False,
            "message": "RAG service not available"
        }

    return {
        "available": rag_service.is_available(),
        "index_name": rag_service.index_name if rag_service else None,
        "plants_cached": len(rag_service.plant_cache) if rag_service else 0,
        "message": "RAG service is ready" if rag_service.is_available() else "RAG service not fully configured"
    }

@app.get("/api/rag/test")
async def test_rag():
    """Test RAG service connectivity"""
    results = {
        "bedrock": {
            "available": False,
            "model": None,
            "test_embedding": None
        },
        "pinecone": {
            "available": False,
            "index_name": None,
            "vector_count": None
        }
    }

    # Test Bedrock
    if rag_service and rag_service.bedrock_runtime:
        try:
            test_embedding = rag_service._generate_embedding("test", input_type="search_query")
            results["bedrock"] = {
                "available": True,
                "model": rag_service.embedding_model,
                "test_embedding": f"Generated ({len(test_embedding)} dimensions)" if test_embedding else "Failed"
            }
        except Exception as e:
            results["bedrock"]["error"] = str(e)

    # Test Pinecone
    if rag_service and rag_service.index:
        try:
            stats = rag_service.index.describe_index_stats()
            results["pinecone"] = {
                "available": True,
                "index_name": rag_service.index_name,
                "vector_count": stats.total_vector_count,
                "dimension": stats.dimension
            }
        except Exception as e:
            results["pinecone"]["error"] = str(e)

    return results

@app.post("/api/users/register")
async def register_user(request: RegisterUserRequest):
    """Register a new user"""
    user_id = str(uuid.uuid4())
    user = {
        "id": user_id,
        "username": request.username,
        "email": request.email,
        "createdAt": datetime.utcnow().isoformat()
    }

    # Save to database
    if db:
        db.collection("users").document(user_id).set(user)
    else:
        users[user_id] = user

    return user


@app.post("/api/auth/google")
async def google_auth(request: dict = Body(...)):
    """Authenticate user with Google OAuth"""
    id_token_str = request.get("idToken")
    access_token_str = request.get("accessToken")

    # Handle None, empty string, or missing values
    id_token_str = id_token_str if id_token_str and str(id_token_str).strip() else None
    access_token_str = access_token_str if access_token_str and str(access_token_str).strip() else None

    if not id_token_str and not access_token_str:
        raise HTTPException(status_code=400, detail="ID token or access token is required")

    try:
        if not GOOGLE_CLIENT_ID:
            raise HTTPException(
                status_code=500,
                detail="Google OAuth not configured. Set GOOGLE_CLIENT_ID environment variable."
            )

        # Try to use ID token first (preferred method)
        if id_token_str:
            # Verify the ID token
            idinfo = id_token.verify_oauth2_token(
                id_token_str,
                google_requests.Request(),
                GOOGLE_CLIENT_ID
            )
            # Extract user info from ID token
            google_id = idinfo.get("sub")
            email = idinfo.get("email")
            name = idinfo.get("name", email.split("@")[0] if email else "User")
            picture = idinfo.get("picture")
        elif access_token_str:
            # Fallback: Use access token to get user info from Google API
            userinfo_response = http_requests.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token_str}"}
            )
            if userinfo_response.status_code != 200:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid access token"
                )
            userinfo = userinfo_response.json()
            google_id = userinfo.get("id")
            email = userinfo.get("email")
            name = userinfo.get("name", email.split("@")[0] if email else "User")
            picture = userinfo.get("picture")
        else:
            raise HTTPException(status_code=400, detail="ID token or access token is required")

        # Check if user exists (by email or Google ID)
        user = None
        user_id = None

        if db:
            # Check Firebase for existing user
            users_ref = db.collection("users")
            # Try to find by email first
            if email:
                email_query = users_ref.where("email", "==", email).limit(1).stream()
                for doc in email_query:
                    user = doc.to_dict()
                    user_id = doc.id
                    break

            # If not found, try to find by Google ID
            if not user:
                google_id_query = users_ref.where("googleId", "==", google_id).limit(1).stream()
                for doc in google_id_query:
                    user = doc.to_dict()
                    user_id = doc.id
                    break
        else:
            # In-memory: search by email or Google ID
            for uid, u in users.items():
                if u.get("email") == email or u.get("googleId") == google_id:
                    user = u.copy()
                    user_id = uid
                    break

        # Create or update user
        if user:
            # Update user info
            updates = {
                "email": email,
                "username": name,
                "googleId": google_id,
                "picture": picture,
                "lastLoginAt": datetime.utcnow().isoformat()
            }
            if db:
                db.collection("users").document(user_id).update(updates)
            else:
                users[user_id].update(updates)
            user.update(updates)
            user["id"] = user_id
        else:
            # Create new user
            user_id = str(uuid.uuid4())
            user = {
                "id": user_id,
                "username": name,
                "email": email,
                "googleId": google_id,
                "picture": picture,
                "createdAt": datetime.utcnow().isoformat(),
                "lastLoginAt": datetime.utcnow().isoformat()
            }

            if db:
                db.collection("users").document(user_id).set(user)
            else:
                users[user_id] = user

        return user

    except ValueError as e:
        # Invalid token
        logger.error(f"Invalid Google token: {e}")
        raise HTTPException(status_code=401, detail="Invalid Google token")
    except Exception as e:
        logger.error(f"Google auth error: {e}")
        raise HTTPException(status_code=500, detail=f"Authentication failed: {str(e)}")


@app.get("/api/users/{user_id}")
async def get_user(user_id: str):
    """Get user information"""
    if db:
        doc = db.collection("users").document(user_id).get()
        return doc.to_dict() if doc.exists else None
    else:
        return users.get(user_id)


@app.post("/api/conversations")
async def create_conversation(request: CreateConversationRequest):
    """Create a new conversation (1-to-1 or group) or return existing one-to-one conversation"""
    # For one-to-one conversations, check if a conversation already exists between these participants
    if request.type == "one_to_one" and len(request.participantIds) == 2:
        existing_conv = await find_conversation_by_participants(request.participantIds, "one_to_one")
        if existing_conv:
            logger.info(f"Found existing one-to-one conversation: {existing_conv['id']}")
            return existing_conv

    # Create new conversation
    conversation_id = str(uuid.uuid4())
    conversation = {
        "id": conversation_id,
        "name": request.name,
        "type": request.type,
        "participants": request.participantIds,
        "createdAt": datetime.utcnow().isoformat(),
        "hasBot": False
    }

    await save_conversation(conversation)

    # If it's a group, broadcast to all connected users so they can see it
    if request.type == "group":
        group_created_message = {
            "type": "group_created",
            "conversation": conversation
        }
        # Broadcast to all connected users
        for user_id in manager.active_connections.keys():
            await manager.send_personal_message(group_created_message, user_id)

    return conversation


@app.get("/api/conversations/{conversation_id}")
async def get_conversation_endpoint(conversation_id: str):
    """Get conversation details"""
    conversation = await get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@app.get("/api/conversations/{conversation_id}/messages")
async def get_messages_endpoint(conversation_id: str, limit: int = 50):
    """Get messages for a conversation"""
    messages = await get_messages(conversation_id, limit)
    return {"messages": messages}


@app.get("/api/conversations")
async def get_all_conversations(user_id: Optional[str] = Query(None, description="User ID to filter conversations")):
    """Get all conversations. For groups, return all groups. For one-to-one, return only user's conversations."""

    if db:
        # Get all conversations from Firebase
        convs_ref = db.collection("conversations")
        docs = convs_ref.stream()
        all_convs = [doc.to_dict() for doc in docs]
    else:
        # In-memory storage
        all_convs = list(conversations.values())

    # Filter: return all groups, but only one-to-one conversations where user is a participant
    if user_id:
        filtered_convs = [
            conv for conv in all_convs
            if conv.get("type") == "group" or (conv.get("type") == "one_to_one" and user_id in conv.get("participants", []))
        ]
    else:
        # If no user_id provided, return all groups only
        filtered_convs = [conv for conv in all_convs if conv.get("type") == "group"]

    return {"conversations": filtered_convs}


@app.post("/api/conversations/{conversation_id}/join")
async def join_group(conversation_id: str, user_id: str = Body(..., embed=True)):
    """Join a group conversation"""
    conversation = await get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if conversation.get("type") != "group":
        raise HTTPException(status_code=400, detail="Can only join group conversations")

    participants = conversation.get("participants", [])
    if user_id in participants:
        return {"message": "Already a member of this group", "conversation": conversation}

    # Add user to participants
    participants.append(user_id)
    await update_conversation(conversation_id, {"participants": participants})

    # Update local conversation object
    conversation["participants"] = participants

    # Broadcast join event to all group members
    join_message = {
        "type": "user_joined_group",
        "conversationId": conversation_id,
        "userId": user_id,
        "conversation": conversation
    }
    await manager.broadcast_to_conversation(join_message, conversation_id)

    return {"message": "Successfully joined group", "conversation": conversation}


@app.post("/api/conversations/{conversation_id}/leave")
async def leave_group(conversation_id: str, user_id: str = Body(..., embed=True)):
    """Leave a group conversation"""
    conversation = await get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if conversation.get("type") != "group":
        raise HTTPException(status_code=400, detail="Can only leave group conversations")

    participants = conversation.get("participants", [])
    if user_id not in participants:
        raise HTTPException(status_code=400, detail="User is not a member of this group")

    # Remove user from participants
    participants = [p for p in participants if p != user_id]
    await update_conversation(conversation_id, {"participants": participants})

    # Update local conversation object
    conversation["participants"] = participants

    # Broadcast leave event to all group members
    leave_message = {
        "type": "user_left_group",
        "conversationId": conversation_id,
        "userId": user_id,
        "conversation": conversation
    }
    await manager.broadcast_to_conversation(leave_message, conversation_id)

    return {"message": "Successfully left group", "conversation": conversation}


@app.post("/api/conversations/{conversation_id}/add-bot")
async def add_bot_to_conversation(conversation_id: str):
    """Add AI bot to a conversation"""
    conversation = await get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if conversation.get("hasBot"):
        return {"message": "Bot already in conversation", "hasBot": True}

    await update_conversation(conversation_id, {"hasBot": True})

    # Notify all participants
    bot_message = {
        "type": "bot_added",
        "conversationId": conversation_id,
        "message": "AI Bot has been added to the conversation",
        "timestamp": datetime.utcnow().isoformat()
    }

    await manager.broadcast_to_conversation(bot_message, conversation_id)

    return {"message": "Bot added successfully", "hasBot": True}


@app.post("/api/conversations/{conversation_id}/remove-bot")
async def remove_bot_from_conversation(conversation_id: str):
    """Remove AI bot from a conversation"""
    conversation = await get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if not conversation.get("hasBot"):
        return {"message": "Bot not in conversation", "hasBot": False}

    await update_conversation(conversation_id, {"hasBot": False})

    # Notify all participants
    bot_message = {
        "type": "bot_removed",
        "conversationId": conversation_id,
        "message": "AI Bot has been removed from the conversation",
        "timestamp": datetime.utcnow().isoformat()
    }

    await manager.broadcast_to_conversation(bot_message, conversation_id)

    return {"message": "Bot removed successfully", "hasBot": False}


@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """WebSocket endpoint for real-time messaging"""
    await manager.connect(websocket, user_id)

    try:
        while True:
            data = await websocket.receive_json()
            message_type = data.get("type")

            if message_type == "send_message":
                # Handle new message
                message_text = data.get("text", "").strip()
                conversation_id = data.get("conversationId")

                if not message_text or not conversation_id:
                    continue

                # Check if user is a participant in the conversation
                conversation = await get_conversation(conversation_id)
                if not conversation:
                    logger.warning(f"Conversation {conversation_id} not found")
                    continue

                participants = conversation.get("participants", [])
                if user_id not in participants:
                    logger.warning(f"User {user_id} is not a participant in conversation {conversation_id}")
                    await manager.send_personal_message({
                        "type": "error",
                        "message": "You are not a member of this conversation. Please join the group first."
                    }, user_id)
                    continue

                # Check for /bot command
                if message_text.startswith("/bot"):
                    # Extract the query part (everything after "/bot")
                    query_part = message_text[4:].strip()  # Remove "/bot" and any leading/trailing spaces

                    # Add bot to conversation if not already added
                    if not conversation.get("hasBot"):
                        await update_conversation(conversation_id, {"hasBot": True})

                        # Send notification
                        notification = {
                            "type": "bot_added",
                            "conversationId": conversation_id,
                            "message": "AI Bot has been added to the conversation",
                            "timestamp": datetime.utcnow().isoformat()
                        }
                        await manager.broadcast_to_conversation(notification, conversation_id)

                    # If there's a query after "/bot", process it as a message to the bot
                    if query_part:
                        # Update message_text to be the query part for bot processing
                        message_text = query_part
                        # Continue to normal message flow below, which will trigger bot response
                    else:
                        # Just "/bot" with no query, so just add bot and stop
                        continue

                # Check for /chat command
                if message_text == "/chat":
                    # Remove bot from conversation
                    if conversation.get("hasBot"):
                        await update_conversation(conversation_id, {"hasBot": False})

                        # Send notification
                        notification = {
                            "type": "bot_removed",
                            "conversationId": conversation_id,
                            "message": "AI Bot has been removed from the conversation",
                            "timestamp": datetime.utcnow().isoformat()
                        }
                        await manager.broadcast_to_conversation(notification, conversation_id)
                    continue

                # Create message
                message = {
                    "id": str(uuid.uuid4()),
                    "text": message_text,
                    "userId": user_id,
                    "userName": data.get("userName", "User"),
                    "conversationId": conversation_id,
                    "createdAt": datetime.utcnow().isoformat(),
                    "isBot": False,
                    "type": "text"
                }

                # Include clientMessageId if provided (for matching optimistic messages)
                client_message_id = data.get("clientMessageId")
                if client_message_id:
                    message["clientMessageId"] = client_message_id

                # Save message
                await save_message(message)

                # Broadcast to conversation participants
                await manager.broadcast_to_conversation({
                    "type": "new_message",
                    "message": message
                }, conversation_id, exclude_user=user_id)

                # Send confirmation to sender (include clientMessageId for matching)
                confirmation_message = {
                    "type": "message_sent",
                    "message": message
                }
                await manager.send_personal_message(confirmation_message, user_id)

                # Check if bot is in conversation and generate response
                conversation = await get_conversation(conversation_id)
                if conversation and conversation.get("hasBot"):
                    # Get recent messages for context
                    recent_messages = await get_messages(conversation_id, limit=10)

                    # Generate AI response
                    ai_response_text = await ai_service.generate_response(message_text, recent_messages)

                    # Create bot message
                    bot_message = {
                        "id": str(uuid.uuid4()),
                        "text": ai_response_text,
                        "userId": "bot",
                        "userName": "AI Bot",
                        "conversationId": conversation_id,
                        "createdAt": datetime.utcnow().isoformat(),
                        "isBot": True,
                        "type": "text"
                    }

                    # Save bot message
                    await save_message(bot_message)

                    # Broadcast bot response
                    await manager.broadcast_to_conversation({
                        "type": "new_message",
                        "message": bot_message
                    }, conversation_id)

            elif message_type == "join_conversation":
                # User joining a conversation
                conversation_id = data.get("conversationId")
                if conversation_id:
                    # Send recent messages
                    recent_messages = await get_messages(conversation_id, limit=50)
                    await manager.send_personal_message({
                        "type": "conversation_history",
                        "conversationId": conversation_id,
                        "messages": recent_messages
                    }, user_id)

            elif message_type == "get_all_groups":
                # User requesting all available groups
                # Get all conversations from database
                if db:
                    convs_ref = db.collection("conversations")
                    docs = convs_ref.stream()
                    all_convs = [doc.to_dict() for doc in docs]
                else:
                    all_convs = list(conversations.values())

                # Filter: return all groups, but only one-to-one conversations where user is a participant
                filtered_convs = [
                    conv for conv in all_convs
                    if conv.get("type") == "group" or (conv.get("type") == "one_to_one" and user_id in conv.get("participants", []))
                ]

                await manager.send_personal_message({
                    "type": "all_groups",
                    "conversations": filtered_convs
                }, user_id)

    except WebSocketDisconnect:
        manager.disconnect(user_id)
        logger.info(f"User {user_id} disconnected")
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
        manager.disconnect(user_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)

