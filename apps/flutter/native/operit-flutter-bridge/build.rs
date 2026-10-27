/// Points the bridge at the shared local inference engine it was linked with.
fn main() {
    let target_os = std::env::var("CARGO_CFG_TARGET_OS").unwrap_or_default();
    let target_env = std::env::var("CARGO_CFG_TARGET_ENV").unwrap_or_default();
    if target_os == "linux" && target_env != "musl" {
        println!("cargo:rustc-link-arg=-Wl,-rpath,$ORIGIN");
    }
}
