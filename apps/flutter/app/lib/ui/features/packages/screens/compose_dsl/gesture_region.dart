// ignore_for_file: file_names

part of '../ToolPkgUiLauncherScreen.dart';

/// Connects Flutter gesture recognition to serialized Compose action callbacks.
class _ComposeGestureRegion extends StatefulWidget {
  /// Creates a gesture region for one modifier or canvas callback.
  const _ComposeGestureRegion({
    required this.kind,
    required this.options,
    required this.onAction,
    required this.child,
  });

  final String kind;
  final Map<String, Object?> options;

  /// Resolves function for the Compose DSL renderer.
  final Future<Object?> Function(String, [Object?]) onAction;
  final Widget child;

  /// Creates persistent gesture delta tracking.
  @override
  State<_ComposeGestureRegion> createState() => _ComposeGestureRegionState();
}

class _ComposeGestureRegionState extends State<_ComposeGestureRegion> {
  Offset _doubleTapPosition = Offset.zero;
  double _scale = 1;
  double _rotation = 0;

  /// Checks whether the plugin supplied a callback for this gesture.
  bool _has(String name) => _actionId(widget.options[name]) != null;

  /// Dispatches one recognized gesture with its contract payload.
  void _emit(String name, [Object? payload]) {
    final actionId = _actionId(widget.options[name]);
    if (actionId != null) {
      unawaited(widget.onAction(actionId, payload));
    }
  }

  /// Encodes local pointer coordinates in the public DSL shape.
  Map<String, Object?> _position(Offset value) => <String, Object?>{
    'x': value.dx,
    'y': value.dy,
  };

  /// Installs only the recognizers requested by this modifier.
  @override
  Widget build(BuildContext context) {
    switch (widget.kind) {
      case 'combinedclickable':
        return GestureDetector(
          behavior: HitTestBehavior.opaque,
          onTap: _has('onClick') ? () => _emit('onClick') : null,
          onDoubleTap: _has('onDoubleClick')
              ? () => _emit('onDoubleClick')
              : null,
          onLongPress: _has('onLongClick') ? () => _emit('onLongClick') : null,
          child: widget.child,
        );
      case 'tapgestures':
        return GestureDetector(
          behavior: HitTestBehavior.opaque,
          onTapDown: _has('onPress')
              ? (details) => _emit('onPress', _position(details.localPosition))
              : null,
          onTapUp: _has('onTap')
              ? (details) => _emit('onTap', _position(details.localPosition))
              : null,
          onDoubleTapDown: _has('onDoubleTap')
              ? (details) => _doubleTapPosition = details.localPosition
              : null,
          onDoubleTap: _has('onDoubleTap')
              ? () => _emit('onDoubleTap', _position(_doubleTapPosition))
              : null,
          onLongPressStart: _has('onLongPress')
              ? (details) =>
                    _emit('onLongPress', _position(details.localPosition))
              : null,
          child: widget.child,
        );
      case 'draggestures':
        return GestureDetector(
          behavior: HitTestBehavior.opaque,
          onPanStart: (details) =>
              _emit('onDragStart', _position(details.localPosition)),
          onPanUpdate: (details) => _emit('onDrag', <String, Object?>{
            ..._position(details.localPosition),
            'deltaX': details.delta.dx,
            'deltaY': details.delta.dy,
          }),
          onPanEnd: (_) => _emit('onDragEnd'),
          onPanCancel: () => _emit('onDragCancel'),
          child: widget.child,
        );
      case 'transformgestures':
        return GestureDetector(
          behavior: HitTestBehavior.opaque,
          onScaleStart: (_) {
            _scale = 1;
            _rotation = 0;
          },
          onScaleUpdate: (details) {
            _emit('onGesture', <String, Object?>{
              'centroidX': details.localFocalPoint.dx,
              'centroidY': details.localFocalPoint.dy,
              'panX': details.focalPointDelta.dx,
              'panY': details.focalPointDelta.dy,
              'zoom': details.scale / _scale,
              'rotation': (details.rotation - _rotation) * 180 / math.pi,
            });
            _scale = details.scale;
            _rotation = details.rotation;
          },
          child: widget.child,
        );
      default:
        throw StateError('Unknown Compose gesture: ${widget.kind}');
    }
  }
}
