"""Áp dụng ttk.Style theme cho toàn bộ app."""
from tkinter import ttk
from .theme import COLORS, FONTS


def apply_theme(root):
    style = ttk.Style(root)
    style.theme_use("clam")

    root.configure(bg=COLORS["bg_primary"])

    # ── Notebook (tabs) ──
    style.configure("TNotebook", background=COLORS["bg_primary"],
                     borderwidth=0)
    style.configure("TNotebook.Tab",
                     background=COLORS["bg_secondary"],
                     foreground=COLORS["text_secondary"],
                     font=FONTS["tab"],
                     padding=(18, 6),
                     borderwidth=0,
                     focuscolor="none")
    style.map("TNotebook.Tab",
              background=[("selected", COLORS["bg_primary"]),
                          ("active", COLORS["bg_hover"])],
              foreground=[("selected", COLORS["text_primary"])])

    # ── Frame ──
    style.configure("TFrame", background=COLORS["bg_primary"])
    style.configure("Card.TFrame", background=COLORS["bg_card"])

    # ── Label ──
    style.configure("TLabel", background=COLORS["bg_primary"],
                     foreground=COLORS["text_primary"],
                     font=FONTS["body"])
    style.configure("Heading.TLabel",
                     font=FONTS["heading"])
    style.configure("Secondary.TLabel",
                     foreground=COLORS["text_secondary"])

    # ── Button ──
    style.configure("TButton",
                     background=COLORS["accent"],
                     foreground=COLORS["text_primary"],
                     font=FONTS["body"],
                     padding=(14, 6),
                     borderwidth=0,
                     focusthickness=0)
    style.map("TButton",
              background=[("active", COLORS["accent_hover"]),
                          ("disabled", COLORS["bg_secondary"])],
              foreground=[("disabled", COLORS["text_muted"])])

    style.configure("Secondary.TButton",
                     background=COLORS["bg_secondary"],
                     foreground=COLORS["text_secondary"],
                     padding=(14, 6))
    style.map("Secondary.TButton",
              background=[("active", COLORS["bg_hover"])])

    # ── Canvas (tk, not ttk) ── needs root.bg
    # We'll handle canvas colors directly in each module

    # ── Entry ──
    style.configure("TEntry",
                     fieldbackground=COLORS["bg_secondary"],
                     foreground=COLORS["text_primary"],
                     insertcolor=COLORS["text_primary"],
                     bordercolor=COLORS["border"],
                     lightcolor=COLORS["border"],
                     darkcolor=COLORS["border"],
                     padding=(8, 5),
                     font=FONTS["body"])
    style.map("TEntry",
              bordercolor=[("focus", COLORS["accent"])],
              lightcolor=[("focus", COLORS["accent"])])

    # ── Combobox ──
    style.configure("TCombobox",
                     fieldbackground=COLORS["bg_secondary"],
                     foreground=COLORS["text_primary"],
                     arrowcolor=COLORS["text_secondary"],
                     selectbackground=COLORS["accent"],
                     selectforeground=COLORS["text_primary"],
                     padding=(8, 4),
                     font=FONTS["body"])
    style.map("TCombobox",
              fieldbackground=[("readonly", COLORS["bg_secondary"])],
              foreground=[("readonly", COLORS["text_primary"])])

    # ── Scrollbar ──
    style.configure("Vertical.TScrollbar",
                     background=COLORS["bg_secondary"],
                     troughcolor=COLORS["bg_primary"],
                     borderwidth=0,
                     arrowsize=0)

    # ── Separator ──
    style.configure("TSeparator", background=COLORS["border"])

    # ── Labelframe ──
    style.configure("TLabelframe",
                     background=COLORS["bg_primary"],
                     foreground=COLORS["text_primary"],
                     bordercolor=COLORS["border"],
                     font=FONTS["body"])
    style.configure("TLabelframe.Label",
                     background=COLORS["bg_primary"],
                     foreground=COLORS["text_primary"],
                     font=FONTS["body"])
