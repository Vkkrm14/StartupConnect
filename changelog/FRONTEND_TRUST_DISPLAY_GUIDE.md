# Trust Level Display - Frontend Implementation Guide

## Overview

The frontend has been updated to display trust levels across the full -1.0 to 1.0 range, including visual indicators for both positive trust (TRUSTS edges) and negative trust (DISTRUSTS edges).

## Trust Score Scale

```
-1.0 ━━━━━━━━━ DISTRUST ━━━━━━━━━ 0.0 ━━━━━━━━━  TRUST  ━━━━━━━━━ 1.0
      Strong Distrust        Neutral        Strong Trust
```

### Score Ranges

| Score Range | TRUSTS Label | Color | Icon |
|---|---|---|---|
| 0.7 to 1.0 | High Trust | 🟢 Green | ✓ Check Circle |
| 0.4 to 0.7 | Medium Trust | 🔵 Blue | 👍 Thumb Up |
| 0.0 to 0.4 | Low Trust | 🔷 Light Blue | 😊 Sentiment Satisfied |
| -0.4 to 0.0 | Neutral | ⚪ Grey | ⭕ Circle |
| -0.7 to -0.4 | Distrust | 🟠 Orange | ⚠️ Warning |
| -1.0 to -0.7 | Strong Distrust | 🔴 Red | 🚫 Block |

### Special Cases

- **Disputed Distrust**: 🟠 Orange (even if severe) - indicates conflict being resolved
- **Conflicting Relationship**: 🟡 Yellow warning - both TRUSTS and DISTRUSTS exist

## UI Components

### 1. TrustLevelWidget

Circular indicator showing trust score at a glance.

```dart
TrustLevelWidget(
  trustScore: 0.75,
  label: 'Alice Smith',
  isDistrust: false,
  size: 60,
)
```

**Features:**
- Circular indicator with icon
- Tooltip on hover
- Color-coded by trust level
- Shows numeric score

### 2. TrustScoreBar

Horizontal progress bar for trust/distrust levels.

```dart
TrustScoreBar(
  trustScore: 0.65,
  label: 'Platform Reliability',
  isDistrust: false,
  height: 20,
)
```

**Features:**
- Directional (left=trust, right=distrust)
- Smooth transitions
- Tooltip with exact score
- Label support

### 3. TrustRelationshipCard

Complete card showing full relationship status.

```dart
TrustRelationshipCard(
  trustEdge: trustEdge,
  distrustEdge: distrustEdge,
  userName: 'David Lee',
  onTap: () => showDetails(),
)
```

**Features:**
- Shows both TRUSTS and DISTRUSTS if present
- Conflict warnings
- Dispute indicators
- Status information

### 4. TrustScoreLabel

Text label with emoji indicators.

```dart
TrustScoreLabel(
  trustScore: 0.85,
  style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
)
```

**Output Examples:**
- `🟢 High Trust` (score >= 0.7)
- `🔵 Medium Trust` (0.4-0.7)
- `🟠 Distrust` (-0.7 to -0.4)
- `🔴 Strong Distrust` (score <= -0.7)

## Models

### TrustEdgeModel (Updated)

Now supports full -1.0 to 1.0 range.

```dart
class TrustEdgeModel {
  final double trustScore; // -1.0 to 1.0
  
  String get trustLevel {
    if (trustScore >= 0.7) return 'high';
    if (trustScore >= 0.4) return 'medium';
    if (trustScore > 0) return 'low';
    if (trustScore == 0) return 'neutral';
    if (trustScore <= -0.7) return 'very_low';
    if (trustScore <= -0.4) return 'low_negative';
    return 'low';
  }
  
  bool get hasDistrustOverride => trustScore < 0;
}
```

### DisTrustEdgeModel (New)

Represents DISTRUSTS edges with full conflict resolution support.

```dart
class DisTrustEdgeModel {
  final double distrustScore; // -1.0 to -0.0
  final bool isActive;
  final bool isDisputed;
  final String reasonCategory; // fraud, unreliable_collaborator, etc.
  final double severity; // 0.0 to 1.0
  
  bool get isEnforced => isActive && !isDisputed;
  String get displayStatus { /* ... */ }
  bool get isExpired => DateTime.now().isAfter(expiresAt);
}
```

## Integration Examples

### Connection List with Trust Display

```dart
ListView.builder(
  itemCount: connections.length,
  itemBuilder: (context, index) {
    final connection = connections[index];
    return TrustRelationshipCard(
      trustEdge: connection.trustEdge,
      distrustEdge: connection.distrustEdge,
      userName: connection.userName,
      onTap: () => showConnectionDetails(connection),
    );
  },
)
```

### Search Results with Trust Badges

```dart
ListTile(
  title: Text(user.name),
  subtitle: TrustScoreLabel(
    trustScore: user.trustScore,
  ),
  leading: CircleAvatar(
    child: TrustLevelWidget(
      trustScore: user.trustScore,
      size: 40,
    ),
  ),
)
```

