/// Model representing a DISTRUSTS edge between two users in the graph database.
/// Maps to the backend DisTrustsEdgeResponse schema.
class DisTrustEdgeModel {
  final String edgeId;
  final String fromUserId;
  final String toUserId;
  final double distrustScore; // -1.0 to -0.0
  final String reasonCategory; // fraud, unreliable_collaborator, harassment, dispute
  final double severity; // 0.0 to 1.0
  final bool isActive;
  final bool isDisputed;
  final int disputeCount;
  final bool moderatorReviewed;
  final DateTime createdAt;
  final DateTime expiresAt;
  
  // Conflict resolution fields
  final String? appealReason;
  final String? resolutionType; // mutual_resolution, invalid, mediated, expired
  final DateTime? resolvedAt;

  // Optional: resolved display names (populated by the frontend)
  final String? fromUserName;
  final String? toUserName;

  DisTrustEdgeModel({
    required this.edgeId,
    required this.fromUserId,
    required this.toUserId,
    this.distrustScore = -0.5,
    this.reasonCategory = 'dispute',
    this.severity = 0.5,
    this.isActive = false,
    this.isDisputed = false,
    this.disputeCount = 0,
    this.moderatorReviewed = false,
    required this.createdAt,
    required this.expiresAt,
    this.appealReason,
    this.resolutionType,
    this.resolvedAt,
    this.fromUserName,
    this.toUserName,
  });

  factory DisTrustEdgeModel.fromJson(Map<String, dynamic> json) {
    return DisTrustEdgeModel(
      edgeId: json['edge_id'] ?? '',
      fromUserId: json['from_user_id'] ?? '',
      toUserId: json['to_user_id'] ?? '',
      distrustScore: (json['distrust_score'] ?? -0.5).toDouble(),
      reasonCategory: json['reason_category'] ?? 'dispute',
      severity: (json['severity'] ?? 0.5).toDouble(),
      isActive: json['is_active'] ?? false,
      isDisputed: json['is_disputed'] ?? false,
      disputeCount: json['dispute_count'] ?? 0,
      moderatorReviewed: json['moderator_reviewed'] ?? false,
      createdAt: json['created_at'] != null
          ? DateTime.parse(json['created_at'])
          : DateTime.now(),
      expiresAt: json['expires_at'] != null
          ? DateTime.parse(json['expires_at'])
          : DateTime.now().add(Duration(days: 365)),
      appealReason: json['appeal_reason'],
      resolutionType: json['resolution_type'],
      resolvedAt: json['resolved_at'] != null
          ? DateTime.parse(json['resolved_at'])
          : null,
      fromUserName: json['from_user_name'],
      toUserName: json['to_user_name'],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'edge_id': edgeId,
      'from_user_id': fromUserId,
      'to_user_id': toUserId,
      'distrust_score': distrustScore,
      'reason_category': reasonCategory,
      'severity': severity,
      'is_active': isActive,
      'is_disputed': isDisputed,
      'dispute_count': disputeCount,
      'moderator_reviewed': moderatorReviewed,
      'created_at': createdAt.toIso8601String(),
      'expires_at': expiresAt.toIso8601String(),
      'appeal_reason': appealReason,
      'resolution_type': resolutionType,
      'resolved_at': resolvedAt?.toIso8601String(),
    };
  }

  bool get isPending => !isActive && !moderatorReviewed;
  bool get isResolved => resolutionType != null && resolvedAt != null;

  /// Check if distrust is currently enforced (active and not disputed)
  bool get isEnforced => isActive && !isDisputed;

  /// Get human-readable reason
  String get reasonLabel {
    switch (reasonCategory) {
      case 'fraud':
        return 'Fraud Report';
      case 'unreliable_collaborator':
        return 'Unreliable Collaborator';
      case 'harassment':
        return 'Harassment';
      case 'dispute':
        return 'Dispute';
      default:
        return 'Reported Distrust';
    }
  }

  /// Get severity description
  String get severityLevel {
    if (severity >= 0.7) return 'high';
    if (severity >= 0.3) return 'medium';
    return 'low';
  }

  /// Get display status
  String get displayStatus {
    if (isResolved) return 'Resolved (${resolutionType})';
    if (isPending) return 'Pending Review';
    if (isDisputed) return 'Disputed';
    if (isActive) return 'Active';
    return 'Unknown';
  }

  /// Check if distrust has expired
  bool get isExpired {
    return DateTime.now().isAfter(expiresAt);
  }

  /// Get time until expiration
  Duration get timeToExpiration {
    final now = DateTime.now();
    if (now.isAfter(expiresAt)) {
      return Duration.zero;
    }
    return expiresAt.difference(now);
  }
}
