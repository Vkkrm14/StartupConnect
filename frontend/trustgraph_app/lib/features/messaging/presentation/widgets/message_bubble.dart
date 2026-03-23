import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';
import '../../services/messaging_provider.dart';
import '../../data/models/message_model.dart';
import '../theme/messaging_theme.dart';

/// Premium message bubble with gradient outgoing, timestamp on long press,
/// read receipts, delivery indicators, and smooth animations.
class MessageBubble extends StatefulWidget {
  final MessageModel message;
  final bool isMine;
  final bool showTimestamp;
  final VoidCallback? onImageTap;
  final int index;

  const MessageBubble({
    super.key,
    required this.message,
    required this.isMine,
    this.showTimestamp = false,
    this.onImageTap,
    this.index = 0,
  });

  @override
  State<MessageBubble> createState() => _MessageBubbleState();
}

class _MessageBubbleState extends State<MessageBubble>
    with SingleTickerProviderStateMixin {
  late final AnimationController _animController;
  late final Animation<double> _scaleAnim;
  late final Animation<Offset> _slideAnim;
  bool _showTime = false;

  @override
  void initState() {
    super.initState();
    _animController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 350),
    );

    _scaleAnim = Tween<double>(begin: 0.8, end: 1.0).animate(
      CurvedAnimation(parent: _animController, curve: Curves.elasticOut),
    );

    _slideAnim = Tween<Offset>(
      begin: Offset(widget.isMine ? 0.3 : -0.3, 0),
      end: Offset.zero,
    ).animate(
      CurvedAnimation(parent: _animController, curve: Curves.easeOutCubic),
    );

    // Delayed start for stagger effect
    Future.delayed(Duration(milliseconds: (widget.index * 30).clamp(0, 300)),
        () {
      if (mounted) _animController.forward();
    });
  }

  @override
  void dispose() {
    _animController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return SlideTransition(
      position: _slideAnim,
      child: ScaleTransition(
        scale: _scaleAnim,
        alignment:
            widget.isMine ? Alignment.centerRight : Alignment.centerLeft,
        child: _buildBubbleLayout(isDark),
      ),
    );
  }

  Widget _buildBubbleLayout(bool isDark) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 3),
      child: Column(
        crossAxisAlignment:
            widget.isMine ? CrossAxisAlignment.end : CrossAxisAlignment.start,
        children: [
          // Timestamp (shown on long press)
          if (_showTime || widget.showTimestamp)
            Padding(
              padding: const EdgeInsets.only(bottom: 4),
              child: Text(
                DateFormat('h:mm a').format(widget.message.createdAt),
                style: TextStyle(
                  fontSize: 11,
                  color: isDark
                      ? MessagingTheme.timestampDark
                      : MessagingTheme.timestampLight,
                ),
              ),
            ),

          // Bubble
          GestureDetector(
            onLongPress: () {
              setState(() => _showTime = !_showTime);
            },
            child: Container(
              constraints: BoxConstraints(
                maxWidth: MediaQuery.of(context).size.width * 0.75,
              ),
              child: widget.message.isImage
                  ? _buildImageBubble(isDark)
                  : _buildTextBubble(isDark),
            ),
          ),

          // Status indicators for outgoing messages
          if (widget.isMine) _buildStatusRow(isDark),
        ],
      ),
    );
  }

  Widget _buildTextBubble(bool isDark) {
    final text = widget.message.decryptedContent ??
        widget.message.encryptedPayload;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
      decoration: widget.isMine
          ? MessagingTheme.outgoingBubble(isDark: isDark)
          : MessagingTheme.incomingBubble(isDark: isDark),
      child: Text(
        text,
        style: TextStyle(
          fontSize: 15,
          height: 1.4,
          color: widget.isMine
              ? Colors.white
              : isDark
                  ? const Color(0xFFE2E8F0)
                  : const Color(0xFF1E293B),
        ),
      ),
    );
  }

  Widget _buildImageBubble(bool isDark) {
    final fileId = _resolveImageFileId();

    return GestureDetector(
      onTap: widget.onImageTap,
      child: Container(
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(16),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(isDark ? 0.3 : 0.1),
              blurRadius: 8,
              offset: const Offset(0, 2),
            ),
          ],
        ),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(16),
          child: widget.message.metadata?['local_path'] != null
              ? _buildLocalImage()
              : fileId != null
                  ? _buildRemoteImage(fileId, isDark)
              : _buildPlaceholderImage(isDark),
        ),
      ),
    );
  }

  String? _resolveImageFileId() {
    final metadataFileId = widget.message.metadata?['file_id']?.toString();
    if (metadataFileId != null && metadataFileId.isNotEmpty) {
      return metadataFileId;
    }

    final decrypted = widget.message.decryptedContent;
    if (decrypted != null && decrypted.isNotEmpty && !decrypted.startsWith('[')) {
      return decrypted;
    }

    return null;
  }

  Widget _buildRemoteImage(String fileId, bool isDark) {
    final provider = context.read<MessagingProvider>();

    return FutureBuilder(
      future: provider.downloadImage(widget.message.conversationId, fileId),
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.done &&
            snapshot.data != null &&
            snapshot.data!.isNotEmpty) {
          return Image.memory(
            snapshot.data!,
            width: 200,
            height: 200,
            fit: BoxFit.cover,
            gaplessPlayback: true,
          );
        }

        return _buildPlaceholderImage(isDark);
      },
    );
  }

  Widget _buildLocalImage() {
    return Container(
      width: 200,
      height: 200,
      color: MessagingTheme.shimmerBase,
      child: const Center(
        child: Icon(Icons.image, size: 48, color: Colors.white54),
      ),
    );
  }

  Widget _buildPlaceholderImage(bool isDark) {
    // Shimmer placeholder for loading images
    return Container(
      width: 200,
      height: 200,
      decoration: BoxDecoration(
        color: isDark
            ? const Color(0xFF1E293B)
            : MessagingTheme.shimmerBase,
        borderRadius: BorderRadius.circular(16),
      ),
      child: Stack(
        alignment: Alignment.center,
        children: [
          // Shimmer effect
          _ShimmerEffect(isDark: isDark),
          Icon(
            Icons.photo_rounded,
            size: 40,
            color: isDark ? Colors.white24 : Colors.black12,
          ),
        ],
      ),
    );
  }

  Widget _buildStatusRow(bool isDark) {
    return Padding(
      padding: const EdgeInsets.only(top: 2, right: 4),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (widget.message.status == MessageStatus.sending)
            SizedBox(
              width: 12,
              height: 12,
              child: CircularProgressIndicator(
                strokeWidth: 1.5,
                color: isDark
                    ? MessagingTheme.timestampDark
                    : MessagingTheme.timestampLight,
              ),
            )
          else
            Icon(
              _getStatusIcon(),
              size: 14,
              color: _getStatusColor(isDark),
            ),
        ],
      ),
    );
  }

  IconData _getStatusIcon() {
    switch (widget.message.status) {
      case MessageStatus.sent:
        return Icons.check;
      case MessageStatus.delivered:
        return Icons.done_all;
      case MessageStatus.read:
        return Icons.done_all;
      case MessageStatus.failed:
        return Icons.error_outline;
      default:
        return Icons.check;
    }
  }

  Color _getStatusColor(bool isDark) {
    switch (widget.message.status) {
      case MessageStatus.read:
        return MessagingTheme.onlineGreen;
      case MessageStatus.failed:
        return Colors.red;
      default:
        return isDark
            ? MessagingTheme.timestampDark
            : MessagingTheme.timestampLight;
    }
  }
}

/// Simple shimmer animation effect
class _ShimmerEffect extends StatefulWidget {
  final bool isDark;

  const _ShimmerEffect({required this.isDark});

  @override
  State<_ShimmerEffect> createState() => _ShimmerEffectState();
}

class _ShimmerEffectState extends State<_ShimmerEffect>
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
    return AnimatedBuilder(
      animation: _controller,
      builder: (context, child) {
        return Container(
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment(-1.0 + 2.0 * _controller.value, 0),
              end: Alignment(1.0 + 2.0 * _controller.value, 0),
              colors: widget.isDark
                  ? [
                      const Color(0xFF1E293B),
                      const Color(0xFF334155),
                      const Color(0xFF1E293B),
                    ]
                  : [
                      MessagingTheme.shimmerBase,
                      MessagingTheme.shimmerHighlight,
                      MessagingTheme.shimmerBase,
                    ],
            ),
          ),
        );
      },
    );
  }
}
