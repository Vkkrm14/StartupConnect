import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../../data/repositories/intro_repository.dart';
import '../../../data/repositories/auth_repository.dart';
import '../../../data/providers/api_client.dart';
import '../../../data/models/path_model.dart';

class IntroRequestScreen extends StatefulWidget {
  final String targetUserId;
  final String targetUserName;

  const IntroRequestScreen({
    super.key,
    required this.targetUserId,
    required this.targetUserName,
  });

  @override
  State<IntroRequestScreen> createState() => _IntroRequestScreenState();
}

class _IntroRequestScreenState extends State<IntroRequestScreen> {
  final _introRepo = IntroRepository(ApiClient());
  final _authRepo = AuthRepository(ApiClient());
  final _messageController = TextEditingController();
  
  List<PathModel> _paths = [];
  PathModel? _selectedPath;
  bool _isLoading = true;
  bool _isSubmitting = false;
  String? _currentUserId;

  @override
  void initState() {
    super.initState();
    _loadPaths();
  }

  @override
  void dispose() {
    _messageController.dispose();
    super.dispose();
  }

  Future<void> _loadPaths() async {
    setState(() => _isLoading = true);

    _currentUserId = await _authRepo.getCurrentUserId();
    
    if (_currentUserId == null) {
      setState(() => _isLoading = false);
      return;
    }

    final paths = await _introRepo.discoverPaths(
      founderId: _currentUserId!,
      investorId: widget.targetUserId,
      maxPaths: 5,
    );

    setState(() {
      _paths = paths;
      _isLoading = false;
      if (_paths.isNotEmpty) {
        _selectedPath = _paths.first;
      }
    });
  }

