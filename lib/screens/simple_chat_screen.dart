import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import '../services/chat_service.dart';
import '../services/notification_service.dart';
import '../services/analytics_service.dart';
import '../widgets/input_buttons.dart';
import '../widgets/chat_image_widget.dart';

class SimpleChatScreen extends StatefulWidget {
  const SimpleChatScreen({super.key});

  @override
  State<SimpleChatScreen> createState() => _SimpleChatScreenState();
}

class _SimpleChatScreenState extends State<SimpleChatScreen> {
  final TextEditingController _textController = TextEditingController();
  final ScrollController _scrollController = ScrollController();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      AnalyticsService.logScreenView('chat_screen');
    });
    // Update notification service to track current conversation
    final chatService = context.read<ChatService>();
    final notificationService = NotificationService();
    if (chatService.currentConversationId != null) {
      notificationService.setCurrentConversationId(chatService.currentConversationId);
      notificationService.cancelConversationNotifications(chatService.currentConversationId!);
    }
  }

  @override
  void dispose() {
    // Clear current conversation tracking when leaving chat screen
    final notificationService = NotificationService();
    notificationService.setCurrentConversationId(null);
    _textController.dispose();
    _scrollController.dispose();
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
          IconButton(
            icon: const Icon(Icons.clear_all),
            onPressed: () => _showClearDialog(),
            tooltip: 'Clear Chat',
          ),
        ],
      ),
      body: SafeArea(
        child: Column(
          children: [
            Expanded(
              child: Consumer<ChatService>(
                builder: (context, chatService, child) {
                  return ListView.builder(
                    controller: _scrollController,
                    padding: const EdgeInsets.all(16),
                    itemCount: chatService.messages.length,
                    itemBuilder: (context, index) {
                      final message = chatService.messages[index];
                      return _buildMessageBubble(message);
                    },
                  );
                },
              ),
            ),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
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
                  Expanded(
                    child: TextField(
                      controller: _textController,
                      decoration: InputDecoration(
                        hintText: "Type your message...",
                        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(25),
                          borderSide: const BorderSide(color: Color(0xFF2E7D32)),
                        ),
                        focusedBorder: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(25),
                          borderSide: const BorderSide(color: Color(0xFF2E7D32), width: 2),
                        ),
                      ),
                      onSubmitted: (text) => _sendMessage(),
                    ),
                  ),
                  const SizedBox(width: 8),
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
                      return IconButton(
                        onPressed: _sendMessage,
                        icon: const Icon(
                          Icons.send,
                          color: Color(0xFF2E7D32),
                        ),
                      );
                    },
                  ),
                ],
              ),
            ),
            const InputButtons(),
          ],
        ),
      ),
    );
  }

  Widget _buildMessageBubble(dynamic message) {
    final isUser = message.isUser;
    final isBot = message.isBot ?? false;
    final userName = message.userName ?? (isBot ? 'AI Bot' : 'User');
    final displayName = isBot ? 'AI Bot' : (isUser ? 'You' : userName);

    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      child: Row(
        mainAxisAlignment: isUser ? MainAxisAlignment.end : MainAxisAlignment.start,
        children: [
          if (!isUser) ...[
            CircleAvatar(
              radius: 16,
              backgroundColor: isBot ? const Color(0xFF2E7D32) : Colors.blue,
              child: Text(
                displayName[0].toUpperCase(),
                style: const TextStyle(color: Colors.white, fontSize: 12),
              ),
            ),
            const SizedBox(width: 8),
          ],
          Flexible(
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
              decoration: BoxDecoration(
                color: isUser ? const Color(0xFF2E7D32) : const Color(0xFFE8F5E8),
                borderRadius: BorderRadius.circular(20),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if (!isUser)
                    Text(
                      displayName,
                      style: TextStyle(
                        fontWeight: FontWeight.bold,
                        fontSize: 12,
                        color: isBot ? const Color(0xFF2E7D32) : Colors.blue,
                      ),
                    ),
                  if (message.imageUrl != null) ...[
                    ChatImageWidget(
                      imageUrl: message.imageUrl!,
                      width: 200,
                      height: 200,
                      fit: BoxFit.cover,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    const SizedBox(height: 8),
                  ],
                  isBot
                      ? MarkdownBody(
                          data: message.text,
                          styleSheet: MarkdownStyleSheet(
                            p: TextStyle(
                              color: Colors.black,
                              fontSize: 16,
                            ),
                            strong: TextStyle(
                              color: Colors.black,
                              fontSize: 16,
                              fontWeight: FontWeight.bold,
                            ),
                            em: TextStyle(
                              color: Colors.black,
                              fontSize: 16,
                              fontStyle: FontStyle.italic,
                            ),
                            listBullet: TextStyle(
                              color: Colors.black,
                              fontSize: 16,
                            ),
                            h1: TextStyle(
                              color: Colors.black,
                              fontSize: 20,
                              fontWeight: FontWeight.bold,
                            ),
                            h2: TextStyle(
                              color: Colors.black,
                              fontSize: 18,
                              fontWeight: FontWeight.bold,
                            ),
                            h3: TextStyle(
                              color: Colors.black,
                              fontSize: 16,
                              fontWeight: FontWeight.bold,
                            ),
                            code: TextStyle(
                              color: Colors.black87,
                              fontSize: 14,
                              fontFamily: 'monospace',
                            ),
                            codeblockDecoration: BoxDecoration(
                              color: Colors.grey[200],
                              borderRadius: BorderRadius.circular(4),
                            ),
                            blockquote: TextStyle(
                              color: Colors.black87,
                              fontSize: 16,
                              fontStyle: FontStyle.italic,
                            ),
                            blockquoteDecoration: BoxDecoration(
                              color: Colors.grey[100],
                              border: Border(
                                left: BorderSide(
                                  color: const Color(0xFF2E7D32),
                                  width: 4,
                                ),
                              ),
                            ),
                          ),
                        )
                      : Text(
                          message.text,
                          style: TextStyle(
                            color: isUser ? Colors.white : Colors.black,
                            fontSize: 16,
                          ),
                        ),
                  const SizedBox(height: 4),
                  Text(
                    _formatTime(message.createdAt),
                    style: TextStyle(
                      color: isUser ? Colors.white70 : Colors.grey[600],
                      fontSize: 12,
                    ),
                  ),
                ],
              ),
            ),
          ),
          if (isUser) ...[
            const SizedBox(width: 8),
            CircleAvatar(
              radius: 16,
              backgroundColor: const Color(0xFF2E7D32),
              child: const Text(
                'Y',
                style: TextStyle(color: Colors.white, fontSize: 12),
              ),
            ),
          ],
        ],
      ),
    );
  }

  String _formatTime(DateTime dateTime) {
    final now = DateTime.now();
    final difference = now.difference(dateTime);

    if (difference.inDays > 0) {
      return '${dateTime.day}/${dateTime.month} ${dateTime.hour}:${dateTime.minute.toString().padLeft(2, '0')}';
    } else if (difference.inHours > 0) {
      return '${difference.inHours}h ago';
    } else if (difference.inMinutes > 0) {
      return '${difference.inMinutes}m ago';
    } else {
      return 'Just now';
    }
  }

  void _sendMessage() {
    final text = _textController.text.trim();
    if (text.isNotEmpty) {
      context.read<ChatService>().sendTextMessage(text);
      _textController.clear();
      _scrollToBottom();
    }
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
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
}
