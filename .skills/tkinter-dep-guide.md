# Hướng Dẫn Làm Đẹp App Desktop với Tkinter

> Tkinter mặc định trông khá "cổ lỗ" — nhưng với một số kỹ thuật đúng, bạn hoàn toàn có thể tạo ra giao diện hiện đại, sạch sẽ, chuyên nghiệp.

---

## Mục Lục

1. [Tư duy thiết kế trước khi code](#1-tư-duy-thiết-kế-trước-khi-code)
2. [Cài thư viện cần thiết](#2-cài-thư-viện-cần-thiết)
3. [Nền tảng: Màu sắc & Font chữ](#3-nền-tảng-màu-sắc--font-chữ)
4. [Dùng ttk thay tk thuần](#4-dùng-ttk-thay-tk-thuần)
5. [Tùy chỉnh Style với ttk.Style](#5-tùy-chỉnh-style-với-ttkstyle)
6. [Layout đẹp với grid & pack](#6-layout-đẹp-với-grid--pack)
7. [CustomTkinter — nâng cấp toàn diện](#7-customtkinter--nâng-cấp-toàn-diện)
8. [Sidebar Navigation](#8-sidebar-navigation)
9. [Card & Panel Component](#9-card--panel-component)
10. [Animation đơn giản](#10-animation-đơn-giản)
11. [Icon với Pillow](#11-icon-với-pillow)
12. [Ví dụ app hoàn chỉnh](#12-ví-dụ-app-hoàn-chỉnh)
13. [Checklist trước khi release](#13-checklist-trước-khi-release)

---

## 1. Tư duy thiết kế trước khi code

Trước khi viết một dòng code, hãy quyết định:

| Yếu tố | Câu hỏi cần trả lời |
|--------|---------------------|
| **Màu chủ đạo** | Dark mode hay Light mode? Màu accent là gì? |
| **Font** | Dùng font hệ thống hay import font riêng? |
| **Layout** | Sidebar trái + content phải? Hay top nav + content? |
| **Spacing** | Padding/margin nhất quán (dùng bội số của 8: 8, 16, 24, 32...) |
| **Trạng thái** | Hover, active, disabled trông như thế nào? |

**Nguyên tắc vàng:** Ít màu, nhiều khoảng trắng, font nhất quán.

---

## 2. Cài thư viện cần thiết

```bash
pip install customtkinter       # Tkinter hiện đại, đẹp hơn nhiều
pip install Pillow              # Xử lý ảnh, icon
pip install ttkbootstrap        # Bootstrap themes cho ttk
pip install darkdetect          # Phát hiện dark/light mode hệ thống
```

---

## 3. Nền tảng: Màu sắc & Font chữ

Định nghĩa palette màu và font ở **một chỗ duy nhất** — dễ thay đổi sau này.

```python
# theme.py
COLORS = {
    # Backgrounds
    "bg_primary":   "#0F1117",   # Nền chính (dark)
    "bg_secondary": "#1A1D27",   # Nền panel/card
    "bg_hover":     "#252836",   # Hover state

    # Accent
    "accent":       "#7C6FF7",   # Tím indigo
    "accent_hover": "#9B96F8",

    # Text
    "text_primary":   "#F1F1F3",
    "text_secondary": "#8B8FA8",
    "text_muted":     "#4A4D61",

    # Borders
    "border":       "#2A2D3E",

    # Status
    "success":      "#22C55E",
    "warning":      "#F59E0B",
    "error":        "#EF4444",
}

FONTS = {
    "heading_lg": ("Segoe UI", 20, "bold"),
    "heading_md": ("Segoe UI", 14, "bold"),
    "body":       ("Segoe UI", 11),
    "body_small": ("Segoe UI", 9),
    "mono":       ("Consolas", 10),
}

SPACING = {
    "xs": 4,
    "sm": 8,
    "md": 16,
    "lg": 24,
    "xl": 32,
}
```

---

## 4. Dùng `ttk` thay `tk` thuần

Widget `ttk` có thể style được — `tk` thuần thì không.

```python
import tkinter as tk
from tkinter import ttk

# ❌ Tránh
btn = tk.Button(root, text="Click")

# ✅ Nên dùng
btn = ttk.Button(root, text="Click")

# Widget ttk quan trọng:
# ttk.Button, ttk.Label, ttk.Entry, ttk.Combobox
# ttk.Notebook (tabs), ttk.Treeview (bảng), ttk.Progressbar
```

---

## 5. Tùy chỉnh Style với `ttk.Style`

```python
import tkinter as tk
from tkinter import ttk
from theme import COLORS, FONTS

def apply_dark_theme(root):
    style = ttk.Style(root)
    style.theme_use("clam")  # Base theme linh hoạt nhất

    # Nền app
    root.configure(bg=COLORS["bg_primary"])

    # Button
    style.configure(
        "Custom.TButton",
        background=COLORS["accent"],
        foreground=COLORS["text_primary"],
        font=FONTS["body"],
        padding=(16, 8),
        borderwidth=0,
        relief="flat",
        focusthickness=0,
    )
    style.map(
        "Custom.TButton",
        background=[
            ("active",   COLORS["accent_hover"]),
            ("disabled", COLORS["bg_secondary"]),
        ],
        foreground=[
            ("disabled", COLORS["text_muted"]),
        ],
    )

    # Label
    style.configure(
        "Custom.TLabel",
        background=COLORS["bg_primary"],
        foreground=COLORS["text_primary"],
        font=FONTS["body"],
    )

    # Entry
    style.configure(
        "Custom.TEntry",
        fieldbackground=COLORS["bg_secondary"],
        foreground=COLORS["text_primary"],
        insertcolor=COLORS["text_primary"],
        bordercolor=COLORS["border"],
        lightcolor=COLORS["border"],
        darkcolor=COLORS["border"],
        padding=(8, 6),
        font=FONTS["body"],
    )
    style.map(
        "Custom.TEntry",
        bordercolor=[("focus", COLORS["accent"])],
        lightcolor=[("focus", COLORS["accent"])],
    )

# Dùng trong code:
root = tk.Tk()
apply_dark_theme(root)

btn = ttk.Button(root, text="Lưu", style="Custom.TButton")
btn.pack()
```

---

## 6. Layout đẹp với `grid` & `pack`

### Nguyên tắc spacing nhất quán

```python
PAD = 16  # 1 đơn vị spacing

# Luôn dùng padx/pady bằng nhau và là bội số PAD
widget.grid(row=0, column=0, padx=PAD, pady=PAD//2, sticky="ew")
```

### Grid layout 2 cột (Sidebar + Content)

```python
root.columnconfigure(0, minsize=220)   # Sidebar cố định
root.columnconfigure(1, weight=1)      # Content co giãn
root.rowconfigure(0, weight=1)

sidebar = tk.Frame(root, bg=COLORS["bg_secondary"], width=220)
sidebar.grid(row=0, column=0, sticky="nsew")
sidebar.grid_propagate(False)  # Không để widget con thay đổi kích thước sidebar

content = tk.Frame(root, bg=COLORS["bg_primary"])
content.grid(row=0, column=1, sticky="nsew")
```

### Frame làm Divider

```python
divider = tk.Frame(root, bg=COLORS["border"], height=1)
divider.pack(fill="x", padx=16, pady=8)
```

---

## 7. CustomTkinter — nâng cấp toàn diện

`customtkinter` là wrapper hiện đại nhất cho Tkinter — có sẵn rounded corners, dark mode, và nhiều widget đẹp.

```python
import customtkinter as ctk

# Config toàn app
ctk.set_appearance_mode("dark")          # "dark" | "light" | "system"
ctk.set_default_color_theme("blue")      # "blue" | "green" | "dark-blue"

app = ctk.CTk()
app.title("My App")
app.geometry("900x600")

# Button đẹp, có bo góc
btn = ctk.CTkButton(
    app,
    text="Bắt đầu",
    width=140,
    height=40,
    corner_radius=8,
    fg_color="#7C6FF7",
    hover_color="#9B96F8",
    font=("Segoe UI", 13, "bold"),
    command=lambda: print("clicked"),
)
btn.pack(pady=20)

# Entry với placeholder
entry = ctk.CTkEntry(
    app,
    placeholder_text="Nhập tên...",
    width=300,
    height=40,
    corner_radius=8,
)
entry.pack()

# Scrollable Frame
scroll_frame = ctk.CTkScrollableFrame(app, width=400, height=300)
scroll_frame.pack(pady=10)

for i in range(20):
    ctk.CTkLabel(scroll_frame, text=f"Item {i+1}").pack(pady=2)

# Tabs (Notebook)
tabview = ctk.CTkTabview(app, width=500)
tabview.pack()
tabview.add("Tổng quan")
tabview.add("Cài đặt")

ctk.CTkLabel(tabview.tab("Tổng quan"), text="Nội dung tab 1").pack()

app.mainloop()
```

---

## 8. Sidebar Navigation

```python
import customtkinter as ctk

class Sidebar(ctk.CTkFrame):
    def __init__(self, parent, nav_items, on_select):
        super().__init__(parent, width=220, corner_radius=0, fg_color="#1A1D27")
        self.grid_propagate(False)
        self.on_select = on_select
        self.buttons = {}
        self.active = None

        # Logo / App name
        logo = ctk.CTkLabel(
            self,
            text="⚡ MyApp",
            font=("Segoe UI", 16, "bold"),
            text_color="#F1F1F3",
        )
        logo.pack(pady=(24, 32), padx=20, anchor="w")

        # Nav items
        for icon, label, key in nav_items:
            btn = ctk.CTkButton(
                self,
                text=f"  {icon}  {label}",
                anchor="w",
                height=40,
                corner_radius=8,
                fg_color="transparent",
                hover_color="#252836",
                text_color="#8B8FA8",
                font=("Segoe UI", 12),
                command=lambda k=key: self.select(k),
            )
            btn.pack(fill="x", padx=12, pady=2)
            self.buttons[key] = btn

    def select(self, key):
        # Reset button cũ
        if self.active and self.active in self.buttons:
            self.buttons[self.active].configure(
                fg_color="transparent",
                text_color="#8B8FA8",
            )
        # Highlight button mới
        self.buttons[key].configure(
            fg_color="#252836",
            text_color="#F1F1F3",
        )
        self.active = key
        self.on_select(key)


# Dùng:
NAV_ITEMS = [
    ("🏠", "Trang chủ",  "home"),
    ("📊", "Thống kê",   "stats"),
    ("⚙️", "Cài đặt",   "settings"),
]

sidebar = Sidebar(root, NAV_ITEMS, on_select=lambda k: print(f"Chuyển đến: {k}"))
sidebar.grid(row=0, column=0, sticky="nsew")
sidebar.select("home")  # Mặc định chọn trang chủ
```

---

## 9. Card & Panel Component

```python
import customtkinter as ctk

class Card(ctk.CTkFrame):
    """Panel bo góc, có tiêu đề và nội dung."""

    def __init__(self, parent, title="", **kwargs):
        super().__init__(
            parent,
            corner_radius=12,
            fg_color="#1A1D27",
            border_width=1,
            border_color="#2A2D3E",
            **kwargs,
        )

        if title:
            title_label = ctk.CTkLabel(
                self,
                text=title,
                font=("Segoe UI", 13, "bold"),
                text_color="#F1F1F3",
                anchor="w",
            )
            title_label.pack(fill="x", padx=16, pady=(14, 0))

            sep = ctk.CTkFrame(self, height=1, fg_color="#2A2D3E")
            sep.pack(fill="x", padx=16, pady=(10, 0))

    def add(self, widget):
        """Thêm widget vào card."""
        widget.pack(fill="x", padx=16, pady=8)
        return widget


class StatCard(ctk.CTkFrame):
    """Card hiển thị 1 con số thống kê."""

    def __init__(self, parent, label, value, color="#7C6FF7", **kwargs):
        super().__init__(
            parent,
            corner_radius=12,
            fg_color="#1A1D27",
            border_width=1,
            border_color="#2A2D3E",
            **kwargs,
        )
        ctk.CTkLabel(self, text=label, font=("Segoe UI", 11), text_color="#8B8FA8").pack(
            anchor="w", padx=16, pady=(14, 2)
        )
        ctk.CTkLabel(self, text=value, font=("Segoe UI", 28, "bold"), text_color=color).pack(
            anchor="w", padx=16, pady=(0, 14)
        )


# Dùng:
card = Card(parent, title="Thông tin người dùng")
ctk.CTkLabel(card, text="Tên: Nguyễn Văn A").pack(...)
```

---

## 10. Animation đơn giản

Tkinter không có animation sẵn, nhưng dùng `after()` ta có thể tạo hiệu ứng mượt.

```python
class FadeLabel(tk.Label):
    """Label xuất hiện bằng cách fade in."""

    def __init__(self, parent, text, **kwargs):
        super().__init__(parent, text=text, **kwargs)
        self._alpha = 0
        self._fade_in()

    def _fade_in(self):
        if self._alpha < 255:
            self._alpha = min(self._alpha + 15, 255)
            gray = self._alpha
            color = f"#{gray:02x}{gray:02x}{gray:02x}"
            self.configure(fg=color)
            self.after(16, self._fade_in)  # ~60fps


class SlideFrame(tk.Frame):
    """Frame trượt vào từ phải."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._offset = 60
        self._slide_in()

    def _slide_in(self):
        if self._offset > 0:
            self._offset = max(0, self._offset - 6)
            self.place(x=self._offset, y=0, relwidth=1, relheight=1)
            self.after(16, self._slide_in)


def pulse_button(btn, original_color="#7C6FF7", pulse_color="#9B96F8", steps=10):
    """Hiệu ứng nhấp nháy khi click."""
    def restore(i):
        if i > 0:
            btn.configure(fg_color=pulse_color)
            btn.after(30, lambda: restore(i - 1))
        else:
            btn.configure(fg_color=original_color)

    btn.configure(fg_color=pulse_color)
    btn.after(30, lambda: restore(steps))
```

---

## 11. Icon với Pillow

```python
from PIL import Image, ImageTk
import customtkinter as ctk

# Load và resize icon
def load_icon(path, size=(20, 20)):
    img = Image.open(path).resize(size, Image.LANCZOS)
    return ctk.CTkImage(img, size=size)

# Dùng với Button
icon = load_icon("icons/save.png")
btn = ctk.CTkButton(parent, image=icon, text="Lưu", compound="left")

# Dùng với Label
avatar = load_icon("avatar.png", size=(48, 48))
ctk.CTkLabel(parent, image=avatar, text="").pack()
```

> 💡 **Tip:** Dùng icon SVG → PNG từ [Heroicons](https://heroicons.com) hoặc [Tabler Icons](https://tabler-icons.io) — free và đẹp.

---

## 12. Ví dụ app hoàn chỉnh

```python
import customtkinter as ctk

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Dashboard")
        self.geometry("1000x650")
        self.minsize(800, 500)

        # Layout chính: sidebar + content
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_content()

    def _build_sidebar(self):
        sidebar = ctk.CTkFrame(self, width=200, corner_radius=0, fg_color="#111318")
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        sidebar.grid_rowconfigure(10, weight=1)

        # Logo
        ctk.CTkLabel(
            sidebar,
            text="⚡ Dashboard",
            font=("Segoe UI", 15, "bold"),
        ).grid(row=0, column=0, pady=(20, 30), padx=20, sticky="w")

        # Nav buttons
        nav = [
            ("🏠  Tổng quan",  0, self.show_home),
            ("📈  Thống kê",   1, self.show_stats),
            ("👥  Người dùng", 2, lambda: None),
            ("⚙️  Cài đặt",    3, lambda: None),
        ]
        self.nav_btns = []
        for text, row, cmd in nav:
            btn = ctk.CTkButton(
                sidebar,
                text=text,
                anchor="w",
                height=38,
                corner_radius=8,
                fg_color="transparent",
                hover_color="#1E2130",
                text_color="#8A8FA8",
                font=("Segoe UI", 12),
                command=cmd,
            )
            btn.grid(row=row + 1, column=0, padx=10, pady=2, sticky="ew")
            self.nav_btns.append(btn)

        # Highlight mặc định
        self.nav_btns[0].configure(fg_color="#1E2130", text_color="white")

    def _build_content(self):
        self.content = ctk.CTkFrame(self, fg_color="#0D0F17")
        self.content.grid(row=0, column=1, sticky="nsew", padx=0)
        self.content.grid_columnconfigure((0, 1, 2), weight=1)

        # Header
        ctk.CTkLabel(
            self.content,
            text="Tổng quan",
            font=("Segoe UI", 20, "bold"),
        ).grid(row=0, column=0, columnspan=3, padx=24, pady=(24, 8), sticky="w")

        # Stat cards
        stats = [
            ("Người dùng",   "1,284",  "#7C6FF7"),
            ("Doanh thu",    "₫48.2M", "#22C55E"),
            ("Đơn hàng",     "342",    "#F59E0B"),
        ]
        for i, (label, value, color) in enumerate(stats):
            card = ctk.CTkFrame(
                self.content,
                corner_radius=12,
                fg_color="#1A1D27",
                border_width=1,
                border_color="#2A2D3E",
            )
            card.grid(row=1, column=i, padx=(24 if i == 0 else 8, 8 if i < 2 else 24), pady=8, sticky="ew")
            ctk.CTkLabel(card, text=label, font=("Segoe UI", 11), text_color="#8B8FA8").pack(anchor="w", padx=16, pady=(14, 2))
            ctk.CTkLabel(card, text=value, font=("Segoe UI", 26, "bold"), text_color=color).pack(anchor="w", padx=16, pady=(0, 14))

        # Bảng dữ liệu
        table_frame = ctk.CTkFrame(self.content, corner_radius=12, fg_color="#1A1D27", border_width=1, border_color="#2A2D3E")
        table_frame.grid(row=2, column=0, columnspan=3, padx=24, pady=16, sticky="nsew")
        self.content.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(table_frame, text="Giao dịch gần đây", font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=16, pady=(14, 8))

        rows = [
            ("#001", "Nguyễn Văn A", "₫1,200,000", "✅ Thành công"),
            ("#002", "Trần Thị B",   "₫850,000",   "⏳ Đang xử lý"),
            ("#003", "Lê Văn C",     "₫3,400,000", "✅ Thành công"),
            ("#004", "Phạm Thị D",   "₫500,000",   "❌ Thất bại"),
        ]
        for mã, tên, số_tiền, trạng_thái in rows:
            row_frame = ctk.CTkFrame(table_frame, fg_color="transparent")
            row_frame.pack(fill="x", padx=16, pady=2)
            for col, (text, w) in enumerate(zip(
                [mã, tên, số_tiền, trạng_thái],
                [80, 160, 120, 140],
            )):
                ctk.CTkLabel(row_frame, text=text, width=w, anchor="w", font=("Segoe UI", 11), text_color="#C0C4D8").pack(side="left")

    def show_home(self):
        print("Home")

    def show_stats(self):
        print("Stats")


if __name__ == "__main__":
    app = App()
    app.mainloop()
```

---

## 13. Checklist trước khi release

```
✅ Font nhất quán — chỉ dùng 1-2 font trong toàn app
✅ Màu sắc định nghĩa ở 1 file theme duy nhất
✅ Spacing dùng bội số 8 (8, 16, 24, 32...)
✅ Tất cả widget có hover state rõ ràng
✅ App resize được đẹp (dùng weight=1 đúng chỗ)
✅ Không có widget nào bị "nhảy layout" khi resize
✅ Window title, icon app đã set
✅ Minsize hợp lý để không bị vỡ layout
✅ Error state (thông báo lỗi) hiển thị đúng màu (đỏ)
✅ Loading state nếu có tác vụ nặng (Progressbar)
```

---

---

## 14. Làm Giống Web Thật Sự

Đây là những kỹ thuật tạo ra sự khác biệt lớn nhất giữa app "trông như desktop cũ" và app "trông như web hiện đại".

---

### 14.1 Typography Scale — chữ có tầng bậc rõ ràng

Web đẹp không phải vì màu sắc — mà vì chữ có **kích thước tương phản rõ**. Tránh dùng tất cả text cùng 1 size.

```python
# Đặt rõ 5 cấp độ chữ, dùng nhất quán
SCALE = {
    "display":  ("Segoe UI", 32, "bold"),   # Số lớn, hero text
    "h1":       ("Segoe UI", 22, "bold"),   # Tiêu đề trang
    "h2":       ("Segoe UI", 15, "bold"),   # Tiêu đề section/card
    "body":     ("Segoe UI", 12, "normal"), # Văn bản thường
    "caption":  ("Segoe UI", 10, "normal"), # Chú thích, label nhỏ
}

# ✅ Đúng — có tầng bậc rõ
ctk.CTkLabel(frame, text="1,284",        font=SCALE["display"], text_color="#7C6FF7")
ctk.CTkLabel(frame, text="Người dùng",  font=SCALE["caption"], text_color="#8B8FA8")

# ❌ Sai — đồng đều, nhạt nhẽo
ctk.CTkLabel(frame, text="1,284",        font=("Segoe UI", 12))
ctk.CTkLabel(frame, text="Người dùng",  font=("Segoe UI", 12))
```

---

### 14.2 Shadow giả bằng Frame xếp lớp

Tkinter không hỗ trợ `box-shadow` như CSS, nhưng có thể giả lập bằng cách đặt 2 Frame chồng nhau lệch vài pixel.

```python
def make_card_with_shadow(parent, width=300, height=150, bg="#1A1D27"):
    """Tạo card có shadow giả — trông giống web."""
    # Layer 1: shadow (đặt trước, màu tối hơn, lệch 3px)
    shadow = tk.Frame(parent, bg="#0A0C12", width=width, height=height)
    shadow.place(x=3, y=3)

    # Layer 2: card thật (đặt sau, che shadow)
    card = ctk.CTkFrame(
        parent,
        width=width,
        height=height,
        corner_radius=12,
        fg_color=bg,
        border_width=1,
        border_color="#2A2D3E",
    )
    card.place(x=0, y=0)
    return card

# Dùng trong Canvas để place hoạt động:
canvas = tk.Canvas(root, bg="#0D0F17", highlightthickness=0)
canvas.pack(fill="both", expand=True)
card = make_card_with_shadow(canvas, width=280, height=140)
```

> 💡 Cách đơn giản hơn: dùng `border_width=1` + `border_color` tối là đã đủ "depth" cho hầu hết trường hợp.

---

### 14.3 Hover transition mượt (màu thay đổi dần)

Web có CSS `transition: 0.2s` — Tkinter cần tự code bằng `after()`.

```python
def smooth_hover(widget, normal_color, hover_color, steps=8, delay=15):
    """Tạo hiệu ứng hover màu chuyển dần — giống CSS transition."""

    def hex_to_rgb(h):
        h = h.lstrip("#")
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

    def rgb_to_hex(r, g, b):
        return f"#{int(r):02x}{int(g):02x}{int(b):02x}"

    def interpolate(c1, c2, t):
        return tuple(c1[i] + (c2[i] - c1[i]) * t for i in range(3))

    nc = hex_to_rgb(normal_color)
    hc = hex_to_rgb(hover_color)
    _step = [0]
    _job  = [None]

    def animate(target):
        if _job[0]:
            widget.after_cancel(_job[0])
        def tick():
            _step[0] = min(steps, max(0, _step[0] + (1 if target else -1)))
            t = _step[0] / steps
            color = rgb_to_hex(*interpolate(nc, hc, t))
            widget.configure(fg_color=color)
            if 0 < _step[0] < steps:
                _job[0] = widget.after(delay, tick)
        tick()

    widget.bind("<Enter>", lambda e: animate(True))
    widget.bind("<Leave>", lambda e: animate(False))

# Dùng:
btn = ctk.CTkButton(frame, text="Hover tôi", fg_color="#1A1D27")
smooth_hover(btn, normal_color="#1A1D27", hover_color="#2D2F45")
```

---

### 14.4 Tooltip — hiện khi hover, giống web

```python
import tkinter as tk
import customtkinter as ctk

class Tooltip:
    """Tooltip nhỏ xuất hiện khi hover — giống web title attribute."""

    def __init__(self, widget, text, delay=500):
        self.widget = widget
        self.text   = text
        self.delay  = delay
        self._tip   = None
        self._job   = None
        widget.bind("<Enter>",  self._schedule)
        widget.bind("<Leave>",  self._cancel)
        widget.bind("<Button>", self._cancel)

    def _schedule(self, e=None):
        self._cancel()
        self._job = self.widget.after(self.delay, self._show)

    def _cancel(self, e=None):
        if self._job:
            self.widget.after_cancel(self._job)
            self._job = None
        if self._tip:
            self._tip.destroy()
            self._tip = None

    def _show(self):
        x = self.widget.winfo_rootx() + 10
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4

        self._tip = tk.Toplevel(self.widget)
        self._tip.wm_overrideredirect(True)  # Không có titlebar
        self._tip.wm_geometry(f"+{x}+{y}")

        label = tk.Label(
            self._tip,
            text=self.text,
            bg="#1E2130",
            fg="#E0E0E8",
            font=("Segoe UI", 10),
            padx=10,
            pady=5,
            relief="flat",
        )
        label.pack()

# Dùng:
btn = ctk.CTkButton(frame, text="?")
Tooltip(btn, "Nhấn để xem thêm thông tin")
```

---

### 14.5 Badge / Tag — chip màu như web

```python
def make_badge(parent, text, color="#7C6FF7", text_color="#FFFFFF"):
    """Badge nhỏ bo góc — dùng cho status, tag, label."""
    badge = tk.Label(
        parent,
        text=f"  {text}  ",
        bg=color,
        fg=text_color,
        font=("Segoe UI", 9, "bold"),
        padx=6,
        pady=2,
        relief="flat",
    )
    # Bo góc giả: dùng CTkFrame nếu cần bo thật
    return badge

# Hoặc dùng CTkFrame để bo góc thật:
def make_badge_rounded(parent, text, color="#7C6FF7", text_color="white"):
    frame = ctk.CTkFrame(parent, fg_color=color, corner_radius=20)
    ctk.CTkLabel(
        frame,
        text=text,
        font=("Segoe UI", 9, "bold"),
        text_color=text_color,
        padx=10,
        pady=2,
    ).pack()
    return frame

# Ví dụ dùng:
# make_badge_rounded(row, "✅ Thành công", color="#14532D", text_color="#4ADE80")
# make_badge_rounded(row, "⏳ Chờ",        color="#451A03", text_color="#FCD34D")
# make_badge_rounded(row, "❌ Lỗi",        color="#450A0A", text_color="#F87171")
```

---

### 14.6 Skeleton Loading — hiệu ứng chờ như web

Web hiện đại dùng skeleton thay vì spinner. Tkinter có thể giả lập bằng animation màu.

```python
import customtkinter as ctk

class SkeletonBar(ctk.CTkFrame):
    """Thanh skeleton nhấp nháy — dùng khi đang load data."""

    def __init__(self, parent, width=200, height=14, **kwargs):
        super().__init__(parent, width=width, height=height,
                         corner_radius=6, fg_color="#1E2130", **kwargs)
        self.grid_propagate(False)
        self._bright = False
        self._animate()

    def _animate(self):
        self._bright = not self._bright
        color = "#2A2D40" if self._bright else "#1E2130"
        self.configure(fg_color=color)
        self.after(700, self._animate)


class SkeletonCard(ctk.CTkFrame):
    """Card skeleton — placeholder khi chờ API."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, corner_radius=12, fg_color="#1A1D27",
                         border_width=1, border_color="#2A2D3E", **kwargs)
        # Avatar tròn giả
        SkeletonBar(self, width=40, height=40).pack(anchor="w", padx=16, pady=(16, 0))
        SkeletonBar(self, width=160, height=12).pack(anchor="w", padx=16, pady=(10, 2))
        SkeletonBar(self, width=100, height=10).pack(anchor="w", padx=16, pady=(0, 16))

# Dùng:
# Hiện skeleton khi đang load
skeleton = SkeletonCard(content_frame)
skeleton.pack(fill="x", padx=16, pady=8)

# Sau khi data về, destroy skeleton và hiện data thật
# skeleton.destroy()
```

---

### 14.7 Modal / Dialog tự tạo — giống popup web

`tk.messagebox` trông rất cũ. Làm modal riêng sẽ đẹp hơn nhiều.

```python
import customtkinter as ctk
import tkinter as tk

class Modal(ctk.CTkToplevel):
    """Modal popup trông giống web — có overlay mờ và animation."""

    def __init__(self, parent, title="Xác nhận", message="", on_confirm=None):
        super().__init__(parent)
        self.on_confirm = on_confirm

        # Cấu hình cửa sổ
        self.title("")
        self.resizable(False, False)
        self.grab_set()           # Chặn tương tác cửa sổ chính
        self.focus()

        # Tính vị trí giữa màn hình
        w, h = 380, 200
        px = parent.winfo_rootx() + (parent.winfo_width()  - w) // 2
        py = parent.winfo_rooty() + (parent.winfo_height() - h) // 2
        self.geometry(f"{w}x{h}+{px}+{py}")
        self.configure(fg_color="#1A1D27")

        # Nội dung
        ctk.CTkLabel(
            self, text=title,
            font=("Segoe UI", 15, "bold"),
            text_color="#F1F1F3",
        ).pack(pady=(28, 8), padx=28, anchor="w")

        ctk.CTkLabel(
            self, text=message,
            font=("Segoe UI", 12),
            text_color="#8B8FA8",
            wraplength=320,
            justify="left",
        ).pack(padx=28, anchor="w")

        # Nút hành động
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(side="bottom", fill="x", padx=20, pady=20)

        ctk.CTkButton(
            btn_row, text="Hủy",
            fg_color="#252836", hover_color="#2D3046",
            text_color="#8B8FA8", width=100,
            command=self.destroy,
        ).pack(side="right", padx=(8, 0))

        ctk.CTkButton(
            btn_row, text="Xác nhận",
            fg_color="#7C6FF7", hover_color="#9B96F8",
            width=120,
            command=self._confirm,
        ).pack(side="right")

    def _confirm(self):
        if self.on_confirm:
            self.on_confirm()
        self.destroy()

# Dùng:
def delete_item():
    Modal(
        root,
        title="Xóa mục này?",
        message="Hành động này không thể hoàn tác. Dữ liệu sẽ bị xóa vĩnh viễn.",
        on_confirm=lambda: print("Đã xóa!"),
    )
```

---

### 14.8 Scrollbar ẩn nhưng vẫn scroll được

Scrollbar mặc định của Tkinter trông xấu. Giải pháp: ẩn đi, dùng chuột cuộn.

```python
def make_hidden_scrollframe(parent, bg="#0D0F17"):
    """Frame cuộn được nhưng không thấy scrollbar — giống web."""
    container = tk.Frame(parent, bg=bg)
    canvas    = tk.Canvas(container, bg=bg, highlightthickness=0)
    scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)

    inner = tk.Frame(canvas, bg=bg)
    inner.bind("<Configure>", lambda e: canvas.configure(
        scrollregion=canvas.bbox("all")
    ))
    canvas.create_window((0, 0), window=inner, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True)
    # Không pack scrollbar → ẩn đi

    # Cuộn bằng chuột
    def _on_mousewheel(e):
        canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
    canvas.bind_all("<MouseWheel>", _on_mousewheel)

    return container, inner  # Thêm widget vào `inner`

# Dùng:
scroll_container, scroll_inner = make_hidden_scrollframe(root)
scroll_container.pack(fill="both", expand=True)
for i in range(30):
    ctk.CTkLabel(scroll_inner, text=f"Dòng {i+1}").pack(anchor="w", padx=16, pady=4)
```

---

### 14.9 Tóm tắt: Web vs Tkinter cũ

| Tính năng web | Cách làm trong Tkinter |
|---------------|------------------------|
| `border-radius` | `corner_radius` trong CustomTkinter |
| `box-shadow` | Frame xếp lớp lệch offset |
| `transition: 0.2s` | `after()` + interpolate màu |
| `tooltip` | `Toplevel` + `bind("<Enter>")` |
| `badge/chip` | `CTkFrame` bo góc + Label |
| `skeleton loading` | Frame nhấp nháy bằng `after()` |
| `modal/dialog` | `CTkToplevel` + `grab_set()` |
| `hidden scrollbar` | Canvas + ẩn Scrollbar widget |
| `font scale` | Định nghĩa 5 cấp size rõ ràng |
| `hover color` | `bind("<Enter>/<Leave>")` |

---

## Tài nguyên thêm

| Tài nguyên | Link |
|------------|------|
| CustomTkinter docs | https://customtkinter.tomschimansky.com |
| Tabler Icons (free) | https://tabler-icons.io |
| Coolors (tạo palette) | https://coolors.co |
| ttkbootstrap | https://ttkbootstrap.readthedocs.io |
| Tkinter docs | https://docs.python.org/3/library/tkinter.html |

---

*Được viết cho Python 3.10+ | customtkinter 5.x | Pillow 10.x*