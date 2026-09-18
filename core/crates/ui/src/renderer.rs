#![allow(non_snake_case)]

use crate::{Color, Icon, Rect, Screen, TextAlignment};

pub trait Canvas {
    fn size(&self) -> (u16, u16);
    fn fill(&mut self, color: Color);
    fn fill_rect(&mut self, rect: Rect, color: Color);
}

pub const FONT_WIDTH: u16 = 3;
pub const FONT_HEIGHT: u16 = 5;
pub const FONT_ADVANCE: u16 = 4;

pub fn textSize(text: &str) -> (u16, u16) {
    let width = if text.is_empty() {
        0
    } else {
        u16::try_from(text.chars().count())
            .unwrap_or(u16::MAX)
            .saturating_mul(FONT_ADVANCE)
            .saturating_sub(FONT_ADVANCE - FONT_WIDTH)
    };
    (width, FONT_HEIGHT)
}

pub fn drawText(
    canvas: &mut dyn Canvas,
    bounds: Rect,
    text: &str,
    color: Color,
    alignment: TextAlignment,
) {
    let (textWidth, _) = textSize(text);
    let startX = match alignment {
        TextAlignment::Left => bounds.x,
        TextAlignment::Center => {
            bounds.x + bounds.width.saturating_sub(textWidth) / 2
        }
        TextAlignment::Right => bounds
            .x
            .saturating_add(bounds.width)
            .saturating_sub(textWidth),
    };
    let mut penX = startX;
    for character in text.to_ascii_uppercase().chars() {
        if character == ' ' {
            penX = penX.saturating_add(FONT_ADVANCE);
            continue;
        }
        let Some(glyph) = glyph(character) else {
            penX = penX.saturating_add(FONT_ADVANCE);
            continue;
        };
        for row in 0..FONT_HEIGHT {
            let bits = glyph[row as usize];
            let mut column = 0;
            while column < FONT_WIDTH {
                let mut run = 0;
                while column + run < FONT_WIDTH
                    && bits & (1u8 << (FONT_WIDTH - 1 - column - run)) != 0
                {
                    run += 1;
                }
                if run > 0 {
                    canvas.fill_rect(
                        Rect::new(penX + column, bounds.y + row, run, 1),
                        color,
                    );
                    column += run;
                } else {
                    column += 1;
                }
            }
        }
        penX = penX.saturating_add(FONT_ADVANCE);
    }
}

fn glyph(character: char) -> Option<[u8; 5]> {
    Some(match character {
        'A' => [0b010, 0b101, 0b111, 0b101, 0b101],
        'B' => [0b110, 0b101, 0b110, 0b101, 0b110],
        'C' => [0b011, 0b100, 0b100, 0b100, 0b011],
        'D' => [0b110, 0b101, 0b101, 0b101, 0b110],
        'E' => [0b111, 0b100, 0b111, 0b100, 0b111],
        'F' => [0b111, 0b100, 0b111, 0b100, 0b100],
        'G' => [0b011, 0b100, 0b101, 0b101, 0b011],
        'H' => [0b101, 0b101, 0b111, 0b101, 0b101],
        'I' => [0b111, 0b010, 0b010, 0b010, 0b111],
        'K' => [0b101, 0b110, 0b100, 0b110, 0b101],
        'L' => [0b100, 0b100, 0b100, 0b100, 0b111],
        'M' => [0b101, 0b111, 0b111, 0b101, 0b101],
        'N' => [0b101, 0b111, 0b111, 0b111, 0b101],
        'O' => [0b010, 0b101, 0b101, 0b101, 0b010],
        'P' => [0b111, 0b101, 0b111, 0b100, 0b100],
        'R' => [0b110, 0b101, 0b110, 0b101, 0b101],
        'S' => [0b011, 0b100, 0b010, 0b001, 0b110],
        'T' => [0b111, 0b010, 0b010, 0b010, 0b010],
        'U' => [0b101, 0b101, 0b101, 0b101, 0b111],
        'V' => [0b101, 0b101, 0b101, 0b101, 0b010],
        'W' => [0b101, 0b101, 0b111, 0b111, 0b101],
        'X' => [0b101, 0b010, 0b010, 0b010, 0b101],
        'Y' => [0b101, 0b101, 0b010, 0b010, 0b010],
        '>' => [0b100, 0b010, 0b001, 0b010, 0b100],
        _ => return None,
    })
}

