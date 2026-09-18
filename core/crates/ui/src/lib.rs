#![allow(non_snake_case)]

mod renderer;

pub use renderer::{Canvas, drawText, textSize, FONT_ADVANCE, FONT_HEIGHT, FONT_WIDTH};

use std::fmt;

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq, Hash)]
#[cfg_attr(feature = "serde", derive(serde::Serialize, serde::Deserialize))]
#[cfg_attr(feature = "serde", serde(transparent))]
pub struct Color(pub u16);

impl Color {
    pub const BLACK: Self = Self(0);
    pub const WHITE: Self = Self(0xffff);

    pub fn rgb565(r: u8, g: u8, b: u8) -> Self {
        Self(
            ((u16::from(r) >> 3) << 11) | ((u16::from(g) >> 2) << 5) | u16::from(b >> 3),
        )
    }
}

impl fmt::Display for Color {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{:#06x}", self.0)
    }
}

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq, Hash)]
#[cfg_attr(feature = "serde", derive(serde::Serialize, serde::Deserialize))]
pub struct Rect {
    pub x: u16,
    pub y: u16,
    pub width: u16,
    pub height: u16,
}

impl Rect {
    pub const fn new(x: u16, y: u16, width: u16, height: u16) -> Self {
        Self { x, y, width, height }
    }

    pub fn contains(&self, x: u16, y: u16) -> bool {
        x >= self.x
            && y >= self.y
            && x < self.x.saturating_add(self.width)
            && y < self.y.saturating_add(self.height)
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[cfg_attr(feature = "serde", derive(serde::Serialize, serde::Deserialize))]
pub enum Icon {
    Back,
    Battery,
    Face,
    Gear,
    Grid,
    Terminal,
    Wifi,
}

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
#[cfg_attr(feature = "serde", derive(serde::Serialize, serde::Deserialize))]
pub enum TextAlignment {
    #[default]
    Left,
    Center,
    Right,
}

#[derive(Clone, Debug, PartialEq, Eq)]
#[cfg_attr(feature = "serde", derive(serde::Serialize, serde::Deserialize))]
pub enum Widget {
    Panel {
        rect: Rect,
        color: Color,
        radius: u8,
    },
    Text {
        rect: Rect,
        content: String,
        color: Color,
        alignment: TextAlignment,
    },
    Button {
        rect: Rect,
        label: String,
        target: String,
        color: Color,
        icon: Option<Icon>,
    },
    Icon {
        rect: Rect,
        icon: Icon,
        color: Color,
    },
}

impl Widget {
    pub fn rect(&self) -> Rect {
        match self {
            Self::Panel { rect, .. }
            | Self::Text { rect, .. }
            | Self::Button { rect, .. }
            | Self::Icon { rect, .. } => *rect,
        }
    }

    pub fn target(&self) -> Option<&str> {
        match self {
            Self::Button { target, .. } => Some(target),
            _ => None,
        }
    }
}

#[derive(Clone, Debug, Default, PartialEq, Eq)]
#[cfg_attr(feature = "serde", derive(serde::Serialize, serde::Deserialize))]
pub struct Screen {
    pub id: String,
    pub title: String,
    pub background: Color,
    pub widgets: Vec<Widget>,
}

impl Screen {
    pub fn builder(id: &str, title: &str, background: Color) -> ScreenBuilder {
        ScreenBuilder {
            id: id.to_string(),
            title: title.to_string(),
            background,
            widgets: Vec::new(),
        }
    }

    pub fn targetAt(&self, x: u16, y: u16) -> Option<&str> {
        self.widgets
            .iter()
            .rev()
            .filter_map(|widget| {
                if widget.rect().contains(x, y) {
                    widget.target()
                } else {
                    None
                }
            })
            .next()
    }
}

#[derive(Debug)]
pub struct ScreenBuilder {
    pub id: String,
    pub title: String,
    pub background: Color,
    pub widgets: Vec<Widget>,
}

impl ScreenBuilder {
    pub fn panel(&mut self, rect: Rect, color: Color) -> &mut Self {
        self.widgets.push(Widget::Panel {
            rect,
            color,
            radius: 0,
        });
        self
    }

    pub fn text(
        &mut self,
        rect: Rect,
        content: &str,
        color: Color,
        alignment: TextAlignment,
    ) -> &mut Self {
        self.widgets.push(Widget::Text {
            rect,
            content: content.to_string(),
            color,
            alignment,
        });
        self
    }

    pub fn button(
        &mut self,
        rect: Rect,
        label: &str,
        target: &str,
        color: Color,
        icon: Option<Icon>,
    ) -> &mut Self {
        self.widgets.push(Widget::Button {
            rect,
            label: label.to_string(),
            target: target.to_string(),
            color,
            icon,
        });
        self
    }

    pub fn icon(&mut self, rect: Rect, icon: Icon, color: Color) -> &mut Self {
        self.widgets.push(Widget::Icon { rect, icon, color });
        self
    }

    pub fn build(&self) -> Screen {
        Screen {
            id: self.id.clone(),
            title: self.title.clone(),
            background: self.background,
            widgets: self.widgets.clone(),
        }
    }
}

#[derive(Clone, Debug, Default, PartialEq, Eq)]
#[cfg_attr(feature = "serde", derive(serde::Serialize, serde::Deserialize))]
pub struct Document {
    pub screens: Vec<Screen>,
}

impl Document {
    pub fn screen(&self, id: &str) -> Option<&Screen> {
        self.screens.iter().find(|screen| screen.id == id)
    }

    pub fn targetAt(&self, screenId: &str, x: u16, y: u16) -> Option<&str> {
        self.screen(screenId)?.targetAt(x, y)
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Gesture {
    Back,
    SwipeDown,
    SwipeUp,
    Tap { x: u16, y: u16 },
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn buttonsRouteByTopmostWidget() {
        let mut screen = Screen::builder("home", "Home", Color::BLACK);
        screen.button(Rect::new(10, 10, 40, 20), "A", "alpha", Color::WHITE, None);
        screen.panel(Rect::new(15, 15, 20, 10), Color::BLACK);
        let screen = screen.build();
        assert_eq!(screen.targetAt(12, 12), Some("alpha"));
        assert_eq!(screen.targetAt(16, 16), Some("alpha"));
        assert_eq!(screen.targetAt(200, 200), None);
    }
}
