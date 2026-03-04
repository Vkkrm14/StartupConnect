import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import 'package:intl/intl.dart';
import '../../data/models/models.dart';
import '../../services/messaging_provider.dart';
import '../widgets/widgets.dart';
import '../theme/messaging_theme.dart';

/// Premium Chat Screen with message bubbles, real-time updates,
/// typing indicator, infinite scroll, new messages button, and more.
class ChatScreen extends StatefulWidget {
  final String conversationId;
  final ConversationModel? conversation;

  const ChatScreen({
    super.key,
    required this.conversationId,
    this.conversation,
  });

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen>
    with TickerProviderStateMixin {
  final ScrollController _scrollController = ScrollController();
  late final AnimationController _fabAnimController;
  bool _isAtBottom = true;
  int _newMessageCount = 0;
  bool _isLoadingMore = false;
  String? _participantName;

  @override
  void initState() {
    super.initState();

    _fabAnimController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 250),
    );

    _participantName = widget.conversation?.participantName ?? 'Chat';

    _scrollController.addListener(_onScroll);

    WidgetsBinding.instance.addPostFrameCallback((_) {
      final provider = context.read<MessagingProvider>();
      provider.setActiveConversation(widget.conversationId);
      provider.loadMessages(widget.conversationId);

      // Listen for new messages while scrolled up
      provider.addListener(_onProviderChange);
    });
  }

  void _onProviderChange() {
    if (!_isAtBottom && mounted) {
      setState(() {
        _newMessageCount++;
      });
    }
  }

  void _onScroll() {
    // Check if at bottom
    final isAtBottom = _scrollController.position.pixels <=
        _scrollController.position.minScrollExtent + 50;

    if (isAtBottom != _isAtBottom) {
      setState(() {
        _isAtBottom = isAtBottom;
        if (isAtBottom) {
          _newMessageCount = 0;
          _fabAnimController.reverse();
        } else {
          _fabAnimController.forward();
        }
      });
    }

    // Load more when near top (scrolled up to load older messages)
    if (_scrollController.position.pixels >=
        _scrollController.position.maxScrollExtent - 100) {
      _loadMore();
    }
  }

  Future<void> _loadMore() async {
    if (_isLoadingMore) return;
    final provider = context.read<MessagingProvider>();
    if (!provider.hasMoreMessages(widget.conversationId)) return;

    setState(() => _isLoadingMore = true);

    // Save scroll position by measuring distance from max
    final maxBefore = _scrollController.position.maxScrollExtent;

    await provider.loadMoreMessages(widget.conversationId);

    // Restore position
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        final maxAfter = _scrollController.position.maxScrollExtent;
        final diff = maxAfter - maxBefore;
        _scrollController.jumpTo(_scrollController.offset + diff);
      }
      if (mounted) setState(() => _isLoadingMore = false);
    });
  }

  void _scrollToBottom() {
    _scrollController.animateTo(
      _scrollController.position.minScrollExtent,
      duration: const Duration(milliseconds: 300),
      curve: Curves.easeOutCubic,
    );
    setState(() => _newMessageCount = 0);
  }

  @override
  void dispose() {
    final provider = context.read<MessagingProvider>();
    provider.setActiveConversation(null);
    provider.removeListener(_onProviderChange);
    _scrollController.dispose();
    _fabAnimController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      backgroundColor: isDark
          ? MessagingTheme.chatBgDark
          : MessagingTheme.chatBgLight,
      appBar: _buildAppBar(isDark),
      body: Column(
        children: [
          // Messages
          Expanded(child: _buildMessageList(isDark)),

          // Typing indicator
          _buildTypingIndicator(),

          // Input bar
          _buildInputBar(),
        ],
      ),
    );
  }

  PreferredSizeWidget _buildAppBar(bool isDark) {
    return AppBar(
      backgroundColor: isDark ? const Color(0xFF1E293B) : Colors.white,
      elevation: 0.5,
      titleSpacing: 0,
      leading: IconButton(
        icon: const Icon(Icons.arrow_back_ios_new_rounded, size: 20),
        onPressed: () => Navigator.pop(context),
      ),
      title: Consumer<MessagingProvider>(
        builder: (context, provider, _) {
          final isTyping =
              provider.isUserTyping(widget.conversationId);

          return Row(
            children: [
              // Avatar with hero
              Hero(
                tag: 'avatar_${widget.conversationId}',
                child: Container(
                  width: 36,
                  height: 36,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    gradient: LinearGradient(
                      colors: _avatarGradient(_participantName ?? 'U'),
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                    ),
                  ),
                  child: Center(
                    child: Text(
                      (_participantName ?? 'U')[0].toUpperCase(),
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 14,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      _participantName ?? 'Chat',
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.w600,
                        color: isDark ? Colors.white : const Color(0xFF0F172A),
                      ),
                    ),
                    if (isTyping)
                      Text(
                        'typing...',
                        style: TextStyle(
                          fontSize: 12,
                          color: MessagingTheme.onlineGreen,
                          fontStyle: FontStyle.italic,
                        ),
                      )
                    else if (widget.conversation?.isOnline == true)
                      const Text(
                        'online',
                        style: TextStyle(
                          fontSize: 12,
                          color: MessagingTheme.onlineGreen,
                        ),
                      ),
                  ],
                ),
              ),
            ],
          );
        },
      ),
      actions: [
        IconButton(
          icon: Icon(
            Icons.more_vert_rounded,
            color: isDark ? Colors.white70 : const Color(0xFF475569),
          ),
          onPressed: () => _showChatOptions(context),
        ),
      ],
    );
  }

  Widget _buildMessageList(bool isDark) {
    return Consumer<MessagingProvider>(
      builder: (context, provider, _) {
        final messages = provider.getMessages(widget.conversationId);
        final isLoading = provider.isLoadingMessages(widget.conversationId);

        if (isLoading && messages.isEmpty) {
          return const Center(child: CircularProgressIndicator());
        }

        if (messages.isEmpty) {
          return Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(
                  Icons.waving_hand_rounded,
                  size: 48,
                  color: isDark ? Colors.white24 : Colors.black12,
                ),
                const SizedBox(height: 12),
                Text(
                  'Say hello! 👋',
                  style: TextStyle(
                    fontSize: 16,
                    color: isDark
                        ? MessagingTheme.timestampDark
                        : MessagingTheme.timestampLight,
                  ),
                ),
              ],
            ),
          );
        }

        final currentUserId = provider.currentUserId ?? '';

        return Stack(
          children: [
            ListView.builder(
              controller: _scrollController,
              reverse: true,
              physics: const BouncingScrollPhysics(),
              padding: const EdgeInsets.symmetric(vertical: 8),
              itemCount: messages.length + (_isLoadingMore ? 1 : 0),
              itemBuilder: (context, index) {
                // Loading indicator at the top (end of reversed list)
                if (_isLoadingMore && index == messages.length) {
                  return const Padding(
                    padding: EdgeInsets.all(16),
                    child: Center(
                      child: SizedBox(
                        width: 24,
                        height: 24,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      ),
                    ),
                  );
                }

                final message = messages[index];
                final isMine = message.isMine(currentUserId);

                // Date separator
                final showDate = _shouldShowDateSeparator(
                    messages, index);

                return Column(
                  children: [
                    if (showDate)
                      _buildDateSeparator(message.createdAt, isDark),
                    MessageBubble(
                      message: message,
                      isMine: isMine,
                      index: index,
                      onImageTap: message.isImage
                          ? () => _openImageViewer(message)
                          : null,
                    ),
                  ],
                );
              },
            ),

            // New messages floating button
            if (_newMessageCount > 0 && !_isAtBottom)
              Positioned(
                bottom: 8,
                left: 0,
                right: 0,
                child: Center(
                  child: NewMessagesButton(
                    count: _newMessageCount,
                    onPressed: _scrollToBottom,
                  ),
                ),
              ),
          ],
        );
      },
    );
  }

  Widget _buildTypingIndicator() {
    return Consumer<MessagingProvider>(
      builder: (context, provider, _) {
        final isTyping = provider.isUserTyping(widget.conversationId);

        return AnimatedSize(
          duration: const Duration(milliseconds: 200),
          child: isTyping
              ? Padding(
                  padding:
                      const EdgeInsets.only(left: 12, right: 12, bottom: 4),
                  child: Row(
                    children: [
                      const TypingIndicatorWidget(showBubble: true),
                      const SizedBox(width: 8),
                      TypingTextIndicator(
                          userName: _participantName ?? 'User'),
                    ],
                  ),
                )
              : const SizedBox.shrink(),
        );
      },
    );
  }

  Widget _buildInputBar() {
    return FancyInputBar(
      onSend: (text) {
        final provider = context.read<MessagingProvider>();
        provider.sendTextMessage(widget.conversationId, text);

        // Scroll to bottom
        Future.delayed(const Duration(milliseconds: 100), () {
          if (_scrollController.hasClients) {
            _scrollToBottom();
          }
        });
      },
      onAttachImage: () => _pickAndSendImage(),
      onTypingStart: () {
        context.read<MessagingProvider>().sendTyping(widget.conversationId);
      },
      onTypingStop: () {
        context
            .read<MessagingProvider>()
            .sendStopTyping(widget.conversationId);
      },
    );
  }

  bool _shouldShowDateSeparator(List<MessageModel> messages, int index) {
    if (index == messages.length - 1) return true;

    final current = messages[index].createdAt;
    final next = messages[index + 1].createdAt;

    return current.day != next.day ||
        current.month != next.month ||
        current.year != next.year;
  }

  Widget _buildDateSeparator(DateTime date, bool isDark) {
    final now = DateTime.now();
    final diff = now.difference(date);

    String label;
    if (diff.inDays == 0) {
      label = 'Today';
    } else if (diff.inDays == 1) {
      label = 'Yesterday';
    } else if (diff.inDays < 7) {
      label = DateFormat('EEEE').format(date);
    } else {
      label = DateFormat('MMMM d, y').format(date);
    }

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 16),
      child: Center(
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
          decoration: BoxDecoration(
            color: isDark
                ? const Color(0xFF1E293B)
                : const Color(0xFFE2E8F0),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Text(
            label,
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w500,
              color: isDark
                  ? MessagingTheme.timestampDark
                  : MessagingTheme.timestampLight,
            ),
          ),
        ),
      ),
    );
  }

  Future<void> _pickAndSendImage() async {
    // Image picking is handled through platform channels
    // For now, show a placeholder dialog
    HapticFeedback.selectionClick();

    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (context) => _buildImagePickerSheet(context),
    );
  }

  Widget _buildImagePickerSheet(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: isDark ? const Color(0xFF1E293B) : Colors.white,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 40,
            height: 4,
            decoration: BoxDecoration(
              color: isDark ? Colors.white24 : Colors.black12,
              borderRadius: BorderRadius.circular(2),
            ),
          ),
          const SizedBox(height: 20),
          Text(
            'Send Image',
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.w600,
              color: isDark ? Colors.white : const Color(0xFF0F172A),
            ),
          ),
          const SizedBox(height: 20),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            children: [
              _buildImageOption(
                icon: Icons.camera_alt_rounded,
                label: 'Camera',
                color: const Color(0xFF6366F1),
                onTap: () {
                  Navigator.pop(context);
                  // Camera picker integration would go here
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(
                      content: Text('Camera requires image_picker package'),
                    ),
                  );
                },
              ),
              _buildImageOption(
                icon: Icons.photo_library_rounded,
                label: 'Gallery',
                color: const Color(0xFF10B981),
                onTap: () {
                  Navigator.pop(context);
                  // Gallery picker integration would go here
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(
                      content: Text('Gallery requires image_picker package'),
                    ),
                  );
                },
              ),
            ],
          ),
          const SizedBox(height: 16),
        ],
      ),
    );
  }

  Widget _buildImageOption({
    required IconData icon,
    required String label,
    required Color color,
    required VoidCallback onTap,
  }) {
    return GestureDetector(
      onTap: onTap,
      child: Column(
        children: [
          Container(
            width: 60,
            height: 60,
            decoration: BoxDecoration(
              color: color.withOpacity(0.1),
              shape: BoxShape.circle,
            ),
            child: Icon(icon, color: color, size: 28),
          ),
          const SizedBox(height: 8),
          Text(
            label,
            style: TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.w500,
              color: color,
            ),
          ),
        ],
      ),
    );
  }

  void _openImageViewer(MessageModel message) {
    Navigator.push(
      context,
      PageRouteBuilder(
        opaque: false,
        pageBuilder: (_, __, ___) => FullScreenImageViewer(
          heroTag: 'image_${message.messageId}',
          title: _participantName,
        ),
        transitionsBuilder: (_, anim, __, child) {
          return FadeTransition(opacity: anim, child: child);
        },
      ),
    );
  }

  void _showChatOptions(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (ctx) => Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: isDark ? const Color(0xFF1E293B) : Colors.white,
          borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 40,
              height: 4,
              decoration: BoxDecoration(
                color: isDark ? Colors.white24 : Colors.black12,
                borderRadius: BorderRadius.circular(2),
              ),
            ),
            const SizedBox(height: 16),
            ListTile(
              leading: const Icon(Icons.block_rounded, color: Colors.red),
              title: const Text('Block User'),
              onTap: () => Navigator.pop(ctx),
            ),
            ListTile(
              leading: const Icon(Icons.delete_outline_rounded,
                  color: Colors.red),
              title: const Text('Delete Conversation'),
              onTap: () {
                Navigator.pop(ctx);
                context
                    .read<MessagingProvider>()
                    .deleteConversation(widget.conversationId);
                Navigator.pop(context);
              },
            ),
          ],
        ),
      ),
    );
  }

  List<Color> _avatarGradient(String name) {
    final initial = name.isNotEmpty ? name[0].toUpperCase() : 'U';
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
