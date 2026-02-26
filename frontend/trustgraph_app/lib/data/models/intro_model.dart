class IntroModel {
  final String introId;
  final String requesterId;
  final String founderId;
  final String investorId;
  final List<String> pathNodes;
  final int currentNodeIndex;
  final String status;
  final String message;
  final DateTime createdAt;
  final DateTime updatedAt;
  
  IntroModel({
    required this.introId,
    required this.requesterId,
    required this.founderId,
    required this.investorId,
    required this.pathNodes,
    this.currentNodeIndex = 0,
    this.status = 'pending',
    required this.message,
    required this.createdAt,
    required this.updatedAt,
  });
  
  factory IntroModel.fromJson(Map<String, dynamic> json) {
    return IntroModel(
      introId: json['intro_id'],
      requesterId: json['requester_id'],
      founderId: json['founder_id'],
      investorId: json['investor_id'],
      pathNodes: List<String>.from(json['path_nodes']),
      currentNodeIndex: json['current_node_index'] ?? 0,
      status: json['status'] ?? 'pending',
      message: json['message'],
      createdAt: DateTime.parse(json['created_at']),
      updatedAt: DateTime.parse(json['updated_at']),
    );
  }
}
