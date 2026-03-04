import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';
import 'package:flutter/foundation.dart';
import '../../../data/providers/api_client.dart';
import '../data/models/models.dart';
import '../data/repositories/messaging_repository.dart';
import 'encryption_service.dart';
import 'websocket_service.dart';

/// Central state management for the messaging feature.
/// Uses ChangeNotifier (Provider pattern) for reactive UI updates.
class MessagingProvider extends ChangeNotifier {
  final ApiClient _apiClient;
  late final MessagingRepository _repository;
  late final WebSocketService _wsService;
  late final EncryptionService _encryptionService;

  // State
  List<ConversationModel> _conversations = [];
  final Map<String, List<MessageModel>> _messages = {};
  final Map<String, bool> _hasMoreMessages = {};
  final Map<String, bool> _loadingMessages = {};
  final Map<String, String> _recipientPublicKeys = {};

  bool _isLoadingConversations = false;
  bool _isInitialized = false;
  String? _currentUserId;
  String? _activeConversationId;
  String? _error;

  // Typing state
  final Map<String, bool> _typingUsers = {};
  Timer? _typingDebounce;
  Timer? _typingTimeout;

  // Getters
  List<ConversationModel> get conversations => _conversations;
  bool get isLoadingConversations => _isLoadingConversations;
  bool get isInitialized => _isInitialized;
  String? get currentUserId => _currentUserId;
  String? get error => _error;

  List<MessageModel> getMessages(String conversationId) =>
      _messages[conversationId] ?? [];

  bool isLoadingMessages(String conversationId) =>
      _loadingMessages[conversationId] ?? false;

  bool hasMoreMessages(String conversationId) =>
      _hasMoreMessages[conversationId] ?? true;

  bool isUserTyping(String conversationId) =>
      _typingUsers[conversationId] ?? false;

  MessagingProvider(this._apiClient) {
    _repository = MessagingRepository(_apiClient);
    _wsService = WebSocketService(_apiClient);
    _encryptionService = EncryptionService();
  }

  /// Initialize the messaging system
  Future<void> initialize() async {
    if (_isInitialized) return;

    try {
      _currentUserId = await _apiClient.getCurrentUserId();
      if (_currentUserId == null) return;

      // Initialize encryption
      await _encryptionService.initialize();

      // Upload our public key
      try {
        final publicKey = await _encryptionService.getPublicKey();
        await _repository.uploadEncryptionKey(publicKey);
      } catch (e) {
        debugPrint('[Messaging] Key upload failed (non-critical): $e');
      }

      // Connect WebSocket
      await _wsService.connect();
      _listenToWebSocket();

      _isInitialized = true;
      notifyListeners();

      // Load conversations
      await loadConversations();
    } catch (e) {
      _error = 'Failed to initialize messaging: $e';
      debugPrint('[Messaging] Init error: $e');
      notifyListeners();
    }
  }

  /// Listen to WebSocket events
  void _listenToWebSocket() {
    _wsService.events.listen((event) {
      switch (event.type) {
        case WsEventType.newMessage:
          _handleNewMessage(event.data);
          break;
        case WsEventType.typing:
          _handleTypingEvent(event.data, true);
          break;
        case WsEventType.stopTyping:
          _handleTypingEvent(event.data, false);
          break;
        case WsEventType.readReceipt:
          _handleReadReceipt(event.data);
          break;
        case WsEventType.connected:
          notifyListeners();
          break;
        case WsEventType.disconnected:
          notifyListeners();
          break;
        default:
          break;
      }
    });
  }

  /// Handle incoming new message from WebSocket
  void _handleNewMessage(Map<String, dynamic> data) {
    final message = MessageModel.fromJson(data);

    // Decrypt message
    final decrypted = _decryptMessage(message);

    final conversationId = message.conversationId;

    // Add to messages list
    if (_messages.containsKey(conversationId)) {
      // Check for duplicate
      final exists = _messages[conversationId]!
          .any((m) => m.messageId == message.messageId);
      if (!exists) {
        _messages[conversationId]!.insert(0, decrypted);
      }
    }

    // Update conversation preview
    _updateConversationPreview(conversationId, decrypted);

    // If not in this conversation, increment unread  
    if (_activeConversationId != conversationId) {
      final convIdx = _conversations
          .indexWhere((c) => c.conversationId == conversationId);
      if (convIdx >= 0) {
        _conversations[convIdx].unreadCount++;
      }
    } else {
      // Auto-send read receipt if viewing this conversation
      _wsService.sendReadReceipt(conversationId, message.messageId);
    }

    // Clear typing indicator
    _typingUsers[conversationId] = false;

    notifyListeners();
  }

