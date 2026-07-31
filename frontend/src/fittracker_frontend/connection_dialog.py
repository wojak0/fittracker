from __future__ import annotations

import os
import tkinter as tk
from tkinter import messagebox, ttk
from urllib.parse import urlparse


class ConnectionDialog(tk.Toplevel):
    def __init__(self, parent: tk.Tk) -> None:
        super().__init__(parent)

        self.title("Connect to Fit Tracker API")
        self.resizable(False, False)
        

        self.confirmed = False
        self._url = tk.StringVar(
            value=os.getenv(
                "FITTRACKER_API_URL",
                "http://localhost:8888",
            )
        )
        self._api_key = tk.StringVar()

        frame = ttk.Frame(self, padding=20)
        frame.grid(row=0, column=0)

        ttk.Label(
            frame,
            text="Fit Tracker",
            font=("Sans", 18, "bold"),
        ).grid(
            row=0,
            column=0,
            columnspan=2,
            pady=(0, 20),
        )

        ttk.Label(frame, text="API URL:").grid(
            row=1,
            column=0,
            sticky=tk.E,
            padx=(0, 10),
            pady=8,
        )
        self.url_entry = ttk.Entry(
            frame,
            textvariable=self._url,
            width=42,
        )
        self.url_entry.grid(row=1, column=1, pady=8)

        ttk.Label(frame, text="X-API-Key:").grid(
            row=2,
            column=0,
            sticky=tk.E,
            padx=(0, 10),
            pady=8,
        )
        self.key_entry = ttk.Entry(
            frame,
            textvariable=self._api_key,
            width=42,
            show="*",
        )
        self.key_entry.grid(row=2, column=1, pady=8)

        button_row = ttk.Frame(frame)
        button_row.grid(
            row=3,
            column=0,
            columnspan=2,
            pady=(15, 0),
        )

        ttk.Button(
            button_row,
            text="Cancel",
            command=self._cancel,
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            button_row,
            text="Connect",
            command=self._confirm,
        ).pack(side=tk.LEFT, padx=5)

        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.bind("<Return>", lambda _event: self._confirm())
        self.bind("<Escape>", lambda _event: self._cancel())

        self.update_idletasks()
        self._center_on_screen()

        self.grab_set()
        self.key_entry.focus_set()
        self.wait_window()

    def _center_on_screen(self) -> None:
        width = self.winfo_reqwidth()
        height = self.winfo_reqheight()
        x = (self.winfo_screenwidth() - width) // 2
        y = (self.winfo_screenheight() - height) // 2
        self.geometry(f"+{x}+{y}")

    def _confirm(self) -> None:
        url = self._url.get().strip()
        api_key = self._api_key.get().strip()
        parsed_url = urlparse(url)

        if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
            messagebox.showwarning(
                "Invalid API URL",
                "Enter a valid URL beginning with http:// or https://.",
                parent=self,
            )
            self.url_entry.focus_set()
            return

        if not api_key:
            messagebox.showwarning(
                "Missing API key",
                "Enter the X-API-Key.",
                parent=self,
            )
            self.key_entry.focus_set()
            return

        self.confirmed = True
        self.destroy()

    def _cancel(self) -> None:
        self.confirmed = False
        self.destroy()

    @property
    def url(self) -> str:
        return self._url.get().strip().rstrip("/")

    @property
    def api_key(self) -> str:
        return self._api_key.get().strip()
