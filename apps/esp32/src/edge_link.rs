#![allow(non_snake_case)]

use std::sync::Arc;
use std::thread::JoinHandle;

use esp_idf_hal::uart::UartDriver;
use operit_edge_transport::{EdgePairingAuthority, EdgePairingStore};
use operit_host_api::{HostError, HostResult};
use operit_link::LinkDeviceInfo;
use tokio::runtime::Builder;

use crate::edge_serial::Esp32UartLinkChannel;
use crate::edge_session::handleChannel;
use crate::status::FirmwareStatus;

/// Runs the authenticated standard-Link listener on a dedicated ESP-IDF task.
pub struct Esp32EdgeLinkServer {
    _thread: JoinHandle<()>,
}

impl Esp32EdgeLinkServer {
    pub fn start(
        port: u16,
        token: String,
        status: Arc<FirmwareStatus>,
        store: Arc<dyn EdgePairingStore>,
        uart: Option<UartDriver<'static>>,
    ) -> HostResult<Option<Self>> {
        if token.trim().is_empty() {
            log::warn!("Edge Link disabled: OPERIT_EDGE_TOKEN is not configured");
            return Ok(None);
        }
        let thread = std::thread::Builder::new()
            .name("operit-edge-link".to_string())
            .spawn(move || {
                let runtime = match Builder::new_current_thread().enable_all().build() {
                    Ok(runtime) => runtime,
                    Err(error) => {
                        log::error!("Edge Link runtime: {error}");
                        return;
                    }
                };
                let authority = match EdgePairingAuthority::newWithStore(
                    token,
                    "esp32-edge".to_string(),
                    LinkDeviceInfo {
                        platform: "esp32".to_string(),
                        model: "ESP32-2432S028".to_string(),
                    },
                    store,
                    {
                        let status = Arc::clone(&status);
                        move |code| {
                            status.setPairingCode(code.clone());
                            log::info!("Edge Link pairing code: {code}");
                        }
                    },
                ) {
                    Ok(authority) => Arc::new(authority),
                    Err(error) => {
                        log::error!("Edge Link persistent store: {error}");
                        return;
                    }
                };
                runtime.block_on(async move {
                    let serialChannel = match uart {
                        Some(uart) => match Esp32UartLinkChannel::new(uart) {
                            Ok(channel) => Some(channel),
                            Err(error) => {
                                log::error!("Edge UART listener: {}", error.message);
                                None
                            }
                        },
                        None => None,
                    };
                    if let Some(channel) = serialChannel {
                        let serialAuthority = Arc::clone(&authority);
                        tokio::spawn(async move {
                            loop {
                                match handleChannel(Arc::clone(&serialAuthority), channel.clone())
                                    .await
                                {
                                    Ok(()) => {}
                                    Err(error) => {
                                        log::warn!("Edge UART session: {error}");
                                        if channel.isClosed() {
                                            break;
                                        }
                                    }
                                }
                            }
                        });
                        log::info!("Edge Link listening on UART0 GPIO1/GPIO3 at 115200 baud");
                    }
                    let listener = match operit_edge_transport::tcp::TcpLinkChannel::bind(&format!(
                        "0.0.0.0:{port}"
                    ))
                    .await
                    {
                        Ok(listener) => listener,
                        Err(error) => {
                            log::error!("Edge Link listener: {error}");
                            return;
                        }
                    };
                    log::info!("Edge Link listening on TCP port {port}");
                    loop {
                        let (stream, peer) = match listener.accept().await {
                            Ok(value) => value,
                            Err(error) => {
                                log::warn!("Edge Link accept: {error}");
                                continue;
                            }
                        };
                        log::info!("Edge Link connection from {peer}");
                        let channel =
                            operit_edge_transport::tcp::TcpLinkChannel::fromStream(stream);
                        let authority = Arc::clone(&authority);
                        tokio::spawn(async move {
                            if let Err(error) = handleChannel(authority, channel).await {
                                log::warn!("Edge Link session: {error}");
                            }
                        });
                    }
                });
            })
            .map_err(|error| HostError::new(format!("Edge Link thread: {error}")))?;
        Ok(Some(Self { _thread: thread }))
    }
}
