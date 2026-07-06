"""Collection Priority Analyzer page: upload an outstanding/receivables
report, map its columns, and get a rule-based, prioritized follow-up list."""
import logging
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .. import collection_writer, generic_excel
from ..collection_analyzer import CollectionColumnMapping, CollectionThresholds, analyze_collections
from .common import FILETYPES, BackgroundTaskRunner, ColumnMappingRow

logger = logging.getLogger(__name__)

APP_TITLE = "Garg Dental Operations Toolkit"


class CollectionPage(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding=24)
        self.workbook = None
        self.file_path = None
        self.sheet_data = None
        self.result = None

        self._runner = BackgroundTaskRunner(self, self._on_result, self._on_error)
        self._build_widgets()

    # ---------------------------------------------------------------- UI --
    def _build_widgets(self):
        ttk.Label(self, text="COLLECTION PRIORITY ANALYZER", font=("Helvetica", 18, "bold")).pack(anchor="w")
        ttk.Label(
            self,
            text="Upload an outstanding/receivables report to find out who to follow up with first.",
            font=("Helvetica", 11),
        ).pack(anchor="w", pady=(0, 18))

        self.setup_frame = ttk.Frame(self)
        self.setup_frame.pack(fill="both", expand=True)

        file_box = ttk.LabelFrame(self.setup_frame, text="Outstanding / Receivables File", padding=12)
        file_box.pack(fill="x", pady=6)
        ttk.Button(file_box, text="Select File", command=self._select_file).pack(anchor="w")
        self.file_label = ttk.Label(file_box, text="No file selected", foreground="#666666")
        self.file_label.pack(anchor="w", pady=(6, 0))

        self.sheet_row = ttk.Frame(file_box)
        ttk.Label(self.sheet_row, text="Sheet:").pack(side="left")
        self.sheet_var = tk.StringVar()
        self.sheet_combo = ttk.Combobox(self.sheet_row, textvariable=self.sheet_var, state="readonly")
        self.sheet_combo.pack(side="left", padx=(6, 6), fill="x", expand=True)
        ttk.Button(self.sheet_row, text="Load Sheet", command=self._load_selected_sheet).pack(side="left")

        self.mapping_box = ttk.LabelFrame(self.setup_frame, text="Column Mapping", padding=12)
        self.customer_row = ColumnMappingRow(self.mapping_box, "Customer / Party Name", required=True)
        self.amount_row = ColumnMappingRow(self.mapping_box, "Outstanding Amount", required=True)
        self.days_overdue_row = ColumnMappingRow(self.mapping_box, "Days Overdue")
        self.due_date_row = ColumnMappingRow(self.mapping_box, "Due Date")
        self.last_payment_row = ColumnMappingRow(self.mapping_box, "Last Payment Date")
        self.salesperson_row = ColumnMappingRow(self.mapping_box, "Salesperson")
        self.invoice_number_row = ColumnMappingRow(self.mapping_box, "Invoice Number")

        self.threshold_box = ttk.LabelFrame(self.setup_frame, text="Priority Rules (editable)", padding=12)
        self.critical_days_var = tk.StringVar(value="90")
        self.high_days_var = tk.StringVar(value="60")
        self.medium_days_var = tk.StringVar(value="30")
        self.critical_amount_var = tk.StringVar(value="100000")
        self.high_amount_var = tk.StringVar(value="50000")
        self._threshold_entry(self.threshold_box, "Critical Overdue Days:", self.critical_days_var)
        self._threshold_entry(self.threshold_box, "High Overdue Days:", self.high_days_var)
        self._threshold_entry(self.threshold_box, "Medium Overdue Days:", self.medium_days_var)
        self._threshold_entry(self.threshold_box, "Critical Amount:", self.critical_amount_var)
        self._threshold_entry(self.threshold_box, "High Amount:", self.high_amount_var)
        ttk.Label(
            self.threshold_box,
            text=(
                "Rule: CRITICAL if overdue days or amount clear the Critical bar; HIGH if they clear the "
                "High bar; MEDIUM if overdue days clear the Medium bar; otherwise NORMAL. Accounts with 3+ "
                "open invoices move up one priority level. Nothing is owed (≤ 0) is always NORMAL."
            ),
            foreground="#666666",
            wraplength=560,
            justify="left",
        ).pack(anchor="w", pady=(8, 0))

        self.analyze_button = ttk.Button(
            self.setup_frame, text="ANALYZE", command=self._start_analyze, state="disabled"
        )
        self.analyze_button.pack(pady=18)

        self.progress = ttk.Progressbar(self.setup_frame, mode="indeterminate")

        self.status_var = tk.StringVar(value="Select an outstanding/receivables Excel file to begin.")
        ttk.Label(self, textvariable=self.status_var, foreground="#444444", wraplength=620).pack(
            anchor="w", pady=(10, 0)
        )

        self.results_frame = ttk.Frame(self)
        ttk.Label(self.results_frame, text="ANALYSIS COMPLETE", font=("Helvetica", 15, "bold")).pack(
            anchor="w", pady=(0, 12)
        )
        self.result_stats_var = tk.StringVar()
        ttk.Label(
            self.results_frame, textvariable=self.result_stats_var, justify="left", font=("Helvetica", 11)
        ).pack(anchor="w")
        button_row = ttk.Frame(self.results_frame)
        button_row.pack(pady=20, anchor="w")
        ttk.Button(button_row, text="EXPORT COLLECTION REPORT", command=self._export).pack(
            side="left", padx=(0, 10)
        )
        ttk.Button(button_row, text="NEW ANALYSIS", command=self._reset).pack(side="left")

    @staticmethod
    def _threshold_entry(parent, label, var):
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=2)
        ttk.Label(row, text=label, width=22, anchor="w").pack(side="left")
        ttk.Entry(row, textvariable=var, width=14).pack(side="left")

    # ------------------------------------------------------------ loading --
    def _select_file(self):
        path = filedialog.askopenfilename(title="Select Outstanding/Receivables File", filetypes=FILETYPES)
        if not path:
            return
        self.file_path = path
        self.workbook = None
        self.sheet_data = None
        self.analyze_button.config(state="disabled")
        self.mapping_box.pack_forget()
        self.threshold_box.pack_forget()
        self.file_label.config(text=Path(path).name)
        self._set_status(f"Opening {Path(path).name}...")
        self._start_background(lambda: ("workbook_opened", generic_excel.open_workbook(path, "uploaded file")))

    def _load_selected_sheet(self):
        sheet_name = self.sheet_var.get()
        if not self.workbook or not sheet_name:
            return
        self._set_status(f'Reading sheet "{sheet_name}"...')
        self._start_background(
            lambda: ("sheet_loaded", generic_excel.load_generic_sheet(self.workbook, sheet_name, "uploaded file"))
        )

    def _start_background(self, worker):
        self.progress.pack(fill="x", pady=(4, 0))
        self.progress.start(12)
        self._runner.run(worker)

    def _on_error(self, message):
        self.progress.stop()
        self.progress.pack_forget()
        self._set_status("Ready.")
        messagebox.showerror(APP_TITLE, message)

    def _on_result(self, payload):
        self.progress.stop()
        self.progress.pack_forget()
        kind, data = payload

        if kind == "workbook_opened":
            self.workbook = data
            sheet_names = self.workbook.sheetnames
            self.sheet_combo.config(values=sheet_names)
            self.sheet_var.set(sheet_names[0])
            if len(sheet_names) > 1:
                self.sheet_row.pack(fill="x", pady=(6, 0))
            else:
                self.sheet_row.pack_forget()
            self._set_status(f"Opened {Path(self.file_path).name}. Loading sheet...")
            self._start_background(
                lambda: (
                    "sheet_loaded",
                    generic_excel.load_generic_sheet(self.workbook, sheet_names[0], "uploaded file"),
                )
            )
            return

        if kind == "sheet_loaded":
            self.sheet_data = data
            self._populate_mapping(data.headers)
            self._set_status(f"Loaded {len(data.rows):,} rows. Map the required columns, then click Analyze.")
            self.analyze_button.config(state="normal")
        elif kind == "analysis_done":
            self.result = data
            self._show_results(data)

    def _populate_mapping(self, headers):
        for row in (
            self.customer_row,
            self.amount_row,
            self.days_overdue_row,
            self.due_date_row,
            self.last_payment_row,
            self.salesperson_row,
            self.invoice_number_row,
        ):
            row.set_options(headers, allow_none=not row.required)

        self._auto_map(self.customer_row, headers, ["customer", "party", "party name", "customer name"])
        self._auto_map(self.amount_row, headers, ["outstanding amount", "outstanding", "amount", "balance"])
        self._auto_map(self.days_overdue_row, headers, ["days overdue", "overdue days"])
        self._auto_map(self.due_date_row, headers, ["due date"])
        self._auto_map(self.last_payment_row, headers, ["last payment date", "last payment"])
        self._auto_map(self.salesperson_row, headers, ["salesperson", "sales person", "sales rep"])
        self._auto_map(self.invoice_number_row, headers, ["invoice number", "invoice no", "invoice"])

        self.mapping_box.pack(fill="x", pady=6, before=self.analyze_button)
        self.threshold_box.pack(fill="x", pady=6, before=self.analyze_button)

    @staticmethod
    def _auto_map(row, headers, candidates):
        lowered = {h.strip().lower(): h for h in headers}
        for candidate in candidates:
            if candidate in lowered:
                row.var.set(lowered[candidate])
                return

    # --------------------------------------------------------- analysis --
    def _read_thresholds(self):
        try:
            return CollectionThresholds(
                critical_days=int(self.critical_days_var.get()),
                high_days=int(self.high_days_var.get()),
                medium_days=int(self.medium_days_var.get()),
                critical_amount=float(self.critical_amount_var.get()),
                high_amount=float(self.high_amount_var.get()),
            )
        except ValueError:
            raise ValueError("Priority rule values must be numbers.")

    def _start_analyze(self):
        if not self.sheet_data:
            return
        customer_col = self.customer_row.get()
        amount_col = self.amount_row.get()
        if not customer_col or not amount_col:
            messagebox.showerror(APP_TITLE, "Please map both Customer/Party Name and Outstanding Amount.")
            return
        try:
            thresholds = self._read_thresholds()
        except ValueError as exc:
            messagebox.showerror(APP_TITLE, str(exc))
            return

        mapping = CollectionColumnMapping(
            customer=customer_col,
            amount=amount_col,
            days_overdue=self.days_overdue_row.get(),
            due_date=self.due_date_row.get(),
            last_payment_date=self.last_payment_row.get(),
            salesperson=self.salesperson_row.get(),
            invoice_number=self.invoice_number_row.get(),
        )

        self._set_status("Analyzing outstanding accounts...")
        self.analyze_button.config(state="disabled")
        headers = self.sheet_data.headers
        rows = self.sheet_data.rows
        self._start_background(
            lambda: ("analysis_done", analyze_collections(headers, rows, mapping, thresholds))
        )

    def _show_results(self, result):
        self.analyze_button.config(state="normal")
        self.setup_frame.pack_forget()
        stats = (
            f"Total Outstanding: {result.total_outstanding:,.2f}\n"
            f"Total Customers With Outstanding: {result.total_customers:,}\n"
            f"Critical Accounts: {result.critical_count:,}\n"
            f"High Priority Accounts: {result.high_count:,}\n"
            f"Amount Over 90 Days: {result.amount_over_90:,.2f}"
        )
        self.result_stats_var.set(stats)
        self.results_frame.pack(fill="both", expand=True)
        self._set_status("Analysis complete. Export the report to see the full prioritized list.")

    def _export(self):
        if not self.result:
            return
        default_name = collection_writer.default_output_filename()
        path = filedialog.asksaveasfilename(
            title="Export Collection Report",
            defaultextension=".xlsx",
            initialfile=default_name,
            filetypes=[("Excel Workbook", "*.xlsx")],
        )
        if not path:
            return
        try:
            collection_writer.write_collection_report(path, self.result)
            messagebox.showinfo(APP_TITLE, f"Report saved to:\n{path}")
        except Exception:
            logger.exception("Failed to save collection report")
            messagebox.showerror(
                APP_TITLE, "The report could not be saved. Details were written to the error log."
            )

    def _set_status(self, text):
        self.status_var.set(text)

    def _reset(self):
        self.workbook = None
        self.file_path = None
        self.sheet_data = None
        self.result = None
        self.file_label.config(text="No file selected")
        self.sheet_row.pack_forget()
        self.mapping_box.pack_forget()
        self.threshold_box.pack_forget()
        self.analyze_button.config(state="disabled")
        self.results_frame.pack_forget()
        self.setup_frame.pack(fill="both", expand=True)
        self._set_status("Select an outstanding/receivables Excel file to begin.")
