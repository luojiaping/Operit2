#![allow(non_snake_case)]

use super::LinkChannel;
use async_trait::async_trait;
use operit_link::LinkFrame;
use std::sync::Arc;
use tokio::io::{AsyncReadExt, AsyncWriteExt, ReadHalf, WriteHalf};
use tokio::sync::Mutex;
use tokio_serial::{SerialPortBuilderExt, SerialStream};

use super::serial_codec::{encodeSerialFrame, SerialFrameDecoder};

/// Length/checksum framed serial carrier for standard Operit Link frames.
///
/// The magic prefix makes it possible to recover after ordinary UART logs or
/// a partial frame have appeared on the same physical line. Production ESP32
/// firmware should still use a dedicated UART for this carrier when possible.
pub struct SerialLinkChannel {
    reader: Mutex<ReadHalf<SerialStream>>,
    writer: Mutex<WriteHalf<SerialStream>>,
    decoder: Mutex<SerialFrameDecoder>,
}

impl SerialLinkChannel {
    /// Opens a host serial port such as `COM27`.
    pub fn open(port: &str, baudRate: u32) -> Result<Arc<Self>, String> {
        let stream = tokio_serial::new(port, baudRate)
            .open_native_async()
            .map_err(|error| format!("open Edge serial port {port}: {error}"))?;
        Ok(Self::fromStream(stream))
    }

    pub fn fromStream(stream: SerialStream) -> Arc<Self> {
        let (reader, writer) = tokio::io::split(stream);
        Arc::new(Self {
            reader: Mutex::new(reader),
            writer: Mutex::new(writer),
            decoder: Mutex::new(SerialFrameDecoder::new()),
        })
    }
}

#[async_trait]
impl LinkChannel for SerialLinkChannel {
    async fn send(&self, frame: LinkFrame) -> Result<(), String> {
        let encoded = encodeSerialFrame(&frame)?;
        let mut writer = self.writer.lock().await;
        writer
            .write_all(&encoded)
            .await
            .map_err(|error| error.to_string())?;
        writer.flush().await.map_err(|error| error.to_string())
    }

    async fn receive(&self) -> Result<Option<LinkFrame>, String> {
        let mut reader = self.reader.lock().await;
        let mut decoder = self.decoder.lock().await;
        let mut bytes = [0u8; 1024];
        loop {
            let count = match reader.read(&mut bytes).await {
                Ok(0) => return Ok(None),
                Ok(count) => count,
                Err(error) => return Err(error.to_string()),
            };
            if let Some(frame) = decoder.push(&bytes[..count])? {
                return Ok(Some(frame));
            }
        }
    }

    async fn close(&self) {
        let _ = self.writer.lock().await.shutdown().await;
    }
}

#[cfg(test)]
mod tests {
    use super::super::serial_codec::crc32;

    #[test]
    fn crcMatchesKnownVector() {
        assert_eq!(crc32(b"123456789"), 0xcbf4_3926);
    }
}
