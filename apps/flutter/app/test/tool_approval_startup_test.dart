import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:operit2/core/permissions/ToolApprovalBridge.dart';
import 'package:operit2/core/permissions/ToolApprovalModels.dart';
import 'package:operit2/ui/permissions/ToolApprovalHost.dart';

class _RecordingApprovalBridge extends ToolApprovalBridge {
  int polls = 0;

  /// Records access to runtime permission state.
  @override
  Future<ToolApprovalRequest?> currentPermissionRequest() async {
    polls++;
    return null;
  }
}

/// Verifies permission polling across the runtime startup boundary.
void main() {
  testWidgets('approval polling waits for runtime readiness', (tester) async {
    final bridge = _RecordingApprovalBridge();

    /// Rebuilds the same approval host with the current runtime readiness.
    Widget host(bool enabled) => MaterialApp(
      home: ToolApprovalHost(
        enabled: enabled,
        bridge: bridge,
        child: const Text('onboarding'),
      ),
    );

    await tester.pumpWidget(host(false));
    await tester.pump(const Duration(seconds: 1));
    expect(find.text('onboarding'), findsOneWidget);
    expect(bridge.polls, 0);

    await tester.pumpWidget(host(true));
    await tester.pump(const Duration(milliseconds: 160));
    expect(bridge.polls, greaterThan(0));

    await tester.pumpWidget(host(false));
    final polls = bridge.polls;
    await tester.pump(const Duration(seconds: 1));
    expect(bridge.polls, polls);
    await tester.pumpWidget(const SizedBox.shrink());
  });
}
