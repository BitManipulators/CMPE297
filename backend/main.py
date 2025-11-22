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

# Firebase imports
try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    FIREBASE_AVAILABLE = True
except ImportError as e:
    FIREBASE_AVAILABLE = False
    print(f"Firebase not available, using in-memory storage. Import error: {e}")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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


# AI Service (shared AI for all users)
class AIService:
    """Shared AI service that generates responses"""

    @staticmethod
    async def generate_response(user_message: str, conversation_context: List[Dict] = None) -> str:
        """
        Generate AI response.
        In production, this would call your AI model (Gemma 3n or other)
        For now, returns a mock response
        """
        # TODO: Integrate with your AI model here
        # This could call the on-device model via API or use a server-side model

        responses = [
            f"I understand you said: {user_message}. Let me help you with survival guidance.",
            "That's an interesting question about survival. Here's what I think...",
            "Based on your message, I'd recommend considering the following survival tips...",
            "I can help you with that! In survival situations, it's important to...",
        ]

        # Simulate AI processing delay
        await asyncio.sleep(0.5)

        return responses[hash(user_message) % len(responses)]


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
ai_service = AIService()


@app.get("/")
async def root():
    return {"message": "IntoTheWild Chat API", "status": "running"}


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
                if message_text == "/bot":
                    # Add bot to conversation
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

