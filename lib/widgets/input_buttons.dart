import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/chat_service.dart';

class InputButtons extends StatelessWidget {
  const InputButtons({super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
      decoration: BoxDecoration(
        color: Colors.white,
        boxShadow: [
          BoxShadow(
            color: Colors.grey.withOpacity(0.2),
            spreadRadius: 1,
            blurRadius: 5,
            offset: const Offset(0, -3),
          ),
        ],
      ),
      child: Row(
        children: [
          // Microphone Button
          Consumer<ChatService>(
            builder: (context, chatService, child) {
              return IconButton(
                onPressed: chatService.isListening
                    ? () => chatService.stopListening()
                    : () => _handleVoiceInput(context, chatService),
                icon: Icon(
                  chatService.isListening ? Icons.stop : Icons.mic,
                  color: chatService.isListening ? Colors.red : const Color(0xFF2E7D32),
                  size: 28,
                ),
                tooltip: chatService.isListening ? 'Stop Recording' : 'Voice Input',
              );
            },
          ),

          // Camera Button
          Consumer<ChatService>(
            builder: (context, chatService, child) {
              return IconButton(
                onPressed: () => _handleImageInput(context, chatService),
                icon: const Icon(
                  Icons.camera_alt,
                  color: Color(0xFF2E7D32),
                  size: 28,
                ),
                tooltip: 'Camera/Gallery',
              );
            },
          ),

          // Gallery Button
          Consumer<ChatService>(
            builder: (context, chatService, child) {
              return IconButton(
                onPressed: () => _handleGalleryInput(context, chatService),
                icon: const Icon(
                  Icons.photo_library,
                  color: Color(0xFF2E7D32),
                  size: 28,
                ),
                tooltip: 'Photo Gallery',
              );
            },
          ),

          const Spacer(),

          // Loading indicator
          Consumer<ChatService>(
            builder: (context, chatService, child) {
              if (chatService.isLoading) {
                return const SizedBox(
                  width: 20,
                  height: 20,
                  child: CircularProgressIndicator(
                    strokeWidth: 2,
                    valueColor: AlwaysStoppedAnimation<Color>(Color(0xFF2E7D32)),
                  ),
                );
              }
              return const SizedBox.shrink();
            },
          ),
        ],
      ),
    );
  }

  Future<void> _handleVoiceInput(
    BuildContext context,
    ChatService chatService,
  ) async {
    if (chatService.isListening) {
      await chatService.stopListening();
    } else {
      await chatService.startListening();
    }
  }

  Future<void> _handleImageInput(
    BuildContext context,
    ChatService chatService,
  ) async {
    // Image is already sent in pickImageFromCamera
    await chatService.pickImageFromCamera();
  }

  Future<void> _handleGalleryInput(
    BuildContext context,
    ChatService chatService,
  ) async {
    // Image is already sent in pickImageFromGallery
    await chatService.pickImageFromGallery();
  }
}
