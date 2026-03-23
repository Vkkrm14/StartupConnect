import 'package:flutter/material.dart';
import '../data/models/trust_edge_model.dart';
import '../data/models/distrust_edge_model.dart';

/// Widget to display a trust level with visual indicators.
/// Supports both positive trust (TRUSTS edges) and negative trust (DISTRUSTS edges).
class TrustLevelWidget extends StatelessWidget {
  final double trustScore; // -1.0 to 1.0
  final String? label;
  final bool isDistrust; // true for DISTRUSTS, false for TRUSTS
  final bool isDisputed; // relevant for DISTRUSTS
  final double? size; // Size of the indicator (diameter for circle)

  const TrustLevelWidget({
    Key? key,
    required this.trustScore,
    this.label,
    this.isDistrust = false,
    this.isDisputed = false,
    this.size = 60,
  }) : super(key: key);

  Color getColorForScore(double score) {
    // Handle distrust colors (negative scores)
    if (isDistrust) {
      if (isDisputed) {
        return Colors.orange; // Disputed distrust
      }
      final absoluteScore = score.abs(); // Convert to 0-1 range
      if (absoluteScore >= 0.7) return Colors.red; // Strong distrust
      if (absoluteScore >= 0.4) return Colors.red.shade300; // Medium distrust
      return Colors.orange; // Low distrust
    }

    // Handle trust colors (positive scores)
    if (score >= 0.7) return Colors.green; // High trust
    if (score >= 0.4) return Colors.blue; // Medium trust
    if (score > 0) return Colors.blue.shade200; // Low trust
    return Colors.grey; // Neutral (0)
  }

  String getScoreLabel(double score) {
    if (isDistrust) {
      if (isDisputed) return 'Disputed';
      if (score <= -0.7) return 'High Distrust';
      if (score <= -0.4) return 'Medium Distrust';
      return 'Low Distrust';
    }

    if (score >= 0.7) return 'High Trust';
    if (score >= 0.4) return 'Medium Trust';
    if (score > 0) return 'Low Trust';
    return 'Neutral';
  }

  IconData getIconForScore(double score) {
    if (isDistrust) {
      if (isDisputed) return Icons.help_outline;
      if (score <= -0.7) return Icons.block;
      if (score <= -0.4) return Icons.warning;
      return Icons.warning_amber;
    }

    if (score >= 0.7) return Icons.check_circle;
    if (score >= 0.4) return Icons.thumb_up;
    if (score > 0) return Icons.sentiment_satisfied;
    return Icons.circle;
  }

