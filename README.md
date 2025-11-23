# IntoTheWild - Flutter Chat Application

A Flutter mobile chat application for survival guidance and plant recognition with offline-first capabilities.

## Features

- WhatsApp-style chat UI using custom implementation
- Voice input with speech-to-text
- Camera and gallery image input
- Text messaging with mock responses
- Offline-first data persistence
- Ready for AI integration (Gemma 3N + RAG)

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

- WhatsApp-style chat UI (custom implementation)
- Text input with send button
- Voice input (speech-to-text)
- Camera and gallery image input
- Mock response system
- Offline-first data persistence
- Permission handling

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