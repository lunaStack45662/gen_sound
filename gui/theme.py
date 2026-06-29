"""Design tokens: màu sắc, font, spacing dùng chung toàn app."""

COLORS = {
    "bg_primary":   "#0F1117",
    "bg_secondary": "#1A1D27",
    "bg_hover":     "#252836",
    "bg_card":      "#1E2130",
    "accent":       "#7C6FF7",
    "accent_hover": "#9B96F8",
    "text_primary": "#F1F1F3",
    "text_secondary": "#8B8FA8",
    "text_muted":   "#4A4D61",
    "border":       "#2A2D3E",
    "success":      "#22C55E",
    "warning":      "#F59E0B",
    "error":        "#EF4444",
    "canvas_bg":    "#1A1D27",
    "timeline_bg":  "#252836",
    "playhead":     "#EF4444",
}

FONTS = {
    "heading":  ("Segoe UI", 14, "bold"),
    "body":     ("Segoe UI", 11),
    "small":    ("Segoe UI", 9),
    "mono":     ("Consolas", 10),
    "tab":      ("Segoe UI", 10),
}

SPACING = {
    "xs": 4,
    "sm": 8,
    "md": 16,
    "lg": 24,
    "xl": 32,
}

SEGMENT_COLORS = [
    "#7C6FF7", "#4ECDC4", "#45B7D1", "#96CEB4",
    "#FFEAA7", "#DDA0DD", "#98D8C8", "#FF6B6B",
]


def round_rect(canvas, x1, y1, x2, y2, r=8, **kwargs):
    """Vẽ hình chữ nhật bo góc trên canvas. Trả về list tags."""
    tags = kwargs.pop("tags", None)
    parts = []
    # 4 góc bo
    parts.append(canvas.create_arc(x1, y1, x1 + r * 2, y1 + r * 2,
                                    start=90, extent=90, fill=kwargs.get("fill"), outline="", tags=tags))
    parts.append(canvas.create_arc(x2 - r * 2, y1, x2, y1 + r * 2,
                                    start=0, extent=90, fill=kwargs.get("fill"), outline="", tags=tags))
    parts.append(canvas.create_arc(x1, y2 - r * 2, x1 + r * 2, y2,
                                    start=180, extent=90, fill=kwargs.get("fill"), outline="", tags=tags))
    parts.append(canvas.create_arc(x2 - r * 2, y2 - r * 2, x2, y2,
                                    start=270, extent=90, fill=kwargs.get("fill"), outline="", tags=tags))
    # 4 cạnh
    parts.append(canvas.create_rectangle(x1 + r, y1, x2 - r, y1 + r,
                                          fill=kwargs.get("fill"), outline="", tags=tags))
    parts.append(canvas.create_rectangle(x1 + r, y2 - r, x2 - r, y2,
                                          fill=kwargs.get("fill"), outline="", tags=tags))
    parts.append(canvas.create_rectangle(x1, y1 + r, x1 + r, y2 - r,
                                          fill=kwargs.get("fill"), outline="", tags=tags))
    parts.append(canvas.create_rectangle(x2 - r, y1 + r, x2, y2 - r,
                                          fill=kwargs.get("fill"), outline="", tags=tags))
    # outline
    if "outline" in kwargs and kwargs["outline"]:
        w = kwargs.get("width", 1)
        parts.append(canvas.create_arc(x1, y1, x1 + r * 2, y1 + r * 2,
                                        start=90, extent=90, fill="", outline=kwargs["outline"], width=w, tags=tags))
        parts.append(canvas.create_arc(x2 - r * 2, y1, x2, y1 + r * 2,
                                        start=0, extent=90, fill="", outline=kwargs["outline"], width=w, tags=tags))
        parts.append(canvas.create_arc(x1, y2 - r * 2, x1 + r * 2, y2,
                                        start=180, extent=90, fill="", outline=kwargs["outline"], width=w, tags=tags))
        parts.append(canvas.create_arc(x2 - r * 2, y2 - r * 2, x2, y2,
                                        start=270, extent=90, fill="", outline=kwargs["outline"], width=w, tags=tags))
        parts.append(canvas.create_line(x1 + r, y1, x2 - r, y1,
                                         fill=kwargs["outline"], width=w, tags=tags))
        parts.append(canvas.create_line(x1 + r, y2, x2 - r, y2,
                                         fill=kwargs["outline"], width=w, tags=tags))
        parts.append(canvas.create_line(x1, y1 + r, x1, y2 - r,
                                         fill=kwargs["outline"], width=w, tags=tags))
        parts.append(canvas.create_line(x2, y1 + r, x2, y2 - r,
                                         fill=kwargs["outline"], width=w, tags=tags))
    return parts
