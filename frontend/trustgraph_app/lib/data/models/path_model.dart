class PathModel {
  final List<PathNode> nodes;
  final List<PathEdge> edges;
  final int hopCount;
  final double pathScore;
  final double successProbability;
  final String explanation;
  
  PathModel({
    required this.nodes,
    required this.edges,
    required this.hopCount,
    required this.pathScore,
    required this.successProbability,
    required this.explanation,
  });
  
  factory PathModel.fromJson(Map<String, dynamic> json) {
    return PathModel(
      nodes: (json['nodes'] as List)
          .map((n) => PathNode.fromJson(n))
          .toList(),
      edges: (json['edges'] as List)
          .map((e) => PathEdge.fromJson(e))
          .toList(),
      hopCount: json['hop_count'],
      pathScore: json['path_score'].toDouble(),
      successProbability: json['success_probability'].toDouble(),
      explanation: json['explanation'],
    );
  }
}

class PathNode {
  final String userId;
  final String name;
  final String role;
  final double reputationScore;
  
  PathNode({
    required this.userId,
    required this.name,
    required this.role,
    required this.reputationScore,
  });
  
  factory PathNode.fromJson(Map<String, dynamic> json) {
    return PathNode(
      userId: json['user_id'],
      name: json['name'],
      role: json['role'],
      reputationScore: json['reputation_score'].toDouble(),
    );
  }
}

class PathEdge {
  final String from;
  final String to;
  final double trust;
  final double strength;
  final double recency;
  final bool mutual;
  
  PathEdge({
    required this.from,
    required this.to,
    required this.trust,
    required this.strength,
    required this.recency,
    required this.mutual,
  });
  
  factory PathEdge.fromJson(Map<String, dynamic> json) {
    return PathEdge(
      from: json['from'],
      to: json['to'],
      trust: json['trust'].toDouble(),
      strength: json['strength'].toDouble(),
      recency: json['recency'].toDouble(),
      mutual: json['mutual'] ?? false,
    );
  }
}
