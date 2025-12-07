# IntoTheWild Chat Backend

FastAPI backend server for multi-user chat with AI support.

## Features

- Real-time messaging via WebSocket
- One-to-one and group conversations
- Shared AI bot powered by Google Gemini (add with `/bot` command)
- Firebase database support (with in-memory fallback)
- REST API for conversation management

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure Gemini AI (Required for AI bot functionality):
   - Get your Gemini API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Create a `.env` file in the backend directory
   - Add your API key: `GEMINI_API_KEY=your_api_key_here`
   - The AI bot will use mock responses if the API key is not configured

3. Configure Firebase:
   - Add your Firebase service account key as `serviceAccountKey.json` in the backend directory
   - Firebase will be automatically initialized if the key file is found

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
1. Firebase Firestore (primary) - automatically used if `serviceAccountKey.json` is present
2. In-memory storage (fallback) - used if Firebase is not configured

