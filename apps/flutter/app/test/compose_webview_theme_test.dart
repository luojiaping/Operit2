import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:webview_all_linux/webview_all_linux.dart';
import 'package:webview_flutter_platform_interface/webview_flutter_platform_interface.dart';
import 'package:operit2/ui/features/packages/screens/ToolPkgComposeDslWebView.dart';

/// Verifies native preference delivery and browser-preserving theme updates.
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('Linux registers into the shared browser interface', () {
    LinuxWebViewPlatform.registerWith();
    expect(WebViewPlatform.instance, isA<LinuxWebViewPlatform>());
  });

  testWidgets(
    'applies theme before navigation and changes it without reloading',
    (tester) async {
      final platform = _ThemeTestPlatform();
      WebViewPlatform.instance = platform;
      final events = <String>[];
      final ready = Completer<void>();
      platform.controller.events = events;
      const channel = MethodChannel('operit/webview_theme');
      tester.binding.defaultBinaryMessenger.setMockMethodCallHandler(channel, (
        call,
      ) async {
        expect(call.method, 'setPreferredColorScheme');
        events.add('theme:${call.arguments}');
        await ready.future;
        return null;
      });
      addTearDown(
        () => tester.binding.defaultBinaryMessenger.setMockMethodCallHandler(
          channel,
          null,
        ),
      );

      /// Rebuilds the inherited app theme while retaining the same browser element.
      Widget screen(Brightness brightness) => MaterialApp(
        theme: ThemeData(brightness: brightness),
        home: ComposeDslWebView(
          props: const {'url': 'https://example.com'},
          onAction: (id, [payload]) async => null,
          hostContext: null,
        ),
      );

      await tester.pumpWidget(screen(Brightness.dark));
      await tester.pump();
      expect(events, ['theme:dark']);
      ready.complete();
      await tester.pumpAndSettle();
      expect(events, ['theme:dark', 'load:https://example.com']);
      await tester.pumpWidget(screen(Brightness.light));
      await tester.pumpAndSettle();
      expect(events, ['theme:dark', 'load:https://example.com', 'theme:light']);
      await tester.pumpWidget(screen(Brightness.light));
      await tester.pumpAndSettle();
      expect(events.length, 3);
      await tester.pumpWidget(const SizedBox());
    },
  );
}

class _ThemeTestPlatform extends WebViewPlatform {
  final controller = _ThemeTestController();

  /// Returns one stable browser for the lifecycle test.
  @override
  PlatformWebViewController createPlatformWebViewController(
    PlatformWebViewControllerCreationParams params,
  ) => controller;

  /// Creates a no-op delegate because this test does not emulate page events.
  @override
  PlatformNavigationDelegate createPlatformNavigationDelegate(
    PlatformNavigationDelegateCreationParams params,
  ) => _ThemeTestDelegate(params);

  /// Renders an inert view while exercising the production browser controller.
  @override
  PlatformWebViewWidget createPlatformWebViewWidget(
    PlatformWebViewWidgetCreationParams params,
  ) => _ThemeTestWidget(params);
}

class _ThemeTestWidget extends PlatformWebViewWidget {
  /// Creates a native-view placeholder.
  _ThemeTestWidget(super.params) : super.implementation();

  /// Avoids native view composition during widget tests.
  @override
  Widget build(BuildContext context) => const SizedBox.expand();
}

class _ThemeTestController extends PlatformWebViewController {
  /// Creates a controller that uses the real native theme channel contract.
  _ThemeTestController()
    : super.implementation(const PlatformWebViewControllerCreationParams());
  List<String> events = [];

  /// Records navigation for detecting unexpected page reloads.
  @override
  Future<void> loadRequest(LoadRequestParams params) async {
    events.add('load:${params.uri}');
  }

  /// Accepts the blank page used during disposal.
  @override
  Future<void> loadHtmlString(String html, {String? baseUrl}) async {}

  /// Accepts page bridge injection.
  @override
  Future<void> runJavaScript(String javaScript) async {}

  /// Accepts the page's JavaScript policy.
  @override
  Future<void> setJavaScriptMode(JavaScriptMode mode) async {}

  /// Accepts the page's background color.
  @override
  Future<void> setBackgroundColor(Color color) async {}

  /// Accepts the page's navigation delegate.
  @override
  Future<void> setPlatformNavigationDelegate(
    PlatformNavigationDelegate handler,
  ) async {}

  /// Accepts the page bridge channel.
  @override
  Future<void> addJavaScriptChannel(JavaScriptChannelParams params) async {}

  /// Accepts console observation.
  @override
  Future<void> setOnConsoleMessage(
    void Function(JavaScriptConsoleMessage) callback,
  ) async {}

  /// Accepts permission observation.
  @override
  Future<void> setOnPlatformPermissionRequest(
    void Function(PlatformWebViewPermissionRequest) callback,
  ) async {}

  /// Accepts native alert handling.
  @override
  Future<void> setOnJavaScriptAlertDialog(
    Future<void> Function(JavaScriptAlertDialogRequest) callback,
  ) async {}

  /// Accepts native confirmation handling.
  @override
  Future<void> setOnJavaScriptConfirmDialog(
    Future<bool> Function(JavaScriptConfirmDialogRequest) callback,
  ) async {}

  /// Accepts native text dialog handling.
  @override
  Future<void> setOnJavaScriptTextInputDialog(
    Future<String> Function(JavaScriptTextInputDialogRequest) callback,
  ) async {}

  /// Accepts zoom configuration.
  @override
  Future<void> enableZoom(bool enabled) async {}

  /// Accepts vertical scrollbar configuration.
  @override
  Future<void> setVerticalScrollBarEnabled(bool enabled) async {}

  /// Accepts horizontal scrollbar configuration.
  @override
  Future<void> setHorizontalScrollBarEnabled(bool enabled) async {}
}

class _ThemeTestDelegate extends PlatformNavigationDelegate {
  /// Creates a delegate with inert callbacks.
  _ThemeTestDelegate(super.params) : super.implementation();

  /// Accepts navigation request callbacks.
  @override
  Future<void> setOnNavigationRequest(
    NavigationRequestCallback callback,
  ) async {}

  /// Accepts page start callbacks.
  @override
  Future<void> setOnPageStarted(PageEventCallback callback) async {}

  /// Accepts page completion callbacks.
  @override
  Future<void> setOnPageFinished(PageEventCallback callback) async {}

  /// Accepts loading progress callbacks.
  @override
  Future<void> setOnProgress(ProgressCallback callback) async {}

  /// Accepts resource failure callbacks.
  @override
  Future<void> setOnWebResourceError(WebResourceErrorCallback callback) async {}

  /// Accepts URL change callbacks.
  @override
  Future<void> setOnUrlChange(UrlChangeCallback callback) async {}

  /// Accepts HTTP authentication callbacks.
  @override
  Future<void> setOnHttpAuthRequest(HttpAuthRequestCallback callback) async {}

  /// Accepts HTTP error callbacks.
  @override
  Future<void> setOnHttpError(HttpResponseErrorCallback callback) async {}

  /// Accepts certificate error callbacks.
  @override
  Future<void> setOnSSlAuthError(SslAuthErrorCallback callback) async {}
}
