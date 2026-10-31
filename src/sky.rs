use iced::mouse;
use iced::widget::canvas::{self, Path, Stroke};
use iced::{Color, Element, Point, Rectangle, Renderer, Theme};

use crate::weather::Sky;

pub fn glyph<'a, Message: 'a>(kind: Sky) -> Element<'a, Message> {
    canvas::Canvas::new(Glyph { kind })
        .width(64.0)
        .height(48.0)
        .into()
}

struct Glyph {
    kind: Sky,
}

impl<Message> canvas::Program<Message> for Glyph {
    type State = ();

    fn draw(
        &self,
        _state: &(),
        renderer: &Renderer,
        _theme: &Theme,
        bounds: Rectangle,
        _cursor: mouse::Cursor,
    ) -> Vec<canvas::Geometry> {
        let mut frame = canvas::Frame::new(renderer, bounds.size());
        let center = frame.center();
        match self.kind {
            Sky::Clear => sun(&mut frame, center),
            Sky::MostlySunny => {
                sun(&mut frame, shift(center, -8.0, -2.0));
                cloud(&mut frame, shift(center, 8.0, 6.0), 0.82);
            }
            Sky::Partly => {
                sun(&mut frame, shift(center, -10.0, -4.0));
                cloud(&mut frame, shift(center, 6.0, 4.0), 1.0);
            }
            Sky::Cloudy => cloud(&mut frame, center, 1.0),
            Sky::Fog => fog(&mut frame, center),
            Sky::Drizzle => {
                cloud(&mut frame, shift(center, 0.0, -6.0), 1.0);
                drops(&mut frame, center, 2);
            }
            Sky::Rain => {
                cloud(&mut frame, shift(center, 0.0, -6.0), 1.0);
                drops(&mut frame, center, 3);
            }
            Sky::Snow => {
                cloud(&mut frame, shift(center, 0.0, -6.0), 1.0);
                flakes(&mut frame, center, 3);
            }
            Sky::Sleet => {
                cloud(&mut frame, shift(center, 0.0, -6.0), 1.0);
                drops(&mut frame, shift(center, -6.0, 0.0), 2);
                flakes(&mut frame, shift(center, 8.0, 2.0), 1);
            }
            Sky::Storm => {
                cloud(&mut frame, shift(center, 0.0, -6.0), 1.0);
                bolt(&mut frame, shift(center, 1.0, 10.0));
            }
        }
        vec![frame.into_geometry()]
    }
}

fn shift(point: Point, x: f32, y: f32) -> Point {
    Point::new(point.x + x, point.y + y)
}

fn sun(frame: &mut canvas::Frame, center: Point) {
    let gold = Color::from_rgb(0.94, 0.76, 0.42);
    frame.fill(&Path::circle(center, 7.5), gold);
    let stroke = Stroke::default()
        .with_color(gold)
        .with_width(1.6);
    for index in 0..8 {
        let angle = index as f32 * std::f32::consts::TAU / 8.0;
        let inner = 11.0;
        let outer = 15.0;
        frame.stroke(
            &Path::line(
                Point::new(center.x + angle.cos() * inner, center.y + angle.sin() * inner),
                Point::new(center.x + angle.cos() * outer, center.y + angle.sin() * outer),
            ),
            stroke,
        );
    }
}

fn cloud(frame: &mut canvas::Frame, center: Point, scale: f32) {
    let color = Color::from_rgb(0.78, 0.82, 0.88);
    let puffs = [
        (-11.0, 3.0, 7.0),
        (-2.0, -2.0, 9.0),
        (9.0, 2.0, 7.5),
        (0.0, 5.0, 7.0),
    ];
    for (x, y, radius) in puffs {
        frame.fill(
            &Path::circle(shift(center, x * scale, y * scale), radius * scale),
            color,
        );
    }
}

fn drops(frame: &mut canvas::Frame, center: Point, count: i32) {
    let color = Color::from_rgb(0.56, 0.78, 0.90);
    let stroke = Stroke::default().with_color(color).with_width(1.6);
    let start = -((count - 1) as f32) * 5.0;
    for index in 0..count {
        let x = start + index as f32 * 10.0;
        frame.stroke(
            &Path::line(
                shift(center, x, 8.0),
                shift(center, x - 1.5, 16.0),
            ),
            stroke,
        );
    }
}

fn flakes(frame: &mut canvas::Frame, center: Point, count: i32) {
    let color = Color::from_rgb(0.93, 0.95, 0.97);
    let stroke = Stroke::default().with_color(color).with_width(1.2);
    let start = -((count - 1) as f32) * 6.0;
    for index in 0..count {
        let origin = shift(center, start + index as f32 * 12.0, 12.0);
        frame.fill(&Path::circle(origin, 1.3), color);
        for arm in 0..6 {
            let angle = arm as f32 * std::f32::consts::TAU / 6.0;
            frame.stroke(
                &Path::line(
                    origin,
                    Point::new(origin.x + angle.cos() * 4.2, origin.y + angle.sin() * 4.2),
                ),
                stroke,
            );
        }
    }
}

fn fog(frame: &mut canvas::Frame, center: Point) {
    let color = Color::from_rgb(0.70, 0.74, 0.80);
    let stroke = Stroke::default().with_color(color).with_width(2.0);
    for (y, inset) in [(-6.0, 0.0), (0.0, 4.0), (6.0, 1.0)] {
        frame.stroke(
            &Path::line(
                shift(center, -16.0 + inset, y),
                shift(center, 16.0 - inset, y),
            ),
            stroke,
        );
    }
}

fn bolt(frame: &mut canvas::Frame, origin: Point) {
    let path = Path::new(|builder| {
        builder.move_to(shift(origin, 3.0, -8.0));
        builder.line_to(shift(origin, -4.0, 1.0));
        builder.line_to(shift(origin, 0.0, 1.0));
        builder.line_to(shift(origin, -3.0, 9.0));
        builder.line_to(shift(origin, 5.0, -1.0));
        builder.line_to(shift(origin, 1.0, -1.0));
        builder.close();
    });
    frame.fill(&path, Color::from_rgb(0.91, 0.82, 0.48));
}
