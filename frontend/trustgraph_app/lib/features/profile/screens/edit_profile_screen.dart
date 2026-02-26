import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../../data/repositories/auth_repository.dart';
import '../../../data/repositories/user_repository.dart';
import '../../../data/providers/api_client.dart';

class EditProfileScreen extends StatefulWidget {
  const EditProfileScreen({super.key});

  @override
  State<EditProfileScreen> createState() => _EditProfileScreenState();
}

class _EditProfileScreenState extends State<EditProfileScreen> {
  final _apiClient = ApiClient();
  late final _authRepository = AuthRepository(_apiClient);
  late final _userRepository = UserRepository(_apiClient);

  final _formKey = GlobalKey<FormState>();
  final _bioController = TextEditingController();
  final _geographyController = TextEditingController();

  bool _isLoading = true;
  bool _isSaving = false;
  String? _userId;
  List<String> _selectedDomains = [];

  final List<String> _availableDomains = [
    'fintech',
    'healthtech',
    'edtech',
    'saas',
    'marketplace',
    'enterprise',
    'consumer',
    'deeptech',
    'ai/ml',
    'blockchain',
    'ecommerce',
    'hardware',
  ];

  @override
  void initState() {
    super.initState();
    _loadCurrentUser();
  }

  @override
  void dispose() {
    _bioController.dispose();
    _geographyController.dispose();
    super.dispose();
  }

  Future<void> _loadCurrentUser() async {
    setState(() => _isLoading = true);

    try {
      final user = await _authRepository.getCurrentUser();
      if (user != null) {
        setState(() {
          _userId = user.userId;
          _bioController.text = user.bio ?? '';
          _geographyController.text = user.geography ?? '';
          _selectedDomains = List.from(user.domainTags);
          _isLoading = false;
        });
      }
    } catch (e) {
      setState(() => _isLoading = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: ${ApiClient.getErrorMessage(e)}')),
        );
      }
    }
  }

  Future<void> _saveProfile() async {
    if (!_formKey.currentState!.validate() || _userId == null) return;

    setState(() => _isSaving = true);

    try {
      await _userRepository.updateProfile(
        userId: _userId!,
        bio: _bioController.text.trim(),
        domainTags: _selectedDomains,
        geography: _geographyController.text.trim().isEmpty ? null : _geographyController.text.trim(),
      );

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Profile updated successfully')),
        );
        context.pop();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: ${ApiClient.getErrorMessage(e)}')),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isSaving = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Edit Profile'),
        actions: [
          if (!_isLoading)
            TextButton(
              onPressed: _isSaving ? null : _saveProfile,
              child: _isSaving
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Text('SAVE'),
            ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : SingleChildScrollView(
              padding: const EdgeInsets.all(16),
              child: Form(
                key: _formKey,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Bio
                    TextFormField(
                      controller: _bioController,
                      decoration: const InputDecoration(
                        labelText: 'Bio',
                        hintText: 'Tell us about yourself...',
                        border: OutlineInputBorder(),
                      ),
                      maxLines: 4,
                      maxLength: 500,
                    ),

                    const SizedBox(height: 24),

                    // Domain Tags
                    Text(
                      'Expertise Areas',
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    const SizedBox(height: 8),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: _availableDomains.map((domain) {
                        final isSelected = _selectedDomains.contains(domain);
                        return FilterChip(
                          label: Text(domain),
                          selected: isSelected,
                          onSelected: (selected) {
                            setState(() {
                              if (selected) {
                                _selectedDomains.add(domain);
                              } else {
                                _selectedDomains.remove(domain);
                              }
                            });
                          },
                        );
                      }).toList(),
                    ),

                    const SizedBox(height: 24),

                    // Geography
                    TextFormField(
                      controller: _geographyController,
                      decoration: const InputDecoration(
                        labelText: 'Location',
                        hintText: 'San Francisco, CA',
                        border: OutlineInputBorder(),
                        prefixIcon: Icon(Icons.location_on),
                      ),
                    ),

                    const SizedBox(height: 32),

                    // Save Button
                    ElevatedButton(
                      onPressed: _isSaving ? null : _saveProfile,
                      style: ElevatedButton.styleFrom(
                        minimumSize: const Size(double.infinity, 48),
                      ),
                      child: _isSaving
                          ? const CircularProgressIndicator()
                          : const Text('Save Changes'),
                    ),
                  ],
                ),
              ),
            ),
    );
  }
}
