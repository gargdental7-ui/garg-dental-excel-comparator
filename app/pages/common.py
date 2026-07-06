"""Shared GUI helpers used by every Operations Toolkit page: background task
running (so the GUI never blocks on file I/O), a scrollable dialog for
arbitrarily long messages, and a reusable column-mapping row widget."""
import logging
import queue
import threading
import tkinter as tk
from tkinter import ttk

from ..exceptions import AppError

logger = logging.getLogger(__name__)

FILETYPES = [("Excel files", "*.xlsx *.xlsm"), ("All files", "*.*")]


class BackgroundTaskRunner:
    """Runs a worker callable on a daemon thread and delivers its result (or
    error) back to the Tk main thread via polling with `widget.after` - this
    keeps all widget mutation on the main thread no matter which page owns
    the runner."""

    def __init__(self, widget, on_result, on_error, poll_ms=100):
        self._widget = widget
        self._queue = queue.Queue()
        self._on_result = on_result
        self._on_error = on_error
        self._poll_ms = poll_ms
        self._poll()

    def run(self, worker):
        def runner():
            try:
                self._queue.put(("ok", worker()))
            except AppError as exc:
                self._queue.put(("error", str(exc)))
            except Exception:
                logger.exception("Unexpected error in background task")
                self._queue.put(
                    ("error", "An unexpected error occurred. Details were written to the error log.")
                )

        threading.Thread(target=runner, daemon=True).start()

    def _poll(self):
        # The reschedule must always happen, even if a result/error handler
        # raises - otherwise a single bad callback permanently freezes this
        # page's background updates with no further feedback of any kind.
        try:
            try:
                while True:
                    status, payload = self._queue.get_nowait()
                    if status == "error":
                        self._on_error(payload)
                    else:
                        self._on_result(payload)
            except queue.Empty:
                pass
        finally:
            self._widget.after(self._poll_ms, self._poll)


def show_scrollable_text(parent, title, lines):
    """A dialog for arbitrarily long message lists. Plain messagebox sizes
    itself to fit all the text, which can push the OK button off-screen when
    there are many lines - this stays within a fixed, scrollable size."""
    root = parent.winfo_toplevel()

    dialog = tk.Toplevel(root)
    dialog.title(title)
    dialog.transient(root)
    dialog.geometry("560x420")
    dialog.minsize(400, 300)

    text_frame = ttk.Frame(dialog, padding=12)
    text_frame.pack(fill="both", expand=True)

    text = tk.Text(text_frame, wrap="word")
    scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=text.yview)
    text.configure(yscrollcommand=scrollbar.set)
    text.insert("1.0", "\n".join(lines))
    text.configure(state="disabled")
    text.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    button_frame = ttk.Frame(dialog, padding=(12, 0, 12, 12))
    button_frame.pack(fill="x")
    ok_button = ttk.Button(button_frame, text="OK", command=dialog.destroy)
    ok_button.pack(side="right")

    dialog.bind("<Return>", lambda e: dialog.destroy())
    dialog.bind("<Escape>", lambda e: dialog.destroy())

    dialog.update_idletasks()
    x = root.winfo_x() + (root.winfo_width() - dialog.winfo_width()) // 2
    y = root.winfo_y() + (root.winfo_height() - dialog.winfo_height()) // 2
    dialog.geometry(f"+{max(x, 0)}+{max(y, 0)}")

    dialog.grab_set()
    ok_button.focus_set()
    root.wait_window(dialog)


class ColumnMappingRow:
    """One 'Field Name: [dropdown of detected headers]' row, used by both the
    Collection and Inventory pages to map uploaded columns to logical
    fields. A required field is marked with a trailing asterisk."""

    def __init__(self, parent, label, required=False):
        self.required = required
        self.var = tk.StringVar()
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=2)
        text = f"{label} *" if required else label
        ttk.Label(row, text=text, width=26, anchor="w").pack(side="left")
        self.combo = ttk.Combobox(row, textvariable=self.var, state="readonly")
        self.combo.pack(side="left", fill="x", expand=True)

    def set_options(self, headers, allow_none=True):
        values = (["-- None --"] + list(headers)) if allow_none else list(headers)
        self.combo.config(values=values)
        if allow_none:
            self.var.set("-- None --")
        elif headers:
            self.var.set(headers[0])

    def get(self):
        value = self.var.get()
        if not value or value == "-- None --":
            return None
        return value
