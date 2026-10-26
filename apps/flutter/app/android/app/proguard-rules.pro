# AndroidRuntimeHost methods are resolved by Rust through JNI GetMethodID.
# Their Java names and descriptors are an ABI shared with the native bridge.
-keepclassmembers class app.operit.AndroidRuntimeHost {
    public *** *(...);
}

# OperitRuntimeNative methods are exported by liboperit_flutter_bridge with exact JNI symbol names.
-keep class app.operit.OperitRuntimeNative {
    *;
}

# Sherpa ONNX JNI resolves binding classes, constructors, fields, and methods by exact JVM names.
-keep class com.k2fsa.sherpa.onnx.** {
    *;
}

# FlutterEngine loads the generated plugin registrant by name, and the embedding
# reaches several entry points through reflection.
-keep class io.flutter.plugins.** {
    *;
}
-keep class io.flutter.app.** {
    *;
}
-keep class io.flutter.embedding.** {
    *;
}
-keep class io.flutter.plugin.** {
    *;
}
-keep class io.flutter.util.** {
    *;
}
-keep class io.flutter.view.** {
    *;
}

# Keep source information so release crash reports stay readable.
-keepattributes SourceFile,LineNumberTable
-renamesourcefileattribute SourceFile
