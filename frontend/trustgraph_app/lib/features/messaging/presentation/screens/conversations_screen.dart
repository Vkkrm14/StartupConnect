import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import '../../services/messaging_provider.dart';
import '../widgets/widgets.dart';
import '../theme/messaging_theme.dart';

/// Premium Conversations List Screen
/// Features: search, pull-to-refresh, skeleton loading, swipe actions,
/// animated transitions, empty state, unread badges.
class ConversationsScreen extends StatefulWidget {
  const ConversationsScreen({super.key});

  @override
  State<ConversationsScreen> createState() => _ConversationsScreenState();
}

class _ConversationsScreenState extends State<ConversationsScreen>
    with SingleTickerProviderStateMixin {
  final TextEditingController _searchController = TextEditingController();
  late final AnimationController _searchAnimController;
  bool _isSearchOpen = false;
  String _searchQuery = '';

  @override
  void initState() {
    super.initState();
    _searchAnimController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 250),
    );

    // Initialize messaging when screen loads
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final provider = context.read<MessagingProvider>();
      if (!provider.isInitialized) {
        provider.initialize();
      }
    });
  }

  @override
  void dispose() {
    _searchController.dispose();
    _searchAnimController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      backgroundColor: isDark ? const Color(0xFF111827) : Colors.white,
      appBar: _buildAppBar(isDark),
      body: _buildBody(isDark),
    );
  }

  PreferredSizeWidget _buildAppBar(bool isDark) {
    return AppBar(
      backgroundColor: isDark ? const Color(0xFF111827) : Colors.white,
      elevation: 0,
      title: _isSearchOpen
          ? _buildSearchField(isDark)
          : const Text(
              'Messages',
              style: TextStyle(
                fontSize: 24,
                fontWeight: FontWeight.w700,
              ),
            ),
      actions: [
        // Search toggle
        IconButton(
          icon: Icon(
            _isSearchOpen ? Icons.close : Icons.search_rounded,
            color: isDark ? Colors.white : const Color(0xFF1E293B),
          ),
          onPressed: () {
            HapticFeedback.selectionClick();
            setState(() {
              _isSearchOpen = !_isSearchOpen;
              if (!_isSearchOpen) {
                _searchController.clear();
                _searchQuery = '';
              }
            });
          },
        ),
      ],
    );
  }

  Widget _buildSearchField(bool isDark) {
    return TextField(
      controller: _searchController,
      autofocus: true,
      style: TextStyle(
        color: isDark ? Colors.white : const Color(0xFF1E293B),
        fontSize: 16,
      ),
      decoration: InputDecoration(
        hintText: 'Search conversations...',
        hintStyle: TextStyle(
          color: isDark
              ? MessagingTheme.timestampDark
              : MessagingTheme.timestampLight,
        ),
        border: InputBorder.none,
        contentPadding: EdgeInsets.zero,
      ),
      onChanged: (value) {
        setState(() => _searchQuery = value);
      },
    );
  }

  Widget _buildBody(bool isDark) {
    return Consumer<MessagingProvider>(
      builder: (context, provider, _) {
        // Loading state
        if (provider.isLoadingConversations && provider.conversations.isEmpty) {
          return const ConversationSkeleton();
        }

        // Error state
        if (provider.error != null && provider.conversations.isEmpty) {
          return _buildErrorState(provider);
        }

        // Get filtered conversations
        final conversations = _searchQuery.isEmpty
            ? provider.conversations
            : provider.searchConversations(_searchQuery);

        // Empty state
        if (conversations.isEmpty && _searchQuery.isEmpty) {
          return RefreshIndicator(
            onRefresh: provider.loadConversations,
            child: ListView(
              children: const [
                SizedBox(height: 100),
                EmptyConversationsState(),
              ],
            ),
          );
        }

        // No search results
        if (conversations.isEmpty && _searchQuery.isNotEmpty) {
          return Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(
                  Icons.search_off_rounded,
                  size: 48,
                  color: isDark
                      ? MessagingTheme.timestampDark
                      : MessagingTheme.timestampLight,
                ),
                const SizedBox(height: 12),
                Text(
                  'No results found',
                  style: TextStyle(
                    color: isDark
                        ? MessagingTheme.timestampDark
                        : MessagingTheme.timestampLight,
                  ),
                ),
              ],
            ),
          );
        }

        // Conversation list
        return RefreshIndicator(
          onRefresh: provider.loadConversations,
          color: MessagingTheme.outgoingStart,
          child: AnimatedSwitcher(
            duration: const Duration(milliseconds: 300),
            child: ListView.builder(
              key: ValueKey(conversations.length),
              physics: const AlwaysScrollableScrollPhysics(
                parent: BouncingScrollPhysics(),
              ),
              itemCount: conversations.length,
              itemBuilder: (context, index) {
                final conversation = conversations[index];
                return ConversationTile(
                  conversation: conversation,
                  index: index,
                  onTap: () {
                    context.push(
                      '/chat/${conversation.conversationId}',
                      extra: conversation,
                    );
                  },
                  onMarkRead: () {
                    provider.markAsRead(conversation.conversationId);
                  },
                  onDelete: () {
                    provider.deleteConversation(conversation.conversationId);
                  },
                );
              },
            ),
          ),
        );
      },
    );
  }

  Widget _buildErrorState(MessagingProvider provider) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(
              Icons.wifi_off_rounded,
              size: 56,
              color: Color(0xFF94A3B8),
            ),
            const SizedBox(height: 16),
            Text(
              provider.error ?? 'Something went wrong',
              textAlign: TextAlign.center,
              style: const TextStyle(
                fontSize: 14,
                color: Color(0xFF94A3B8),
              ),
            ),
            const SizedBox(height: 24),
            ElevatedButton.icon(
              onPressed: provider.loadConversations,
              icon: const Icon(Icons.refresh, size: 18),
              label: const Text('Retry'),
              style: ElevatedButton.styleFrom(
                backgroundColor: MessagingTheme.outgoingStart,
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildBottomNav(BuildContext context) {
    return Consumer<MessagingProvider>(
      builder: (context, provider, _) {
        int totalUnread = 0;
        for (final c in provider.conversations) {
          totalUnread += c.unreadCount;
        }

        return NavigationBar(
          selectedIndex: 3,
          onDestinationSelected: (index) {
            switch (index) {
              case 0:
                context.go('/home');
                break;
              case 1:
                context.go('/search');
                break;
              case 2:
                context.go('/connections');
                break;
              case 3:
                break; // Already here
              case 4:
                context.go('/intros/pending');
                break;
              case 5:
                context.go('/profile');
                break;
            }
          },
          destinations: [
            const NavigationDestination(
              icon: Icon(Icons.home_outlined),
              selectedIcon: Icon(Icons.home),
              label: 'Home',
            ),
            const NavigationDestination(
              icon: Icon(Icons.search_outlined),
              selectedIcon: Icon(Icons.search),
              label: 'Search',
            ),
            const NavigationDestination(
              icon: Icon(Icons.people_outline),
              selectedIcon: Icon(Icons.people),
              label: 'Connections',
            ),
            NavigationDestination(
              icon: Badge(
                isLabelVisible: totalUnread > 0,
                label: Text(
                  totalUnread > 99 ? '99+' : totalUnread.toString(),
                  style: const TextStyle(fontSize: 10),
                ),
                child: const Icon(Icons.chat_bubble_outline),
              ),
              selectedIcon: Badge(
                isLabelVisible: totalUnread > 0,
                label: Text(
                  totalUnread > 99 ? '99+' : totalUnread.toString(),
                  style: const TextStyle(fontSize: 10),
                ),
                child: const Icon(Icons.chat_bubble),
              ),
              label: 'Messages',
            ),
            const NavigationDestination(
              icon: Icon(Icons.handshake_outlined),
              selectedIcon: Icon(Icons.handshake),
              label: 'Intros',
            ),
            const NavigationDestination(
              icon: Icon(Icons.person_outline),
              selectedIcon: Icon(Icons.person),
              label: 'Profile',
            ),
          ],
        );
      },
    );
  }
}