  @override
  Widget build(BuildContext context) {
    final color = getColorForScore(trustScore);
    final label = getScoreLabel(trustScore);
    final icon = getIconForScore(trustScore);

    return Tooltip(
      message: label,
      child: Container(
        width: size,
        height: size,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: color.withOpacity(0.1),
          border: Border.all(color: color, width: 2),
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, color: color, size: size! * 0.4),
            SizedBox(height: 2),
            Text(
              '${trustScore.abs().toStringAsFixed(2)}',
              style: TextStyle(
                fontSize: size! * 0.2,
                fontWeight: FontWeight.bold,
                color: color,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Widget to display a horizontal trust score bar.
class TrustScoreBar extends StatelessWidget {
  final double trustScore; // -1.0 to 1.0
  final String? label;
  final bool isDistrust;
  final bool isDisputed;
  final double height;

  const TrustScoreBar({
    Key? key,
    required this.trustScore,
    this.label,
    this.isDistrust = false,
    this.isDisputed = false,
    this.height = 20,
  }) : super(key: key);

  Color getColorForScore(double score) {
    if (isDistrust) {
      if (isDisputed) return Colors.orange;
      if (score.abs() >= 0.7) return Colors.red;
      if (score.abs() >= 0.4) return Colors.red.shade300;
      return Colors.orange;
    }

    if (score >= 0.7) return Colors.green;
    if (score >= 0.4) return Colors.blue;
    if (score > 0) return Colors.blue.shade200;
    return Colors.grey;
  }

  @override
  Widget build(BuildContext context) {
    // For negative trust, position bar from right to left
    if (isDistrust) {
      final width = trustScore.abs(); // Convert to positive
      return Tooltip(
        message: '${trustScore.toStringAsFixed(2)} (${isDisputed ? 'Disputed' : 'Distrust'})',
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (label != null) ...[
              Text(
                label!,
                style: Theme.of(context).textTheme.bodySmall,
              ),
              SizedBox(height: 4),
            ],
            Stack(
              children: [
                // Background
                Container(
                  height: height,
                  width: double.infinity,
                  decoration: BoxDecoration(
                    color: Colors.grey.shade300,
                    borderRadius: BorderRadius.circular(height / 2),
                  ),
                ),
                // Distrust bar (from right)
                Align(
                  alignment: Alignment.centerRight,
                  child: Container(
                    height: height,
                    width: width * 100, // Scale to width
                    decoration: BoxDecoration(
                      color: getColorForScore(trustScore),
                      borderRadius: BorderRadius.circular(height / 2),
                    ),
                  ),
                ),
              ],
            ),
          ],
        ),
      );
    }

    // For positive trust, position bar from left to right
    return Tooltip(
      message: '${trustScore.toStringAsFixed(2)} (Trust)',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (label != null) ...[
            Text(
              label!,
              style: Theme.of(context).textTheme.bodySmall,
            ),
            SizedBox(height: 4),
          ],
          Stack(
            children: [
              // Background
              Container(
                height: height,
                width: double.infinity,
                decoration: BoxDecoration(
                  color: Colors.grey.shade300,
                  borderRadius: BorderRadius.circular(height / 2),
                ),
              ),
              // Trust bar (from left)
              Container(
                height: height,
                width: trustScore * 100, // Scale to width (0-100)
                decoration: BoxDecoration(
                  color: getColorForScore(trustScore),
                  borderRadius: BorderRadius.circular(height / 2),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

/// Widget to display full trust relationship status including both TRUSTS and DISTRUSTS
class TrustRelationshipCard extends StatelessWidget {
  final TrustEdgeModel? trustEdge;
  final DisTrustEdgeModel? distrustEdge;
  final String userName;
  final VoidCallback? onTap;

  const TrustRelationshipCard({
    Key? key,
    this.trustEdge,
    this.distrustEdge,
    required this.userName,
    this.onTap,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Card(
        child: Padding(
          padding: EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // User name
              Text(
                userName,
                style: Theme.of(context).textTheme.titleMedium,
              ),
              SizedBox(height: 12),

              // Trust score if available
              if (trustEdge != null) ...[
                Text(
                  'Trust Level',
                  style: Theme.of(context).textTheme.labelSmall,
                ),
                SizedBox(height: 8),
                TrustScoreBar(
                  trustScore: trustEdge!.trustScore,
                  label: trustEdge!.trustLevel.toUpperCase(),
                ),
                SizedBox(height: 12),
              ],

              // Distrust indicator if available
              if (distrustEdge != null) ...[
                Container(
                  padding: EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: distrustEdge!.isDisputed
                        ? Colors.orange.shade50
                        : Colors.red.shade50,
                    border: Border.all(
                      color: distrustEdge!.isDisputed
                          ? Colors.orange
                          : Colors.red,
                    ),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Icon(
                            distrustEdge!.isDisputed
                                ? Icons.warning
                                : Icons.block,
                            color: distrustEdge!.isDisputed
                                ? Colors.orange
                                : Colors.red,
                            size: 20,
                          ),
                          SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              distrustEdge!.reasonLabel,
                              style: TextStyle(
                                fontWeight: FontWeight.bold,
                                color: distrustEdge!.isDisputed
                                    ? Colors.orange
                                    : Colors.red,
                              ),
                            ),
                          ),
                        ],
                      ),
                      SizedBox(height: 8),
                      Text(
                        'Status: ${distrustEdge!.displayStatus}',
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                      if (distrustEdge!.isDisputed) ...[
                        SizedBox(height: 4),
                        Text(
                          'This distrust is being disputed',
                          style: TextStyle(
                            fontSize: 12,
                            color: Colors.orange.shade700,
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              ],

              // Show both if present
              if (trustEdge != null && distrustEdge != null) ...[
                SizedBox(height: 12),
                Divider(),
                SizedBox(height: 12),
                Container(
                  padding: EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: Colors.yellow.shade50,
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Row(
                    children: [
                      Icon(Icons.warning_amber, size: 16, color: Colors.orange),
                      SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          'Conflicting relationship: Trust and Distrust edges exist',
                          style: TextStyle(fontSize: 12),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

/// Widget to display a trust score range label
class TrustScoreLabel extends StatelessWidget {
  final double trustScore;
  final TextStyle? style;

  const TrustScoreLabel({
    Key? key,
    required this.trustScore,
    this.style,
  }) : super(key: key);

  String getLabel() {
    if (trustScore >= 0.7) return '🟢 High Trust';
    if (trustScore >= 0.4) return '🔵 Medium Trust';
    if (trustScore > 0) return '🔷 Low Trust';
    if (trustScore == 0) return '⚪ Neutral';
    if (trustScore <= -0.7) return '🔴 Strong Distrust';
    if (trustScore <= -0.4) return '🟠 Distrust';
    return '🟡 Low Distrust';
  }

  @override
  Widget build(BuildContext context) {
    return Text(
      getLabel(),
      style: style ?? Theme.of(context).textTheme.bodyMedium,
    );
  }
}
