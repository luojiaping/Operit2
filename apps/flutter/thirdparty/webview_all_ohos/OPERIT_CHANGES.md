# Operit integration

Based on webview_all_ohos 1.4.0, retaining its upstream license.

The main ArkWeb view and popup view bind `darkMode` to `operitWebViewDark` in
AppStorage. The host theme channel updates that value from Flutter's resolved
brightness. Forced page recoloring is disabled; websites receive the browser's
native color preference. No page JavaScript is needed and navigation is retained.

`webview_platform_interface` is resolved through the shared local interface package.
OHOS Dart checks require the Flutter OHOS SDK, whose services library defines
OhosViewController and OhosViewSurface.
