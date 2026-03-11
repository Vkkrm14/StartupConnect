import 'package:flutter/material.dart';

class StartupSelectorDropdown extends StatelessWidget {
  final List<Map<String, dynamic>> startups;
  final String? selectedStartupId;
  final ValueChanged<String?> onChanged;
  final bool isLoading;

  const StartupSelectorDropdown({
    super.key,
    required this.startups,
    required this.selectedStartupId,
    required this.onChanged,
    this.isLoading = false,
  });

  @override
  Widget build(BuildContext context) {
    if (isLoading) {
      return const InputDecorator(
        decoration: InputDecoration(
          labelText: 'Select Startup',
          border: OutlineInputBorder(),
        ),
        child: Row(
          children: [
            SizedBox(
              width: 16,
              height: 16,
              child: CircularProgressIndicator(strokeWidth: 2),
            ),
            SizedBox(width: 12),
            Text('Loading startups...'),
          ],
        ),
      );
    }

    if (startups.isEmpty) {
      return const InputDecorator(
        decoration: InputDecoration(
          labelText: 'Select Startup',
          border: OutlineInputBorder(),
        ),
        child: Text(
          'No startups found. You must be a founder to create posts.',
          style: TextStyle(color: Colors.grey),
        ),
      );
    }

    return DropdownButtonFormField<String>(
      value: selectedStartupId,
      decoration: const InputDecoration(
        labelText: 'Select Startup',
        border: OutlineInputBorder(),
      ),
      items: startups.map((s) {
        return DropdownMenuItem<String>(
          value: s['startup_id'] as String,
          child: Text(
            '${s['name']} (${s['stage']})',
            overflow: TextOverflow.ellipsis,
          ),
        );
      }).toList(),
      onChanged: onChanged,
      validator: (value) {
        if (value == null || value.isEmpty) {
          return 'Please select a startup';
        }
        return null;
      },
    );
  }
}
