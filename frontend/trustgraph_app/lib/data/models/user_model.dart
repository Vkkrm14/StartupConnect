class UserModel {
  final String userId;
  final String name;
  final String? email;
  final String? bio;
  final String rolePrimary;
  final List<String> rolesSecondary;
  final List<String> domainTags;
  final String? geography;
  final int experienceYears;
  final double reputationScore;
  final String verificationStatus;
  final DateTime createdAt;
  
  UserModel({
    required this.userId,
    required this.name,
    this.email,
    this.bio,
    required this.rolePrimary,
    this.rolesSecondary = const [],
    this.domainTags = const [],
    this.geography,
    this.experienceYears = 0,
    this.reputationScore = 0.5,
    this.verificationStatus = 'unverified',
    required this.createdAt,
  });
  
  factory UserModel.fromJson(Map<String, dynamic> json) {
    List<String> safeStringList(dynamic value) {
      if (value is List) {
        return value
            .where((e) => e != null)
            .map((e) => e.toString())
            .toList();
      }
      return const [];
    }

    return UserModel(
      userId: (json['user_id'] ?? '').toString(),
      name: (json['name'] ?? '').toString(),
      email: json['email']?.toString(),
      bio: json['bio']?.toString(),
      rolePrimary: (json['role_primary'] ?? '').toString(),
      rolesSecondary: safeStringList(json['roles_secondary']),
      domainTags: safeStringList(json['domain_tags']),
      geography: json['geography']?.toString(),
      experienceYears: json['experience_years'] ?? 0,
      reputationScore: (json['reputation_score'] ?? 0.0).toDouble(),
      verificationStatus: (json['verification_status'] ?? 'unverified').toString(),
      createdAt: json['created_at'] != null
          ? DateTime.parse(json['created_at'].toString())
          : DateTime.now(),
    );
  }
  
  Map<String, dynamic> toJson() {
    return {
      'user_id': userId,
      'name': name,
      'email': email,
      'bio': bio,
      'role_primary': rolePrimary,
      'roles_secondary': rolesSecondary,
      'domain_tags': domainTags,
      'geography': geography,
      'experience_years': experienceYears,
      'reputation_score': reputationScore,
      'verification_status': verificationStatus,
      'created_at': createdAt.toIso8601String(),
    };
  }
}
