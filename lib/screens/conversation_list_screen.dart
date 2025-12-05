import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import '../services/auth_service.dart';
import '../services/conversation_service.dart';
import '../services/websocket_service.dart';
import '../services/chat_service.dart';
import '../services/notification_service.dart';
import '../services/analytics_service.dart';
import '../models/conversation.dart';
import '../widgets/input_buttons.dart';
import '../widgets/chat_image_widget.dart';
import 'simple_chat_screen.dart';
import 'login_screen.dart';

class ConversationListScreen extends StatefulWidget {
  const ConversationListScreen({super.key});

  @override
  State<ConversationListScreen> createState() => _ConversationListScreenState();
}

class _ConversationListScreenState extends State<ConversationListScreen> {
  final TextEditingController _messageController = TextEditingController();
  final ScrollController _chatScrollController = ScrollController();
  bool _hasAutoSelectedConversation = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      AnalyticsService.logScreenView('conversation_list_screen');
      _initializeServices();
    });
  }

  Widget _buildConversationSidebar(AuthService authService, dynamic user, bool isWideLayout) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        border: isWideLayout
            ? const Border(
                right: BorderSide(color: Color(0xFFE0E0E0)),
              )
            : null,
      ),
      child: Column(
        children: [
          _buildUserHeader(user, isWideLayout),
          const Divider(height: 1),
          Expanded(
            child: _buildConversationListSection(authService, user, isWideLayout),
          ),
        ],
      ),
    );
  }

  Widget _buildUserHeader(dynamic user, bool isWideLayout) {
    return Container(
      color: isWideLayout ? const Color(0xFF1B5E20) : Colors.transparent,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 20),
      child: Row(
        children: [
          CircleAvatar(
            backgroundColor: isWideLayout ? Colors.white : const Color(0xFF2E7D32),
            foregroundColor: isWideLayout ? const Color(0xFF1B5E20) : Colors.white,
            child: Text(user.username[0].toUpperCase()),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  user.username,
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                    color: isWideLayout ? Colors.white : Colors.black,
                  ),
                ),
                Text(
                  'User ID: ${user.id.substring(0, 8)}...',
                  style: TextStyle(
                    fontSize: 12,
                    color: isWideLayout ? Colors.white70 : Colors.grey,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildConversationListSection(AuthService authService, dynamic user, bool isWideLayout) {
    return Consumer<ConversationService>(
      builder: (context, conversationService, child) {
        final conversations = conversationService.conversations;

        if (isWideLayout &&
            !_hasAutoSelectedConversation &&
            conversations.isNotEmpty &&
            conversationService.currentConversation == null) {
          WidgetsBinding.instance.addPostFrameCallback((_) {
            if (mounted) {
              _hasAutoSelectedConversation = true;
              _openConversation(conversations.first, stayOnScreen: true);
            }
          });
        }

        if (conversations.isEmpty) {
          return _buildEmptyConversationState();
        }

        return ListView.separated(
          padding: const EdgeInsets.symmetric(vertical: 8),
          itemCount: conversations.length,
          separatorBuilder: (context, index) => const Divider(height: 1, indent: 72),
          itemBuilder: (context, index) {
            final conversation = conversations[index];
            final isGroup = conversation.type == 'group';
            final isParticipant = conversation.participants.contains(user.id);

            if (!isGroup && conversation.participants.length == 2) {
              final otherParticipantId = conversation.participants.firstWhere(
                (id) => id != user.id,
                orElse: () => '',
              );
              if (otherParticipantId.isNotEmpty && !conversationService.usernameCache.containsKey(otherParticipantId)) {
                _getOtherParticipantUsername(conversation, user.id).then((username) {
                  if (mounted && username != null) {
                    setState(() {});
                  }
                });
              }
            }

            final isSelected = conversationService.currentConversation?.id == conversation.id;

            return Consumer<NotificationService>(
              builder: (context, notificationService, child) {
                final unreadCount = notificationService.getUnreadCount(conversation.id);

                return ListTile(
                  contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
                  selected: isWideLayout && isSelected,
                  selectedTileColor: const Color(0xFFE8F5E9),
                  leading: CircleAvatar(
                    backgroundColor: const Color(0xFF2E7D32),
                    child: conversation.type == 'one_to_one'
                        ? const Icon(Icons.person, color: Colors.white)
                        : const Icon(Icons.group, color: Colors.white),
                  ),
                  title: Row(
                    children: [
                      Expanded(
                        child: Text(
                          _getConversationDisplayName(conversation, user.id),
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                      if (unreadCount > 0)
                        Container(
                          margin: const EdgeInsets.only(left: 8),
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                          decoration: BoxDecoration(
                            color: Colors.red,
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: Text(
                            unreadCount > 99 ? '99+' : unreadCount.toString(),
                            style: const TextStyle(
                              color: Colors.white,
                              fontSize: 12,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ),
                    ],
                  ),
                  subtitle: Text(
                    '${conversation.participants.length} participants${conversation.hasBot ? ' • AI Bot' : ''}',
                  ),
                  trailing: isGroup
                      ? Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            if (conversation.hasBot)
                              const Icon(Icons.smart_toy, color: Color(0xFF2E7D32)),
                            const SizedBox(width: 8),
                            if (isParticipant)
                              IconButton(
                                icon: const Icon(Icons.exit_to_app, color: Colors.red),
                                onPressed: () => _leaveGroup(conversation),
                                tooltip: 'Leave group',
                              )
                            else
                              ElevatedButton.icon(
                                onPressed: () => _joinGroup(conversation),
                                icon: const Icon(Icons.person_add, size: 16),
                                label: const Text('Join'),
                                style: ElevatedButton.styleFrom(
                                  backgroundColor: const Color(0xFF2E7D32),
                                  foregroundColor: Colors.white,
                                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                                ),
                              ),
                          ],
                        )
                      : (conversation.hasBot ? const Icon(Icons.smart_toy, color: Color(0xFF2E7D32)) : null),
                  onTap: isGroup && !isParticipant
                      ? () => _joinGroup(conversation)
                      : () => _openConversation(conversation, stayOnScreen: isWideLayout),
                );
              },
            );
          },
        );
      },
    );
  }

  Widget _buildEmptyConversationState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: const [
          Icon(
            Icons.chat_bubble_outline,
            size: 64,
            color: Colors.grey,
          ),
          SizedBox(height: 16),
          Text(
            'No conversations yet',
            style: TextStyle(
              fontSize: 18,
              color: Colors.grey,
            ),
          ),
          SizedBox(height: 8),
          Text(
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

  Widget _buildChatPane() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
      child: Consumer<ConversationService>(
        builder: (context, conversationService, child) {
          final conversation = conversationService.currentConversation;

          if (conversation == null) {
            return _buildEmptyChatState();
          }

          return Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              _buildChatHeader(conversation),
              const SizedBox(height: 12),
              Expanded(child: _buildChatMessages()),
              _buildMessageInput(),
              const SizedBox(height: 8),
              const InputButtons(),
            ],
          );
        },
      ),
    );
  }

  Widget _buildChatHeader(Conversation conversation) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.05),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Row(
        children: [
          CircleAvatar(
            backgroundColor: const Color(0xFF2E7D32),
            radius: 22,
            child: conversation.type == 'one_to_one'
                ? const Icon(Icons.person, color: Colors.white)
                : const Icon(Icons.group, color: Colors.white),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  _getConversationDisplayName(conversation, context.read<AuthService>().currentUser?.id),
                  style: const TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                Text(
                  '${conversation.participants.length} participants${conversation.hasBot ? ' • AI Bot' : ''}',
                  style: const TextStyle(
                    fontSize: 13,
                    color: Colors.grey,
                  ),
                ),
              ],
            ),
          ),
          if (conversation.hasBot)
            const Icon(
              Icons.smart_toy,
              color: Color(0xFF2E7D32),
            ),
        ],
      ),
    );
  }

  Widget _buildChatMessages() {
    return Consumer<ChatService>(
      builder: (context, chatService, child) {
        final messages = chatService.messages;

        if (messages.isEmpty) {
          return const Center(
            child: Text(
              'No messages yet. Say hello!',
              style: TextStyle(color: Colors.grey),
            ),
          );
        }

        return ListView.builder(
          controller: _chatScrollController,
          padding: const EdgeInsets.symmetric(vertical: 16),
          itemCount: messages.length,
          itemBuilder: (context, index) {
            final message = messages[index];
            return _buildChatMessageBubble(message);
          },
        );
      },
    );
  }

  Widget _buildMessageInput() {
    return Container(
      margin: const EdgeInsets.symmetric(vertical: 12),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(32),
        border: Border.all(color: const Color(0xFF2E7D32).withOpacity(0.3)),
      ),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: _messageController,
              decoration: const InputDecoration(
                hintText: "Type your message...",
                border: InputBorder.none,
              ),
              onSubmitted: (_) => _sendMessage(),
            ),
          ),
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
                icon: const Icon(Icons.send, color: Color(0xFF2E7D32)),
              );
            },
          ),
        ],
      ),
    );
  }

  Widget _buildChatMessageBubble(dynamic message) {
    final bool isUser = message.isUser ?? false;
    final bool isBot = message.isBot ?? false;
    final String userName = message.userName ?? (isBot ? 'AI Bot' : 'User');
    final String displayName = isBot ? 'AI Bot' : (isUser ? 'You' : userName);

    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      child: Row(
        mainAxisAlignment: isUser ? MainAxisAlignment.end : MainAxisAlignment.start,
        crossAxisAlignment: CrossAxisAlignment.start,
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
                    const SizedBox(height: 8),
                    ChatImageWidget(
                      imageUrl: message.imageUrl!,
                      width: 240,
                      height: 240,
                      fit: BoxFit.cover,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    const SizedBox(height: 8),
                  ],
                  isBot
                      ? MarkdownBody(
                          data: message.text ?? '',
                          styleSheet: MarkdownStyleSheet(
                            p: TextStyle(
                              color: Colors.black87,
                              fontSize: 16,
                            ),
                            strong: TextStyle(
                              color: Colors.black87,
                              fontSize: 16,
                              fontWeight: FontWeight.bold,
                            ),
                            em: TextStyle(
                              color: Colors.black87,
                              fontSize: 16,
                              fontStyle: FontStyle.italic,
                            ),
                            listBullet: TextStyle(
                              color: Colors.black87,
                              fontSize: 16,
                            ),
                            h1: TextStyle(
                              color: Colors.black87,
                              fontSize: 20,
                              fontWeight: FontWeight.bold,
                            ),
                            h2: TextStyle(
                              color: Colors.black87,
                              fontSize: 18,
                              fontWeight: FontWeight.bold,
                            ),
                            h3: TextStyle(
                              color: Colors.black87,
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
                          message.text ?? '',
                          style: TextStyle(
                            color: isUser ? Colors.white : Colors.black87,
                            fontSize: 16,
                          ),
                        ),
                  const SizedBox(height: 4),
                  Text(
                    _formatMessageTime(message.createdAt),
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

  Widget _buildEmptyChatState() {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: const [
          Icon(Icons.chat_outlined, size: 64, color: Colors.grey),
          SizedBox(height: 16),
          Text(
            'Select a conversation to start chatting',
            style: TextStyle(fontSize: 18, color: Colors.grey),
          ),
        ],
      ),
    );
  }

  String _formatMessageTime(DateTime? dateTime) {
    if (dateTime == null) return '';
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
    final text = _messageController.text.trim();
    if (text.isEmpty) return;
    context.read<ChatService>().sendTextMessage(text);
    _messageController.clear();
    _scrollChatToBottom();
  }

  void _scrollChatToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_chatScrollController.hasClients) {
        _chatScrollController.animateTo(
          _chatScrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  @override
  void dispose() {
    _messageController.dispose();
    _chatScrollController.dispose();
    super.dispose();
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

    // Load all conversations (including available groups)
    final conversationService = context.read<ConversationService>();
    await conversationService.getAllConversations(user.id);

    // Preload usernames for one-to-one conversations
    _preloadUsernames(conversationService, user.id);

    // Also request groups via WebSocket for real-time updates
    webSocketService.requestAllGroups();
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
          participantIds: result['type'] == 'group'
              ? [user.id] // For groups, only creator is initially a participant
              : [user.id, ...(result['participants'] as List<String>)],
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

  Future<void> _joinGroup(Conversation group) async {
    final authService = context.read<AuthService>();
    final user = authService.currentUser;

    if (user == null) return;

    try {
      final conversationService = context.read<ConversationService>();
      final updatedGroup = await conversationService.joinGroup(group.id, user.id);

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Successfully joined group')),
        );
        // Automatically open the conversation after joining
        _openConversation(updatedGroup);
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error joining group: $e')),
        );
      }
    }
  }

  void _preloadUsernames(ConversationService conversationService, String currentUserId) {
    // Load usernames for all one-to-one conversations
    for (final conversation in conversationService.conversations) {
      if (conversation.type == 'one_to_one' && conversation.participants.length == 2) {
        final otherParticipantId = conversation.participants.firstWhere(
          (id) => id != currentUserId,
          orElse: () => '',
        );
        if (otherParticipantId.isNotEmpty &&
            !conversationService.usernameCache.containsKey(otherParticipantId)) {
          _getOtherParticipantUsername(conversation, currentUserId);
        }
      }
    }
  }

  Future<void> _leaveGroup(Conversation group) async {
    final authService = context.read<AuthService>();
    final user = authService.currentUser;

    if (user == null) return;

    try {
      final conversationService = context.read<ConversationService>();
      await conversationService.leaveGroup(group.id, user.id);

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Successfully left group')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error leaving group: $e')),
        );
      }
    }
  }

  Future<String?> _getOtherParticipantUsername(Conversation conversation, String currentUserId) async {
    if (conversation.type != 'one_to_one') return null;

    // Find the other participant (not the current user)
    final otherParticipantId = conversation.participants.firstWhere(
      (id) => id != currentUserId,
      orElse: () => '',
    );

    if (otherParticipantId.isEmpty) return null;

    // Check cache in conversation service first
    final conversationService = context.read<ConversationService>();
    if (conversationService.usernameCache.containsKey(otherParticipantId)) {
      return conversationService.usernameCache[otherParticipantId];
    }

    // Fetch username from API
    try {
      final authService = context.read<AuthService>();
      final otherUser = await authService.getUser(otherParticipantId);
      if (otherUser != null) {
        conversationService.updateUsernameCache(otherParticipantId, otherUser.username);
        return otherUser.username;
      }
    } catch (e) {
      debugPrint('Error fetching username for $otherParticipantId: $e');
    }

    return null;
  }

  String _getConversationDisplayName(Conversation conversation, String? currentUserId) {
    if (conversation.name != null && conversation.name!.isNotEmpty) {
      return conversation.name!;
    }

    if (conversation.type == 'group') {
      return 'Group Chat';
    }

    // For one-to-one chats, try to get the other participant's username
    if (currentUserId != null && conversation.participants.length == 2) {
      final conversationService = context.read<ConversationService>();
      final otherParticipantId = conversation.participants.firstWhere(
        (id) => id != currentUserId,
        orElse: () => '',
      );

      if (otherParticipantId.isNotEmpty && conversationService.usernameCache.containsKey(otherParticipantId)) {
        return conversationService.usernameCache[otherParticipantId]!;
      }
    }

    return 'One-to-One Chat';
  }

  void _openConversation(Conversation conversation, {bool stayOnScreen = false}) {
    final chatService = context.read<ChatService>();
    final conversationService = context.read<ConversationService>();
    final notificationService = context.read<NotificationService>();

    conversationService.setCurrentConversation(conversation);
    chatService.loadConversation(conversation.id);
    // Update notification service to track current conversation
    // This will also clear the unread count for this conversation
    notificationService.setCurrentConversationId(conversation.id);
    // Cancel any notifications for this conversation
    notificationService.cancelConversationNotifications(conversation.id);

    if (stayOnScreen) {
      return;
    }

    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => const SimpleChatScreen(),
      ),
    ).then((_) {
      // Clear current conversation tracking when returning from chat screen
      notificationService.setCurrentConversationId(null);
      // Also clear the conversation in ChatService so notifications work
      chatService.clearConversation();
    });
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
          : LayoutBuilder(
              builder: (context, constraints) {
                final isWideLayout = constraints.maxWidth >= 900;

                if (!isWideLayout) {
                  return _buildConversationSidebar(authService, user, false);
                }

                return Row(
                  children: [
                    SizedBox(
                      width: 360,
                      child: _buildConversationSidebar(authService, user, true),
                    ),
                    Expanded(
                      child: Container(
                        color: const Color(0xFFF3F4F6),
                        child: _buildChatPane(),
                      ),
                    ),
                  ],
                );
              },
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
    final isGroup = _selectedType == 'group';

    return AlertDialog(
      title: const Text('New Conversation'),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: _nameController,
              decoration: InputDecoration(
                labelText: isGroup ? 'Group Name' : 'Conversation Name (optional)',
                border: const OutlineInputBorder(),
                hintText: isGroup ? 'Enter a name for your group' : null,
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
            if (!isGroup) ...[
              const SizedBox(height: 16),
              TextField(
                controller: _participantController,
                decoration: const InputDecoration(
                  labelText: 'Participant IDs (comma-separated)',
                  hintText: 'user-id-1, user-id-2',
                  border: OutlineInputBorder(),
                ),
              ),
            ] else ...[
              const SizedBox(height: 8),
              const Text(
                'Other users will be able to see and join this group',
                style: TextStyle(
                  fontSize: 12,
                  color: Colors.grey,
                  fontStyle: FontStyle.italic,
                ),
              ),
            ],
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
            final participants = isGroup
                ? <String>[] // Groups don't need participant IDs upfront
                : _participantController.text
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

