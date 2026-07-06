"""Main window for the Garg Dental Operations Toolkit: a sidebar with three
tools, each rendered as a swappable page in the same window (one desktop
application, one executable - not three separate apps)."""
import tkinter as tk
from tkinter import ttk

from .pages.collection_page import CollectionPage
from .pages.comparator_page import ComparatorPage
from .pages.inventory_page import InventoryPage

APP_VERSION = "2.0.0"


class OperationsToolkitApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Garg Dental Operations Toolkit")
        self.geometry("920x700")
        self.minsize(860, 640)

        self._configure_style()
        self._build_layout()

    def _configure_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("Sidebar.TFrame", background="#1f2933")
        style.configure(
            "SidebarTitle.TLabel", background="#1f2933", foreground="#ffffff", font=("Helvetica", 15, "bold")
        )
        style.configure(
            "SidebarSubtitle.TLabel", background="#1f2933", foreground="#9aa5b1", font=("Helvetica", 10)
        )
        style.configure(
            "SidebarVersion.TLabel", background="#1f2933", foreground="#616e7c", font=("Helvetica", 9)
        )
        style.configure("NavButton.TButton", font=("Helvetica", 11), padding=(16, 10))
        style.map("NavButton.TButton", background=[("active", "#e2e8f0")])
        style.configure("NavButtonSelected.TButton", font=("Helvetica", 11, "bold"), padding=(16, 10))

    def _build_layout(self):
        root = ttk.Frame(self)
        root.pack(fill="both", expand=True)

        sidebar = ttk.Frame(root, style="Sidebar.TFrame", width=220)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        ttk.Label(sidebar, text="GARG DENTAL", style="SidebarTitle.TLabel").pack(anchor="w", padx=18, pady=(24, 0))
        ttk.Label(sidebar, text="Operations Toolkit", style="SidebarSubtitle.TLabel").pack(
            anchor="w", padx=18, pady=(0, 24)
        )
        ttk.Label(sidebar, text="TOOLS", style="SidebarSubtitle.TLabel").pack(anchor="w", padx=18, pady=(0, 4))

        self.content = ttk.Frame(root)
        self.content.pack(side="left", fill="both", expand=True)

        self.pages = {
            "Excel Comparator": ComparatorPage(self.content),
            "Collection Analyzer": CollectionPage(self.content),
            "Inventory Analyzer": InventoryPage(self.content),
        }
        for page in self.pages.values():
            page.place(in_=self.content, x=0, y=0, relwidth=1, relheight=1)

        self.nav_buttons = {}
        for name in self.pages:
            btn = ttk.Button(sidebar, text=name, style="NavButton.TButton", command=lambda n=name: self._show_page(n))
            btn.pack(fill="x", padx=10, pady=2)
            self.nav_buttons[name] = btn

        ttk.Label(sidebar, text=f"v{APP_VERSION}", style="SidebarVersion.TLabel").pack(
            side="bottom", anchor="w", padx=18, pady=12
        )

        self._show_page("Excel Comparator")

    def _show_page(self, name):
        for page_name, btn in self.nav_buttons.items():
            btn.configure(style="NavButtonSelected.TButton" if page_name == name else "NavButton.TButton")
        self.pages[name].tkraise()


def main():
    app = OperationsToolkitApp()
    app.mainloop()
