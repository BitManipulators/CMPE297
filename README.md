# IntoTheWild - Flutter Chat Application

A Flutter mobile chat application for survival guidance and plant recognition powered by AI and RAG (Retrieval-Augmented Generation).

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
   - Google project Client ID (The same account used for firebase)

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

5. **Run on Android emulator**:
   ```bash
   flutter run -d emulator-(emulatorid)
   eg. flutter run -d emulator-5554
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

4. **Set up environment variables**

   - Create `.env` file:

   - Add your API keys to the `.env` file:
   ```env
   GEMINI_API_KEY=your_actual_key_here
   AWS_ACCESS_KEY_ID=your_actual_key_here
   AWS_SECRET_ACCESS_KEY=your_actual_secret_here
   PINECONE_API_KEY=your_actual_key_here
   AWS_REGION=us-west-2
   GOOGLE_CLIENT_ID=your_actual_client_id


5. **Configure Firebase (Creating serviceAccountKey.json for Firebase)**:
   - Go to the Firebase Console → Project Settings → Service Accounts.
   - Click "Generate new private key" under the Firebase Admin SDK section.
   - Confirm the prompt — a file named serviceAccountKey.json will be downloaded.
   - Place `serviceAccountKey.json` in the `backend/` directory
   - If not provided, the app will use in-memory storage

6. **Set up Google Project for SSO (Optional)**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Select the same project used for Firebase (or create a new project)
   - Navigate to **APIs & Services** → **Credentials**
   - Click **Create Credentials** → **OAuth client ID**
   - If prompted, configure the OAuth consent screen:
     - Choose **External** user type
     - Fill in app name, user support email, and developer contact
     - Add scopes: `email`, `profile`, `openid`
     - Add test users if needed
   - Create OAuth client IDs:
     - **For Web**:
       - Application type: **Web application**
       - Name: `IntoTheWild Web Client`
       - Authorized JavaScript origins:
         - `http://localhost:8001` (for local development)
         - `https://yourdomain.com` (for production)
       - Authorized redirect URIs:
         - `http://localhost:8001` (for local development)
         - `https://yourdomain.com` (for production)
       - Copy the **Client ID** (format: `xxxxx.apps.googleusercontent.com`)
     - **For Android** (if using Android app):
       - Application type: **Android**
       - Name: `IntoTheWild Android Client`
       - Package name: `com.example.into_the_wild`
       - SHA-1 certificate fingerprint: Get from `keytool -list -v -keystore ~/.android/debug.keystore -alias androiddebugkey -storepass android -keypass android`
       - Copy the **Client ID** (or use the one from `google-services.json`)
   - Add the Web Client ID to your backend `.env` file:
     ```env
     GOOGLE_CLIENT_ID=your_web_client_id_here.apps.googleusercontent.com
     ```
   - For Flutter web: Create a `.env` file in the project root with:
     ```env
     GOOGLE_CLIENT_ID=your_web_client_id_here.apps.googleusercontent.com
     ```

7. **Add plant data file**:
   - Ensure `plantae_wikipedia_content.json` and `animalia_wikipedia_content.json` are present in `backend/rag/` directory
   - This file contains plant information for the RAG system
   - The file should be included in the repository or obtained separately

8. **Run the backend server**:
   ```bash
   python main.py
   ```


## Generate Embeddings

The system uses AWS Bedrock with Cohere models to generate embeddings and stores them in Pinecone vector database.

### Prerequisites

1. **AWS Bedrock Access**: Ensure Cohere `embed-english-v3` model is available in your AWS Bedrock account
2. **Pinecone Account**: Create a Pinecone account and get your API key
3. **Environment Variables**: Set the following in your `.env` file:
   ```env
   AWS_ACCESS_KEY_ID=your_aws_access_key
   AWS_SECRET_ACCESS_KEY=your_aws_secret_key
   AWS_REGION=us-west-2
   PINECONE_API_KEY=your_pinecone_api_key
   ```

### How It Works

1. **AWS Bedrock**: Uses `cohere.embed-english-v3` model to generate 1024-dimensional embeddings
2. **Pinecone**: Stores embeddings in vector indexes for semantic search
3. **Index Names**:
   - Plants: `plant-knowledge-base-bedrock`
   - Animals: `animal-knowledge-base-bedrock`

### Indexing Plants

1. **Ensure data file exists**:
   ```bash
   ls backend/rag/plantae_wikipedia_content.json
   ```

2. **Run indexing script**:
   ```bash
   cd backend
   python index_plants.py
   ```

3. **The script will**:
   - Load plant data from `plantae_wikipedia_content.json`
   - Generate embeddings using AWS Bedrock (Cohere)
   - Store embeddings in Pinecone index `plant-knowledge-base-bedrock`
   - Process in batches of 100

### Indexing Animals

1. **Ensure data file exists**:
   ```bash
   ls backend/rag/animalia_wikipedia_content.json
   ```

2. **Run indexing script**:
   ```bash
   cd backend
   python index_animals.py
   ```

3. **The script will**:
   - Load animal data from `animalia_wikipedia_content.json`
   - Generate embeddings using AWS Bedrock (Cohere)
   - Store embeddings in Pinecone index `animal-knowledge-base-bedrock`
   - Process in batches of 100

