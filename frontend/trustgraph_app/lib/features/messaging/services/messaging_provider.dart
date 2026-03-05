import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';
import 'package:flutter/foundation.dart';
import '../../../data/providers/api_client.dart';
import '../../../data/repositories/user_repository.dart';
import '../data/models/models.dart';
import '../data/repositories/messaging_repository.dart';
import 'encryption_service.dart';
import 'websocket_service.dart';

/// Central state management for the messaging feature.
/// Uses ChangeNotifier (Provider pattern) for reactive UI updates.
class MessagingProvider extends ChangeNotifier {
  final ApiClient _apiClient;
  late final MessagingRepository _repository;
  late final UserRepository _userRepository;
  late final WebSocketService _wsService;
  late final EncryptionService _encryptionService;

  // State
  List<ConversationModel> _conversations = [];
  final Map<String, List<MessageModel>> _messages = {};
  final Map<String, Set<String>> _messageIds = {}; // Track seen message IDs to prevent duplicates
  final Map<String, bool> _hasMoreMessages = {};
  final Map<String, bool> _loadingMessages = {};
  final Map<String, String> _recipientPublicKeys = {};
  final Map<String, String> _userNameCache = {}; // Cache for user names

  bool _isLoadingConversations = false;
  bool _isInitialized = false;
  bool _wsListenerSetup = false;
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
    _userRepository = UserRepository(_apiClient);
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
      if (!_wsListenerSetup) {
        _listenToWebSocket();
        _wsListenerSetup = true;
      }

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

  /// Populate participant names for a list of conversations
  Future<void> _populateParticipantNames(
      List<ConversationModel> conversations) async {
    for (final conversation in conversations) {
      if (conversation.participants.isEmpty) continue;

      // Get the other participant
      final otherParticipantId = conversation.getOtherParticipant(
        _currentUserId ?? '',
      );

      if (otherParticipantId.isEmpty) continue;

      // Check cache first
      if (_userNameCache.containsKey(otherParticipantId)) {
        conversation.participantName = _userNameCache[otherParticipantId];
        conversation.participantId = otherParticipantId;
        continue;
      }

      // Fetch user info
      try {
        final user = await _userRepository.getUserById(otherParticipantId);
        if (user != null) {
          conversation.participantName = user.name;
          conversation.participantId = user.userId;
          _userNameCache[otherParticipantId] = user.name;
        } else {
          conversation.participantName = 'User';
          _userNameCache[otherParticipantId] = 'User';
        }
      } catch (e) {
        debugPrint(
            '[Messaging] Failed to fetch user $otherParticipantId: $e');
        conversation.participantName = 'User';
        _userNameCache[otherParticipantId] = 'User';
      }
    }
  }

  /// Helper to add a message, with automatic deduplication
  void _addMessageUnique(String conversationId, MessageModel message) {
    try {
      // Defensive programming: ensure _messageIds is initialized
      if (_messageIds == null) {
        debugPrint('[Messaging] WARNING: _messageIds is null, reinitializing');
        return;
      }
      
      // Ensure the message ID set is initialized
      _messageIds.putIfAbsent(conversationId, () => <String>{});
      
      // Skip if we've seen this message ID before
      final ids = _messageIds[conversationId];
      if (ids != null && ids.contains(message.messageId)) {
        return;
      }

      // Ensure the messages list is initialized
      _messages.putIfAbsent(conversationId, () => []);
      _messages[conversationId]!.insert(0, message);
      
      if (_messageIds[conversationId] != null) {
        _messageIds[conversationId]!.add(message.messageId);
      }
    } catch (e) {
      debugPrint('[Messaging] Error in _addMessageUnique: $e');
    }
  }

