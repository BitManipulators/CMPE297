import 'dart:io';
import 'dart:typed_data';
import 'package:flutter/services.dart';
import 'package:path_provider/path_provider.dart';
import 'package:http/http.dart' as http;

class ModelAssetService {
  // For demonstration purposes, we'll use a placeholder model
  // In production, you would download from a public CDN or use a smaller model
  static const String _modelFileName = 'model.litertlm';

  /// Downloads the model from URL to internal storage
  /// Returns the path to the downloaded model file
  static Future<String> copyModelToStorage() async {
    try {
      // Get the internal storage directory
      final directory = await getApplicationDocumentsDirectory();
      final modelsDir = Directory('${directory.path}/models');

      // Create models directory if it doesn't exist
      if (!await modelsDir.exists()) {
        await modelsDir.create(recursive: true);
      }

      final modelFile = File('${modelsDir.path}/$_modelFileName');

      // Check if model already exists
      if (await modelFile.exists()) {
        print('Model already exists at: ${modelFile.path}');
        return modelFile.path;
      }

      // This method should not be called if the model doesn't exist
      // Users should download the model from Hugging Face and select it via file picker
      throw Exception('AI model not found. Please download the model and select it using the file picker in the app.');

    } catch (e) {
      print('Error creating model file: $e');
      throw Exception('Failed to create model file: $e');
    }
  }

  /// Checks if the model file exists in internal storage
  static Future<bool> isModelInStorage() async {
    try {
      final directory = await getApplicationDocumentsDirectory();
      final modelFile = File('${directory.path}/models/$_modelFileName');
      return await modelFile.exists();
    } catch (e) {
      print('Error checking model existence: $e');
      return false;
    }
  }

  /// Gets the path to the model file in internal storage
  static Future<String> getModelPath() async {
    final directory = await getApplicationDocumentsDirectory();
    return '${directory.path}/models/$_modelFileName';
  }

  /// Gets the size of the model file in bytes
  static Future<int> getModelSize() async {
    try {
      final modelPath = await getModelPath();
      final modelFile = File(modelPath);
      if (await modelFile.exists()) {
        return await modelFile.length();
      }
      return 0;
    } catch (e) {
      print('Error getting model size: $e');
      return 0;
    }
  }

  /// Validates that the model file is not corrupted
  static Future<bool> validateModel() async {
    try {
      final modelPath = await getModelPath();
      final modelFile = File(modelPath);

      if (!await modelFile.exists()) {
        return false;
      }

      // Basic validation: check file size is reasonable for a real model
      final fileSize = await modelFile.length();
      if (fileSize < 100 * 1024 * 1024) { // At least 100MB for a real model
        print('Model file too small: $fileSize bytes. Expected at least 100MB for the model.');
        return false;
      }

      // Log info about model size
      print('Model file size: ${(fileSize / (1024 * 1024)).toStringAsFixed(2)} MB');

      // Additional validation: check if it's a .litertlm file
      if (!modelFile.path.endsWith('.litertlm')) {
        print('Invalid file extension. Expected .litertlm file.');
        return false;
      }

      // TODO: Add more sophisticated validation (checksum, header validation)
      print('Model validation passed. Size: ${fileSize / (1024 * 1024)} MB');
      return true;

    } catch (e) {
      print('Error validating model: $e');
      return false;
    }
  }
}
