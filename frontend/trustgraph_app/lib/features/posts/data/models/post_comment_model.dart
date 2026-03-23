class PostCommentModel {
  final String commentId;
  final String postId;
  final String authorUserId;
  final String authorName;
  final String body;
  final DateTime createdAt;
  final DateTime updatedAt;

  PostCommentModel({
    required this.commentId,
    required this.postId,
    required this.authorUserId,
    required this.authorName,
    required this.body,
    required this.createdAt,
    required this.updatedAt,
  });

  factory PostCommentModel.fromJson(Map<String, dynamic> json) {
    return PostCommentModel(
      commentId: (json['comment_id'] ?? json['id'] ?? '').toString(),
      postId: (json['post_id'] ?? '').toString(),
      authorUserId: (json['author_user_id'] ?? '').toString(),
      authorName: (json['author_name'] ?? 'Unknown').toString(),
      body: (json['body'] ?? '').toString(),
      createdAt: DateTime.tryParse((json['created_at'] ?? '').toString()) ??
          DateTime.now(),
      updatedAt: DateTime.tryParse((json['updated_at'] ?? '').toString()) ??
          DateTime.now(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'comment_id': commentId,
      'post_id': postId,
      'author_user_id': authorUserId,
      'author_name': authorName,
      'body': body,
      'created_at': createdAt.toIso8601String(),
      'updated_at': updatedAt.toIso8601String(),
    };
  }
}