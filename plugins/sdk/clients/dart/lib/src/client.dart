import 'transport.dart';

/// Concrete external Plugin SDK client backed by the built-in IPC connection.
final class OperitPluginSdkClient {
  const OperitPluginSdkClient._(this._connection);

  final PluginSdkIpcConnection _connection;

  /// Activates Operit and connects through the SDK's packaged platform host.
  static Future<OperitPluginSdkClient> connect({
    String nativeLibraryPath = 'liboperit_plugin_sdk.so',
  }) async {
    return OperitPluginSdkClient._(
      await PluginSdkIpcConnection.connect(
        nativeLibraryPath: nativeLibraryPath,
      ),
    );
  }

  /// Releases the SDK session and its pending operations.
  void close() => _connection.close();

  /// Calls one generated Core object method through Link IPC.
  Future<Object?> call(
    int targetObjectId,
    String methodName,
    Object? args,
  ) async {
    final response = await _connection.call(targetObjectId, methodName, args);
    return response['value'];
  }

  /// Calls one route and decodes its typed result.
  Future<T> callTyped<T>(
    int targetObjectId,
    String methodName,
    Object? args,
    T Function(Object? value) decode,
  ) async {
    final value = await call(targetObjectId, methodName, args);
    return decode(value);
  }

  /// Watches one generated Core object property through Link IPC.
  Stream<PluginSdkEvent> watch(
    int targetObjectId,
    String propertyName,
    Object? args,
  ) => _connection.watch(targetObjectId, propertyName, args);

  /// Watches one route and decodes each event value.
  Stream<T> watchTyped<T>(
    int targetObjectId,
    String propertyName,
    Object? args,
    T Function(Object? value) decode,
  ) => watch(
    targetObjectId,
    propertyName,
    args,
  ).map((event) => decode(event.value));

  /// Opens one generated caller-owned Core input stream through Link IPC.
  Future<PluginSdkPushSink> push(
    int targetObjectId,
    String methodName,
    Object? args,
  ) => _connection.push(targetObjectId, methodName, args);
}
