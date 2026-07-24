"""Excel Comparator page: compares two Excel reports by product Code across
every shared column and reports exact old/new values per changed field."""
import logging
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .. import comparator, workbook_reader, workbook_writer
from .common import FILETYPES, BackgroundTaskRunner, ColumnChecklist, ScrollableFrame, show_scrollable_text

logger = logging.getLogger(__name__)

APP_TITLE = "Garg Dental Operations Toolkit"


class ComparatorPage(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding=24)
        self.current_path = None
        self.oms_path = None
        self.current_sheet = None
        self.oms_sheet = None
        self.comparison_result = None

        self._runner = BackgroundTaskRunner(self, self._on_result, self._on_error)
        self._build_widgets()

    # ---------------------------------------------------------------- UI --
    def _build_widgets(self):
        ttk.Label(self, text="EXCEL COMPARATOR", font=("Helvetica", 18, "bold")).pack(anchor="w")
        ttk.Label(
            self,
            text="Compare two Excel reports by product Code across every shared column.",
            font=("Helvetica", 11),
        ).pack(anchor="w", pady=(0, 18))

        self.setup_container = ScrollableFrame(self)
        self.setup_container.pack(fill="both", expand=True)
        self.setup_frame = self.setup_container.body

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

        self.columns_box = ttk.LabelFrame(self.setup_frame, text="Columns To Compare", padding=12)
        self.columns_checklist = ColumnChecklist(self.columns_box)
        self.columns_checklist.pack(fill="x")

        self.compare_button = ttk.Button(
            self.setup_frame, text="COMPARE FILES", command=self._start_compare, state="disabled"
        )
        self.compare_button.pack(pady=18)

        self.progress = ttk.Progressbar(self.setup_frame, mode="indeterminate")

        self.status_var = tk.StringVar(value="Select both Excel files to begin.")
        ttk.Label(self, textvariable=self.status_var, foreground="#444444", wraplength=620).pack(
            anchor="w", pady=(10, 0)
        )

        self.results_frame = ttk.Frame(self)
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
        self._start_background(
            lambda: ("current_loaded", workbook_reader.load_sheet(self.current_path, "Current File"))
        )

    def _select_oms(self):
        path = filedialog.askopenfilename(title="Select OMS File", filetypes=FILETYPES)
        if not path:
            return
        self.oms_path = path
        self.oms_sheet = None
        self.oms_label.config(text=Path(path).name)
        self.compare_button.config(state="disabled")
        self._set_status(f"Loading {Path(path).name}...")
        self._start_background(
            lambda: ("oms_loaded", workbook_reader.load_sheet(self.oms_path, "OMS File"))
        )

    # ------------------------------------------------- background plumbing --
    def _start_background(self, worker):
        self.progress.pack(fill="x", pady=(4, 0))
        self.progress.start(12)
        self._runner.run(worker)

    def _on_error(self, message):
        self.progress.stop()
        self.progress.pack_forget()
        if self.current_sheet and self.oms_sheet:
            self.compare_button.config(state="normal")
        self._set_status("Ready.")
        messagebox.showerror(APP_TITLE, message)

    def _on_result(self, payload):
        self.progress.stop()
        self.progress.pack_forget()

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
            self._refresh_column_selector()
            self.compare_button.config(state="normal")
            self._set_status("Both files loaded. Click Compare Files.")

    # ----------------------------------------------------- column selector --
    def _refresh_column_selector(self):
        shared = comparator.find_shared_columns(self.current_sheet.headers, self.oms_sheet.headers)
        columns = [c for c in shared if c.strip().lower() != "code"]
        self.columns_checklist.set_columns(columns)
        if columns:
            self.columns_box.pack(fill="x", pady=6, before=self.compare_button)
        else:
            self.columns_box.pack_forget()

    # --------------------------------------------------------- comparison --
    def _start_compare(self):
        if not self.current_sheet or not self.oms_sheet:
            messagebox.showerror(APP_TITLE, "Please select both Excel files.")
            return
        selected_columns = self.columns_checklist.get_selected()
        if not selected_columns:
            messagebox.showerror(APP_TITLE, "Please select at least one column to compare.")
            return
        self._set_status("Comparing files...")
        self.compare_button.config(state="disabled")
        self._start_background(
            lambda: (
                "compare_done",
                comparator.compare(self.current_sheet, self.oms_sheet, selected_columns=selected_columns),
            )
        )

    def _show_results(self, result):
        self.compare_button.config(state="normal")
        if result.duplicate_warnings:
            show_scrollable_text(self, "Duplicate Codes Found", result.duplicate_warnings)

        self.setup_container.pack_forget()
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
            messagebox.showinfo(APP_TITLE, f"Result saved to:\n{path}")
        except Exception:
            logger.exception("Failed to save result workbook")
            messagebox.showerror(
                APP_TITLE,
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
        self.columns_checklist.set_columns([])
        self.columns_box.pack_forget()
        self.compare_button.config(state="disabled")
        self.results_frame.pack_forget()
        self.setup_container.pack(fill="both", expand=True)
        self._set_status("Select both Excel files to begin.")
