# IntoTheWild - Flutter Chat Application

A Flutter mobile chat application for survival guidance and plant recognition with offline-first capabilities.

## Features

- 📱 WhatsApp-style chat UI using custom implementation
- 🎙️ Voice input with speech-to-text
- 📷 Camera and gallery image input
- 💬 Text messaging with mock responses
- 🔄 Offline-first data persistence
- 🌿 Ready for AI integration (Gemma 3N + RAG)

## Prerequisites

1. **Flutter SDK**: Install Flutter from [flutter.dev](https://flutter.dev/docs/get-started/install)
2. **Android Studio**: For Android development
3. **Android SDK**: API level 21 or higher

## Installation

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
   cd /Users/aishwaryamurahari/Documents/study/CMPE297/SurvivalEdge
   flutter pub get
   ```

4. **Run the app**:
   ```bash
   flutter run
   ```

## Project Structure

```
lib/
├── main.dart                 # App entry point
├── models/
│   ├── chat_message.dart    # Message data model
│   └── chat_message.g.dart  # Generated JSON serialization
├── services/
│   ├── chat_service.dart    # Chat logic and state management
│   └── permission_service.dart # Permission handling
├── screens/
│   └── simple_chat_screen.dart # Main chat interface
└── widgets/
    └── input_buttons.dart   # Voice and camera input buttons
```

## Permissions

The app requires the following Android permissions:
- `RECORD_AUDIO` - For voice input
- `CAMERA` - For taking photos
- `READ_EXTERNAL_STORAGE` / `READ_MEDIA_IMAGES` - For accessing gallery
- `WRITE_EXTERNAL_STORAGE` - For saving chat data

## Usage

1. **Text Messages**: Type in the text input and press send
2. **Voice Input**: Tap the microphone button and speak
3. **Image Input**: Tap the camera button to take a photo or gallery button to select from gallery
4. **Clear Chat**: Use the clear button in the app bar to reset the conversation

## Current Features

- ✅ WhatsApp-style chat UI (custom implementation)
- ✅ Text input with send button
- ✅ Voice input (speech-to-text)
- ✅ Camera and gallery image input
- ✅ Mock response system
- ✅ Offline-first data persistence
- ✅ Permission handling

## Next Steps

This scaffold is ready for:
- Integration with Gemma 3N for local AI inference
- RAG (Retrieval Augmented Generation) for plant recognition
- Enhanced survival guidance responses
- Image analysis and plant identification

## Dependencies

- `image_picker` - Camera and gallery access
- `speech_to_text` - Voice input
- `flutter_tts` - Text-to-speech (ready for future use)
- `permission_handler` - Runtime permissions
- `path_provider` - File system access
- `provider` - State management

## Troubleshooting

If you encounter issues:

1. **Flutter not found**: Add Flutter to your PATH
   ```bash
   export PATH="$PATH:/path/to/flutter/bin"
   ```

2. **Permission denied**: Ensure all required permissions are granted in Android settings

3. **Build errors**: Run `flutter clean` and `flutter pub get`

4. **Dependencies issues**: Check that all packages are compatible with your Flutter version

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
