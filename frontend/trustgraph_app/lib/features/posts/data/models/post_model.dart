class PostModel {
  final String postId;
  final String startupId;
  final String startupName;
  final String authorUserId;
  final String authorName;
  final String title;
  final String body;
  final List<String> tags;
  final List<String> mediaUrls;
  final int likeCount;
  final int commentCount;
  final bool isPinned;
  final DateTime createdAt;
  final DateTime updatedAt;

  // Transient field — managed by provider, not from server
  bool isLikedByCurrentUser;

  PostModel({
    required this.postId,
    required this.startupId,
    required this.startupName,
    required this.authorUserId,
    required this.authorName,
    required this.title,
    required this.body,
    this.tags = const [],
    this.mediaUrls = const [],
    this.likeCount = 0,
    this.commentCount = 0,
    this.isPinned = false,
    required this.createdAt,
    required this.updatedAt,
    this.isLikedByCurrentUser = false,
  });

  factory PostModel.fromJson(Map<String, dynamic> json) {
    return PostModel(
      postId: json['post_id'],
      startupId: json['startup_id'],
      startupName: json['startup_name'] ?? '',
      authorUserId: json['author_user_id'],
      authorName: json['author_name'] ?? 'Unknown',
      title: json['title'],
      body: json['body'],
      tags: List<String>.from(json['tags'] ?? []),
      mediaUrls: List<String>.from(json['media_urls'] ?? []),
      likeCount: json['like_count'] ?? 0,
      commentCount: json['comment_count'] ?? 0,
      isPinned: json['is_pinned'] ?? false,
      createdAt: DateTime.parse(json['created_at']),
      updatedAt: DateTime.parse(json['updated_at']),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'post_id': postId,
      'startup_id': startupId,
      'startup_name': startupName,
      'author_user_id': authorUserId,
      'author_name': authorName,
      'title': title,
      'body': body,
      'tags': tags,
      'media_urls': mediaUrls,
      'like_count': likeCount,
      'comment_count': commentCount,
      'is_pinned': isPinned,
      'created_at': createdAt.toIso8601String(),
      'updated_at': updatedAt.toIso8601String(),
    };
  }

  PostModel copyWith({
    int? likeCount,
    int? commentCount,
    bool? isLikedByCurrentUser,
  }) {
    return PostModel(
      postId: postId,
      startupId: startupId,
      startupName: startupName,
      authorUserId: authorUserId,
      authorName: authorName,
      title: title,
      body: body,
      tags: tags,
      mediaUrls: mediaUrls,
      likeCount: likeCount ?? this.likeCount,
      commentCount: commentCount ?? this.commentCount,
      isPinned: isPinned,
      createdAt: createdAt,
      updatedAt: updatedAt,
      isLikedByCurrentUser: isLikedByCurrentUser ?? this.isLikedByCurrentUser,
    );
  }
}
