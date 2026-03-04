import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../theme/messaging_theme.dart';

/// Premium fancy input bar for the chat screen
class FancyInputBar extends StatefulWidget {
  final Function(String) onSend;
  final VoidCallback? onAttachImage;
  final VoidCallback? onTypingStart;
  final VoidCallback? onTypingStop;

  const FancyInputBar({
    super.key,
    required this.onSend,
    this.onAttachImage,
    this.onTypingStart,
    this.onTypingStop,
  });

  @override
  State<FancyInputBar> createState() => _FancyInputBarState();
}

class _FancyInputBarState extends State<FancyInputBar>
    with SingleTickerProviderStateMixin {
  final TextEditingController _controller = TextEditingController();
  final FocusNode _focusNode = FocusNode();
  late final AnimationController _sendAnimController;
  late final Animation<double> _sendScaleAnim;
  bool _hasText = false;
  bool _isTyping = false;

  @override
  void initState() {
    super.initState();

    _sendAnimController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 200),
    );

    _sendScaleAnim = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(parent: _sendAnimController, curve: Curves.elasticOut),
    );

    _controller.addListener(_onTextChanged);
  }

  void _onTextChanged() {
    final hasText = _controller.text.trim().isNotEmpty;
    if (hasText != _hasText) {
      setState(() => _hasText = hasText);
      if (hasText) {
        _sendAnimController.forward();
      } else {
        _sendAnimController.reverse();
      }
    }

    // Typing indicator logic
    if (hasText && !_isTyping) {
      _isTyping = true;
      widget.onTypingStart?.call();
    } else if (!hasText && _isTyping) {
      _isTyping = false;
      widget.onTypingStop?.call();
    }
  }

  void _handleSend() {
    final text = _controller.text.trim();
    if (text.isEmpty) return;

    // Haptic feedback
    HapticFeedback.lightImpact();

    widget.onSend(text);
    _controller.clear();
    _isTyping = false;
    widget.onTypingStop?.call();
  }

  @override
  void dispose() {
    _controller.dispose();
    _focusNode.dispose();
    _sendAnimController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final bottomPadding = MediaQuery.of(context).viewPadding.bottom;

    return Container(
      padding: EdgeInsets.only(
        left: 8,
        right: 8,
        top: 8,
        bottom: 8 + bottomPadding,
      ),
      decoration: BoxDecoration(
        color: isDark ? const Color(0xFF111827) : Colors.white,
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(isDark ? 0.3 : 0.06),
            blurRadius: 12,
            offset: const Offset(0, -2),
          ),
        ],
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          // Attach button
          _buildAttachButton(isDark),
          const SizedBox(width: 8),

          // Text field
          Expanded(child: _buildTextField(isDark)),
          const SizedBox(width: 8),

          // Send button
          _buildSendButton(isDark),
        ],
      ),
    );
  }

  Widget _buildAttachButton(bool isDark) {
    return GestureDetector(
      onTap: () {
        HapticFeedback.selectionClick();
        widget.onAttachImage?.call();
      },
      child: Container(
        width: 42,
        height: 42,
        margin: const EdgeInsets.only(bottom: 2),
        decoration: BoxDecoration(
          color: isDark
              ? MessagingTheme.inputBgDark
              : const Color(0xFFF1F5F9),
          borderRadius: BorderRadius.circular(21),
        ),
        child: Icon(
          Icons.add_photo_alternate_rounded,
          color: isDark
              ? MessagingTheme.timestampDark
              : MessagingTheme.timestampLight,
          size: 22,
        ),
      ),
    );
  }

  Widget _buildTextField(bool isDark) {
    return Container(
      constraints: const BoxConstraints(maxHeight: 120),
      decoration: MessagingTheme.inputDecoration(isDark: isDark),
      child: RawKeyboardListener(
        focusNode: FocusNode(),
        onKey: (event) {
          // Send on Enter (desktop/web), Shift+Enter for new line
          if (event is RawKeyDownEvent &&
              event.logicalKey == LogicalKeyboardKey.enter &&
              !event.isShiftPressed) {
            _handleSend();
          }
        },
        child: TextField(
          controller: _controller,
          focusNode: _focusNode,
          maxLines: 5,
          minLines: 1,
          textCapitalization: TextCapitalization.sentences,
          textInputAction: TextInputAction.newline,
          style: TextStyle(
            fontSize: 15,
            color: isDark ? Colors.white : const Color(0xFF1E293B),
            height: 1.4,
          ),
          decoration: InputDecoration(
            hintText: 'Type a message...',
            hintStyle: TextStyle(
              color: isDark
                  ? const Color(0xFF475569)
                  : const Color(0xFF94A3B8),
              fontSize: 15,
            ),
            border: InputBorder.none,
            contentPadding: const EdgeInsets.symmetric(
              horizontal: 16,
              vertical: 10,
            ),
            isDense: true,
          ),
        ),
      ),
    );
  }

  Widget _buildSendButton(bool isDark) {
    return ScaleTransition(
      scale: _sendScaleAnim,
      child: GestureDetector(
        onTap: _hasText ? _handleSend : null,
        child: Container(
          width: 42,
          height: 42,
          margin: const EdgeInsets.only(bottom: 2),
          decoration: MessagingTheme.sendButtonDecoration(enabled: _hasText),
          child: const Icon(
            Icons.send_rounded,
            color: Colors.white,
            size: 20,
          ),
        ),
      ),
    );
  }
}
