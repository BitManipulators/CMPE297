import 'package:flutter/services.dart';
import 'model_asset_service.dart';

class AIModelService {
  static const MethodChannel _channel = MethodChannel('ai_model_channel');

  bool _isInitialized = false;
  bool _isLoading = false;
  String? _errorMessage;

  bool get isInitialized => _isInitialized;
  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;

  /// Initializes the AI model
  /// Returns true if successful, false otherwise
  Future<bool> initializeModel() async {
    if (_isInitialized) {
      return true;
    }

    if (_isLoading) {
      return false;
    }

    try {
      _isLoading = true;
      _errorMessage = null;

      // First, ensure model is copied to storage
      print('Copying model to storage...');
      final modelPath = await ModelAssetService.copyModelToStorage();

      // Validate the model
      final isValid = await ModelAssetService.validateModel();
      if (!isValid) {
        throw Exception('Model validation failed');
      }

      // Initialize the native AI engine
      print('Initializing native AI engine...');
      final initResult = await _channel.invokeMethod('initModel', {'modelPath': modelPath});

      if (initResult == true) {
        _isInitialized = true;
        print('AI model initialized successfully');
        return true;
      } else {
        throw Exception('Native AI engine initialization failed');
      }

    } catch (e) {
      _errorMessage = e.toString();
      print('Error initializing AI model: $e');
      return false;
    } finally {
      _isLoading = false;
    }
  }

  /// Generates text using the AI model
  /// Returns the generated text or null if failed
  Future<String?> generateText(String prompt) async {
    if (!_isInitialized) {
      print('AI model not initialized');
      return null;
    }

    try {
      print('Generating text for prompt: $prompt');

      // Call the native AI engine
      final response = await _channel.invokeMethod('generateText', {'prompt': prompt});

      if (response != null) {
        print('Generated text: $response');
        return response.toString();
      } else {
        throw Exception('Native AI engine returned null response');
      }

    } catch (e) {
      print('Error generating text: $e');
      _errorMessage = e.toString();
      return null;
    }
  }

  /// Generates a survival-focused response
  /// This adds context to make the AI more helpful for survival scenarios
  Future<String?> generateSurvivalResponse(String userMessage) async {
    if (!_isInitialized) {
      return null;
    }

    // Send only the user message to the native model. Any system prompting
    // should be handled inside the native inference layer / model config.
    final raw = await generateText(userMessage);
    return raw?.trim();
  }


  /// Checks if the model is ready for use
  Future<bool> isModelReady() async {
    try {
      final result = await _channel.invokeMethod('isModelReady');
      return result == true;
    } catch (e) {
      print('Error checking model status: $e');
      return false;
    }
  }

  /// Resets the model state
  void reset() {
    _isInitialized = false;
    _isLoading = false;
    _errorMessage = null;
  }

  /// Gets model information
  Future<Map<String, dynamic>> getModelInfo() async {
    try {
      final modelPath = await ModelAssetService.getModelPath();
      final modelSize = await ModelAssetService.getModelSize();

      return {
        'modelPath': modelPath,
        'modelSize': modelSize,
        'isInitialized': _isInitialized,
        'isLoading': _isLoading,
        'errorMessage': _errorMessage,
      };
    } catch (e) {
      return {
        'error': e.toString(),
        'isInitialized': _isInitialized,
        'isLoading': _isLoading,
        'errorMessage': _errorMessage,
      };
    }
  }
}