## RAG System Setup

The RAG (Retrieval-Augmented Generation) system enhances AI responses with plant-specific knowledge.

### Initial Setup

1. **Ensure all environment variables are set** (see above)

2. **Verify plant data file exists**:
   ```bash
   ls backend/rag/plantae_wikipedia_content.json
   ls ls backend/rag/animalia_wikipedia_content.json
   ```

3. **Verify RAG status**:
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

   {
     "available": true,
     "index_name": "animal-knowledge-base-bedrock",
     "animals_cached": <number>,
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
2. **Multi-User Chat**: Create or join conversations with other users (Refer to **Testing Multi-User Conversations** section for more details)
3. **AI Bot**: Type `/bot` to add AI assistance to any conversation
4. **Remove Bot**: Type `/chat` to remove bot and continue with normal conversation

### Testing Multi-User Conversations

#### One-to-One Chat

1. **Get User ID**:
   - Open the app in a web browser
   - Right-click and select **Inspect** (or press F12)
   - Open the **Console** tab in Developer Tools
   - Look for `userID` in the console logs or network requests
   - Copy the user ID

2. **Create One-to-One Conversation**:
   - Click the **+** button to create a new conversation
   - Select **One-to-One** as the conversation type
   - In the **Participant IDs** field, enter the other user's ID (comma-separated if multiple)
   - Click **Create**
   - The conversation will connect both users

**Note**: Adding a user ID in the participant ID box is **mandatory** for one-to-one chats.

#### Group Chat

1. **Create Group Chat**:
   - Click the **+** button to create a new conversation
   - Select **Group** as the conversation type
   - Enter a **Group Name** (required)
   - Click **Create**
   - The group will be visible to all users who can join it

2. **Join Group Chat**:
   - Other users can see available groups in the conversation list
   - Click on a group to join and start chatting

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

## Deployment Guide: Flutter Web + FastAPI on AWS EKS

**Architecture Overview**

    Infrastructure: AWS EKS (managed via Terraform).

    Ingress: NGINX Ingress Controller + AWS Network Load Balancer (NLB).

    DNS & SSL: Cloudflare (managing DNS + SSL) → AWS NLB.

    Frontend: Flutter Web (served via Nginx container).

    Backend: FastAPI (Python).

    Registry: AWS ECR (Elastic Container Registry).

**Prerequisites**

    AWS CLI installed and configured (aws configure).

    Terraform installed.

    Docker installed and running.

    Kubectl installed.

    Domain Name: Purchased (e.g., Namecheap) and added to Cloudflare.

### Phase 1: Infrastructure (Terraform)

1. Initialize terraform
```
terraform init
```

2. Create terraform.tfvars
```
aws_region   = "us-west-2"  # or your preferred region
cluster_name = "eks-into-the-wild"
vpc_cidr     = "10.0.0.0/16"

node_instance_types = ["t3.medium"]
node_desired_size   = 1
node_min_size       = 1
node_max_size       = 3

# Cloudflare Origin Certificate (SSL/TLS > Origin Server)
tls_crt = <<EOT
-----BEGIN CERTIFICATE-----
... paste your cloudflare cert here ...
-----END CERTIFICATE-----
EOT

tls_key = <<EOT
-----BEGIN PRIVATE KEY-----
... paste your cloudflare key here ...
-----END PRIVATE KEY-----
EOT
```

3. Apply infrastructure
```
terraform apply
# Type 'yes' to confirm
```

4. Get the Load Balancer URL
```
kubectl get svc -n ingress-nginx
```

5. Update Cloudflare DNS:

    Log in to Cloudflare.

    Create a CNAME record for @ (root) pointing to the AWS Address.

    Create a CNAME record for www pointing to the AWS Address.

    Important: Ensure the "Proxy Status" is Proxied (Orange Cloud).

    SSL Mode: Set SSL/TLS to Full (Strict).

### Phase 2: Build & Deploy Applications

1. Login to AWS ECR

```
aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin <YOUR-ACCOUNT-ID>.dkr.ecr.us-west-2.amazonaws.com
```

2. Deploy Backend

```
# Variables
export ACCOUNT_ID=123456789012 # Replace with your ID
export REGION=us-west-2        # Replace with your region
export REPO_URL=$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/fastapi-backend

# Build
docker build -t $REPO_URL:v1 .

# Push
docker push $REPO_URL:v1
```

3. Deploy Frontend (Flutter)

```
# Variables
export REPO_URL=$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/flutter-web-app
export BACKEND_BASE_URL=https://iotsmarthome.org/api
export WEBSOCKET_BASE_URL=wss://iotsmarthome.org/api

# Build (Injects the URL into the JS bundle)
docker build \
  --build-arg BACKEND_BASE_URL_ARG=$BACKEND_BASE_URL \
  --build-arg WEBSOCKET_BASE_URL_ARG=$WEBSOCKET_BASE_URL \
  -t $REPO_URL:v1 .

# Push
docker push $REPO_URL:v1
```

### Phase 3: Verification

Check ingress-nginx logs
```
kubectl logs -n ingress-nginx -l app.kubernetes.io/name=ingress-nginx -f
```

Check running pods
```
kubectl get pods
# Should show 2/2 running for frontend and 1/1 for backend
```
