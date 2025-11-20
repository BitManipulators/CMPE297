import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/auth_service.dart';
import '../services/conversation_service.dart';
import '../services/websocket_service.dart';
import '../services/chat_service.dart';
import '../models/conversation.dart';
import 'simple_chat_screen.dart';
import 'login_screen.dart';

class ConversationListScreen extends StatefulWidget {
  const ConversationListScreen({super.key});

  @override
  State<ConversationListScreen> createState() => _ConversationListScreenState();
}

class _ConversationListScreenState extends State<ConversationListScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _initializeServices();
    });
  }

  Future<void> _initializeServices() async {
    final authService = context.read<AuthService>();
    final user = authService.currentUser;

    if (user == null) {
      // Should not happen, but handle gracefully
      return;
    }

    // Connect WebSocket
    final webSocketService = context.read<WebSocketService>();
    await webSocketService.connect(user.id);

    // Initialize ChatService with services
    final chatService = context.read<ChatService>();
    chatService.initializeServices(
      webSocketService: webSocketService,
      conversationService: context.read<ConversationService>(),
      authService: authService,
    );
  }

  Future<void> _createConversation() async {
    final authService = context.read<AuthService>();
    final user = authService.currentUser;

    if (user == null) return;

    // Show dialog to create conversation
    final result = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (context) => _CreateConversationDialog(),
    );

    if (result != null) {
      try {
        final conversationService = context.read<ConversationService>();
        final conversation = await conversationService.createConversation(
          name: result['name'],
          type: result['type'],
          participantIds: [user.id, ...(result['participants'] as List<String>)],
        );

        if (mounted) {
          _openConversation(conversation);
        }
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Error creating conversation: $e')),
          );
        }
      }
    }
  }

  void _openConversation(Conversation conversation) {
    final chatService = context.read<ChatService>();
    final conversationService = context.read<ConversationService>();

    conversationService.setCurrentConversation(conversation);
    chatService.loadConversation(conversation.id);

    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => const SimpleChatScreen(),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final authService = context.watch<AuthService>();
    final user = authService.currentUser;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Conversations'),
        actions: [
          IconButton(
            icon: const Icon(Icons.logout),
            onPressed: () async {
              await authService.logout();
              final webSocketService = context.read<WebSocketService>();
              await webSocketService.disconnect();
              if (mounted) {
                Navigator.of(context).pushReplacement(
                  MaterialPageRoute(builder: (_) => const LoginScreen()),
                );
              }
            },
            tooltip: 'Logout',
          ),
        ],
      ),
      body: user == null
          ? const Center(child: CircularProgressIndicator())
          : Column(
              children: [
                Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Row(
                    children: [
                      CircleAvatar(
                        child: Text(user.username[0].toUpperCase()),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              user.username,
                              style: const TextStyle(
                                fontSize: 18,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            Text(
                              'User ID: ${user.id.substring(0, 8)}...',
                              style: const TextStyle(
                                fontSize: 12,
                                color: Colors.grey,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
                const Divider(),
                Expanded(
                  child: Consumer<ConversationService>(
                    builder: (context, conversationService, child) {
                      final conversations = conversationService.conversations;

                      if (conversations.isEmpty) {
                        return Center(
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              const Icon(
                                Icons.chat_bubble_outline,
                                size: 64,
                                color: Colors.grey,
                              ),
                              const SizedBox(height: 16),
                              const Text(
                                'No conversations yet',
                                style: TextStyle(
                                  fontSize: 18,
                                  color: Colors.grey,
                                ),
                              ),
                              const SizedBox(height: 8),
                              const Text(
                                'Create a new conversation to get started',
                                style: TextStyle(
                                  fontSize: 14,
                                  color: Colors.grey,
                                ),
                              ),
                            ],
                          ),
                        );
                      }

                      return ListView.builder(
                        itemCount: conversations.length,
                        itemBuilder: (context, index) {
                          final conversation = conversations[index];
                          return ListTile(
                            leading: CircleAvatar(
                              backgroundColor: const Color(0xFF2E7D32),
                              child: conversation.type == 'one_to_one'
                                  ? const Icon(Icons.person, color: Colors.white)
                                  : const Icon(Icons.group, color: Colors.white),
                            ),
                            title: Text(
                              conversation.name ??
                              (conversation.type == 'one_to_one'
                                  ? 'One-to-One Chat'
                                  : 'Group Chat'),
                            ),
                            subtitle: Text(
                              '${conversation.participants.length} participants${conversation.hasBot ? ' • AI Bot' : ''}',
                            ),
                            trailing: conversation.hasBot
                                ? const Icon(Icons.smart_toy, color: Color(0xFF2E7D32))
                                : null,
                            onTap: () => _openConversation(conversation),
                          );
                        },
                      );
                    },
                  ),
                ),
              ],
            ),
      floatingActionButton: FloatingActionButton(
        onPressed: _createConversation,
        backgroundColor: const Color(0xFF2E7D32),
        child: const Icon(Icons.add, color: Colors.white),
      ),
    );
  }
}

class _CreateConversationDialog extends StatefulWidget {
  @override
  State<_CreateConversationDialog> createState() => _CreateConversationDialogState();
}

class _CreateConversationDialogState extends State<_CreateConversationDialog> {
  final _nameController = TextEditingController();
  String _selectedType = 'group';
  final _participantController = TextEditingController();

  @override
  void dispose() {
    _nameController.dispose();
    _participantController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('New Conversation'),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: _nameController,
              decoration: const InputDecoration(
                labelText: 'Conversation Name (optional)',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 16),
            DropdownButtonFormField<String>(
              value: _selectedType,
              decoration: const InputDecoration(
                labelText: 'Type',
                border: OutlineInputBorder(),
              ),
              items: const [
                DropdownMenuItem(value: 'one_to_one', child: Text('One-to-One')),
                DropdownMenuItem(value: 'group', child: Text('Group')),
              ],
              onChanged: (value) {
                if (value != null) {
                  setState(() => _selectedType = value);
                }
              },
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _participantController,
              decoration: const InputDecoration(
                labelText: 'Participant IDs (comma-separated)',
                hintText: 'user-id-1, user-id-2',
                border: OutlineInputBorder(),
              ),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Cancel'),
        ),
        ElevatedButton(
          onPressed: () {
            final participants = _participantController.text
                .split(',')
                .map((e) => e.trim())
                .where((e) => e.isNotEmpty)
                .toList();

            Navigator.of(context).pop({
              'name': _nameController.text.trim().isEmpty
                  ? null
                  : _nameController.text.trim(),
              'type': _selectedType,
              'participants': participants,
            });
          },
          style: ElevatedButton.styleFrom(
            backgroundColor: const Color(0xFF2E7D32),
            foregroundColor: Colors.white,
          ),
          child: const Text('Create'),
        ),
      ],
    );
  }
}

