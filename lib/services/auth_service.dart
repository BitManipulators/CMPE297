import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import '../models/user.dart';
import '../config/app_config.dart';

class AuthService extends ChangeNotifier {
  static const String _baseUrl = AppConfig.backendBaseUrl;
  User? _currentUser;
  bool _isAuthenticated = false;

  User? get currentUser => _currentUser;
  bool get isAuthenticated => _isAuthenticated;

  AuthService() {
    _loadUser();
  }

  Future<void> _loadUser() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final userJson = prefs.getString('current_user');
      if (userJson != null) {
        _currentUser = User.fromJson(json.decode(userJson));
        _isAuthenticated = true;
        notifyListeners();
      }
    } catch (e) {
      debugPrint('Error loading user: $e');
    }
  }

  Future<User> register(String username, {String? email}) async {
    try {
      final response = await http.post(
        Uri.parse('$_baseUrl/api/users/register'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'username': username,
          'email': email,
        }),
      ).timeout(
        const Duration(seconds: 10),
        onTimeout: () {
          throw Exception(
            'Connection timeout. Please check if the backend server is running at $_baseUrl',
          );
        },
      );

      if (response.statusCode == 200) {
        final userData = json.decode(response.body);
        _currentUser = User.fromJson(userData);
        _isAuthenticated = true;

        // Save to local storage
        final prefs = await SharedPreferences.getInstance();
        await prefs.setString('current_user', json.encode(userData));

        notifyListeners();
        return _currentUser!;
      } else {
        throw Exception('Failed to register user: ${response.body}');
      }
    } on http.ClientException catch (e) {
      debugPrint('Registration error: $e');
      throw Exception(
        'Cannot connect to backend server at $_baseUrl. '
        'Please ensure the server is running. '
        'Error: ${e.message}',
      );
    } catch (e) {
      debugPrint('Registration error: $e');
      // Check if it's a connection error
      final errorString = e.toString().toLowerCase();
      if (errorString.contains('failed to fetch') ||
          errorString.contains('connection refused') ||
          errorString.contains('network is unreachable')) {
        throw Exception(
          'Cannot connect to backend server at $_baseUrl. '
          'Please ensure the server is running. '
          'For Android emulator, use http://10.0.2.2:8000. '
          'For iOS simulator, use http://localhost:8000. '
          'For physical device, use your computer\'s IP address.',
        );
      }
      rethrow;
    }
  }

  Future<User?> getUser(String userId) async {
    try {
      final response = await http.get(
        Uri.parse('$_baseUrl/api/users/$userId'),
      ).timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        return User.fromJson(json.decode(response.body));
      }
      return null;
    } catch (e) {
      debugPrint('Error getting user: $e');
      return null;
    }
  }

  Future<void> logout() async {
    _currentUser = null;
    _isAuthenticated = false;

    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('current_user');

    notifyListeners();
  }
}

