import 'package:flutter/material.dart';

/// Premium messaging color palette and theme extensions
class MessagingTheme {
  // Outgoing message gradient
  static const Color outgoingStart = Color(0xFF6366F1);
  static const Color outgoingEnd = Color(0xFF818CF8);

  // Incoming message
  static const Color incomingLight = Color(0xFFF1F5F9);
  static const Color incomingDark = Color(0xFF1E293B);

  // Online indicator
  static const Color onlineGreen = Color(0xFF22C55E);
  static const Color offlineGrey = Color(0xFF94A3B8);

  // Unread badge
  static const Color unreadBadge = Color(0xFF6366F1);

  // Chat background
  static const Color chatBgLight = Color(0xFFF8FAFC);
  static const Color chatBgDark = Color(0xFF0F172A);

  // Input bar
  static const Color inputBgLight = Color(0xFFFFFFFF);
  static const Color inputBgDark = Color(0xFF1E293B);
  static const Color inputBorderLight = Color(0xFFE2E8F0);
  static const Color inputBorderDark = Color(0xFF334155);

  // Timestamps
  static const Color timestampLight = Color(0xFF94A3B8);
  static const Color timestampDark = Color(0xFF64748B);

  // Send button
  static const Color sendButton = Color(0xFF6366F1);
  static const Color sendButtonDisabled = Color(0xFFCBD5E1);

  // Skeleton/shimmer
  static const Color shimmerBase = Color(0xFFE2E8F0);
  static const Color shimmerHighlight = Color(0xFFF1F5F9);

  // Swipe action colors
  static const Color swipeRead = Color(0xFF3B82F6);
  static const Color swipeDelete = Color(0xFFEF4444);

  /// Outgoing message gradient
  static const LinearGradient outgoingGradient = LinearGradient(
    colors: [outgoingStart, outgoingEnd],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  /// Message bubble decoration for outgoing messages
  static BoxDecoration outgoingBubble({bool isDark = false}) => BoxDecoration(
        gradient: outgoingGradient,
        borderRadius: const BorderRadius.only(
          topLeft: Radius.circular(20),
          topRight: Radius.circular(20),
          bottomLeft: Radius.circular(20),
          bottomRight: Radius.circular(4),
        ),
        boxShadow: [
          BoxShadow(
            color: outgoingStart.withOpacity(0.2),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      );

  /// Message bubble decoration for incoming messages
  static BoxDecoration incomingBubble({bool isDark = false}) => BoxDecoration(
        color: isDark ? incomingDark : incomingLight,
        borderRadius: const BorderRadius.only(
          topLeft: Radius.circular(20),
          topRight: Radius.circular(20),
          bottomLeft: Radius.circular(4),
          bottomRight: Radius.circular(20),
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(isDark ? 0.2 : 0.04),
            blurRadius: 6,
            offset: const Offset(0, 1),
          ),
        ],
      );

  /// Input field decoration
  static BoxDecoration inputDecoration({bool isDark = false}) => BoxDecoration(
        color: isDark ? inputBgDark : inputBgLight,
        borderRadius: BorderRadius.circular(24),
        border: Border.all(
          color: isDark ? inputBorderDark : inputBorderLight,
          width: 1,
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(isDark ? 0.15 : 0.04),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      );

  /// Send button gradient
  static BoxDecoration sendButtonDecoration({bool enabled = true}) =>
      BoxDecoration(
        gradient: enabled ? outgoingGradient : null,
        color: enabled ? null : sendButtonDisabled,
        shape: BoxShape.circle,
        boxShadow: enabled
            ? [
                BoxShadow(
                  color: outgoingStart.withOpacity(0.3),
                  blurRadius: 8,
                  offset: const Offset(0, 2),
                ),
              ]
            : null,
      );
}
