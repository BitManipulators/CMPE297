# IntoTheWild Chat Backend

FastAPI backend server for multi-user chat with AI support.

## Features

- Real-time messaging via WebSocket
- One-to-one and group conversations
- Shared AI bot (add with `/bot` command)
- Firebase/Supabase database support (with in-memory fallback)
- REST API for conversation management

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. (Optional) Configure Firebase:
   - Add your Firebase service account key as `serviceAccountKey.json`
   - Uncomment Firebase initialization in `main.py`

3. (Optional) Configure Supabase:
   - Set environment variables or update `main.py` with your Supabase URL and key
   - Uncomment Supabase initialization in `main.py`

4. Run the server:
```bash
python main.py
```

Or with uvicorn:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## API Endpoints

### REST API

- `POST /api/users/register` - Register a new user
- `GET /api/users/{user_id}` - Get user information
- `POST /api/conversations` - Create a new conversation
- `GET /api/conversations/{conversation_id}` - Get conversation details
- `GET /api/conversations/{conversation_id}/messages` - Get conversation messages
- `POST /api/conversations/{conversation_id}/add-bot` - Add AI bot to conversation

### WebSocket

- `WS /ws/{user_id}` - WebSocket connection for real-time messaging

## WebSocket Message Types

### Client → Server

- `send_message`: Send a new message
  ```json
  {
    "type": "send_message",
    "text": "Hello!",
    "conversationId": "conv-id",
    "userName": "John"
  }
  ```

- `join_conversation`: Join a conversation and get history
  ```json
  {
    "type": "join_conversation",
    "conversationId": "conv-id"
  }
  ```

### Server → Client

- `new_message`: New message received
- `message_sent`: Confirmation of sent message
- `conversation_history`: Conversation message history
- `bot_added`: Bot added to conversation

## Adding AI Bot

Users can add the AI bot to a conversation by typing `/bot` in the chat.

## Database

The server supports:
1. Firebase Firestore (primary)
2. Supabase (fallback)
3. In-memory storage (development)

