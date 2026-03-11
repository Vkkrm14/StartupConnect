import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import '../services/post_provider.dart';
import '../widgets/startup_selector_dropdown.dart';
import '../widgets/tag_input_field.dart';

class CreatePostScreen extends StatefulWidget {
  const CreatePostScreen({super.key});

  @override
  State<CreatePostScreen> createState() => _CreatePostScreenState();
}

class _CreatePostScreenState extends State<CreatePostScreen> {
  final _formKey = GlobalKey<FormState>();
  final _titleController = TextEditingController();
  final _bodyController = TextEditingController();
  String? _selectedStartupId;
  List<String> _tags = [];
  bool _isSubmitting = false;

  @override
  void dispose() {
    _titleController.dispose();
    _bodyController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    if (_selectedStartupId == null) return;

    setState(() => _isSubmitting = true);

    try {
      await context.read<PostProvider>().createPost(
            startupId: _selectedStartupId!,
            title: _titleController.text.trim(),
            body: _bodyController.text.trim(),
            tags: _tags,
          );

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Post published!')),
        );
        context.pop();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to publish: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _isSubmitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('New Update'),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 8),
            child: FilledButton(
              onPressed: _isSubmitting ? null : _submit,
              child: _isSubmitting
                  ? const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Text('Publish'),
            ),
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              StartupSelectorDropdown(
                selectedStartupId: _selectedStartupId,
                onChanged: (id) => setState(() => _selectedStartupId = id),
              ),
              const SizedBox(height: 16),
              TextFormField(
                controller: _titleController,
                decoration: const InputDecoration(
                  labelText: 'Title',
                  hintText: 'e.g. "Series A Closed!" or "New Feature Launch"',
                  border: OutlineInputBorder(),
                ),
                maxLength: 120,
                validator: (v) =>
                    (v == null || v.trim().isEmpty) ? 'Title is required' : null,
              ),
              const SizedBox(height: 16),
              TextFormField(
                controller: _bodyController,
                decoration: const InputDecoration(
                  labelText: 'Body',
                  hintText: 'Share your update details...',
                  border: OutlineInputBorder(),
                  alignLabelWithHint: true,
                ),
                maxLength: 2000,
                maxLines: 8,
                minLines: 4,
                validator: (v) =>
                    (v == null || v.trim().isEmpty) ? 'Body is required' : null,
              ),
              const SizedBox(height: 16),
              TagInputField(
                tags: _tags,
                onTagsChanged: (tags) => setState(() => _tags = tags),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