  /// Handle typing event
  void _handleTypingEvent(Map<String, dynamic> data, bool isTyping) {
    final conversationId = data['conversation_id'] as String?;
    final userId = data['user_id'] as String?;

    if (conversationId == null || userId == _currentUserId) return;

    _typingUsers[conversationId] = isTyping;
    notifyListeners();

    // Auto-clear typing after 5 seconds
    if (isTyping) {
      _typingTimeout?.cancel();
      _typingTimeout = Timer(const Duration(seconds: 5), () {
        _typingUsers[conversationId] = false;
        notifyListeners();
      });
    }
  }

  /// Handle read receipt event
  void _handleReadReceipt(Map<String, dynamic> data) {
    final conversationId = data['conversation_id'] as String?;
    final messageId = data['message_id'] as String?;

    if (conversationId == null || messageId == null) return;

    final messages = _messages[conversationId];
    if (messages != null) {
      for (final msg in messages) {
        if (msg.messageId == messageId) {
          msg.status = MessageStatus.read;
          break;
        }
        // Mark all messages up to this one as read
        if (msg.senderId == _currentUserId) {
          msg.status = MessageStatus.read;
        }
      }
      notifyListeners();
    }
  }

  // ============================================
  // Conversations
  // ============================================

  /// Load all conversations
  Future<void> loadConversations() async {
    _isLoadingConversations = true;
    _error = null;
    notifyListeners();

    try {
      _conversations = await _repository.getConversations();

      // Sort by most recent
      _conversations.sort((a, b) {
        final aTime = a.lastMessageAt ?? a.updatedAt;
        final bTime = b.lastMessageAt ?? b.updatedAt;
        return bTime.compareTo(aTime);
      });

      notifyListeners();
    } catch (e) {
      _error = ApiClient.getErrorMessage(e);
      debugPrint('[Messaging] Load conversations error: $e');
    } finally {
      _isLoadingConversations = false;
      notifyListeners();
    }
  }

  /// Create or get a conversation with a user
  Future<ConversationModel> getOrCreateConversation(String otherUserId) async {
    try {
      final conversation = await _repository.createConversation(otherUserId);

      // Add to list if not already present
      final exists = _conversations
          .any((c) => c.conversationId == conversation.conversationId);
      if (!exists) {
        _conversations.insert(0, conversation);
        notifyListeners();
      }

      return conversation;
    } catch (e) {
      throw Exception(ApiClient.getErrorMessage(e));
    }
  }

  /// Set the active conversation (for read receipt handling)
  void setActiveConversation(String? conversationId) {
    _activeConversationId = conversationId;

    if (conversationId != null) {
      // Clear unread count
      final idx = _conversations
          .indexWhere((c) => c.conversationId == conversationId);
      if (idx >= 0) {
        _conversations[idx].unreadCount = 0;
        notifyListeners();
      }
    }
  }

  /// Filter conversations by search query
  List<ConversationModel> searchConversations(String query) {
    if (query.isEmpty) return _conversations;
    final lower = query.toLowerCase();
    return _conversations.where((c) {
      final name = c.participantName?.toLowerCase() ?? '';
      final preview = c.lastMessagePreview?.toLowerCase() ?? '';
      return name.contains(lower) || preview.contains(lower);
    }).toList();
  }

  // ============================================
  // Messages
  // ============================================

  /// Load messages for a conversation
  Future<void> loadMessages(String conversationId) async {
    if (_loadingMessages[conversationId] == true) return;

    _loadingMessages[conversationId] = true;
    notifyListeners();

    try {
      final messages = await _repository.getMessages(conversationId);

      // Decrypt all messages
      final decrypted = messages.map(_decryptMessage).toList();

      _messages[conversationId] = decrypted;
      _hasMoreMessages[conversationId] = messages.length >= 50;

      // Send read receipt for the latest message
      if (decrypted.isNotEmpty && _activeConversationId == conversationId) {
        final latest = decrypted.first;
        if (latest.senderId != _currentUserId) {
          _wsService.sendReadReceipt(conversationId, latest.messageId);
        }
      }
    } catch (e) {
      debugPrint('[Messaging] Load messages error: $e');
    } finally {
      _loadingMessages[conversationId] = false;
      notifyListeners();
    }
  }

