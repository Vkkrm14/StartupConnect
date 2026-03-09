import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../../data/providers/api_client.dart';
import '../../../data/repositories/auth_repository.dart';
import '../../../data/repositories/intro_repository.dart';
import '../../../data/models/user_model.dart';
import '../../../data/models/intro_model.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final _apiClient = ApiClient();
  late final AuthRepository _authRepo;
  late final IntroRepository _introRepo;

  UserModel? _currentUser;
  List<IntroModel> _recentIntros = [];
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _authRepo = AuthRepository(_apiClient);
    _introRepo = IntroRepository(_apiClient);
    _loadData();
  }

  Future<void> _loadData() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final user = await _authRepo.getCurrentUser();
      List<IntroModel> intros = [];

      if (user != null) {
        intros = await _introRepo.getUserIntroRequests(user.userId);
      }

      setState(() {
        _currentUser = user;
        _recentIntros = intros;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _error = 'Failed to load data: ${e.toString()}';
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('TrustGraph'),
        actions: [
          IconButton(
            icon: const Icon(Icons.notifications_outlined),
            onPressed: () => context.push('/intros/pending'),
          ),
          IconButton(
            icon: const Icon(Icons.account_circle_outlined),
            onPressed: () => context.push('/profile'),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _loadData,
        child: _isLoading
            ? const Center(child: CircularProgressIndicator())
            : _error != null
                ? _buildError()
                : _buildHomeFeed(),
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: 0,
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
              context.go('/messages');
              break;
            case 4:
              context.go('/intros/pending');
              break;
            case 5:
              context.go('/profile');
              break;
          }
        },
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.home_outlined),
            selectedIcon: Icon(Icons.home),
            label: 'Home',
          ),
          NavigationDestination(
            icon: Icon(Icons.search_outlined),
            selectedIcon: Icon(Icons.search),
            label: 'Search',
          ),
          NavigationDestination(
            icon: Icon(Icons.people_outline),
            selectedIcon: Icon(Icons.people),
            label: 'Connections',
          ),
          NavigationDestination(
            icon: Icon(Icons.chat_bubble_outline),
            selectedIcon: Icon(Icons.chat_bubble),
            label: 'Messages',
          ),
          NavigationDestination(
            icon: Icon(Icons.handshake_outlined),
            selectedIcon: Icon(Icons.handshake),
            label: 'Intros',
          ),
          NavigationDestination(
            icon: Icon(Icons.person_outline),
            selectedIcon: Icon(Icons.person),
            label: 'Profile',
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () => context.push('/search'),
        child: const Icon(Icons.search),
      ),
    );
  }

  Widget _buildError() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(Icons.error_outline, size: 48, color: Colors.red),
          const SizedBox(height: 16),
          Text(_error!, textAlign: TextAlign.center),
          const SizedBox(height: 16),
          ElevatedButton(
            onPressed: _loadData,
            child: const Text('Retry'),
          ),
        ],
      ),
    );
  }

  Widget _buildHomeFeed() {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        // Welcome Banner
        if (_currentUser != null) ...[
          Text(
            'Welcome back, ${_currentUser!.name.split(' ').first}!',
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
          ),
          const SizedBox(height: 4),
          Text(
            _currentUser!.rolePrimary[0].toUpperCase() +
                _currentUser!.rolePrimary.substring(1),
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: Colors.grey[600],
                ),
          ),
          const SizedBox(height: 16),
        ],

        // Trust Score Card
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const Icon(Icons.verified_user, color: Colors.blue),
                    const SizedBox(width: 8),
                    Text(
                      'Your Trust Score',
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                Row(
                  children: [
                    Expanded(
                      child: LinearProgressIndicator(
                        value: _currentUser?.reputationScore ?? 0.5,
                        minHeight: 8,
                        backgroundColor: Colors.grey[200],
                        color: _scoreTint(_currentUser?.reputationScore ?? 0.5),
                      ),
                    ),
                    const SizedBox(width: 16),
                    Text(
                      (_currentUser?.reputationScore ?? 0.5)
                          .toStringAsFixed(2),
                      style: const TextStyle(
                        fontSize: 20,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Text(
                  _scoreLabel(_currentUser?.reputationScore ?? 0.5),
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: Colors.grey[600],
                      ),
                ),
                if (_currentUser != null &&
                    _currentUser!.domainTags.isNotEmpty) ...[
                  const SizedBox(height: 12),
                  Wrap(
                    spacing: 6,
                    children: _currentUser!.domainTags
                        .take(4)
                        .map((tag) => Chip(
                              label: Text(tag,
                                  style: const TextStyle(fontSize: 11)),
                              padding: EdgeInsets.zero,
                              visualDensity: VisualDensity.compact,
                            ))
                        .toList(),
                  ),
                ],
              ],
            ),
          ),
        ),
        const SizedBox(height: 16),

        // Recent Intros
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              'Recent Intro Requests',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            TextButton(
              onPressed: () => context.push('/intros/pending'),
              child: const Text('See all'),
            ),
          ],
        ),
        const SizedBox(height: 8),

        if (_recentIntros.isEmpty)
          Card(
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Column(
                children: [
                  Icon(Icons.handshake_outlined,
                      size: 48, color: Colors.grey[400]),
                  const SizedBox(height: 8),
                  Text(
                    'No intro requests yet',
                    style: TextStyle(color: Colors.grey[600]),
                  ),
                  const SizedBox(height: 8),
                  ElevatedButton.icon(
                    onPressed: () => context.push('/search'),
                    icon: const Icon(Icons.search),
                    label: const Text('Find people to connect with'),
                  ),
                ],
              ),
            ),
          )
        else
          ..._recentIntros.take(5).map((intro) => _buildIntroCard(intro)),
      ],
    );
  }

  Widget _buildIntroCard(IntroModel intro) {
    final statusColor = _statusColor(intro.status);
    final statusIcon = _statusIcon(intro.status);

    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: statusColor.withOpacity(0.1),
          child: Icon(statusIcon, color: statusColor),
        ),
        title: Text(
          'Intro Request',
          style: const TextStyle(fontWeight: FontWeight.w600),
        ),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              intro.message.isNotEmpty
                  ? intro.message
                  : 'No message provided',
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
            const SizedBox(height: 2),
            Container(
              padding:
                  const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
              decoration: BoxDecoration(
                color: statusColor.withOpacity(0.1),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Text(
                intro.status.toUpperCase(),
                style: TextStyle(
                    fontSize: 10,
                    color: statusColor,
                    fontWeight: FontWeight.bold),
              ),
            ),
          ],
        ),
        trailing: const Icon(Icons.chevron_right),
        onTap: () => context.push('/intro/${intro.introId}'),
        isThreeLine: true,
      ),
    );
  }

  Color _scoreTint(double score) {
    if (score >= 0.75) return Colors.green;
    if (score >= 0.5) return Colors.blue;
    if (score >= 0.25) return Colors.orange;
    return Colors.red;
  }

  String _scoreLabel(double score) {
    if (score >= 0.75) return 'Excellent standing in the network';
    if (score >= 0.5) return 'Good standing in the network';
    if (score >= 0.25) return 'Building trust in the network';
    return 'New to the network';
  }

  Color _statusColor(String status) {
    switch (status) {
      case 'approved':
        return Colors.green;
      case 'pending':
        return Colors.orange;
      case 'declined':
        return Colors.red;
      case 'completed':
        return Colors.blue;
      default:
        return Colors.grey;
    }
  }

  IconData _statusIcon(String status) {
    switch (status) {
      case 'approved':
        return Icons.check_circle;
      case 'pending':
        return Icons.handshake_outlined;
      case 'declined':
        return Icons.cancel;
      case 'completed':
        return Icons.verified;
      default:
        return Icons.info_outline;
    }
  }
}

