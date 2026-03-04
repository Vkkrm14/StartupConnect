import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../../data/models/conversation_model.dart';
import '../theme/messaging_theme.dart';

/// Premium conversation list tile with avatar, online indicator,
/// unread badge, swipe actions, and smooth animations.
class ConversationTile extends StatelessWidget {
  final ConversationModel conversation;
  final VoidCallback onTap;
  final VoidCallback? onMarkRead;
  final VoidCallback? onDelete;
  final int index;

  const ConversationTile({
    super.key,
    required this.conversation,
    required this.onTap,
    this.onMarkRead,
    this.onDelete,
    this.index = 0,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Dismissible(
      key: Key(conversation.conversationId),
      background: _buildSwipeBackground(
        color: MessagingTheme.swipeRead,
        icon: Icons.mark_email_read_rounded,
        label: 'Read',
        alignment: Alignment.centerLeft,
      ),
      secondaryBackground: _buildSwipeBackground(
        color: MessagingTheme.swipeDelete,
        icon: Icons.delete_rounded,
        label: 'Delete',
        alignment: Alignment.centerRight,
      ),
      confirmDismiss: (direction) async {
        HapticFeedback.mediumImpact();
        if (direction == DismissDirection.startToEnd) {
          onMarkRead?.call();
          return false;
        } else {
          return await _showDeleteConfirmation(context);
        }
      },
      onDismissed: (_) => onDelete?.call(),
      child: InkWell(
        onTap: () {
          HapticFeedback.selectionClick();
          onTap();
        },
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          decoration: BoxDecoration(
            color: isDark ? const Color(0xFF111827) : Colors.white,
            border: Border(
              bottom: BorderSide(
                color: isDark
                    ? const Color(0xFF1F2937)
                    : const Color(0xFFF1F5F9),
                width: 0.5,
              ),
            ),
          ),
          child: Row(
            children: [
              _buildAvatar(isDark),
              const SizedBox(width: 14),
              Expanded(child: _buildContent(isDark)),
              const SizedBox(width: 8),
              _buildTrailing(isDark),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildAvatar(bool isDark) {
    final name = conversation.participantName ?? 'U';
    final initial = name.isNotEmpty ? name[0].toUpperCase() : 'U';

    return Stack(
      children: [
        Hero(
          tag: 'avatar_${conversation.conversationId}',
          child: Container(
            width: 52,
            height: 52,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              gradient: LinearGradient(
                colors: _avatarGradient(initial),
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              boxShadow: [
                BoxShadow(
                  color: _avatarGradient(initial)[0].withOpacity(0.3),
                  blurRadius: 8,
                  offset: const Offset(0, 2),
                ),
              ],
            ),
            child: Center(
              child: Text(
                initial,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 20,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
          ),
        ),
        // Online indicator
        if (conversation.isOnline)
          Positioned(
            right: 1,
            bottom: 1,
            child: Container(
              width: 14,
              height: 14,
              decoration: BoxDecoration(
                color: MessagingTheme.onlineGreen,
                shape: BoxShape.circle,
                border: Border.all(
                  color: isDark ? const Color(0xFF111827) : Colors.white,
                  width: 2.5,
                ),
              ),
            ),
          ),
      ],
    );
  }

  Widget _buildContent(bool isDark) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Name
        Text(
          conversation.participantName ?? 'Unknown User',
          style: TextStyle(
            fontSize: 16,
            fontWeight: conversation.unreadCount > 0
                ? FontWeight.w700
                : FontWeight.w500,
            color: isDark ? Colors.white : const Color(0xFF0F172A),
          ),
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
        ),
        const SizedBox(height: 3),

        // Typing indicator or last message preview
        if (conversation.isTyping)
          Text(
            'typing...',
            style: TextStyle(
              fontSize: 14,
              color: MessagingTheme.onlineGreen,
              fontStyle: FontStyle.italic,
            ),
          )
        else
          Text(
            conversation.displayPreview,
            style: TextStyle(
              fontSize: 14,
              color: conversation.unreadCount > 0
                  ? (isDark ? const Color(0xFFCBD5E1) : const Color(0xFF475569))
                  : (isDark
                      ? MessagingTheme.timestampDark
                      : MessagingTheme.timestampLight),
              fontWeight: conversation.unreadCount > 0
                  ? FontWeight.w500
                  : FontWeight.w400,
            ),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
      ],
    );
  }

  Widget _buildTrailing(bool isDark) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.end,
      children: [
        // Time
        Text(
          conversation.formattedTime,
          style: TextStyle(
            fontSize: 12,
            color: conversation.unreadCount > 0
                ? MessagingTheme.unreadBadge
                : (isDark
                    ? MessagingTheme.timestampDark
                    : MessagingTheme.timestampLight),
            fontWeight: conversation.unreadCount > 0
                ? FontWeight.w600
                : FontWeight.w400,
          ),
        ),
        const SizedBox(height: 6),

        // Unread badge
        if (conversation.unreadCount > 0)
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
            decoration: BoxDecoration(
              color: MessagingTheme.unreadBadge,
              borderRadius: BorderRadius.circular(12),
            ),
            child: Text(
              conversation.unreadCount > 99
                  ? '99+'
                  : conversation.unreadCount.toString(),
              style: const TextStyle(
                color: Colors.white,
                fontSize: 11,
                fontWeight: FontWeight.w700,
              ),
            ),
          )
        else
          const SizedBox(height: 18),
      ],
    );
  }

  Widget _buildSwipeBackground({
    required Color color,
    required IconData icon,
    required String label,
    required Alignment alignment,
  }) {
    return Container(
      color: color,
      alignment: alignment,
      padding: const EdgeInsets.symmetric(horizontal: 24),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (alignment == Alignment.centerRight) ...[
            Text(
              label,
              style: const TextStyle(
                color: Colors.white,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(width: 8),
          ],
          Icon(icon, color: Colors.white, size: 24),
          if (alignment == Alignment.centerLeft) ...[
            const SizedBox(width: 8),
            Text(
              label,
              style: const TextStyle(
                color: Colors.white,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ],
      ),
    );
  }

  Future<bool> _showDeleteConfirmation(BuildContext context) async {
    return await showDialog<bool>(
          context: context,
          builder: (context) => AlertDialog(
            title: const Text('Delete Conversation'),
            content: const Text(
                'Are you sure you want to delete this conversation?'),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(context, false),
                child: const Text('Cancel'),
              ),
              TextButton(
                onPressed: () => Navigator.pop(context, true),
                style: TextButton.styleFrom(
                  foregroundColor: MessagingTheme.swipeDelete,
                ),
                child: const Text('Delete'),
              ),
            ],
          ),
        ) ??
        false;
  }

  /// Generate avatar gradient based on name initial
  List<Color> _avatarGradient(String initial) {
    final gradients = [
      [const Color(0xFF6366F1), const Color(0xFF8B5CF6)],
      [const Color(0xFF06B6D4), const Color(0xFF3B82F6)],
      [const Color(0xFF10B981), const Color(0xFF059669)],
      [const Color(0xFFF59E0B), const Color(0xFFEF4444)],
      [const Color(0xFFEC4899), const Color(0xFFF43F5E)],
      [const Color(0xFF8B5CF6), const Color(0xFFC084FC)],
    ];
    return gradients[initial.codeUnitAt(0) % gradients.length];
  }
}