  /// Handle incoming new message from WebSocket
  void _handleNewMessage(Map<String, dynamic> data) {
    final message = MessageModel.fromJson(data);

    // Skip messages we sent - we handle those locally with optimistic + REST
    if (message.senderId == _currentUserId) {
      return;
    }

    final conversationId = message.conversationId;

    // First, fetch sender's public key if we don't have it
    if (!_recipientPublicKeys.containsKey(message.senderId)) {
      _fetchAndDecryptMessage(message);
      return;
    }

    // Decrypt message with known key
    final decrypted = _decryptMessage(message);
    _addMessageUnique(conversationId, decrypted);

    // Update conversation preview
    _updateConversationPreview(conversationId, decrypted);

    // Populate participant name if not already set
    final convIdx = _conversations
        .indexWhere((c) => c.conversationId == conversationId);
    if (convIdx >= 0 &&
        (_conversations[convIdx].participantName == null ||
            _conversations[convIdx].participantName == 'Unknown User')) {
      _populateParticipantNames([_conversations[convIdx]]);
    }

    // If not in this conversation, increment unread  
    if (_activeConversationId != conversationId) {
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
    final readerId = data['reader_id'] as String?;

    if (conversationId == null || messageId == null) return;

    // Only process read receipts from other users (not our own)
    if (readerId == _currentUserId) return;

    final messages = _messages[conversationId];
    if (messages != null) {
      bool updated = false;
      
      // Find and mark the specific message as read
      for (final msg in messages) {
        // Only process OUR messages (messages we sent)
        if (msg.senderId != _currentUserId) continue;
        
        // Found the matching message - mark it and all earlier ones as read
        if (msg.messageId == messageId) {
          msg.status = MessageStatus.read;
          updated = true;
          // Continue to mark all earlier messages (they're before this one in time)
          continue;
        }
        
        // Mark earlier messages as read too (messages we sent before the read receipt)
        if (updated && msg.status != MessageStatus.read) {
          msg.status = MessageStatus.read;
        }
      }
      
      if (updated) {
        notifyListeners();
      }
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

      // Populate participant names
      await _populateParticipantNames(_conversations);

      notifyListeners();
    } catch (e) {
      _error = ApiClient.getErrorMessage(e);
      debugPrint('[Messaging] Load conversations error: $e');
    } finally {
      _isLoadingConversations = false;
      notifyListeners();
    }

    // After showing the list, silently decrypt real previews in the background.
    // The server stores "[text]"/"[image]" because messages are E2E encrypted.
    // We fetch the latest message for each conversation in parallel and patch
    // the preview with the actual decrypted content.
    _refreshConversationPreviews();
  }

  /// Background-fetches the latest message for every conversation that has a
  /// placeholder preview ("[text]", "[image]", etc.) and patches it with the
  /// real decrypted content. Runs all fetches concurrently and notifies once.
  Future<void> _refreshConversationPreviews() async {
    // Snapshot the list so mutations during iteration don't cause issues
    final convs = List<ConversationModel>.from(_conversations);
    if (convs.isEmpty) return;

    bool anyUpdated = false;

    await Future.wait(
      convs.map((conv) async {
        try {
          // Only fetch if the preview looks like a backend placeholder
          final preview = conv.lastMessagePreview ?? '';
          final isPlaceholder = preview.isEmpty ||
              preview == '[text]' ||
              preview == '[image]' ||
              preview == '[url]';
          if (!isPlaceholder) return;

          final messages = await _repository.getMessages(
            conv.conversationId,
            limit: 1,
          );
          if (messages.isEmpty) return;

          final decrypted = _decryptMessage(messages.first);

          // Find the conversation in the live list (not the snapshot) and patch
          final idx = _conversations
              .indexWhere((c) => c.conversationId == conv.conversationId);
          if (idx < 0) return;

          _conversations[idx] = _conversations[idx].copyWith(
            lastMessagePreview: decrypted.isImage
                ? '📷 Photo'
                : (decrypted.decryptedContent ?? preview),
          );
          anyUpdated = true;
        } catch (e) {
          debugPrint('[Messaging] Preview refresh failed for ${conv.conversationId}: $e');
        }
      }),
    );

    if (anyUpdated) notifyListeners();
  }

  /// Create or get a conversation with a user
  Future<ConversationModel> getOrCreateConversation(String otherUserId) async {
    try {
      final conversation = await _repository.createConversation(otherUserId);

      // Fetch and populate participant name
      await _populateParticipantNames([conversation]);

      // Add to list if not already present
      final exists = _conversations
          .any((c) => c.conversationId == conversation.conversationId);
      if (!exists) {
        _conversations.insert(0, conversation);
      } else {
        // Update existing conversation with new name info
        final idx = _conversations
            .indexWhere((c) => c.conversationId == conversation.conversationId);
        if (idx >= 0) {
          _conversations[idx].participantName = conversation.participantName;
          _conversations[idx].participantId = conversation.participantId;
        }
      }

      notifyListeners();
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

      // Initialize or preserve existing IDs
      _messageIds.putIfAbsent(conversationId, () => <String>{});
      
      // Build new list: server messages + any local messages not on server
      final serverIds = decrypted.map((m) => m.messageId).toSet();
      final existing = _messages[conversationId] ?? [];
      // Keep optimistic (temp) messages that aren't on the server yet
      final localOnlyMessages = existing
          .where((m) => !serverIds.contains(m.messageId) && m.messageId.startsWith('temp_'))
          .toList();

      // Replace with server messages + local-only messages
      _messages[conversationId] = [...decrypted, ...localOnlyMessages];
      
      // Update ID set
      _messageIds[conversationId] = {
        ...decrypted.map((m) => m.messageId),
        ...localOnlyMessages.map((m) => m.messageId),
      };

      // Patch the conversation preview now that we have decrypted content.
      // This corrects the "[text]" placeholder from the server.
      if (decrypted.isNotEmpty) {
        _updateConversationPreview(conversationId, decrypted.first);
      }

      // If we got fewer messages than the limit, we've reached the end
      _hasMoreMessages[conversationId] = messages.length >= 50; // 50 is the default limit

      // Send read receipt for the latest message from the OTHER user.
      // We must search for it explicitly — if OUR message is the newest overall,
      // checking only decrypted.first would miss all unread messages from them.
      if (_activeConversationId == conversationId) {
        final latestFromOther = decrypted.firstWhere(
          (m) => m.senderId != _currentUserId,
          orElse: () => decrypted.first, // will be our own, receipt won't fire below
        );
        if (latestFromOther.senderId != _currentUserId) {
          _wsService.sendReadReceipt(conversationId, latestFromOther.messageId);
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

      // Add only messages we haven't seen before
      for (final msg in decrypted) {
        _addMessageUnique(conversationId, msg);
      }

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
    _messageIds.putIfAbsent(conversationId, () => <String>{});
    
    _messages[conversationId]!.insert(0, optimistic);
    _messageIds[conversationId]!.add(optimisticId);
    
    _updateConversationPreview(conversationId, optimistic);
    notifyListeners();

    try {
      // Send via REST — the server stores the message AND broadcasts it via
      // WebSocket to all participants, so we must NOT also send via WebSocket
      // or the receiver will receive two separate stored messages with different IDs.
      final sent = await _repository.sendMessage(
        conversationId: conversationId,
        encryptedPayload: encrypted,
      );

      // Replace optimistic message with real one
      final messageList = _messages[conversationId];
      if (messageList != null) {
        final idx = messageList.indexWhere((m) => m.messageId == optimisticId);
        if (idx >= 0) {
          messageList.removeAt(idx);
          _messageIds[conversationId]?.remove(optimisticId);
          
          final real = _decryptMessage(sent);
          real.status = MessageStatus.sent;
          messageList.insert(idx, real);
          _messageIds[conversationId]?.add(sent.messageId);
          notifyListeners();
        }
      }
    } catch (e) {
      // Mark as failed
      final messageList = _messages[conversationId];
      if (messageList != null) {
        final idx = messageList.indexWhere((m) => m.messageId == optimisticId);
        if (idx >= 0) {
          messageList[idx].status = MessageStatus.failed;
          notifyListeners();
        }
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
      final messageList = _messages[conversationId];
      if (messageList != null) {
        final idx = messageList.indexWhere((m) => m.messageId == optimisticId);
        if (idx >= 0) {
          final real = _decryptMessage(sent);
          real.status = MessageStatus.sent;
          messageList[idx] = real;
        }
      }

      _updateConversationPreview(conversationId, sent);
      notifyListeners();
    } catch (e) {
      final messageList = _messages[conversationId];
      if (messageList != null) {
        final idx = messageList.indexWhere((m) => m.messageId == optimisticId);
        if (idx >= 0) {
          messageList[idx].status = MessageStatus.failed;
          notifyListeners();
        }
      }
      debugPrint('[Messaging] Image send error: $e');
    }
  }

  /// Send an image message from bytes (for web support)
  Future<void> sendImageMessageBytes(
    String conversationId,
    List<int> imageBytes,
    String filename,
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
      metadata: {'filename': filename},
      decryptedContent: filename,
    );

    _messages.putIfAbsent(conversationId, () => []);
    _messages[conversationId]!.insert(0, optimistic);
    notifyListeners();

    try {
      // Upload image bytes
      final uploadResult =
          await _repository.uploadImageBytes(conversationId, imageBytes, filename);

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
      final messageList = _messages[conversationId];
      if (messageList != null) {
        final idx = messageList.indexWhere((m) => m.messageId == optimisticId);
        if (idx >= 0) {
          final real = _decryptMessage(sent);
          real.status = MessageStatus.sent;
          messageList[idx] = real;
        }
      }

      _updateConversationPreview(conversationId, sent);
      notifyListeners();
    } catch (e) {
      final messageList = _messages[conversationId];
      if (messageList != null) {
        final idx = messageList.indexWhere((m) => m.messageId == optimisticId);
        if (idx >= 0) {
          messageList[idx].status = MessageStatus.failed;
          notifyListeners();
        }
      }
      debugPrint('[Messaging] Image bytes send error: $e');
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

  /// Fetch sender's public key and decrypt message (async)
  Future<void> _fetchAndDecryptMessage(MessageModel message) async {
    final conversationId = message.conversationId;
    
    try {
      // Ensure message ID set is initialized for this conversation
      _messageIds.putIfAbsent(conversationId, () => <String>{});
      
      final key = await _repository.getEncryptionKey(message.senderId);
      if (key != null) {
        _recipientPublicKeys[message.senderId] = key;
      }

      // Now decrypt with the fetched key
      final decrypted = _decryptMessage(message);
      _addMessageUnique(conversationId, decrypted);

      // Update conversation preview with decrypted content
      _updateConversationPreview(conversationId, decrypted);

      // Send read receipt if this conversation is currently open.
      // _handleNewMessage returns early (before sending a receipt) when the key
      // isn't cached yet, so we must send it here after the async fetch completes.
      if (_activeConversationId == conversationId) {
        _wsService.sendReadReceipt(conversationId, decrypted.messageId);
      }

      // Populate participant names as well
      final convIdx = _conversations
          .indexWhere((c) => c.conversationId == conversationId);
      if (convIdx >= 0 &&
          (_conversations[convIdx].participantName == null ||
              _conversations[convIdx].participantName == 'Unknown User')) {
        await _populateParticipantNames([_conversations[convIdx]]);
      }

      notifyListeners();
    } catch (e) {
      // If key fetch fails (404) or decryption fails, we still have the encrypted message
      // It was already added when it arrived via WebSocket if the key can't be fetched
      debugPrint('[Messaging] Error processing incoming message: $e');
    }
  }

  MessageModel _decryptMessage(MessageModel message) {
    try {
      final senderKey = _recipientPublicKeys[message.senderId];
      final decrypted = _encryptionService.decryptMessage(
        message.encryptedPayload,
        senderPublicKey: senderKey,
      );
      return message.copyWith(decryptedContent: decrypted);
    } catch (e) {
      debugPrint('[Messaging] Decryption error for ${message.messageId}: $e');
      return message.copyWith(decryptedContent: '[Encrypted message]');
    }
  }

  /// Get recipient's public key for a conversation
  Future<String?> _getRecipientKey(String conversationId) async {
    final matches = _conversations.where((c) => c.conversationId == conversationId);
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
      // Never fall back to the raw encrypted payload — show a placeholder instead
      final previewText = message.isImage
          ? '📷 Photo'
          : (message.decryptedContent?.isNotEmpty == true
              ? message.decryptedContent!
              : '…');
      _conversations[idx] = conv.copyWith(
        lastMessagePreview: previewText,
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
