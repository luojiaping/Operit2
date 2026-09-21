#![allow(non_snake_case)]

use std::collections::VecDeque;
use std::sync::{Arc, Mutex};

use operit_board_esp32::Esp32ScreenMirror;
use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, Deserialize)]
pub struct EdgeScreenInputRequest {
    pub action: String,
    pub x: u16,
    pub y: u16,
    #[serde(default)]
    pub endX: Option<u16>,
    #[serde(default)]
    pub endY: Option<u16>,
}

#[derive(Clone, Debug, Serialize)]
pub struct EdgeScreenInputState {
    pub accepted: bool,
    pub action: String,
}

#[derive(Clone, Debug, Serialize)]
pub struct EdgeScreenSnapshot {
    pub width: u16,
    pub height: u16,
    pub format: String,
    pub pixels: Vec<u8>,
}

#[derive(Clone, Debug)]
pub struct EdgeServiceError(String);

impl EdgeServiceError {
    fn new(message: impl Into<String>) -> Self {
        Self(message.into())
    }
}

impl std::fmt::Display for EdgeServiceError {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        formatter.write_str(&self.0)
    }
}

pub trait ScreenService: Send + Sync {
    fn getScreenSnapshot(&self) -> Result<EdgeScreenSnapshot, EdgeServiceError>;
    fn sendScreenInput(
        &self,
        request: EdgeScreenInputRequest,
    ) -> Result<EdgeScreenInputState, EdgeServiceError>;
}

/// Board-backed generic display service for the authenticated EdgeLink.
pub struct Esp32ScreenService {
    mirror: Arc<Esp32ScreenMirror>,
    inputs: Arc<Mutex<VecDeque<EdgeScreenInputRequest>>>,
}

impl Esp32ScreenService {
    pub fn new(mirror: Arc<Esp32ScreenMirror>) -> Self {
        Self {
            mirror,
            inputs: Arc::new(Mutex::new(VecDeque::new())),
        }
    }

    /// Takes all remote input events for execution by the firmware main loop.
    pub fn drainInputs(&self) -> Vec<EdgeScreenInputRequest> {
        let Ok(mut inputs) = self.inputs.lock() else {
            return Vec::new();
        };
        inputs.drain(..).collect()
    }
}

impl ScreenService for Esp32ScreenService {
    fn getScreenSnapshot(&self) -> Result<EdgeScreenSnapshot, EdgeServiceError> {
        let (width, height) = self.mirror.dimensions();
        let length = usize::from(width) * usize::from(height) * 2;
        let mut pixels = Vec::new();
        pixels.try_reserve_exact(length).map_err(|_| {
            EdgeServiceError::new(
                "insufficient memory for full screen snapshot; use /screen.bmp streaming preview",
            )
        })?;
        pixels.resize(length, 0);
        self.mirror.withRgb332(|source| {
            for (index, pixel) in source.iter().copied().enumerate() {
                let pixel = operit_board_esp32::mirror_color::unpack_rgb332(pixel);
                let offset = index * 2;
                if offset + 1 >= pixels.len() {
                    break;
                }
                pixels[offset] = (pixel >> 8) as u8;
                pixels[offset + 1] = pixel as u8;
            }
        });
        Ok(EdgeScreenSnapshot {
            width,
            height,
            format: "rgb565-be".to_string(),
            pixels,
        })
    }

    fn sendScreenInput(
        &self,
        request: EdgeScreenInputRequest,
    ) -> Result<EdgeScreenInputState, EdgeServiceError> {
        let action = request.action.trim().to_ascii_lowercase();
        if !matches!(action.as_str(), "tap" | "down" | "up" | "swipe") {
            return Err(EdgeServiceError::new(format!(
                "unsupported screen input action: {action}"
            )));
        }
        let (width, height) = self.mirror.dimensions();
        if request.x >= width || request.y >= height {
            return Err(EdgeServiceError::new(
                "screen input point is outside display",
            ));
        }
        if action == "swipe" && (request.endX.is_none() || request.endY.is_none()) {
            return Err(EdgeServiceError::new("screen swipe requires endX and endY"));
        }
        self.inputs
            .lock()
            .map_err(|error| EdgeServiceError::new(error.to_string()))?
            .push_back(EdgeScreenInputRequest {
                action: action.clone(),
                ..request
            });
        Ok(EdgeScreenInputState {
            accepted: true,
            action,
        })
    }
}
