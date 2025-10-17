import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/chat_service.dart';
import '../services/permission_service.dart';

class InputButtons extends StatelessWidget {
  const InputButtons({super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
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
          Consumer2<ChatService, PermissionService>(
            builder: (context, chatService, permissionService, child) {
              return IconButton(
                onPressed: chatService.isListening
                    ? () => chatService.stopListening()
                    : () => _handleVoiceInput(context, chatService, permissionService),
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
          Consumer2<ChatService, PermissionService>(
            builder: (context, chatService, permissionService, child) {
              return IconButton(
                onPressed: () => _handleImageInput(context, chatService, permissionService),
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
          Consumer2<ChatService, PermissionService>(
            builder: (context, chatService, permissionService, child) {
              return IconButton(
                onPressed: () => _handleGalleryInput(context, chatService, permissionService),
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
    PermissionService permissionService,
  ) async {
    if (!await permissionService.checkMicrophonePermission()) {
      _showPermissionDialog(
        context,
        'Microphone Permission',
        'This app needs microphone permission to record voice messages.',
        () => permissionService.requestPermissions(),
      );
      return;
    }

    if (chatService.isListening) {
      await chatService.stopListening();
    } else {
      await chatService.startListening();
    }
  }

  Future<void> _handleImageInput(
    BuildContext context,
    ChatService chatService,
    PermissionService permissionService,
  ) async {
    if (!await permissionService.checkCameraPermission()) {
      _showPermissionDialog(
        context,
        'Camera Permission',
        'This app needs camera permission to take photos.',
        () => permissionService.requestPermissions(),
      );
      return;
    }

    final imagePath = await chatService.pickImageFromCamera();
    if (imagePath != null) {
      await chatService.sendImageMessage(imagePath);
    }
  }

  Future<void> _handleGalleryInput(
    BuildContext context,
    ChatService chatService,
    PermissionService permissionService,
  ) async {
    if (!await permissionService.checkStoragePermission()) {
      _showPermissionDialog(
        context,
        'Storage Permission',
        'This app needs storage permission to access photos.',
        () => permissionService.requestPermissions(),
      );
      return;
    }

    final imagePath = await chatService.pickImageFromGallery();
    if (imagePath != null) {
      await chatService.sendImageMessage(imagePath);
    }
  }

  void _showPermissionDialog(
    BuildContext context,
    String title,
    String message,
    VoidCallback onRequest,
  ) {
    showDialog(
      context: context,
      builder: (BuildContext context) {
        return AlertDialog(
          title: Text(title),
          content: Text(message),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('Cancel'),
            ),
            TextButton(
              onPressed: () {
                Navigator.of(context).pop();
                onRequest();
              },
              child: const Text('Grant Permission'),
            ),
          ],
        );
      },
    );
  }
}

