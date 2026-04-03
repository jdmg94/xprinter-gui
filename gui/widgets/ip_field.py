"""IPv4 address entry widget with built-in validation."""
import re
import customtkinter as ctk

_IPV4_RE = re.compile(
    r"^((25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(25[0-5]|2[0-4]\d|[01]?\d\d?)$"
)


class IPField(ctk.CTkEntry):
    """Entry widget that highlights red when the IP address is invalid."""

    def __init__(self, master, placeholder: str = "0.0.0.0", **kwargs):
        super().__init__(master, placeholder_text=placeholder, width=150, **kwargs)
        self.bind("<FocusOut>", self._validate)
        self.bind("<KeyRelease>", self._validate)

    def _validate(self, _event=None) -> None:
        val = self.get().strip()
        if val == "" or _IPV4_RE.match(val):
            self.configure(border_color=("gray65", "gray30"))
        else:
            self.configure(border_color="#e74c3c")

    def valid(self) -> bool:
        return _IPV4_RE.match(self.get().strip()) is not None

    def value(self) -> str:
        return self.get().strip()
