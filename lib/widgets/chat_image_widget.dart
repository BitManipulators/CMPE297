import 'dart:convert';
import 'dart:typed_data';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

/// A platform-aware image widget that handles both data URLs and HTTP URLs
/// Works on both web (Chrome) and Android (emulator/physical device)
class ChatImageWidget extends StatelessWidget {
  final String imageUrl;
  final double? width;
  final double? height;
  final BoxFit fit;
  final BorderRadius? borderRadius;

  const ChatImageWidget({
    super.key,
    required this.imageUrl,
    this.width,
    this.height,
    this.fit = BoxFit.cover,
    this.borderRadius,
  });

  /// Check if the URL is a data URL (base64 encoded)
  bool get _isDataUrl => imageUrl.startsWith('data:');

  /// Decode base64 data URL to bytes
  Uint8List? _decodeDataUrl() {
    if (!_isDataUrl) return null;

    try {
      // Data URL format: data:image/jpeg;base64,<base64_data>
      final commaIndex = imageUrl.indexOf(',');
      if (commaIndex == -1) {
        debugPrint('Invalid data URL format: no comma found');
        return null;
      }

      String base64Data = imageUrl.substring(commaIndex + 1);

      // Clean the base64 data: remove whitespace, newlines, and other invalid characters
      base64Data = base64Data.replaceAll(RegExp(r'\s+'), '');

      // Check if base64 data looks truncated (ends with ... or is suspiciously short)
      if (base64Data.endsWith('...') || base64Data.length < 100) {
        debugPrint('Warning: Base64 data appears truncated (length: ${base64Data.length})');
        // Don't try to decode truncated data
        return null;
      }

      // Validate base64 format (should only contain valid base64 characters)
      if (!RegExp(r'^[A-Za-z0-9+/=]+$').hasMatch(base64Data)) {
        debugPrint('Invalid base64 characters detected');
        return null;
      }

      return base64Decode(base64Data);
    } catch (e) {
      debugPrint('Error decoding data URL: $e');
      debugPrint('Data URL length: ${imageUrl.length}');
      debugPrint('Data URL preview: ${imageUrl.substring(0, imageUrl.length > 200 ? 200 : imageUrl.length)}...');
      return null;
    }
  }

  Widget _buildImage() {
    // Handle data URLs (base64 encoded images)
    if (_isDataUrl) {
      final imageBytes = _decodeDataUrl();
      if (imageBytes != null) {
        // Use Image.memory for data URLs (works on all platforms)
        return Image.memory(
          imageBytes,
          width: width,
          height: height,
          fit: fit,
          errorBuilder: (context, error, stackTrace) {
            return _buildErrorWidget();
          },
        );
      } else {
        // If decoding failed, show error
        return _buildErrorWidget();
      }
    } else {
      // Handle regular HTTP/HTTPS URLs
      return Image.network(
        imageUrl,
        width: width,
        height: height,
        fit: fit,
        errorBuilder: (context, error, stackTrace) {
          return _buildErrorWidget();
        },
        loadingBuilder: (context, child, loadingProgress) {
          if (loadingProgress == null) return child;
          return _buildLoadingWidget();
        },
      );
    }
  }

  Widget _buildErrorWidget() {
    return Container(
      width: width,
      height: height,
      color: Colors.grey[300],
      child: const Icon(
        Icons.image_not_supported,
        color: Colors.grey,
        size: 40,
      ),
    );
  }

  Widget _buildLoadingWidget() {
    return Container(
      width: width,
      height: height,
      color: Colors.grey[200],
      child: const Center(
        child: CircularProgressIndicator(),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    Widget image = _buildImage();

    if (borderRadius != null) {
      return ClipRRect(
        borderRadius: borderRadius!,
        child: image,
      );
    }

    return image;
  }
}