### Intro Path Visualization

```dart
Column(
  children: [
    for (var node in introPath.nodes)
      Column(
        children: [
          // User card
          UserCard(user: node),
          // Trust score to next node
          if (node != introPath.nodes.last)
            TrustScoreBar(
              trustScore: path.edgesAt(nodes.indexOf(node)).trustScore,
              label: 'Trust to next',
            ),
          Icon(Icons.arrow_downward),
        ],
      ),
  ],
)
```

## Color Scheme Reference

```dart
// Positive Trust Colors
Colors.green           // High trust (0.7-1.0)
Colors.blue            // Medium trust (0.4-0.7)
Colors.blue.shade200   // Low trust (0.0-0.4)

// Neutral
Colors.grey            // Neutral (0.0)

// Distrust Colors
Colors.orange          // Disputed / Low distrust (-0.4 to -0.0)
Colors.red.shade300    // Medium distrust (-0.7 to -0.4)
Colors.red             // Strong distrust (-1.0 to -0.7)

// Warnings
Colors.yellow.shade50  // Conflict warning background
Colors.orange          // Disputed distrust
```

## Behavior Guidelines

### When to Show DISTRUSTS

1. **On Connection Cards**: Always show if DISTRUSTS exists
2. **In Path Discovery**: Warn user if potential conflicts exist in path
3. **In Intro Requests**: Block if any path participant has active DISTRUSTS
4. **In Search Results**: Show distrust badge if marked by current user

### When to Show Conflict Warnings

- Both TRUSTS and DISTRUSTS edges exist
- DISTRUSTS is active (is_active=True)
- DISTRUSTS is not disputed (is_disputed=False)

### How to Handle Disputes

1. Show 🟠 Orange indicator instead of red
2. Display message: "This distrust is being disputed"
3. Allow appeal/resolution workflow
4. Don't enforce path filtering for disputed DISTRUSTS

## API Integration

### Fetching Connection Data

```dart
// Get trust edge with distrust check
final trustEdge = await connectionRepository.getTrustEdge(fromId, toId);
final distrustEdge = await connectionRepository.getDistrustEdge(fromId, toId);

// Build display
TrustRelationshipCard(
  trustEdge: trustEdge,
  distrustEdge: distrustEdge,
  userName: user.name,
)
```

### Reporting Distrust

```dart
// Create a new DISTRUSTS edge
await connectionRepository.reportDistrust(
  targetUserId: reportedUser.id,
  reasonCategory: 'unreliable_collaborator',
  severity: 0.7,
)
```

### Handling Disputes

```dart
// Dispute a DISTRUSTS edge
await connectionRepository.disputeDistrust(
  accuserId: accuser.id,
  reportedUserId: currentUser.id,
  appealReason: 'This is a misunderstanding...',
)
```

## Accessibility Considerations

1. **Color Blind Friendly**: All colors include icons
   - ✓, 👍, 😊 for trust
   - ⚠️, 🚫 for distrust

2. **Semantic Labels**: All widgets include tooltips and labels

3. **Text Contrast**: All text meets WCAG AA standards

4. **Screen Reader Support**: Labels include full descriptions

## Testing the UI

```dart
testWidgets('Trust level widget displays correct color', (tester) async {
  await tester.pumpWidget(
    MaterialApp(
      home: Scaffold(
        body: TrustLevelWidget(trustScore: 0.85),
      ),
    ),
  );
  
  // Verify green color for high trust
  expect(find.byColor(Colors.green), findsWidgets);
  expect(find.byIcon(Icons.check_circle), findsOneWidget);
});

testWidgets('Distrust indicator shows warning', (tester) async {
  await tester.pumpWidget(
    MaterialApp(
      home: Scaffold(
        body: TrustLevelWidget(
          trustScore: -0.8,
          isDistrust: true,
        ),
      ),
    ),
  );
  
  // Verify red color for strong distrust
  expect(find.byColor(Colors.red), findsWidgets);
  expect(find.byIcon(Icons.block), findsOneWidget);
});
```

## Migration Checklist

- [ ] Add DisTrustEdgeModel to models
- [ ] Update TrustEdgeModel for negative scores
- [ ] Add trust_level_widget.dart to widgets
- [ ] Update connection screens to use TrustRelationshipCard
- [ ] Update search results to show TrustScoreLabel
- [ ] Add DISTRUSTS API endpoints to repositories
- [ ] Update path display to show trust scores
- [ ] Add dispute/appeal UI to conflict screens
- [ ] Test with seeded DISTRUSTS data
- [ ] Update documentation/help screens

## Future Enhancements

1. **Custom Trust Weights**: Allow users to set trust thresholds
2. **Reputation Components**: Show breakdown of trust calculation
3. **Network Visualization**: Visualize trust/distrust relationships
4. **Confidence Indicators**: Show certainty of trust assessments
5. **Historical Tracking**: Show trust score changes over time
