"""A small colored circle that indicates connected / disconnected state."""
import customtkinter as ctk


class StatusDot(ctk.CTkLabel):
    COLORS = {"green": "#2ecc71", "red": "#e74c3c", "yellow": "#f39c12"}

    def __init__(self, master, **kwargs):
        super().__init__(master, text="●", font=("", 18), **kwargs)
        self.set("red")

    def set(self, color: str) -> None:
        self.configure(text_color=self.COLORS.get(color, color))
