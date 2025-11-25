import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter_local_notifications/flutter_local_notifications.dart';

// Conditional import for web
import 'notification_service_web_stub.dart'
    if (dart.library.html) 'notification_service_web.dart' as web;

/// Service to handle local notifications for new messages
/// Uses browser Notification API for web, flutter_local_notifications for mobile
class NotificationService extends ChangeNotifier {
  static final NotificationService _instance = NotificationService._internal();
  factory NotificationService() => _instance;
  NotificationService._internal();

  final FlutterLocalNotificationsPlugin _notifications = FlutterLocalNotificationsPlugin();
  bool _initialized = false;
  String? _currentConversationId; // Track which conversation is currently being viewed
  final StreamController<NotificationResponse> _notificationResponseController =
      StreamController<NotificationResponse>.broadcast();

  // Track unread message counts per conversation
  final Map<String, int> _unreadCounts = {};
  String _originalTitle = 'IntoTheWild'; // Store original app title

  /// Initialize the notification service
  Future<void> initialize() async {
    if (_initialized) {
      debugPrint('NotificationService already initialized');
      return;
    }

    debugPrint('Initializing NotificationService... Platform: ${kIsWeb ? "Web" : "Mobile"}');

    if (kIsWeb) {
      // For web, use browser's native Notification API
      await _initializeWebNotifications();
      // Store original title
      _originalTitle = web.WebNotificationHelper.getDocumentTitle() ?? 'IntoTheWild';
    } else {
      // For mobile, use flutter_local_notifications
      await _initializeMobileNotifications();
    }

    _initialized = true;
    debugPrint('NotificationService initialized');
  }

  /// Initialize web notifications using browser's Notification API
  Future<void> _initializeWebNotifications() async {
    debugPrint('Initializing web notifications...');
    debugPrint('Web notifications will request permission on first use');
    debugPrint('See NOTIFICATIONS_WEB.md for instructions on enabling notifications in Chrome');
  }

  /// Initialize mobile notifications using flutter_local_notifications
  Future<void> _initializeMobileNotifications() async {
    // Android initialization settings
    const androidSettings = AndroidInitializationSettings('@mipmap/ic_launcher');

    // iOS initialization settings
    const iosSettings = DarwinInitializationSettings(
      requestAlertPermission: true,
      requestBadgePermission: true,
      requestSoundPermission: true,
    );

    const initSettings = InitializationSettings(
      android: androidSettings,
      iOS: iosSettings,
    );

    // Initialize the plugin
    try {
      final initialized = await _notifications.initialize(
        initSettings,
        onDidReceiveNotificationResponse: (NotificationResponse response) {
          debugPrint('Notification response received: ${response.payload}');
          _onNotificationTapped(response);
          // Also add to stream for listeners
          _notificationResponseController.add(response);
        },
      );
      debugPrint('NotificationService initialization result: $initialized');
    } catch (e) {
      debugPrint('Error initializing NotificationService: $e');
    }

    // Request permissions for Android 13+
    if (await _notifications.resolvePlatformSpecificImplementation<
            AndroidFlutterLocalNotificationsPlugin>() !=
        null) {
      await _notifications
          .resolvePlatformSpecificImplementation<
              AndroidFlutterLocalNotificationsPlugin>()
          ?.requestNotificationsPermission();
    }

    // Request permissions for iOS
    if (await _notifications.resolvePlatformSpecificImplementation<
            IOSFlutterLocalNotificationsPlugin>() !=
        null) {
      await _notifications
          .resolvePlatformSpecificImplementation<
              IOSFlutterLocalNotificationsPlugin>()
          ?.requestPermissions(
            alert: true,
            badge: true,
            sound: true,
          );
    }
  }

  /// Handle notification tap
  void _onNotificationTapped(NotificationResponse response) {
    debugPrint('Notification tapped: ${response.payload}');
    // The payload will contain the conversation ID
    // Navigation will be handled by the app's navigation system
  }

  /// Handle web notification tap (when NotificationResponse can't be created)
  void _handleWebNotificationTap(String conversationId) {
    debugPrint('Web notification tapped: $conversationId');
    // Create a NotificationResponse for web
    try {
      final response = NotificationResponse(
        id: 0,
        actionId: null,
        input: null,
        payload: conversationId,
        notificationResponseType: NotificationResponseType.selectedNotification,
      );
      _notificationResponseController.add(response);
    } catch (e) {
      debugPrint('Error creating NotificationResponse for web: $e');
      // Fallback: create a minimal response
      // The stream will still work for navigation
    }
  }

  /// Set the current conversation ID (to avoid showing notifications for the active conversation)
  void setCurrentConversationId(String? conversationId) {
    _currentConversationId = conversationId;

    // Clear unread count for the conversation being viewed
    if (conversationId != null) {
      _clearUnreadCount(conversationId);
    }
  }

  /// Get total unread message count across all conversations
  int getTotalUnreadCount() {
    return _unreadCounts.values.fold(0, (sum, count) => sum + count);
  }

  /// Get unread count for a specific conversation
  int getUnreadCount(String conversationId) {
    return _unreadCounts[conversationId] ?? 0;
  }

  /// Clear unread count for a specific conversation
  void _clearUnreadCount(String conversationId) {
    if (_unreadCounts.containsKey(conversationId) && _unreadCounts[conversationId]! > 0) {
      _unreadCounts[conversationId] = 0;
      _updateBadge();
      notifyListeners();
    }
  }

