/// Model representing a TRUSTS edge between two users in the graph database.
/// Maps to the backend TrustsEdgeResponse schema.
class TrustEdgeModel {
  final String edgeId;
  final String fromUserId;
  final String toUserId;
  final double trustScore;
  final double strengthScore;
  final double recencyScore;
  final int interactionCount;
  final int endorsementCount;
  final List<String> domainTags;
  final int successfulIntros;
  final bool isMutual;
  final String status; // pending | accepted | rejected
  final DateTime? lastInteractionAt;
  final DateTime createdAt;

  // Optional: resolved display names (populated by the frontend)
  final String? fromUserName;
  final String? toUserName;

  TrustEdgeModel({
    required this.edgeId,
    required this.fromUserId,
    required this.toUserId,
    this.trustScore = 0.0,
    this.strengthScore = 0.5,
    this.recencyScore = 1.0,
    this.interactionCount = 0,
    this.endorsementCount = 0,
    this.domainTags = const [],
    this.successfulIntros = 0,
    this.isMutual = false,
    this.status = 'pending',
    this.lastInteractionAt,
    required this.createdAt,
    this.fromUserName,
    this.toUserName,
  });

  factory TrustEdgeModel.fromJson(Map<String, dynamic> json) {
    return TrustEdgeModel(
      edgeId: json['edge_id'] ?? '',
      fromUserId: json['from_user_id'] ?? '',
      toUserId: json['to_user_id'] ?? '',
      trustScore: (json['trust_score'] ?? 0.0).toDouble(),
      strengthScore: (json['strength_score'] ?? 0.5).toDouble(),
      recencyScore: (json['recency_score'] ?? 1.0).toDouble(),
      interactionCount: json['interaction_count'] ?? 0,
      endorsementCount: json['endorsement_count'] ?? 0,
      domainTags: List<String>.from(json['domain_tags'] ?? []),
      successfulIntros: json['successful_intros'] ?? 0,
      isMutual: json['is_mutual'] ?? false,
      status: json['status'] ?? 'pending',
      lastInteractionAt: json['last_interaction_at'] != null
          ? DateTime.parse(json['last_interaction_at'])
          : null,
      createdAt: json['created_at'] != null
          ? DateTime.parse(json['created_at'])
          : DateTime.now(),
      fromUserName: json['from_user_name'],
      toUserName: json['to_user_name'],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'edge_id': edgeId,
      'from_user_id': fromUserId,
      'to_user_id': toUserId,
      'trust_score': trustScore,
      'strength_score': strengthScore,
      'recency_score': recencyScore,
      'interaction_count': interactionCount,
      'endorsement_count': endorsementCount,
      'domain_tags': domainTags,
      'successful_intros': successfulIntros,
      'is_mutual': isMutual,
      'status': status,
      'last_interaction_at': lastInteractionAt?.toIso8601String(),
      'created_at': createdAt.toIso8601String(),
    };
  }

  bool get isPending => status == 'pending';
  bool get isAccepted => status == 'accepted';
  bool get isRejected => status == 'rejected';

  String get trustLevel {
    // Now supports negative trust scores (-1.0 to 1.0)
    if (trustScore >= 0.7) return 'high';
    if (trustScore >= 0.4) return 'medium';
    if (trustScore > 0) return 'low';
    if (trustScore == 0) return 'neutral';
    // Negative scores indicate low trust or distrust tendency
    if (trustScore <= -0.7) return 'very_low';
    if (trustScore <= -0.4) return 'low_negative';
    return 'low';
  }

  /// Check if this TRUSTS edge has conflicting distrust signal
  bool get hasDistrustOverride => trustScore < 0;
}
