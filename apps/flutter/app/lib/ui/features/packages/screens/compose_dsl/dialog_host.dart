// ignore_for_file: file_names

part of '../ToolPkgUiLauncherScreen.dart';

/// Owns a modal route for as long as its Compose node remains mounted.
class _ComposeDialogHost extends StatefulWidget {
  /// Creates a modal whose content and dismissal policy follow plugin updates.
  const _ComposeDialogHost({
    required this.properties,
    required this.onDismissRequest,
    required this.closeOnDismissRequest,
    required this.dialogBuilder,
  });

  final Map<String, Object?> properties;

  /// Resolves function for the Compose DSL renderer.
  final Future<void> Function() onDismissRequest;
  final bool closeOnDismissRequest;

  /// Builds function for the Compose DSL renderer.
  final Widget Function(BuildContext, VoidCallback) dialogBuilder;

  /// Creates the modal route lifecycle owner.
  @override
  State<_ComposeDialogHost> createState() => _ComposeDialogHostState();
}

class _ComposeDialogHostState extends State<_ComposeDialogHost> {
  final ValueNotifier<int> _revision = ValueNotifier<int>(0);
  RawDialogRoute<void>? _route;
  bool _closed = false;

  /// Defers route insertion until the owning frame has completed.
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _open());
  }

  /// Refreshes the active modal without replacing its route or input state.
  @override
  void didUpdateWidget(covariant _ComposeDialogHost oldWidget) {
    super.didUpdateWidget(oldWidget);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) _revision.value++;
    });
  }

  /// Dispatches dismissal requests before applying the plugin's close policy.
  Future<void> _dismiss() async {
    await widget.onDismissRequest();
    if (mounted && widget.closeOnDismissRequest) _close();
  }

  /// Removes only the route owned by this dialog node.
  void _close() {
    _closed = true;
    final route = _route;
    _route = null;
    if (route?.isActive == true) route!.navigator!.removeRoute(route);
  }

  /// Opens a modal with independent outside-click and back-button policies.
  void _open() {
    if (!mounted || _closed) return;
    final route = RawDialogRoute<void>(
      barrierDismissible: false,
      barrierColor: Colors.black54,
      pageBuilder: (context, animation, secondaryAnimation) {
        return ValueListenableBuilder<int>(
          valueListenable: _revision,
          builder: (context, revision, child) {
            Widget dialog = widget.dialogBuilder(context, _close);
            if (widget.properties['decorFitsSystemWindows'] != false) {
              dialog = SafeArea(child: dialog);
            }
            return PopScope(
              canPop: false,
              onPopInvokedWithResult: (didPop, result) {
                if (!didPop &&
                    widget.properties['dismissOnBackPress'] != false) {
                  unawaited(_dismiss());
                }
              },
              child: Stack(
                fit: StackFit.expand,
                children: <Widget>[
                  GestureDetector(
                    behavior: HitTestBehavior.opaque,
                    onTap: widget.properties['dismissOnClickOutside'] != false
                        ? _dismiss
                        : null,
                  ),
                  Center(child: dialog),
                ],
              ),
            );
          },
        );
      },
    );
    _route = route;
    unawaited(Navigator.of(context).push(route));
  }

  /// Removes the modal after the frame that removes its source node.
  @override
  void dispose() {
    final route = _route;
    _route = null;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (route?.isActive == true) route!.navigator!.removeRoute(route);
      _revision.dispose();
    });
    super.dispose();
  }

  /// Keeps modal nodes out of the surrounding layout.
  @override
  Widget build(BuildContext context) => const SizedBox.shrink();
}