  /// Load older messages (pagination)
  Future<void> loadMoreMessages(String conversationId) async {
    if (_loadingMessages[conversationId] == true) return;
    if (_hasMoreMessages[conversationId] == false) return;

    final existing = _messages[conversationId];
    if (existing == null || existing.isEmpty) return;

    _loadingMessages[conversationId] = true;
    notifyListeners();

    try {
      final oldest = existing.last;
      final olderMessages = await _repository.getMessages(
        conversationId,
        before: oldest.createdAt.toIso8601String(),
      );

      final decrypted = olderMessages.map(_decryptMessage).toList();
      existing.addAll(decrypted);

      _hasMoreMessages[conversationId] = olderMessages.length >= 50;
    } catch (e) {
      debugPrint('[Messaging] Load more error: $e');
    } finally {
      _loadingMessages[conversationId] = false;
      notifyListeners();
    }
  }

  /// Send a text message
  Future<void> sendTextMessage(
    String conversationId,
    String text,
  ) async {
    if (text.trim().isEmpty) return;

    // Get recipient public key for encryption
    final recipientKey = await _getRecipientKey(conversationId);

    // Encrypt
    final encrypted = _encryptionService.encryptMessage(
      text.trim(),
      recipientPublicKey: recipientKey,
    );

    // Create optimistic message
    final optimisticId = 'temp_${DateTime.now().millisecondsSinceEpoch}';
    final optimistic = MessageModel(
      messageId: optimisticId,
      conversationId: conversationId,
      senderId: _currentUserId!,
      encryptedPayload: encrypted,
      messageType: MessageType.text,
      createdAt: DateTime.now(),
      status: MessageStatus.sending,
      decryptedContent: text.trim(),
    );

    // Add optimistically
    _messages.putIfAbsent(conversationId, () => []);
    _messages[conversationId]!.insert(0, optimistic);
    _updateConversationPreview(conversationId, optimistic);
    notifyListeners();

    try {
      // Send via WebSocket for speed
      _wsService.sendMessage(
        conversationId: conversationId,
        encryptedPayload: encrypted,
      );

      // Also send via REST for reliability
      final sent = await _repository.sendMessage(
        conversationId: conversationId,
        encryptedPayload: encrypted,
      );

      // Replace optimistic message with real one
      final idx = _messages[conversationId]!
          .indexWhere((m) => m.messageId == optimisticId);
      if (idx >= 0) {
        final real = _decryptMessage(sent);
        real.status = MessageStatus.sent;
        _messages[conversationId]![idx] = real;
        notifyListeners();
      }
    } catch (e) {
      // Mark as failed
      final idx = _messages[conversationId]!
          .indexWhere((m) => m.messageId == optimisticId);
      if (idx >= 0) {
        _messages[conversationId]![idx].status = MessageStatus.failed;
        notifyListeners();
      }
      debugPrint('[Messaging] Send error: $e');
    }
  }

