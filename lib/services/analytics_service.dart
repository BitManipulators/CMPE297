import 'package:firebase_analytics/firebase_analytics.dart';
import 'package:flutter/foundation.dart';

class AnalyticsService {
  static final FirebaseAnalytics _analytics = FirebaseAnalytics.instance;

  static FirebaseAnalytics get analytics => _analytics;

  // Log screen views
  static Future<void> logScreenView(String screenName) async {
    try {
      await _analytics.logScreenView(screenName: screenName);
    } catch (e) {
      // Silently fail if analytics is not available
      debugPrint('Analytics error: $e');
    }
  }

  // Log custom events
  static Future<void> logEvent(String name, Map<String, Object>? parameters) async {
    try {
      await _analytics.logEvent(name: name, parameters: parameters);
    } catch (e) {
      // Silently fail if analytics is not available
      debugPrint('Analytics error: $e');
    }
  }

  // Log login events
  static Future<void> logLogin(String loginMethod) async {
    try {
      await _analytics.logLogin(loginMethod: loginMethod);
    } catch (e) {
      // Silently fail if analytics is not available
      debugPrint('Analytics error: $e');
    }
  }

  // Log sign up events
  static Future<void> logSignUp(String signUpMethod) async {
    try {
      await _analytics.logSignUp(signUpMethod: signUpMethod);
    } catch (e) {
      // Silently fail if analytics is not available
      debugPrint('Analytics error: $e');
    }
  }

  // Log chat events
  static Future<void> logChatMessageSent({String? conversationType}) async {
    try {
      await _analytics.logEvent(
        name: 'chat_message_sent',
        parameters: conversationType != null ? {'conversation_type': conversationType} : null,
      );
    } catch (e) {
      debugPrint('Analytics error: $e');
    }
  }

  static Future<void> logImageUploaded({String? conversationType}) async {
    try {
      await _analytics.logEvent(
        name: 'image_uploaded',
        parameters: conversationType != null ? {'conversation_type': conversationType} : null,
      );
    } catch (e) {
      debugPrint('Analytics error: $e');
    }
  }

  static Future<void> logConversationCreated({required String conversationType}) async {
    try {
      await _analytics.logEvent(
        name: 'conversation_created',
        parameters: {'conversation_type': conversationType},
      );
    } catch (e) {
      debugPrint('Analytics error: $e');
    }
  }

  static Future<void> logGroupJoined() async {
    try {
      await _analytics.logEvent(name: 'group_joined');
    } catch (e) {
      debugPrint('Analytics error: $e');
    }
  }

  static Future<void> logGroupLeft() async {
    try {
      await _analytics.logEvent(name: 'group_left');
    } catch (e) {
      debugPrint('Analytics error: $e');
    }
  }

  // Set user properties
  static Future<void> setUserId(String userId) async {
    try {
      await _analytics.setUserId(id: userId);
    } catch (e) {
      debugPrint('Analytics error: $e');
    }
  }

  static Future<void> setUserProperty({required String name, required String value}) async {
    try {
      await _analytics.setUserProperty(name: name, value: value);
    } catch (e) {
      debugPrint('Analytics error: $e');
    }
  }
}

