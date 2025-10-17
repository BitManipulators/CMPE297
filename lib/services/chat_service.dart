import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:path_provider/path_provider.dart';
import 'package:speech_to_text/speech_to_text.dart';
import 'package:image_picker/image_picker.dart';
// import 'package:uuid/uuid.dart'; // Removed due to dependency issues
import '../models/chat_message.dart';

class ChatService extends ChangeNotifier {
  final List<ChatMessage> _messages = [];
  final SpeechToText _speechToText = SpeechToText();
  final ImagePicker _imagePicker = ImagePicker();
  bool _isListening = false;
  bool _isLoading = false;

  List<ChatMessage> get messages => _messages;
  bool get isListening => _isListening;
  bool get isLoading => _isLoading;

  ChatService() {
    _loadMessages();
    _initializeSpeech();
  }

  Future<void> _initializeSpeech() async {
    await _speechToText.initialize();
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

    // Simulate processing delay
    await Future.delayed(const Duration(seconds: 1));

    final responses = [
      "You said: ${userMessage.text}",
      "Interesting! Tell me more about that.",
      "I understand you mentioned: ${userMessage.text}",
      "That's a great observation!",
      "I'm here to help with survival guidance. What else would you like to know?",
    ];

    final randomResponse = responses[DateTime.now().millisecond % responses.length];

    final botMessage = ChatMessage(
      id: DateTime.now().millisecondsSinceEpoch.toString(),
      text: randomResponse,
      createdAt: DateTime.now(),
      isUser: false,
    );

    _messages.add(botMessage);
    _isLoading = false;
    notifyListeners();
    await _saveMessages();
  }

  Future<void> _generateImageResponse() async {
    _isLoading = true;
    notifyListeners();

    await Future.delayed(const Duration(seconds: 2));

    final imageResponses = [
      "I can see you've shared an image! Once I'm connected to plant recognition, I'll be able to identify what you're looking at.",
      "📷 Nice image! I'm ready to help identify plants and provide survival tips once the AI is integrated.",
      "I see you've captured something interesting! The image recognition feature will be available soon.",
    ];

    final randomResponse = imageResponses[DateTime.now().millisecond % imageResponses.length];

    final botMessage = ChatMessage(
      id: DateTime.now().millisecondsSinceEpoch.toString(),
      text: randomResponse,
      createdAt: DateTime.now(),
      isUser: false,
    );

    _messages.add(botMessage);
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