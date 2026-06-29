"""Tooltip hiện text khi hover vào widget."""
import tkinter as tk


class ToolTip:
    _label = None
    _after_id = None

    def __init__(self, widget, text, delay=400):
        self.widget = widget
        self.text = text
        self.delay = delay
        widget.bind("<Enter>", self._enter, "+")
        widget.bind("<Leave>", self._leave, "+")

    def _enter(self, event=None):
        self._after_id = self.widget.after(self.delay, self._show)

    def _leave(self, event=None):
        if self._after_id:
            self.widget.after_cancel(self._after_id)
            self._after_id = None
        self._hide()

    def _show(self):
        x = self.widget.winfo_rootx() + 2
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self._label = tk.Toplevel(self.widget)
        self._label.wm_overrideredirect(True)
        self._label.wm_geometry(f"+{x}+{y}")
        self._label.configure(bg="#252836")
        tk.Label(
            self._label, text=self.text,
            bg="#252836", fg="#F1F1F3",
            font=("Segoe UI", 9),
            padx=8, pady=3,
        ).pack()

    def _hide(self):
        if self._label:
            self._label.destroy()
            self._label = None


def add_tooltip(widget, text, delay=400):
    return ToolTip(widget, text, delay)
