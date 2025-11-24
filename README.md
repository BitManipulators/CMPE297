# IntoTheWild - Flutter Chat Application

A Flutter mobile chat application for survival guidance and plant recognition with offline-first capabilities, powered by AI and RAG (Retrieval-Augmented Generation).

## Prerequisites

### Frontend (Flutter)
1. **Flutter SDK**: Install Flutter from [flutter.dev](https://flutter.dev/docs/get-started/install)

### Backend (Python)
1. **Python 3.8+**: Required for the FastAPI backend
2. **API Keys** (see Environment Variables section below):
   - Google Gemini API key
   - AWS credentials (for Bedrock embeddings)
   - Pinecone API key (for vector database)
   - Firebase service account key

## Installation

### Frontend Setup

1. **Install Flutter** (if not already installed):
   ```bash
   # On macOS with Homebrew
   brew install --cask flutter

   # Or download from https://flutter.dev/docs/get-started/install
   ```

2. **Verify Flutter installation**:
   ```bash
   flutter doctor
   ```

3. **Get dependencies**:
   ```bash
   flutter pub get
   ```

4. **Run the app**:
   ```bash
   flutter run -d chrome --web-port=65103
   flutter run -d chrome --web-port=65107
   ```

### Backend Setup

1. **Navigate to backend directory**:
   ```bash
   cd backend
   ```

2. **Create a virtual environment** (recommended):
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables** (see Environment Variables section below)

5. **Configure Firebase**:
   - Place `serviceAccountKey.json` in the `backend/` directory
   - If not provided, the app will use in-memory storage

6. **Add plant data file**:
   - Ensure `all_plants_streaming.json` is present in `backend/rag/` directory
   - This file contains plant information for the RAG system
   - The file should be included in the repository or obtained separately

6. **Run the backend server**:
   ```bash
   python main.py
   ```

## Environment Variables

Create a `.env` file in the `backend/` directory with the following variables:

### Required Environment Variables

```env
# Google Gemini API Key (Required for AI bot functionality)
# Get your API key from: https://makersuite.google.com/app/apikey
GEMINI_API_KEY=your_gemini_api_key_here

# AWS Credentials (Required for RAG embeddings via Amazon Bedrock)
# Get your AWS credentials from: https://console.aws.amazon.com/
AWS_ACCESS_KEY_ID=your_aws_access_key_id_here
AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key_here

# AWS Region (Optional, defaults to us-west-2)
# Specify the AWS region where Bedrock is available
AWS_REGION=us-west-2

# Pinecone API Key (Required for vector database)
# Get your API key from: https://www.pinecone.io/
PINECONE_API_KEY=your_pinecone_api_key_here
```

### Setting Up Environment Variables

1. **Create `.env` file** in the `backend/` directory:
   ```bash
   cd backend
   touch .env
   ```

2. **Add your API keys** to the `.env` file:
   ```env
   GEMINI_API_KEY=your_actual_key_here
   AWS_ACCESS_KEY_ID=your_actual_key_here
   AWS_SECRET_ACCESS_KEY=your_actual_secret_here
   PINECONE_API_KEY=your_actual_key_here
   AWS_REGION=us-west-2
   ```

## Plant Data File (`all_plants_streaming.json`)

The RAG system requires a plant knowledge base file containing information about various plants.

### File Location
- **Path**: `backend/rag/all_plants_streaming.json`
- **Format**: JSON array containing plant objects

### File Structure
Each plant object in the JSON file should contain:
- `scientific_name`: Scientific name of the plant
- `common_name`: Common name(s) of the plant
- `family`: Plant family
- `genus`: Plant genus
- `summary`: Brief summary about the plant
- `content`: Detailed information about the plant
- `wikipedia_url`: (Optional) Link to Wikipedia page

### Setting Up the Plant Data File

1. **Ensure the file exists**:
   ```bash
   ls backend/rag/all_plants_streaming.json
   ```

2. **If the file is missing**, you need to:
   - Obtain the `all_plants_streaming.json` file
   - Place it in `backend/rag/` directory
   - The file should contain a JSON array of plant objects

3. **Index the plant data** (after setting up environment variables):
   ```bash
   cd backend
   python index_plants.py
   ```

   Or use the API endpoint:
   ```bash
   curl -X POST http://localhost:8001/api/rag/index-plants
   ```

## RAG System Setup

The RAG (Retrieval-Augmented Generation) system enhances AI responses with plant-specific knowledge.

### Initial Setup

1. **Ensure all environment variables are set** (see above)

2. **Verify plant data file exists**:
   ```bash
   ls backend/rag/all_plants_streaming.json
   ```

3. **Index the plant data**:
   ```bash
   cd backend
   python index_plants.py
   ```

4. **Verify RAG status**:
   ```bash
   curl http://localhost:8001/api/rag/status
   ```

   Expected response:
   ```json
   {
     "available": true,
     "index_name": "plant-knowledge-base-bedrock",
     "plants_cached": <number>,
     "message": "RAG service is ready"
   }
   ```

### How RAG Works

1. User asks a question about a plant
2. System searches Pinecone vector database for relevant plant information
3. Retrieved information is added to the AI prompt as context
4. Gemini AI generates a response using both retrieved data and general knowledge
5. User receives an accurate, context-aware response


### Adding AI Bot

Users can add the AI bot to a conversation by typing `/bot` in the chat. The bot will respond to subsequent messages with AI-generated responses enhanced by RAG context.

To remove the bot, type `/chat` in the conversation.


## Usage

### Frontend (Flutter App)

1. **Text Messages**: Type in the text input and press send
2. **Multi-User Chat**: Create or join conversations with other users
3. **AI Bot**: Type `/bot` to add AI assistance to any conversation
4. **Remove Bot**: Type `/chat` to remove bot and continue with normal conversation

### Backend

1. **Start the server**: `python main.py` or `uvicorn main:app --reload`
2. **Index plant data**: `python index_plants.py` (first time setup)
3. **Check RAG status**: `curl http://localhost:8001/api/rag/status`


### Testing RAG System

1. **Check status**:
   ```bash
   curl http://localhost:8001/api/rag/status
   ```

2. **Test connectivity**:
   ```bash
   curl http://localhost:8001/api/rag/test
   ```

3. **Index plants** (if not already indexed):
   ```bash
   curl -X POST http://localhost:8001/api/rag/index-plants
   ```
