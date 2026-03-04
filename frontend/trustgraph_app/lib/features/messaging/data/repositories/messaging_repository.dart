import 'dart:typed_data';
import 'package:dio/dio.dart';
import '../../../../data/providers/api_client.dart';
import '../models/models.dart';

/// Repository for all messaging REST API calls
class MessagingRepository {
  final ApiClient _apiClient;
  static const String _messagingBase = '/api/v1';

  MessagingRepository(this._apiClient);

  // ============================================
  // Conversations
  // ============================================

  /// Create or get an existing conversation with another user
  Future<ConversationModel> createConversation(String otherUserId) async {
    final response = await _apiClient.post(
      '$_messagingBase/conversations/',
      data: {'participant_id': otherUserId},
    );
    return ConversationModel.fromJson(response.data);
  }

  /// Fetch all conversations for current user
  Future<List<ConversationModel>> getConversations({
    int skip = 0,
    int limit = 50,
  }) async {
    final response = await _apiClient.get(
      '$_messagingBase/conversations/',
      queryParameters: {'skip': skip, 'limit': limit},
    );
    final data = response.data;
    if (data is List) {
      return data.map((c) => ConversationModel.fromJson(c)).toList();
    }
    // Handle paginated response
    final conversations = data['conversations'] ?? data['items'] ?? [];
    return (conversations as List)
        .map((c) => ConversationModel.fromJson(c))
        .toList();
  }

  /// Get a single conversation
  Future<ConversationModel> getConversation(String conversationId) async {
    final response = await _apiClient.get(
      '$_messagingBase/conversations/$conversationId',
    );
    return ConversationModel.fromJson(response.data);
  }

  /// Get presence status for a user in a conversation
  Future<Map<String, dynamic>> getPresence(String conversationId) async {
    final response = await _apiClient.get(
      '$_messagingBase/conversations/$conversationId/presence',
    );
    return response.data;
  }

  // ============================================
  // Messages
  // ============================================

  /// Send an encrypted message
  Future<MessageModel> sendMessage({
    required String conversationId,
    required String encryptedPayload,
    String? encryptedKey,
    MessageType messageType = MessageType.text,
    Map<String, dynamic>? metadata,
  }) async {
    final response = await _apiClient.post(
      '$_messagingBase/messages/send',
      data: {
        'conversation_id': conversationId,
        'encrypted_payload': encryptedPayload,
        if (encryptedKey != null) 'encrypted_key': encryptedKey,
        'message_type': messageType.name,
        if (metadata != null) 'metadata': metadata,
      },
    );
    return MessageModel.fromJson(response.data);
  }

  /// Fetch message history for a conversation (paginated)
  Future<List<MessageModel>> getMessages(
    String conversationId, {
    int limit = 50,
    String? before, // ISO timestamp cursor
  }) async {
    final queryParams = <String, dynamic>{'limit': limit};
    if (before != null) queryParams['before'] = before;

    final response = await _apiClient.get(
      '$_messagingBase/messages/$conversationId',
      queryParameters: queryParams,
    );
    final data = response.data;
    List messagesList;
    if (data is List) {
      messagesList = data;
    } else {
      messagesList = data['messages'] ?? data['items'] ?? [];
    }
    return messagesList.map((m) => MessageModel.fromJson(m)).toList();
  }

  /// Send read receipt
  Future<void> sendReadReceipt({
    required String conversationId,
    required String messageId,
  }) async {
    await _apiClient.post(
      '$_messagingBase/messages/read-receipt',
      data: {
        'conversation_id': conversationId,
        'message_id': messageId,
      },
    );
  }

  /// Send typing indicator
  Future<void> sendTypingIndicator({
    required String conversationId,
    bool isTyping = true,
  }) async {
    await _apiClient.post(
      '$_messagingBase/messages/typing',
      data: {
        'conversation_id': conversationId,
        'is_typing': isTyping,
      },
    );
  }

  // ============================================
  // Encryption Keys
  // ============================================

  /// Upload our public encryption key
  Future<void> uploadEncryptionKey(String publicKey) async {
    await _apiClient.put(
      '$_messagingBase/conversations/encryption-key',
      data: {
        'public_key': publicKey,
        'key_type': 'x25519',
      },
    );
  }

  /// Get another user's public encryption key
  Future<String?> getEncryptionKey(String userId) async {
    try {
      final response = await _apiClient.get(
        '$_messagingBase/conversations/encryption-key/$userId',
      );
      return response.data['public_key'];
    } on DioException catch (e) {
      if (e.response?.statusCode == 404) return null;
      rethrow;
    }
  }

  // ============================================
  // Images
  // ============================================

  /// Upload an encrypted image
  Future<Map<String, dynamic>> uploadImage(
    String conversationId,
    String filePath,
  ) async {
    final response = await _apiClient.uploadFile(
      '$_messagingBase/images/upload/$conversationId',
      filePath,
    );
    return response.data;
  }

  /// Download an encrypted image as bytes
  Future<Uint8List> downloadImage(
    String conversationId,
    String fileId,
  ) async {
    final response = await _apiClient.get(
      '$_messagingBase/images/download/$conversationId/$fileId',
      options: Options(responseType: ResponseType.bytes),
    );
    return Uint8List.fromList(response.data);
  }

  // ============================================
  // Block Management
  // ============================================

  /// Block a user
  Future<void> blockUser(String userId) async {
    await _apiClient.post(
      '$_messagingBase/conversations/block',
      data: {'blocked_user_id': userId},
    );
  }

  /// Unblock a user
  Future<void> unblockUser(String userId) async {
    await _apiClient.delete(
      '$_messagingBase/conversations/block/$userId',
    );
  }

  /// Get blocked users list
  Future<List<String>> getBlockedUsers() async {
    final response = await _apiClient.get(
      '$_messagingBase/conversations/block/list',
    );
    return List<String>.from(response.data['blocked_users'] ?? []);
  }
}
