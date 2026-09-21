#![allow(non_snake_case)]
// Compile the actual firmware modules, including the same stream renderer.
#[path = "../../../../apps/esp32/src/edge_chat.rs"]
mod edge_chat;
#[path = "../../../../apps/esp32/src/edge_session.rs"]
mod edge_session;
#[cfg(test)]
mod tests;

use operit_edge_transport::{
    tcp::TcpLinkChannel, EdgePairingAuthority, EdgePairingPersistentState, EdgePairingStore,
};
use std::{
    io::Write,
    path::PathBuf,
    sync::{Arc, Mutex},
};
use tokio::io::{AsyncBufReadExt, BufReader};

struct FileStore(PathBuf);
impl EdgePairingStore for FileStore {
    fn load(&self) -> Result<Option<EdgePairingPersistentState>, String> {
        match std::fs::read(&self.0) {
            Ok(bytes) => serde_json::from_slice(&bytes)
                .map(Some)
                .map_err(|e| e.to_string()),
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => Ok(None),
            Err(e) => Err(e.to_string()),
        }
    }
    fn save(&self, state: &EdgePairingPersistentState) -> Result<(), String> {
        let bytes = serde_json::to_vec(state).map_err(|e| e.to_string())?;
        let temporary = self.0.with_extension("tmp");
        std::fs::write(&temporary, bytes).map_err(|e| e.to_string())?;
        std::fs::rename(temporary, &self.0).map_err(|e| e.to_string())
    }
}

fn emit(value: serde_json::Value) {
    let mut stdout = std::io::stdout().lock();
    writeln!(stdout, "{value}").expect("editor IPC closed");
    stdout.flush().expect("editor IPC closed");
}

#[tokio::main(flavor = "current_thread")]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let token = std::env::var("OPERIT_SIM_TOKEN")?;
    if token.is_empty() {
        return Err("Simulator token is empty".into());
    }
    let statePath = PathBuf::from(std::env::var("OPERIT_SIM_STATE")?);
    let code = Arc::new(Mutex::new(String::new()));
    let error = Arc::new(Mutex::new(String::new()));
    let lastAction = Arc::new(Mutex::new(String::new()));
    let authority = Arc::new(EdgePairingAuthority::newWithStore(
        token,
        "esp32-edge-simulator",
        operit_link::LinkDeviceInfo {
            platform: "esp32".into(),
            model: "ESP32-2432S028".into(),
        },
        Arc::new(FileStore(statePath)),
        {
            let code = code.clone();
            move |value| {
                *code.lock().unwrap() = value;
            }
        },
    )?);
    // Match a normal LAN node: the editor IPC remains local, while the Edge
    // Link carrier is reachable by a Core on the same network by default.
    let address = std::env::var("OPERIT_SIM_BIND").unwrap_or_else(|_| "0.0.0.0:18765".into());
    let listener = TcpLinkChannel::bind(&address).await?;
    let address = listener.local_addr()?.to_string();
    let sessionError = error.clone();
    let active = Arc::new(tokio::sync::Mutex::new(()));
    tokio::spawn(async move {
        loop {
            let (stream, _) = match listener.accept().await {
                Ok(value) => value,
                Err(e) => {
                    *sessionError.lock().unwrap() = e.to_string();
                    break;
                }
            };
            let Ok(guard) = active.clone().try_lock_owned() else {
                drop(stream);
                continue;
            };
            let authority = authority.clone();
            let error = sessionError.clone();
            tokio::spawn(async move {
                let _guard = guard;
                *error.lock().unwrap() = String::new();
                if let Err(e) =
                    edge_session::handleChannel(authority, TcpLinkChannel::fromStream(stream)).await
                {
                    *error.lock().unwrap() = e;
                }
            });
        }
    });
    emit(serde_json::json!({"ready": true, "address": address}));
    let mut lines = BufReader::new(tokio::io::stdin()).lines();
    while let Some(line) = lines.next_line().await? {
        let request: serde_json::Value = serde_json::from_str(&line)?;
        let id = request["id"].clone();
        let result = match request["command"].as_str() {
            Some("state") => Ok(serde_json::json!({"address": address,
                "pairingCode": *code.lock().unwrap(), "error": *error.lock().unwrap(),
                "lastAction": *lastAction.lock().unwrap(),
                "chat": edge_chat::snapshot(), "chatPreview": edge_chat::preview()})),
            Some("action") => {
                let action = request["action"].as_str().unwrap_or("");
                *lastAction.lock().unwrap() = action.to_string();
                Ok(serde_json::json!({"ok": true, "action": action}))
            }
            Some("send") => edge_chat::send(request["text"].as_str().unwrap_or("").into())
                .map(|_| serde_json::json!({"ok": true})),
            _ => Err("Unknown simulator command".into()),
        };
        match result {
            Ok(value) => emit(serde_json::json!({"id": id, "value": value})),
            Err(error) => emit(serde_json::json!({"id": id, "error": error})),
        }
    }
    Ok(())
}
