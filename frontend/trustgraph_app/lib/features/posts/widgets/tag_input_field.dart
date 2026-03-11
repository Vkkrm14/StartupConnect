import 'package:flutter/material.dart';

class TagInputField extends StatefulWidget {
  final List<String> tags;
  final ValueChanged<List<String>> onChanged;
  final int maxTags;

  const TagInputField({
    super.key,
    required this.tags,
    required this.onChanged,
    this.maxTags = 10,
  });

  @override
  State<TagInputField> createState() => _TagInputFieldState();
}

class _TagInputFieldState extends State<TagInputField> {
  final _controller = TextEditingController();
  final _focusNode = FocusNode();

  void _addTag(String raw) {
    final tag = raw.trim().replaceAll(',', '');
    if (tag.isEmpty) return;
    if (tag.length > 30) return;
    if (widget.tags.length >= widget.maxTags) return;
    if (widget.tags.contains(tag.toLowerCase())) return;

    final updated = [...widget.tags, tag.toLowerCase()];
    widget.onChanged(updated);
    _controller.clear();
  }

  void _removeTag(int index) {
    final updated = [...widget.tags]..removeAt(index);
    widget.onChanged(updated);
  }

  @override
  void dispose() {
    _controller.dispose();
    _focusNode.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        TextFormField(
          controller: _controller,
          focusNode: _focusNode,
          decoration: InputDecoration(
            labelText: 'Tags',
            hintText: widget.tags.length >= widget.maxTags
                ? 'Max tags reached'
                : 'Type and press Enter',
            border: const OutlineInputBorder(),
            suffixIcon: IconButton(
              icon: const Icon(Icons.add),
              onPressed: () => _addTag(_controller.text),
            ),
          ),
          enabled: widget.tags.length < widget.maxTags,
          onFieldSubmitted: (value) {
            _addTag(value);
            _focusNode.requestFocus();
          },
          onChanged: (value) {
            if (value.contains(',')) {
              _addTag(value);
            }
          },
        ),
        if (widget.tags.isNotEmpty) ...[
          const SizedBox(height: 8),
          Wrap(
            spacing: 6,
            runSpacing: 4,
            children: widget.tags.asMap().entries.map((entry) {
              return Chip(
                label: Text(entry.value, style: const TextStyle(fontSize: 12)),
                deleteIcon: const Icon(Icons.close, size: 16),
                onDeleted: () => _removeTag(entry.key),
                visualDensity: VisualDensity.compact,
              );
            }).toList(),
          ),
        ],
      ],
    );
  }
}