  Future<void> _submitIntroRequest() async {
    if (_selectedPath == null || _currentUserId == null) return;

    setState(() => _isSubmitting = true);

    final result = await _introRepo.createIntroRequest(
      founderId: _currentUserId!,
      investorId: widget.targetUserId,
      pathUserIds: _selectedPath!.nodes.map((n) => n.userId).toList(),
      message: _messageController.text.trim(),
    );

    setState(() => _isSubmitting = false);

    if (!mounted) return;

    if (result != null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('✅ Intro request sent!'),
          backgroundColor: Colors.green,
        ),
      );
      context.pop();
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('❌ Failed to send intro request'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.go('/home'),
        ),
        title: const Text('Request Introduction'),
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _paths.isEmpty
              ? _buildNoPathsState()
              : SingleChildScrollView(
                  padding: const EdgeInsets.all(16.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      // Target user card
                      Card(
                        child: Padding(
                          padding: const EdgeInsets.all(16.0),
                          child: Row(
                            children: [
                              const CircleAvatar(
                                radius: 24,
                                child: Icon(Icons.person),
                              ),
                              const SizedBox(width: 16),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    const Text(
                                      'Requesting introduction to:',
                                      style: TextStyle(
                                        fontSize: 12,
                                        color: Colors.grey,
                                      ),
                                    ),
                                    Text(
                                      widget.targetUserName,
                                      style: const TextStyle(
                                        fontSize: 18,
                                        fontWeight: FontWeight.bold,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                      const SizedBox(height: 24),

                      // Path selection
                      Text(
                        'Select Introduction Path',
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'Found ${_paths.length} path${_paths.length != 1 ? 's' : ''}',
                        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                              color: Colors.grey[600],
                            ),
                      ),
                      const SizedBox(height: 16),

                      // Path list
                      ..._paths.map((path) => _buildPathCard(path)),

                      const SizedBox(height: 24),

                      // Message field
                      TextField(
                        controller: _messageController,
                        maxLines: 4,
                        decoration: const InputDecoration(
                          labelText: 'Message (Optional)',
                          hintText: 'Add a brief message about why you\'d like this introduction...',
                          border: OutlineInputBorder(),
                        ),
                      ),
                      const SizedBox(height: 24),

                      // Submit button
                      FilledButton(
                        onPressed: _isSubmitting ? null : _submitIntroRequest,
                        style: FilledButton.styleFrom(
                          padding: const EdgeInsets.symmetric(vertical: 16),
                        ),
                        child: _isSubmitting
                            ? const SizedBox(
                                height: 20,
                                width: 20,
                                child: CircularProgressIndicator(strokeWidth: 2),
                              )
                            : const Text('Send Introduction Request'),
                      ),
                    ],
                  ),
                ),
    );
  }

  Widget _buildPathCard(PathModel path) {
    final isSelected = _selectedPath == path;
    
    return Card(
      elevation: isSelected ? 4 : 1,
      color: isSelected ? Colors.green.shade200.withOpacity(0.2) : null,
      margin: const EdgeInsets.only(bottom: 12),
      child: InkWell(
        onTap: () => setState(() => _selectedPath = path),
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Path header
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Row(
                    children: [
                      Icon(
                        isSelected ? Icons.radio_button_checked : Icons.radio_button_unchecked,
                        color: isSelected ? Theme.of(context).colorScheme.primary : Colors.grey,
                      ),
                      const SizedBox(width: 8),
                      Text(
                        '${path.hopCount} Hop${path.hopCount != 1 ? 's' : ''}',
                        style: TextStyle(
                          fontWeight: FontWeight.bold,
                          color: isSelected ? Theme.of(context).colorScheme.primary : null,
                        ),
                      ),
                    ],
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: _getScoreColor(path.pathScore),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Icon(Icons.star, size: 14, color: Colors.white),
                        const SizedBox(width: 4),
                        Text(
                          path.pathScore.toStringAsFixed(2),
                          style: const TextStyle(
                            color: Colors.white,
                            fontWeight: FontWeight.bold,
                            fontSize: 12,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),

              // Path visualization
              Row(
                children: _buildPathNodes(path),
              ),
              
              const SizedBox(height: 8),

              // Success probability
              LinearProgressIndicator(
                value: path.successProbability ?? 0.5,
                backgroundColor: Colors.grey[300],
                valueColor: AlwaysStoppedAnimation<Color>(
                  _getScoreColor(path.successProbability ?? 0.5),
                ),
              ),
              const SizedBox(height: 4),
              Text(
                '${((path.successProbability ?? 0.5) * 100).toStringAsFixed(0)}% success probability',
                style: TextStyle(
                  fontSize: 12,
                  color: Colors.grey[600],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  List<Widget> _buildPathNodes(PathModel path) {
    final widgets = <Widget>[];
    
    for (int i = 0; i < path.nodes.length; i++) {
      final node = path.nodes[i];
      
      // Add node
      widgets.add(
        Column(
          children: [
            CircleAvatar(
              radius: 16,
              child: Text(
                node.name[0].toUpperCase(),
                style: const TextStyle(fontSize: 12),
              ),
            ),
            const SizedBox(height: 4),
            SizedBox(
              width: 50,
              child: Text(
                node.name.split(' ').first,
                textAlign: TextAlign.center,
                style: const TextStyle(fontSize: 10),
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ],
        ),
      );
      
      // Add arrow between nodes (green + mutual indicator if edge is mutual)
      if (i < path.nodes.length - 1) {
        final edgeIsMutual = i < path.edges.length && path.edges[i].mutual;
        widgets.add(
          Padding(
            padding: const EdgeInsets.only(bottom: 20),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(
                  Icons.arrow_forward,
                  size: 16,
                  color: edgeIsMutual ? Colors.green : Colors.grey,
                ),
                if (edgeIsMutual)
                  Container(
                    margin: const EdgeInsets.only(top: 2),
                    width: 6,
                    height: 6,
                    decoration: const BoxDecoration(
                      color: Colors.green,
                      shape: BoxShape.circle,
                    ),
                  ),
              ],
            ),
          ),
        );
      }
    }
    
    return widgets;
  }

  Widget _buildNoPathsState() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.error_outline, size: 64, color: Colors.grey[400]),
            const SizedBox(height: 16),
            Text(
              'No Introduction Paths Found',
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    color: Colors.grey[600],
                  ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 8),
            Text(
              'There are no trust paths connecting you to ${widget.targetUserName}. Try building your network first.',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: Colors.grey[500],
                  ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 24),
            FilledButton.icon(
              onPressed: () => context.pop(),
              icon: const Icon(Icons.arrow_back),
              label: const Text('Go Back'),
            ),
          ],
        ),
      ),
    );
  }

  Color _getScoreColor(double score) {
    if (score >= 0.7) return Colors.green;
    if (score >= 0.4) return Colors.amber;
    return Colors.red;
  }
}
