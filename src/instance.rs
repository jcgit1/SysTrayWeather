use std::fs::{self, File, OpenOptions};
use std::path::{Path, PathBuf};

/// Held for the life of the process. Dropping it releases the lock.
pub struct InstanceLock {
    _file: Option<File>,
}

pub struct AlreadyRunning;

/// Lock this user's copy of this executable.
///
/// The lock file lives in the per-user runtime directory and its name is the
/// path of this binary, so another account can run the same program.
pub fn acquire() -> Result<InstanceLock, AlreadyRunning> {
    let path = lock_path();
    if let Some(dir) = path.parent() {
        if let Err(err) = fs::create_dir_all(dir) {
            crate::log::warn(&format!("could not create instance lock dir: {err}"));
            return Ok(InstanceLock { _file: None });
        }
    }
    let file = match OpenOptions::new()
        .read(true)
        .write(true)
        .create(true)
        .truncate(false)
        .open(&path)
    {
        Ok(file) => file,
        Err(err) => {
            crate::log::warn(&format!(
                "could not open instance lock {}: {err}",
                path.display()
            ));
            return Ok(InstanceLock { _file: None });
        }
    };
    match file.try_lock() {
        Ok(()) => {
            crate::log::info(&format!("single instance lock {}", path.display()));
            Ok(InstanceLock { _file: Some(file) })
        }
        Err(std::fs::TryLockError::WouldBlock) => Err(AlreadyRunning),
        Err(std::fs::TryLockError::Error(err)) => {
            crate::log::warn(&format!("instance lock failed: {err}"));
            Ok(InstanceLock { _file: None })
        }
    }
}

fn lock_path() -> PathBuf {
    lock_dir().join(format!("systrayweather-{}.lock", binary_key()))
}

fn lock_dir() -> PathBuf {
    #[cfg(unix)]
    if let Some(runtime) = std::env::var_os("XDG_RUNTIME_DIR") {
        let path = PathBuf::from(runtime);
        if !path.as_os_str().is_empty() {
            return path;
        }
    }
    crate::config::config_dir()
}

fn binary_key() -> String {
    let exe = std::env::current_exe()
        .ok()
        .and_then(|path| path.canonicalize().ok())
        .unwrap_or_else(|| PathBuf::from("systrayweather"));
    fnv(&exe)
}

fn fnv(path: &Path) -> String {
    let mut hash: u64 = 0xcbf29ce484222325;
    for byte in path.to_string_lossy().as_bytes() {
        hash ^= u64::from(*byte);
        hash = hash.wrapping_mul(0x100000001b3);
    }
    format!("{hash:016x}")
}
