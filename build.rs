use std::process::Command;

fn main() {
    let git = Command::new("git")
        .args(["rev-parse", "--short=7", "HEAD"])
        .output()
        .ok()
        .and_then(|out| {
            if out.status.success() {
                Some(String::from_utf8_lossy(&out.stdout).trim().to_string())
            } else {
                None
            }
        });
    match git {
        Some(hash) => println!("cargo:rustc-env=STW_GIT_HASH={hash}"),
        None => println!("cargo:rustc-env=STW_GIT_HASH=unknown"),
    }
    // Stamp a fresh UTC build time into every binary. Deliberately NOT
    // re-run-if-changed-gated: cargo re-runs build.rs at the start of every
    // build. The stamp is also written into build/compiled-at.rs, a source
    // file the crate includes, so the crate itself re-links each build and
    // every binary carries a distinct stamp.
    let now = Command::new("date")
        .args(["-u", "+%Y-%m-%d %H:%M:%S"])
        .output()
        .ok()
        .and_then(|out| {
            if out.status.success() {
                Some(String::from_utf8_lossy(&out.stdout).trim().to_string())
            } else {
                None
            }
        })
        .unwrap_or_else(|| "unknown".to_string());
    let out = std::path::PathBuf::from(std::env::var("OUT_DIR").unwrap());
    std::fs::write(out.join("compiled-at.rs"), format!("\"{now}\"\n")).expect("write stamp");
    println!("cargo:rustc-env=STW_BUILD_TIME={now}");
}