  /// Increment unread count for a conversation
  void _incrementUnreadCount(String conversationId) {
    _unreadCounts[conversationId] = (_unreadCounts[conversationId] ?? 0) + 1;
    _updateBadge();
    notifyListeners();
  }

  /// Update badge count (web) and document title
  void _updateBadge() {
    if (kIsWeb) {
      final totalCount = getTotalUnreadCount();
      web.WebNotificationHelper.updateBadge(totalCount);
      _updateDocumentTitle(totalCount);
    }
  }

  /// Update document title with unread count
  void _updateDocumentTitle(int count) {
    if (kIsWeb) {
      try {
        // Use dart:html if available, otherwise use JS interop
        web.WebNotificationHelper.updateDocumentTitle(count, _originalTitle);
      } catch (e) {
        debugPrint('Error updating document title: $e');
      }
    }
  }

  /// Show a notification for a new message
  /// Returns true if notification was shown, false if it was suppressed
  Future<bool> showMessageNotification({
    required String conversationId,
    required String messageText,
    required String senderName,
    String? conversationName,
  }) async {
    debugPrint('showMessageNotification called: conversationId=$conversationId, currentConversationId=$_currentConversationId');

    // Don't show notification if user is viewing this conversation
    if (_currentConversationId == conversationId) {
      debugPrint('Suppressing notification for current conversation: $conversationId');
      return false;
    }

    if (!_initialized) {
      debugPrint('Notification service not initialized, initializing now...');
      await initialize();
    }

    // Get notification ID based on conversation ID (to group notifications)
    final notificationId = _getNotificationId(conversationId);

    // Android notification details
    const androidDetails = AndroidNotificationDetails(
      'new_messages',
      'New Messages',
      channelDescription: 'Notifications for new chat messages',
      importance: Importance.high,
      priority: Priority.high,
      showWhen: true,
      enableVibration: true,
      playSound: true,
      icon: '@mipmap/ic_launcher',
      styleInformation: BigTextStyleInformation(''),
    );

    // iOS notification details
    const iosDetails = DarwinNotificationDetails(
      presentAlert: true,
      presentBadge: true,
      presentSound: true,
    );

    final notificationDetails = NotificationDetails(
      android: androidDetails,
      iOS: iosDetails,
    );

    // Create title and body
    final title = conversationName ?? senderName;
    final body = messageText.length > 100
        ? '${messageText.substring(0, 100)}...'
        : messageText;

    // Increment unread count for this conversation
    _incrementUnreadCount(conversationId);

    // Show notification based on platform
    if (kIsWeb) {
      return await _showWebNotification(
        conversationId: conversationId,
        title: title,
        body: body,
      );
    } else {
      return await _showMobileNotification(
        notificationId: notificationId,
        title: title,
        body: body,
        notificationDetails: notificationDetails,
        conversationId: conversationId,
      );
    }
  }

  /// Show notification on web using browser's Notification API
  Future<bool> _showWebNotification({
    required String conversationId,
    required String title,
    required String body,
  }) async {
    try {
      debugPrint('Attempting to show web notification: $title - $body');

      // Use web helper to show notification
      // Only trigger navigation when user clicks the notification
      final success = await web.WebNotificationHelper.showNotification(
        title: title,
        body: body,
        conversationId: conversationId,
        onTap: (convId) {
          debugPrint('Web notification clicked: $convId');
          _handleWebNotificationTap(convId);
        },
      );

      if (success) {
        debugPrint('Web notification shown successfully: $title - $body');
      } else {
        debugPrint('Failed to show web notification. Check browser permissions.');
      }

      return success;
    } catch (e) {
      debugPrint('Error showing web notification: $e');
      return false;
    }
  }

  /// Show notification on mobile using flutter_local_notifications
  Future<bool> _showMobileNotification({
    required int notificationId,
    required String title,
    required String body,
    required NotificationDetails notificationDetails,
    required String conversationId,
  }) async {
    try {
      await _notifications.show(
        notificationId,
        title,
        body,
        notificationDetails,
        payload: conversationId, // Store conversation ID in payload for navigation
      );
      debugPrint('Mobile notification show() called for conversation: $conversationId');
      debugPrint('Notification details - ID: $notificationId, Title: $title, Body: $body');
      return true;
    } catch (e) {
      debugPrint('Error showing mobile notification: $e');
      return false;
    }
  }

  /// Get a consistent notification ID for a conversation
  /// This allows notifications to be updated/replaced for the same conversation
  int _getNotificationId(String conversationId) {
    // Use hash of conversation ID to get a consistent integer
    return conversationId.hashCode.abs() % 2147483647; // Max int32
  }

  /// Cancel all notifications
  Future<void> cancelAll() async {
    await _notifications.cancelAll();
  }

  /// Cancel notifications for a specific conversation
  Future<void> cancelConversationNotifications(String conversationId) async {
    final notificationId = _getNotificationId(conversationId);
    await _notifications.cancel(notificationId);
  }

  /// Get notification response stream (for handling taps)
  Stream<NotificationResponse> get notificationResponseStream {
    return _notificationResponseController.stream;
  }

  /// Clear all unread counts (e.g., when user logs out)
  void clearAllUnreadCounts() {
    _unreadCounts.clear();
    _updateBadge();
    notifyListeners();
  }

  /// Dispose the service
  void dispose() {
    _notificationResponseController.close();
    // Clear badge on dispose
    if (kIsWeb) {
      web.WebNotificationHelper.updateBadge(0);
      web.WebNotificationHelper.updateDocumentTitle(0, _originalTitle);
    }
  }
}

