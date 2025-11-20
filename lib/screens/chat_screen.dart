import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:dash_chat_2/dash_chat_2.dart';
import '../services/chat_service.dart';
import '../widgets/input_buttons.dart';

class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key});

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final TextEditingController _textController = TextEditingController();

  @override
  void initState() {
    super.initState();
  }

  @override
  void dispose() {
    _textController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text(
          'IntoTheWild',
          style: TextStyle(
            fontWeight: FontWeight.bold,
            fontSize: 20,
          ),
        ),
        centerTitle: true,
        actions: [
          Consumer<ChatService>(
            builder: (context, chatService, child) {
              return IconButton(
                icon: Icon(
                  chatService.aiInitialized ? Icons.smart_toy : Icons.smart_toy_outlined,
                  color: chatService.aiInitialized ? Colors.green : Colors.orange,
                ),
                onPressed: () => _showAIStatusDialog(chatService),
                tooltip: chatService.aiInitialized ? 'AI Ready' : 'AI Loading...',
              );
            },
          ),
          IconButton(
            icon: const Icon(Icons.clear_all),
            onPressed: () => _showClearDialog(),
            tooltip: 'Clear Chat',
          ),
        ],
      ),
      body: Column(
        children: [
          Expanded(
            child: Consumer<ChatService>(
              builder: (context, chatService, child) {
                final dashMessages = chatService.messages
                    .map((message) => message.toDashChatMessage())
                    .toList();

                return DashChat(
                  messages: dashMessages,
                  onSend: (ChatMessage message) {
                    if (message.text.isNotEmpty) {
                      chatService.sendTextMessage(message.text);
                    }
                  },
                  currentUser: ChatUser(
                    id: "user",
                    firstName: "You",
                    profileImage: "https://i.pravatar.cc/150?img=1",
                  ),
                  inputOptions: const InputOptions(
                    sendOnEnter: true,
                    alwaysShowSend: true,
                    inputDecoration: InputDecoration(
                      hintText: "Type your message...",
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.all(Radius.circular(25)),
                      ),
                    ),
                  ),
                  messageOptions: MessageOptions(
                    showCurrentUserAvatar: true,
                    showOtherUsersAvatar: true,
                    showOtherUsersName: true,
                    currentUserContainerColor: const Color(0xFF2E7D32),
                    textColor: Colors.black,
                    currentUserTextColor: Colors.white,
                  ),
                );
              },
            ),
          ),
          const InputButtons(),
        ],
      ),
    );
  }

  void _showClearDialog() {
    showDialog(
      context: context,
      builder: (BuildContext context) {
        return AlertDialog(
          title: const Text('Clear Chat'),
          content: const Text('Are you sure you want to clear all messages?'),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('Cancel'),
            ),
            TextButton(
              onPressed: () {
                context.read<ChatService>().clearMessages();
                Navigator.of(context).pop();
              },
              child: const Text('Clear'),
            ),
          ],
        );
      },
    );
  }

  void _showAIStatusDialog(ChatService chatService) {
    showDialog(
      context: context,
      builder: (BuildContext context) {
        return AlertDialog(
          title: Row(
            children: [
              Icon(
                chatService.aiInitialized ? Icons.smart_toy : Icons.smart_toy_outlined,
                color: chatService.aiInitialized ? Colors.green : Colors.orange,
              ),
              const SizedBox(width: 8),
              Text(chatService.aiInitialized ? 'AI Ready' : 'AI Status'),
            ],
          ),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                chatService.aiInitialized
                  ? 'AI model is loaded and ready to help with survival guidance!'
                  : 'AI model is still loading. Please wait...',
                style: const TextStyle(fontSize: 16),
              ),
              if (!chatService.aiInitialized) ...[
                const SizedBox(height: 16),
                const LinearProgressIndicator(),
                const SizedBox(height: 8),
                const Text(
                  'This may take a few minutes on first launch.',
                  style: TextStyle(fontSize: 12, color: Colors.grey),
                ),
              ],
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('OK'),
            ),
          ],
        );
      },
    );
  }
}