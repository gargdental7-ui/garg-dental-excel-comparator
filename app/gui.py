"""Tkinter desktop UI for the Garg Dental Excel Comparator.

File loading and comparison run on a background thread so the GUI stays
responsive on large files; results are relayed back via a thread-safe queue
polled with Tk's own event loop (root.after), which keeps all widget
mutation on the main thread.
"""
import logging
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from . import comparator, workbook_reader, workbook_writer
from .exceptions import AppError

logger = logging.getLogger(__name__)

FILETYPES = [("Excel files", "*.xlsx *.xlsm"), ("All files", "*.*")]


class ComparatorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Garg Dental Excel Comparator")
        self.geometry("700x580")
        self.minsize(640, 540)

        self._queue = queue.Queue()
        self.current_path = None
        self.oms_path = None
        self.current_sheet = None
        self.oms_sheet = None
        self.comparison_result = None

        self._build_widgets()
        self._poll_queue()

    # ---------------------------------------------------------------- UI --
    def _build_widgets(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        container = ttk.Frame(self, padding=24)
        container.pack(fill="both", expand=True)

        ttk.Label(
            container, text="GARG DENTAL EXCEL COMPARATOR", font=("Helvetica", 18, "bold")
        ).pack(anchor="w")
        ttk.Label(
            container,
            text="Compare two Excel reports by product Code across every shared column.",
            font=("Helvetica", 11),
        ).pack(anchor="w", pady=(0, 18))

        self.setup_frame = ttk.Frame(container)
        self.setup_frame.pack(fill="both", expand=True)

        current_box = ttk.LabelFrame(self.setup_frame, text="Current File", padding=12)
        current_box.pack(fill="x", pady=6)
        ttk.Button(current_box, text="Select Current File", command=self._select_current).pack(anchor="w")
        self.current_label = ttk.Label(current_box, text="No file selected", foreground="#666666")
        self.current_label.pack(anchor="w", pady=(6, 0))

        oms_box = ttk.LabelFrame(self.setup_frame, text="Latest OMS File", padding=12)
        oms_box.pack(fill="x", pady=6)
        ttk.Button(oms_box, text="Select OMS File", command=self._select_oms).pack(anchor="w")
        self.oms_label = ttk.Label(oms_box, text="No file selected", foreground="#666666")
        self.oms_label.pack(anchor="w", pady=(6, 0))

        self.compare_button = ttk.Button(
            self.setup_frame, text="COMPARE FILES", command=self._start_compare, state="disabled"
        )
        self.compare_button.pack(pady=18)

        self.progress = ttk.Progressbar(self.setup_frame, mode="indeterminate")

        self.status_var = tk.StringVar(value="Select both Excel files to begin.")
        ttk.Label(container, textvariable=self.status_var, foreground="#444444", wraplength=620).pack(
            anchor="w", pady=(10, 0)
        )

        # Results view, shown in place of setup_frame after a successful compare.
        self.results_frame = ttk.Frame(container)
        ttk.Label(self.results_frame, text="COMPARISON COMPLETE", font=("Helvetica", 15, "bold")).pack(
            anchor="w", pady=(0, 12)
        )
        self.result_stats_var = tk.StringVar()
        ttk.Label(
            self.results_frame, textvariable=self.result_stats_var, justify="left", font=("Helvetica", 11)
        ).pack(anchor="w")

        button_row = ttk.Frame(self.results_frame)
        button_row.pack(pady=20, anchor="w")
        ttk.Button(button_row, text="SAVE RESULT EXCEL", command=self._save_result).pack(
            side="left", padx=(0, 10)
        )
        ttk.Button(button_row, text="NEW COMPARISON", command=self._reset).pack(side="left")

    # ---------------------------------------------------- file selection --
    def _select_current(self):
        path = filedialog.askopenfilename(title="Select Current File", filetypes=FILETYPES)
        if not path:
            return
        self.current_path = path
        self.current_sheet = None
        self.current_label.config(text=Path(path).name)
        self.compare_button.config(state="disabled")
        self._set_status(f"Loading {Path(path).name}...")
        self._run_background(self._load_current_worker)

    def _select_oms(self):
        path = filedialog.askopenfilename(title="Select OMS File", filetypes=FILETYPES)
        if not path:
            return
        self.oms_path = path
        self.oms_sheet = None
        self.oms_label.config(text=Path(path).name)
        self.compare_button.config(state="disabled")
        self._set_status(f"Loading {Path(path).name}...")
        self._run_background(self._load_oms_worker)

    def _load_current_worker(self):
        return "current_loaded", workbook_reader.load_sheet(self.current_path, "Current File")

    def _load_oms_worker(self):
        return "oms_loaded", workbook_reader.load_sheet(self.oms_path, "OMS File")

    # ------------------------------------------------- background plumbing --
    def _run_background(self, worker):
        self.progress.pack(fill="x", pady=(4, 0))
        self.progress.start(12)

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

    def _poll_queue(self):
        try:
            while True:
                status, payload = self._queue.get_nowait()
                self._handle_message(status, payload)
        except queue.Empty:
            pass
        self.after(100, self._poll_queue)

    def _handle_message(self, status, payload):
        self.progress.stop()
        self.progress.pack_forget()

        if status == "error":
            self._set_status("Ready.")
            messagebox.showerror("Garg Dental Excel Comparator", payload)
            return

        kind, data = payload
        if kind == "current_loaded":
            self.current_sheet = data
            self._set_status(f"Loaded {Path(self.current_path).name}.")
        elif kind == "oms_loaded":
            self.oms_sheet = data
            self._set_status(f"Loaded {Path(self.oms_path).name}.")
        elif kind == "compare_done":
            self.comparison_result = data
            self._show_results(data)
            return

        if self.current_sheet and self.oms_sheet:
            self.compare_button.config(state="normal")
            self._set_status("Both files loaded. Click Compare Files.")

    # --------------------------------------------------------- comparison --
    def _start_compare(self):
        if not self.current_sheet or not self.oms_sheet:
            messagebox.showerror("Garg Dental Excel Comparator", "Please select both Excel files.")
            return
        self._set_status("Comparing files...")
        self.compare_button.config(state="disabled")

        def worker():
            return "compare_done", comparator.compare(self.current_sheet, self.oms_sheet)

        self._run_background(worker)

    def _show_scrollable_warning(self, title, lines):
        """A warning dialog for arbitrarily long message lists. Plain
        messagebox.showwarning sizes itself to fit all the text, which can
        push the OK button off-screen when there are many lines (e.g. dozens
        of duplicate-code warnings) - this stays within a fixed, scrollable
        size instead."""
        dialog = tk.Toplevel(self)
        dialog.title(title)
        dialog.transient(self)
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
        x = self.winfo_x() + (self.winfo_width() - dialog.winfo_width()) // 2
        y = self.winfo_y() + (self.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{max(x, 0)}+{max(y, 0)}")

        dialog.grab_set()
        ok_button.focus_set()
        self.wait_window(dialog)

    def _show_results(self, result):
        self.compare_button.config(state="normal")
        if result.duplicate_warnings:
            self._show_scrollable_warning("Duplicate Codes Found", result.duplicate_warnings)

        self.setup_frame.pack_forget()
        stats = (
            f"Products Compared: {result.total_compared:,}\n"
            f"Rows With Differences: {result.total_differences:,}\n"
            f"Field Changes: {result.total_field_differences:,}\n"
            f"New Codes In OMS: {len(result.new_codes):,}\n"
            f"Columns Compared: {', '.join(result.compared_columns)}"
        )
        self.result_stats_var.set(stats)
        self.results_frame.pack(fill="both", expand=True)

        if result.total_differences == 0:
            self._set_status("Comparison complete. No differences were found.")
        else:
            self._set_status("Comparison complete. See FIELD_CHANGES in the saved Excel for exact old/new values.")

    def _save_result(self):
        if not self.comparison_result:
            return
        default_name = workbook_writer.default_output_filename()
        path = filedialog.asksaveasfilename(
            title="Save Result Excel",
            defaultextension=".xlsx",
            initialfile=default_name,
            filetypes=[("Excel Workbook", "*.xlsx")],
        )
        if not path:
            return
        try:
            workbook_writer.write_result(path, self.current_sheet, self.oms_sheet, self.comparison_result)
            messagebox.showinfo("Garg Dental Excel Comparator", f"Result saved to:\n{path}")
        except Exception:
            logger.exception("Failed to save result workbook")
            messagebox.showerror(
                "Garg Dental Excel Comparator",
                "The result file could not be saved. Details were written to the error log.",
            )

    def _set_status(self, text):
        self.status_var.set(text)

    def _reset(self):
        self.current_path = None
        self.oms_path = None
        self.current_sheet = None
        self.oms_sheet = None
        self.comparison_result = None
        self.current_label.config(text="No file selected")
        self.oms_label.config(text="No file selected")
        self.compare_button.config(state="disabled")
        self.results_frame.pack_forget()
        self.setup_frame.pack(fill="both", expand=True)
        self._set_status("Select both Excel files to begin.")


def main():
    app = ComparatorApp()
    app.mainloop()
