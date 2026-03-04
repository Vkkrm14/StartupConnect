import 'package:flutter/material.dart';
import '../theme/messaging_theme.dart';

/// Skeleton loader for conversation list
class ConversationSkeleton extends StatefulWidget {
  final int itemCount;

  const ConversationSkeleton({super.key, this.itemCount = 8});

  @override
  State<ConversationSkeleton> createState() => _ConversationSkeletonState();
}

class _ConversationSkeletonState extends State<ConversationSkeleton>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    )..repeat();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return AnimatedBuilder(
      animation: _controller,
      builder: (context, child) {
        return ListView.builder(
          physics: const NeverScrollableScrollPhysics(),
          itemCount: widget.itemCount,
          padding: EdgeInsets.zero,
          itemBuilder: (context, index) {
            return _buildSkeletonTile(isDark);
          },
        );
      },
    );
  }

  Widget _buildSkeletonTile(bool isDark) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      child: Row(
        children: [
          // Avatar skeleton
          _buildShimmerBox(
            width: 52,
            height: 52,
            borderRadius: 26,
            isDark: isDark,
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _buildShimmerBox(
                  width: 120,
                  height: 14,
                  borderRadius: 4,
                  isDark: isDark,
                ),
                const SizedBox(height: 8),
                _buildShimmerBox(
                  width: 200,
                  height: 12,
                  borderRadius: 4,
                  isDark: isDark,
                ),
              ],
            ),
          ),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              _buildShimmerBox(
                width: 40,
                height: 10,
                borderRadius: 4,
                isDark: isDark,
              ),
              const SizedBox(height: 8),
              _buildShimmerBox(
                width: 22,
                height: 22,
                borderRadius: 11,
                isDark: isDark,
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildShimmerBox({
    required double width,
    required double height,
    required double borderRadius,
    required bool isDark,
  }) {
    return Container(
      width: width,
      height: height,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(borderRadius),
        gradient: LinearGradient(
          begin: Alignment(-1.0 + 2.0 * _controller.value, 0),
          end: Alignment(1.0 + 2.0 * _controller.value, 0),
          colors: isDark
              ? [
                  const Color(0xFF1F2937),
                  const Color(0xFF374151),
                  const Color(0xFF1F2937),
                ]
              : [
                  MessagingTheme.shimmerBase,
                  MessagingTheme.shimmerHighlight,
                  MessagingTheme.shimmerBase,
                ],
        ),
      ),
    );
  }
}

/// Empty state for conversation list
class EmptyConversationsState extends StatelessWidget {
  const EmptyConversationsState({super.key});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            // Illustration
            Container(
              width: 120,
              height: 120,
              decoration: BoxDecoration(
                color: isDark
                    ? const Color(0xFF1F2937)
                    : const Color(0xFFF1F5F9),
                shape: BoxShape.circle,
              ),
              child: Icon(
                Icons.chat_bubble_outline_rounded,
                size: 56,
                color: isDark
                    ? const Color(0xFF475569)
                    : const Color(0xFFCBD5E1),
              ),
            ),
            const SizedBox(height: 24),
            Text(
              'No conversations yet',
              style: TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.w600,
                color: isDark ? Colors.white : const Color(0xFF1E293B),
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'Start a conversation with one of your\nconnections to get started!',
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 14,
                height: 1.5,
                color: isDark
                    ? MessagingTheme.timestampDark
                    : MessagingTheme.timestampLight,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
