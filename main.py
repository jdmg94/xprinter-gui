import ctypes
import ctypes.util

# Must be called before any X11/tkinter initialization to prevent the
# "unknown sequence number while appending request, you called XInitThreads"
# error on Linux caused by Pillow's ImageTk initializing X11 threading late.
_libX11 = ctypes.util.find_library("X11")
if _libX11:
    ctypes.cdll.LoadLibrary(_libX11).XInitThreads()

from gui.app import App


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