pub fn drawIcon(canvas: &mut dyn Canvas, bounds: Rect, icon: Icon, color: Color) {
    if bounds.width < 2 || bounds.height < 2 {
        return;
    }
    match icon {
        Icon::Back => {
            canvas.fill_rect(centered(bounds, 5, 1, 0, 2), color);
            canvas.fill_rect(centered(bounds, 1, 1, 0, 2), color);
            canvas.fill_rect(centered(bounds, 1, 1, 1, 3), color);
            canvas.fill_rect(centered(bounds, 1, 1, 2, 4), color);
        }
        Icon::Battery => {
            let body = Rect::new(bounds.x, bounds.y + 2, bounds.width.saturating_sub(3), 5);
            canvas.fill_rect(body, color);
            canvas.fill_rect(
                Rect::new(body.x + body.width, bounds.y + 4, 2, 1),
                color,
            );
        }
        Icon::Face => {
            canvas.fill_rect(
                Rect::new(bounds.x + 4, bounds.y + 4, 8, 12),
                color,
            );
            canvas.fill_rect(
                Rect::new(bounds.x + bounds.width - 12, bounds.y + 4, 8, 12),
                color,
            );
            canvas.fill_rect(
                Rect::new(bounds.x + 8, bounds.y + 24, bounds.width - 16, 5),
                color,
            );
        }
        Icon::Gear => {
            for y in (0..bounds.height).step_by(5) {
                canvas.fill_rect(
                    Rect::new(bounds.x, bounds.y + y as u16, bounds.width, 2),
                    color,
                );
            }
        }
        Icon::Grid => {
            for row in 0..2u16 {
                for column in 0..2u16 {
                    canvas.fill_rect(
                        Rect::new(
                            bounds.x + column * (bounds.width / 2 + 1),
                            bounds.y + row * (bounds.height / 2 + 1),
                            bounds.width / 2,
                            bounds.height / 2,
                        ),
                        color,
                    );
                }
            }
        }
        Icon::Terminal => {
            for row in 0..4u16 {
                let width = bounds.width - (u32::from(row) * 5).min(u32::from(bounds.width)) as u16;
                canvas.fill_rect(
                    Rect::new(bounds.x, bounds.y + row * 5, width, 3),
                    color,
                );
            }
        }
        Icon::Wifi => {
            for index in 0..3u16 {
                let width = 4 + index * 6;
                canvas.fill_rect(
                    Rect::new(
                        bounds.x + bounds.width / 2 - width / 2,
                        bounds.y + 2 + index * 3,
                        width,
                        2,
                    ),
                    color,
                );
            }
        }
    }
}

fn centered(bounds: Rect, width: u16, height: u16, dx: u16, dy: u16) -> Rect {
    let left = bounds.x
        + bounds.width.saturating_sub(width) / 2
        + dx.saturating_sub(1);
    let top = bounds.y
        + bounds.height.saturating_sub(height) / 2
        + dy.saturating_sub(1);
    Rect::new(left, top, width, height)
}

impl Screen {
    pub fn paint(&self, canvas: &mut dyn Canvas) {
        canvas.fill(self.background);
        for widget in &self.widgets {
            paintWidget(canvas, widget);
        }
    }
}

fn paintWidget(canvas: &mut dyn Canvas, widget: &crate::Widget) {
    match widget {
        crate::Widget::Panel { rect, color, .. } => {
            canvas.fill_rect(*rect, *color);
        }
        crate::Widget::Text {
            rect,
            content,
            color,
            alignment,
        } => drawText(canvas, *rect, content, *color, *alignment),
        crate::Widget::Button {
            rect,
            label,
            color,
            icon,
            ..
        } => {
            canvas.fill_rect(*rect, *color);
            let inner = Rect::new(
                rect.x + 6,
                rect.y + 4,
                rect.width.saturating_sub(12),
                rect.height.saturating_sub(28),
            );
            if let Some(icon) = icon {
                drawIcon(canvas, inner, *icon, Color::rgb565(15, 19, 28));
            }
            drawText(
                canvas,
                Rect::new(
                    rect.x,
                    rect.y + rect.height.saturating_sub(20),
                    rect.width,
                    5,
                ),
                label,
                Color::rgb565(203, 213, 225),
                TextAlignment::Center,
            );
        }
        crate::Widget::Icon { rect, icon, color } => drawIcon(canvas, *rect, *icon, *color),
    }
}
