enum MessageType { text, image, url }

enum MessageStatus { sending, sent, delivered, read, failed }

class MessageModel {
  final String messageId;
  final String conversationId;
  final String senderId;
  final String encryptedPayload;
  final String? encryptedKey;
  final MessageType messageType;
  final Map<String, dynamic>? metadata;
  final DateTime createdAt;
  MessageStatus status;

  // Decrypted content (populated after decryption)
  String? decryptedContent;

  MessageModel({
    required this.messageId,
    required this.conversationId,
    required this.senderId,
    required this.encryptedPayload,
    this.encryptedKey,
    this.messageType = MessageType.text,
    this.metadata,
    required this.createdAt,
    this.status = MessageStatus.sent,
    this.decryptedContent,
  });

  factory MessageModel.fromJson(Map<String, dynamic> json) {
    return MessageModel(
      messageId: json['message_id'] ?? '',
      conversationId: json['conversation_id'] ?? '',
      senderId: json['sender_id'] ?? '',
      encryptedPayload: json['encrypted_payload'] ?? '',
      encryptedKey: json['encrypted_key'],
      messageType: _parseMessageType(json['message_type']),
      metadata: json['metadata'] as Map<String, dynamic>?,
      createdAt: DateTime.tryParse(json['created_at'] ?? '') ?? DateTime.now(),
      status: _parseStatus(json['status']),
    );
  }

  Map<String, dynamic> toJson() => {
        'message_id': messageId,
        'conversation_id': conversationId,
        'sender_id': senderId,
        'encrypted_payload': encryptedPayload,
        'encrypted_key': encryptedKey,
        'message_type': messageType.name,
        'metadata': metadata,
        'created_at': createdAt.toIso8601String(),
      };

  /// For sending via API / WebSocket
  Map<String, dynamic> toSendPayload() => {
        'conversation_id': conversationId,
        'encrypted_payload': encryptedPayload,
        'encrypted_key': encryptedKey,
        'message_type': messageType.name,
        if (metadata != null) 'metadata': metadata,
      };

  bool get isText => messageType == MessageType.text;
  bool get isImage => messageType == MessageType.image;
  bool get isUrl => messageType == MessageType.url;

  bool isMine(String currentUserId) => senderId == currentUserId;

  static MessageType _parseMessageType(String? type) {
    switch (type) {
      case 'image':
        return MessageType.image;
      case 'url':
        return MessageType.url;
      default:
        return MessageType.text;
    }
  }

  static MessageStatus _parseStatus(String? status) {
    switch (status) {
      case 'sending':
        return MessageStatus.sending;
      case 'delivered':
        return MessageStatus.delivered;
      case 'read':
        return MessageStatus.read;
      case 'failed':
        return MessageStatus.failed;
      default:
        return MessageStatus.sent;
    }
  }

  MessageModel copyWith({
    MessageStatus? status,
    String? decryptedContent,
  }) {
    return MessageModel(
      messageId: messageId,
      conversationId: conversationId,
      senderId: senderId,
      encryptedPayload: encryptedPayload,
      encryptedKey: encryptedKey,
      messageType: messageType,
      metadata: metadata,
      createdAt: createdAt,
      status: status ?? this.status,
      decryptedContent: decryptedContent ?? this.decryptedContent,
    );
  }
}
