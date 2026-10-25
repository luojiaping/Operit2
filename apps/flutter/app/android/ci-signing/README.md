# CI test signing material

`ci-test-release.keystore` and `signing.properties` exist so CNB can produce a
signed release APK while Operit2 is still in preview. The keystore password is
public by design; it protects nothing.

Replace this material with a private keystore before the first public release.
Android refuses to update an installed app whose signing certificate changed,
so switching later forces every user to uninstall and reinstall.
