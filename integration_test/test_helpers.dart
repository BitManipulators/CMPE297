import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:into_the_wild/models/user.dart';
import 'dart:convert';

/// Test helpers for integration tests
class IntegrationTestHelpers {
  /// Clean up all app state before each test
  static Future<void> clearAppState() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.clear();
  }

  /// Generate a unique test username
  static String generateTestUsername() {
    return 'test_user_${DateTime.now().millisecondsSinceEpoch}';
  }

  /// Generate a unique test email
  static String generateTestEmail() {
    return 'test_${DateTime.now().millisecondsSinceEpoch}@example.com';
  }

  /// Wait for a widget to appear with timeout
  static Future<void> waitForWidget(
    WidgetTester tester,
    Finder finder, {
    Duration timeout = const Duration(seconds: 10),
  }) async {
    final endTime = DateTime.now().add(timeout);
    
    while (DateTime.now().isBefore(endTime)) {
      await tester.pumpAndSettle(const Duration(milliseconds: 100));
      
      if (finder.evaluate().isNotEmpty) {
        return;
      }
      
      await Future.delayed(const Duration(milliseconds: 100));
    }
    
    throw Exception('Widget not found within timeout: $finder');
  }

  /// Wait for a condition to be true
  static Future<void> waitForCondition(
    WidgetTester tester,
    bool Function() condition, {
    Duration timeout = const Duration(seconds: 10),
  }) async {
    final endTime = DateTime.now().add(timeout);
    
    while (DateTime.now().isBefore(endTime)) {
      await tester.pumpAndSettle(const Duration(milliseconds: 100));
      
      if (condition()) {
        return;
      }
      
      await Future.delayed(const Duration(milliseconds: 100));
    }
    
    throw Exception('Condition not met within timeout');
  }

  /// Save a mock user to SharedPreferences for testing
  static Future<void> saveTestUser(User user) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('current_user', json.encode(user.toJson()));
  }

  /// Get the currently saved user from SharedPreferences
  static Future<User?> getSavedUser() async {
    final prefs = await SharedPreferences.getInstance();
    final userJson = prefs.getString('current_user');
    if (userJson == null) return null;
    return User.fromJson(json.decode(userJson));
  }

  /// Set up larger viewport to prevent RenderFlex overflow
  static void setLargeViewport(WidgetTester tester) {
    tester.view.physicalSize = const Size(1200, 2000);
    tester.view.devicePixelRatio = 1.0;
  }

  /// Reset viewport to default
  static void resetViewport(WidgetTester tester) {
    tester.view.reset();
  }
}
