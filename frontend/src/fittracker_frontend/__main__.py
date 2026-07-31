from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

from fittracker_frontend.api import ApiClient, ApiError
from fittracker_frontend.connection_dialog import ConnectionDialog
from fittracker_frontend.ui import FitTrackerApp


class ApplicationController:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.app: FitTrackerApp | None = None

        self.root.withdraw()
        self.root.protocol("WM_DELETE_WINDOW", self.root.destroy)

    def start(self) -> None:
        self.root.after(0, self._connect)
        self.root.mainloop()

    def _connect(self) -> None:
        self.root.withdraw()

        dialog = ConnectionDialog(self.root)
        if not dialog.confirmed:
            self.root.destroy()
            return

        try:
            api = ApiClient(dialog.url, dialog.api_key)
            exercises = api.get_exercises()
        except ApiError as error:
            messagebox.showerror(
                "Could not connect",
                str(error),
                parent=self.root,
            )
            self.root.after(0, self._connect)
            return

        self.app = FitTrackerApp(
            self.root,
            api,
            exercises,
            self._disconnect,
        )
        self.root.deiconify()

    def _disconnect(self) -> None:
        if self.app is not None:
            self.app.destroy()
            self.app = None

        self.root.withdraw()
        self.root.after(0, self._connect)


def main() -> None:
    root = tk.Tk()
    ApplicationController(root).start()


if __name__ == "__main__":
    main()
