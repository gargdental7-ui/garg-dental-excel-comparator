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


class ScrollableFrame(ttk.Frame):
    """A vertically scrollable container. The Collection and Inventory
    pages have a variable number of column-mapping rows plus a rules box,
    which can add up to more vertical space than the window - without this,
    the Analyze button (and everything after it) is simply pushed off
    screen with no way to reach it. Pack content into `.body`, not `self`."""

    def __init__(self, parent):
        super().__init__(parent)
        canvas = tk.Canvas(self, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.body = ttk.Frame(canvas)

        self.body.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        body_window = canvas.create_window((0, 0), window=self.body, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(body_window, width=e.width))
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def _on_mousewheel(event):
            if event.num == 4:
                canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                canvas.yview_scroll(1, "units")
            elif abs(event.delta) >= 120:
                canvas.yview_scroll(int(-event.delta / 120), "units")
            else:
                canvas.yview_scroll(int(-event.delta), "units")

        def _bind_scroll(_event):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)
            canvas.bind_all("<Button-4>", _on_mousewheel)
            canvas.bind_all("<Button-5>", _on_mousewheel)

        def _unbind_scroll(_event):
            canvas.unbind_all("<MouseWheel>")
            canvas.unbind_all("<Button-4>")
            canvas.unbind_all("<Button-5>")

        canvas.bind("<Enter>", _bind_scroll)
        canvas.bind("<Leave>", _unbind_scroll)


class ColumnChecklist(ttk.Frame):
    """A 'Select All / Select None' checkbox list of column names, used by the
    Comparator page to let the user restrict comparison to a subset of the
    columns shared by both files instead of comparing every shared column."""

    def __init__(self, parent):
        super().__init__(parent)
        self._vars = {}

        controls = ttk.Frame(self)
        controls.pack(fill="x", anchor="w")
        ttk.Button(controls, text="Select All", command=self._select_all).pack(side="left")
        ttk.Button(controls, text="Select None", command=self._select_none).pack(side="left", padx=(6, 0))

        self._list_frame = ttk.Frame(self)
        self._list_frame.pack(fill="x", pady=(6, 0))

    def set_columns(self, columns):
        """Rebuild the checklist for `columns`, all checked by default.
        A column that was already present keeps its previous checked state,
        so reselecting a file doesn't silently drop the user's choices."""
        previous = {name: var.get() for name, var in self._vars.items()}
        for child in self._list_frame.winfo_children():
            child.destroy()
        self._vars = {}
        for name in columns:
            var = tk.BooleanVar(value=previous.get(name, True))
            ttk.Checkbutton(self._list_frame, text=name, variable=var).pack(anchor="w")
            self._vars[name] = var

    def get_selected(self):
        return [name for name, var in self._vars.items() if var.get()]

    def _select_all(self):
        for var in self._vars.values():
            var.set(True)

    def _select_none(self):
        for var in self._vars.values():
            var.set(False)


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