  /// Send an image message
  Future<void> sendImageMessage(
    String conversationId,
    String filePath,
  ) async {
    // Create optimistic message
    final optimisticId = 'temp_img_${DateTime.now().millisecondsSinceEpoch}';
    final optimistic = MessageModel(
      messageId: optimisticId,
      conversationId: conversationId,
      senderId: _currentUserId!,
      encryptedPayload: '',
      messageType: MessageType.image,
      createdAt: DateTime.now(),
      status: MessageStatus.sending,
      metadata: {'local_path': filePath},
      decryptedContent: filePath,
    );

    _messages.putIfAbsent(conversationId, () => []);
    _messages[conversationId]!.insert(0, optimistic);
    notifyListeners();

    try {
      // Upload image
      final uploadResult =
          await _repository.uploadImage(conversationId, filePath);

      final fileId = uploadResult['file_id'];

      // Send image message
      final encrypted = _encryptionService.encryptMessage(
        fileId,
        recipientPublicKey: await _getRecipientKey(conversationId),
      );

      final sent = await _repository.sendMessage(
        conversationId: conversationId,
        encryptedPayload: encrypted,
        messageType: MessageType.image,
        metadata: {
          'file_id': fileId,
          'conversation_id': conversationId,
        },
      );

      // Replace optimistic
      final idx = _messages[conversationId]!
          .indexWhere((m) => m.messageId == optimisticId);
      if (idx >= 0) {
        final real = _decryptMessage(sent);
        real.status = MessageStatus.sent;
        _messages[conversationId]![idx] = real;
      }

      _updateConversationPreview(conversationId, sent);
      notifyListeners();
    } catch (e) {
      final idx = _messages[conversationId]!
          .indexWhere((m) => m.messageId == optimisticId);
      if (idx >= 0) {
        _messages[conversationId]![idx].status = MessageStatus.failed;
        notifyListeners();
      }
      debugPrint('[Messaging] Image send error: $e');
    }
  }

  /// Send typing indicator (debounced)
  void sendTyping(String conversationId) {
    _typingDebounce?.cancel();
    _typingDebounce = Timer(const Duration(milliseconds: 300), () {
      _wsService.sendTyping(conversationId);
    });
  }

  /// Stop typing indicator
  void sendStopTyping(String conversationId) {
    _typingDebounce?.cancel();
    _wsService.sendStopTyping(conversationId);
  }

  // ============================================
  // Helpers
  // ============================================

  /// Decrypt a message
  MessageModel _decryptMessage(MessageModel message) {
    try {
      final senderKey = _recipientPublicKeys[message.senderId];
      final decrypted = _encryptionService.decryptMessage(
        message.encryptedPayload,
        senderPublicKey: senderKey,
      );
      return message.copyWith(decryptedContent: decrypted);
    } catch (e) {
      return message.copyWith(decryptedContent: '[Encrypted message]');
    }
  }

  /// Get recipient's public key for a conversation
  Future<String?> _getRecipientKey(String conversationId) async {
    final matches = _conversations
        .where((c) => c.conversationId == conversationId);
    if (matches.isEmpty) return null;
    final conv = matches.first;

    final otherUserId = conv.getOtherParticipant(_currentUserId!);

    if (_recipientPublicKeys.containsKey(otherUserId)) {
      return _recipientPublicKeys[otherUserId];
    }

    try {
      final key = await _repository.getEncryptionKey(otherUserId);
      if (key != null) {
        _recipientPublicKeys[otherUserId] = key;
      }
      return key;
    } catch (e) {
      return null;
    }
  }

  /// Update conversation preview after new message
  void _updateConversationPreview(
      String conversationId, MessageModel message) {
    final idx = _conversations
        .indexWhere((c) => c.conversationId == conversationId);
    if (idx >= 0) {
      final conv = _conversations[idx];
      _conversations[idx] = conv.copyWith(
        lastMessagePreview: message.isImage
            ? '📷 Photo'
            : message.decryptedContent ?? message.encryptedPayload,
        lastMessageAt: message.createdAt,
        lastMessageType: message.messageType.name,
        updatedAt: DateTime.now(),
      );

      // Move to top
      if (idx > 0) {
        final moved = _conversations.removeAt(idx);
        _conversations.insert(0, moved);
      }
    }
  }

  /// Delete a conversation from the local list
  void deleteConversation(String conversationId) {
    _conversations.removeWhere((c) => c.conversationId == conversationId);
    _messages.remove(conversationId);
    notifyListeners();
  }

  /// Mark a conversation as read
  void markAsRead(String conversationId) {
    final idx = _conversations
        .indexWhere((c) => c.conversationId == conversationId);
    if (idx >= 0) {
      _conversations[idx].unreadCount = 0;
      notifyListeners();
    }
  }

  /// Get download URL for an image
  Future<Uint8List?> downloadImage(
      String conversationId, String fileId) async {
    try {
      return await _repository.downloadImage(conversationId, fileId);
    } catch (e) {
      debugPrint('[Messaging] Image download error: $e');
      return null;
    }
  }

  @override
  void dispose() {
    _typingDebounce?.cancel();
    _typingTimeout?.cancel();
    _wsService.dispose();
    super.dispose();
  }
}
