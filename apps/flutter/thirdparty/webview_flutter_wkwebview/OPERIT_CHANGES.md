# Operit integration

Based on webview_flutter_wkwebview 3.25.1, retaining its upstream license.

The common `operit/webview_theme` channel updates native WKWebView appearance.
The weak browser registry applies the preference to existing and newly created
views on iOS and macOS. It does not override application/window appearance, so
Flutter continues observing system theme changes independently.
