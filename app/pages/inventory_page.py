"""Inventory Movement Analyzer page: upload a stock movement report, map its
columns, and classify products by movement during the uploaded period."""
import logging
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .. import generic_excel, inventory_writer
from ..inventory_analyzer import InventoryColumnMapping, MovementThresholds, analyze_inventory
from .common import FILETYPES, BackgroundTaskRunner, ColumnMappingRow

logger = logging.getLogger(__name__)

APP_TITLE = "Garg Dental Operations Toolkit"


class InventoryPage(ttk.Frame):
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
        ttk.Label(self, text="INVENTORY MOVEMENT ANALYZER", font=("Helvetica", 18, "bold")).pack(anchor="w")
        ttk.Label(
            self,
            text="Upload a stock movement report to classify fast/slow/dead stock for the uploaded period.",
            font=("Helvetica", 11),
        ).pack(anchor="w", pady=(0, 18))

        self.setup_frame = ttk.Frame(self)
        self.setup_frame.pack(fill="both", expand=True)

        file_box = ttk.LabelFrame(self.setup_frame, text="Inventory / Stock Movement File", padding=12)
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
        self.code_row = ColumnMappingRow(self.mapping_box, "Product Code", required=True)
        self.description_row = ColumnMappingRow(self.mapping_box, "Description")
        self.unit_row = ColumnMappingRow(self.mapping_box, "Unit")
        self.opening_row = ColumnMappingRow(self.mapping_box, "Opening Quantity", required=True)
        self.received_row = ColumnMappingRow(self.mapping_box, "Received Quantity", required=True)
        self.delivered_row = ColumnMappingRow(self.mapping_box, "Delivered Quantity", required=True)
        self.balance_row = ColumnMappingRow(self.mapping_box, "Current Balance", required=True)
        self.unit_cost_row = ColumnMappingRow(self.mapping_box, "Unit Cost (optional)")
        self.stock_value_row = ColumnMappingRow(self.mapping_box, "Stock Value (optional)")
        self.brand_row = ColumnMappingRow(self.mapping_box, "Brand (optional)")
        self.category_row = ColumnMappingRow(self.mapping_box, "Category (optional)")

        self.threshold_box = ttk.LabelFrame(self.setup_frame, text="Movement Rules (editable)", padding=12)
        self.fast_ratio_var = tk.StringVar(value="70")
        self.normal_ratio_var = tk.StringVar(value="30")
        self._threshold_entry(self.threshold_box, "Fast Moving Ratio ≥ (%):", self.fast_ratio_var)
        self._threshold_entry(self.threshold_box, "Normal Moving Ratio ≥ (%):", self.normal_ratio_var)
        ttk.Label(
            self.threshold_box,
            text=(
                "Movement Ratio = Delivered ÷ (Opening + Received) for the uploaded period only. "
                "Negative Balance → NEGATIVE STOCK. Balance = 0 → OUT OF STOCK. Delivered = 0 and "
                "Balance > 0 → NO MOVEMENT. Otherwise classified by the ratio above. A single period "
                "cannot prove permanent dead stock - results describe the uploaded period only."
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

        self.status_var = tk.StringVar(value="Select an inventory/stock movement Excel file to begin.")
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
        ttk.Button(button_row, text="EXPORT INVENTORY ANALYSIS", command=self._export).pack(
            side="left", padx=(0, 10)
        )
        ttk.Button(button_row, text="NEW ANALYSIS", command=self._reset).pack(side="left")

    @staticmethod
    def _threshold_entry(parent, label, var):
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=2)
        ttk.Label(row, text=label, width=26, anchor="w").pack(side="left")
        ttk.Entry(row, textvariable=var, width=14).pack(side="left")

    # ------------------------------------------------------------ loading --
    def _select_file(self):
        path = filedialog.askopenfilename(title="Select Inventory/Stock Movement File", filetypes=FILETYPES)
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
        required_rows = (self.code_row, self.opening_row, self.received_row, self.delivered_row, self.balance_row)
        optional_rows = (
            self.description_row,
            self.unit_row,
            self.unit_cost_row,
            self.stock_value_row,
            self.brand_row,
            self.category_row,
        )
        for row in required_rows + optional_rows:
            row.set_options(headers, allow_none=row not in required_rows)

        self._auto_map(self.code_row, headers, ["code", "product code", "item code"])
        self._auto_map(self.description_row, headers, ["description", "item description", "product name"])
        self._auto_map(self.unit_row, headers, ["unit"])
        self._auto_map(self.opening_row, headers, ["opening"])
        self._auto_map(self.received_row, headers, ["received"])
        self._auto_map(self.delivered_row, headers, ["delivered"])
        self._auto_map(self.balance_row, headers, ["balance"])
        self._auto_map(self.unit_cost_row, headers, ["unit cost", "cost"])
        self._auto_map(self.stock_value_row, headers, ["stock value", "inventory value"])
        self._auto_map(self.brand_row, headers, ["brand"])
        self._auto_map(self.category_row, headers, ["category"])

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
            return MovementThresholds(
                fast_ratio=float(self.fast_ratio_var.get()) / 100.0,
                normal_ratio=float(self.normal_ratio_var.get()) / 100.0,
            )
        except ValueError:
            raise ValueError("Movement rule values must be numbers.")

    def _start_analyze(self):
        if not self.sheet_data:
            return
        required = {
            "Product Code": self.code_row.get(),
            "Opening Quantity": self.opening_row.get(),
            "Received Quantity": self.received_row.get(),
            "Delivered Quantity": self.delivered_row.get(),
            "Balance": self.balance_row.get(),
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            messagebox.showerror(APP_TITLE, f"Please map the following required column(s): {', '.join(missing)}.")
            return
        try:
            thresholds = self._read_thresholds()
        except ValueError as exc:
            messagebox.showerror(APP_TITLE, str(exc))
            return

        mapping = InventoryColumnMapping(
            code=required["Product Code"],
            description=self.description_row.get(),
            unit=self.unit_row.get(),
            opening=required["Opening Quantity"],
            received=required["Received Quantity"],
            delivered=required["Delivered Quantity"],
            balance=required["Balance"],
            unit_cost=self.unit_cost_row.get(),
            stock_value=self.stock_value_row.get(),
            brand=self.brand_row.get(),
            category=self.category_row.get(),
        )

        self._set_status("Analyzing inventory movement...")
        self.analyze_button.config(state="disabled")
        headers = self.sheet_data.headers
        rows = self.sheet_data.rows
        row_excel_indexes = self.sheet_data.row_excel_indexes
        self._start_background(
            lambda: (
                "analysis_done",
                analyze_inventory(headers, rows, row_excel_indexes, mapping, thresholds),
            )
        )

    def _show_results(self, result):
        self.analyze_button.config(state="normal")
        self.setup_frame.pack_forget()
        counts = result.counts
        stats = (
            f"Total Products Analyzed: {len(result.products):,}\n"
            f"Fast Moving: {counts['FAST MOVING']:,}   "
            f"Normal Moving: {counts['NORMAL MOVING']:,}   "
            f"Slow Moving: {counts['SLOW MOVING']:,}\n"
            f"No Movement: {counts['NO MOVEMENT']:,}   "
            f"Negative Stock: {counts['NEGATIVE STOCK']:,}   "
            f"Out Of Stock: {counts['OUT OF STOCK']:,}\n"
            f"Stock Exceptions: {len(result.exceptions):,}"
        )
        if result.has_value_data:
            stats += (
                f"\nTotal Inventory Value: {result.total_inventory_value:,.2f}\n"
                f"Value In No-Movement Stock: {result.value_no_movement:,.2f}\n"
                f"Value In Slow-Moving Stock: {result.value_slow_moving:,.2f}"
            )
        self.result_stats_var.set(stats)
        self.results_frame.pack(fill="both", expand=True)
        self._set_status("Analysis complete. Movement is classified for the uploaded period only.")

    def _export(self):
        if not self.result:
            return
        default_name = inventory_writer.default_output_filename()
        path = filedialog.asksaveasfilename(
            title="Export Inventory Analysis",
            defaultextension=".xlsx",
            initialfile=default_name,
            filetypes=[("Excel Workbook", "*.xlsx")],
        )
        if not path:
            return
        try:
            inventory_writer.write_inventory_report(path, self.result)
            messagebox.showinfo(APP_TITLE, f"Report saved to:\n{path}")
        except Exception:
            logger.exception("Failed to save inventory report")
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
        self._set_status("Select an inventory/stock movement Excel file to begin.")
