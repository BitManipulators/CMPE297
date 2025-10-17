import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';
import 'package:path_provider/path_provider.dart';
import 'package:speech_to_text/speech_to_text.dart';
import 'package:image_picker/image_picker.dart';
// import 'package:uuid/uuid.dart'; // Removed due to dependency issues
import '../models/chat_message.dart';
import 'ai_model_interface.dart';
import 'ai_model_service_web.dart';
import 'ai_model_service_android.dart';

class ChatService extends ChangeNotifier {
  final List<ChatMessage> _messages = [];
  final SpeechToText _speechToText = SpeechToText();
  final ImagePicker _imagePicker = ImagePicker();
  late final AIModelInterface _aiModelService;
  bool _isListening = false;
  bool _isLoading = false;

  List<ChatMessage> get messages => _messages;
  bool get isListening => _isListening;
  bool get isLoading => _isLoading;

  ChatService() {
    if (kIsWeb) {
      _aiModelService = AIModelServiceWeb();
    } else {
      _aiModelService = AIModelServiceAndroid();
    }
    _loadMessages();
    _initializeSpeech();
    _initializeAI();
  }

  Future<void> _initializeSpeech() async {
    await _speechToText.initialize();
  }

  Future<void> _initializeAI() async {
    await _aiModelService.initializeModel();
  }

  Future<void> _loadMessages() async {
    try {
      final directory = await getApplicationDocumentsDirectory();
      final file = File('${directory.path}/chat_messages.json');

      if (await file.exists()) {
        final contents = await file.readAsString();
        final List<dynamic> jsonList = json.decode(contents);
        _messages.clear();
        _messages.addAll(
          jsonList.map((json) => ChatMessage.fromJson(json)).toList(),
        );
        notifyListeners();
      }
    } catch (e) {
      debugPrint('Error loading messages: $e');
    }
  }

  Future<void> _saveMessages() async {
    try {
      final directory = await getApplicationDocumentsDirectory();
      final file = File('${directory.path}/chat_messages.json');

      final jsonList = _messages.map((message) => message.toJson()).toList();
      await file.writeAsString(json.encode(jsonList));
    } catch (e) {
      debugPrint('Error saving messages: $e');
    }
  }

  Future<void> sendTextMessage(String text) async {
    if (text.trim().isEmpty) return;

    final userMessage = ChatMessage(
      id: DateTime.now().millisecondsSinceEpoch.toString(),
      text: text.trim(),
      createdAt: DateTime.now(),
      isUser: true,
    );

    _messages.add(userMessage);
    notifyListeners();
    await _saveMessages();

    // Generate mock response
    await _generateMockResponse(userMessage);
  }

  Future<void> sendImageMessage(String imagePath) async {
    final userMessage = ChatMessage(
      id: DateTime.now().millisecondsSinceEpoch.toString(),
      text: "📷 Image shared",
      createdAt: DateTime.now(),
      isUser: true,
      imageUrl: imagePath,
      type: MessageType.image,
    );

    _messages.add(userMessage);
    notifyListeners();
    await _saveMessages();

    // Generate mock response for image
    await _generateImageResponse();
  }

  Future<void> _generateMockResponse(ChatMessage userMessage) async {
    _isLoading = true;
    notifyListeners();

    try {
      // Use AI model to generate intelligent response
      final aiResponse = await _aiModelService.generateResponse(userMessage.text);

      final botMessage = ChatMessage(
        id: DateTime.now().millisecondsSinceEpoch.toString(),
        text: aiResponse,
        createdAt: DateTime.now(),
        isUser: false,
      );

      _messages.add(botMessage);
    } catch (e) {
      debugPrint('Error generating AI response: $e');

      // Fallback to simple response if AI fails
      final fallbackMessage = ChatMessage(
        id: DateTime.now().millisecondsSinceEpoch.toString(),
        text: "I'm here to help with survival guidance and nature questions. What would you like to know?",
        createdAt: DateTime.now(),
        isUser: false,
      );

      _messages.add(fallbackMessage);
    }

    _isLoading = false;
    notifyListeners();
    await _saveMessages();
  }

  Future<void> _generateImageResponse() async {
    _isLoading = true;
    notifyListeners();

    try {
      // For now, provide a response about image analysis capabilities
      // In the next phase, we'll integrate actual image recognition
      final imageResponse = await _aiModelService.generateResponse("I've shared an image for analysis");

      final botMessage = ChatMessage(
        id: DateTime.now().millisecondsSinceEpoch.toString(),
        text: "📷 I can see you've shared an image! While I can provide general survival and nature guidance, detailed image analysis for plant/animal identification will be enhanced in the next update. For now, I can help with general outdoor safety and survival tips based on your description of what you see.",
        createdAt: DateTime.now(),
        isUser: false,
      );

      _messages.add(botMessage);
    } catch (e) {
      debugPrint('Error generating image response: $e');

      final fallbackMessage = ChatMessage(
        id: DateTime.now().millisecondsSinceEpoch.toString(),
        text: "📷 I can see your image! I'm ready to help with survival guidance and nature questions. Describe what you see and I'll provide relevant advice.",
        createdAt: DateTime.now(),
        isUser: false,
      );

      _messages.add(fallbackMessage);
    }

    _isLoading = false;
    notifyListeners();
    await _saveMessages();
  }

  Future<void> startListening() async {
    if (!_speechToText.isAvailable) return;

    _isListening = true;
    notifyListeners();

    await _speechToText.listen(
      onResult: (result) {
        if (result.finalResult) {
          _isListening = false;
          notifyListeners();

          if (result.recognizedWords.isNotEmpty) {
            sendTextMessage(result.recognizedWords);
          }
        }
      },
      listenFor: const Duration(seconds: 30),
      pauseFor: const Duration(seconds: 3),
      partialResults: true,
      localeId: "en_US",
      onSoundLevelChange: (level) {
        // Handle sound level changes if needed
      },
    );
  }

  Future<void> stopListening() async {
    await _speechToText.stop();
    _isListening = false;
    notifyListeners();
  }

  Future<String?> pickImageFromCamera() async {
    try {
      final XFile? image = await _imagePicker.pickImage(
        source: ImageSource.camera,
        imageQuality: 80,
      );
      return image?.path;
    } catch (e) {
      debugPrint('Error picking image from camera: $e');
      return null;
    }
  }

  Future<String?> pickImageFromGallery() async {
    try {
      final XFile? image = await _imagePicker.pickImage(
        source: ImageSource.gallery,
        imageQuality: 80,
      );
      return image?.path;
    } catch (e) {
      debugPrint('Error picking image from gallery: $e');
      return null;
    }
  }

  void clearMessages() {
    _messages.clear();
    notifyListeners();
    _saveMessages();
  }
}
