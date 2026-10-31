use fontdue::Font;

pub fn temperature_icon(label: &str) -> Result<(Vec<u8>, u32, u32), String> {
    let bytes = std::fs::read(font_path()).map_err(|err| format!("font: {err}"))?;
    let font = Font::from_bytes(bytes, fontdue::FontSettings::default())
        .map_err(|err| format!("font: {err}"))?;
    let size = 64u32;
    let px = 30.0;
    let mut glyphs = Vec::new();
    let mut text_width = 0.0f32;
    let mut max_height = 0i32;
    let mut min_y = 0i32;
    for ch in label.chars() {
        let (metrics, bitmap) = font.rasterize(ch, px);
        text_width += metrics.advance_width;
        max_height = max_height.max(metrics.height as i32);
        min_y = min_y.min(metrics.ymin);
        glyphs.push((metrics, bitmap));
    }
    let mut rgba = vec![0u8; (size * size * 4) as usize];
    let mut cursor = ((size as f32 - text_width) / 2.0).max(0.0);
    let baseline = (size as i32 / 2) + 8;
    for (metrics, bitmap) in glyphs {
        let left = cursor.round() as i32 + metrics.xmin;
        let top = baseline - metrics.ymin - metrics.height as i32;
        blit(&mut rgba, size, left, top, metrics.width, metrics.height, &bitmap);
        cursor += metrics.advance_width;
    }
    let _ = (max_height, min_y);
    Ok((rgba, size, size))
}

fn blit(
    rgba: &mut [u8],
    size: u32,
    left: i32,
    top: i32,
    width: usize,
    height: usize,
    coverage: &[u8],
) {
    for row in 0..height {
        for col in 0..width {
            let x = left + col as i32;
            let y = top + row as i32;
            if x < 0 || y < 0 || x >= size as i32 || y >= size as i32 {
                continue;
            }
            let alpha = coverage[row * width + col];
            if alpha == 0 {
                continue;
            }
            let index = ((y as u32 * size + x as u32) * 4) as usize;
            rgba[index] = 244;
            rgba[index + 1] = 245;
            rgba[index + 2] = 246;
            rgba[index + 3] = alpha;
        }
    }
}

fn font_path() -> &'static str {
    #[cfg(windows)]
    {
        "C:\\Windows\\Fonts\\segoeuib.ttf"
    }
    #[cfg(not(windows))]
    {
        if std::path::Path::new("/usr/share/fonts/noto/NotoSans-Bold.ttf").exists() {
            "/usr/share/fonts/noto/NotoSans-Bold.ttf"
        } else {
            "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf"
        }
    }
}
