// Copyright 2013 The Flutter Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#if os(iOS)
  import Flutter
#elseif os(macOS)
  import FlutterMacOS
#else
  #error("Unsupported platform.")
#endif

public class WebViewFlutterPlugin: NSObject, FlutterPlugin {
  var proxyApiRegistrar: ProxyAPIRegistrar?
  private var themeChannel: FlutterMethodChannel?

  init(binaryMessenger: FlutterBinaryMessenger) {
    proxyApiRegistrar = ProxyAPIRegistrar(
      binaryMessenger: binaryMessenger)
    super.init()
    proxyApiRegistrar?.setUp()
    themeChannel = FlutterMethodChannel(name: "operit/webview_theme", binaryMessenger: binaryMessenger)
    // Updates only browser views so the Flutter system-theme source remains unchanged.
    themeChannel?.setMethodCallHandler { call, result in
      guard call.method == "setPreferredColorScheme" else {
        result(FlutterMethodNotImplemented)
        return
      }
      guard let scheme = call.arguments as? String, scheme == "dark" || scheme == "light" else {
        result(FlutterError(code: "invalid_color_scheme", message: "Expected dark or light", details: nil))
        return
      }
      WebViewTheme.setDark(scheme == "dark")
      result(nil)
    }
  }

  public static func register(with registrar: FlutterPluginRegistrar) {
    #if os(iOS)
      let binaryMessenger = registrar.messenger()
    #else
      let binaryMessenger = registrar.messenger
    #endif
    let plugin = WebViewFlutterPlugin(binaryMessenger: binaryMessenger)

    let viewFactory = FlutterViewFactory(instanceManager: plugin.proxyApiRegistrar!.instanceManager)

    #if os(iOS)
      registrar.addApplicationDelegate(plugin)
      registrar.addSceneDelegate(plugin)
    #endif

    registrar.register(viewFactory, withId: "plugins.flutter.io/webview")
    registrar.publish(plugin)
  }

  public func detachFromEngine(for registrar: FlutterPluginRegistrar) {
    themeChannel?.setMethodCallHandler(nil)
    tearDownProxyAPIRegistrar()
  }

  private func tearDownProxyAPIRegistrar() {
    proxyApiRegistrar?.ignoreCallsToDart = true
    proxyApiRegistrar?.tearDown()
    try? proxyApiRegistrar?.instanceManager.removeAllObjects()
    proxyApiRegistrar = nil
  }
}

/// Retains the application browser preference without retaining WebView instances.
enum WebViewTheme {
  private static var dark: Bool?
  private static let views = NSHashTable<WebViewImpl>.weakObjects()

  /// Applies the most recent preference to each newly constructed browser.
  static func register(_ view: WebViewImpl) {
    views.add(view)
    if let dark { apply(view, dark: dark) }
  }

  /// Propagates a preference change to all live browser views without navigation.
  static func setDark(_ value: Bool) {
    dark = value
    for view in views.allObjects { apply(view, dark: value) }
  }

  /// Changes the native appearance that WebKit exposes to page media queries.
  private static func apply(_ view: WebViewImpl, dark: Bool) {
    #if os(iOS)
      view.overrideUserInterfaceStyle = dark ? .dark : .light
    #elseif os(macOS)
      view.appearance = NSAppearance(named: dark ? .darkAqua : .aqua)
    #endif
  }
}

#if os(iOS)
  extension WebViewFlutterPlugin: FlutterApplicationLifeCycleDelegate, FlutterSceneLifeCycleDelegate
  {
    public func applicationWillTerminate(_ application: UIApplication) {
      tearDownProxyAPIRegistrar()
    }

    public func sceneDidDisconnect(_ scene: UIScene) {
      tearDownProxyAPIRegistrar()
    }
  }
#endif
