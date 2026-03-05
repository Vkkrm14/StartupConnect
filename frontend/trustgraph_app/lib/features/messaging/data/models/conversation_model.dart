import 'package:intl/intl.dart';

class ConversationModel {
  final String conversationId;
  final List<String> participants;
  final DateTime createdAt;
  final DateTime updatedAt;
  final String? lastMessagePreview;
  final DateTime? lastMessageAt;
  final String? lastMessageType;
  int unreadCount;
  bool isOnline;
  bool isTyping;

  // Participant display info (filled in later)
  String? participantName;
  String? participantAvatar;
  String? participantId;

  ConversationModel({
    required this.conversationId,
    required this.participants,
    required this.createdAt,
    required this.updatedAt,
    this.lastMessagePreview,
    this.lastMessageAt,
    this.lastMessageType,
    this.unreadCount = 0,
    this.isOnline = false,
    this.isTyping = false,
    this.participantName,
    this.participantAvatar,
    this.participantId,
  });

  factory ConversationModel.fromJson(Map<String, dynamic> json) {
    return ConversationModel(
      conversationId: json['conversation_id'] ?? '',
      participants: List<String>.from(json['participants'] ?? []),
      createdAt: DateTime.tryParse(json['created_at'] ?? '') ?? DateTime.now(),
      updatedAt: DateTime.tryParse(json['updated_at'] ?? '') ?? DateTime.now(),
      lastMessagePreview: json['last_message_preview'],
      lastMessageAt: json['last_message_at'] != null
          ? DateTime.tryParse(json['last_message_at'])
          : null,
      lastMessageType: json['last_message_type'],
      unreadCount: json['unread_count'] ?? 0,
    );
  }

  Map<String, dynamic> toJson() => {
        'conversation_id': conversationId,
        'participants': participants,
        'created_at': createdAt.toIso8601String(),
        'updated_at': updatedAt.toIso8601String(),
        'last_message_preview': lastMessagePreview,
        'last_message_at': lastMessageAt?.toIso8601String(),
        'last_message_type': lastMessageType,
      };

  /// Get the other participant given the current user's ID
  String getOtherParticipant(String currentUserId) {
    return participants.firstWhere(
      (p) => p != currentUserId,
      orElse: () => '',
    );
  }

  /// Smart timestamp formatting
  String get formattedTime {
    final target = lastMessageAt ?? updatedAt;
    final now = DateTime.now();
    final diff = now.difference(target);

    if (diff.inSeconds < 60) return 'now';
    if (diff.inMinutes < 60) return '${diff.inMinutes}m ago';
    if (diff.inHours < 24) return '${diff.inHours}h ago';
    if (diff.inDays == 1) return 'yesterday';
    if (diff.inDays < 7) return DateFormat('EEEE').format(target);
    return DateFormat('MMM d').format(target);
  }

  /// Preview text for last message
  String get displayPreview {
    if (lastMessageType == 'image') return '📷 Photo';
    if (lastMessageType == 'url') return '🔗 Link';
    return lastMessagePreview ?? 'Start a conversation';
  }

  ConversationModel copyWith({
    String? lastMessagePreview,
    DateTime? lastMessageAt,
    String? lastMessageType,
    DateTime? updatedAt,
    int? unreadCount,
    bool? isOnline,
    bool? isTyping,
  }) {
    return ConversationModel(
      conversationId: conversationId,
      participants: participants,
      createdAt: createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      lastMessagePreview: lastMessagePreview ?? this.lastMessagePreview,
      lastMessageAt: lastMessageAt ?? this.lastMessageAt,
      lastMessageType: lastMessageType ?? this.lastMessageType,
      unreadCount: unreadCount ?? this.unreadCount,
      isOnline: isOnline ?? this.isOnline,
      isTyping: isTyping ?? this.isTyping,
      participantName: participantName,
      participantAvatar: participantAvatar,
      participantId: participantId,
    );
  }
}
