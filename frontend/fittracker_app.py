import json
import tkinter as tk
from datetime import date
from decimal import Decimal, InvalidOperation
from tkinter import messagebox, ttk
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class ApiError(Exception):
    pass


class ApiClient:
    def __init__(self, base_url, api_key):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def request(self, method, path, data=None, protected=False):
        headers = {"Accept": "application/json"}

        if data is not None:
            headers["Content-Type"] = "application/json"

        if protected:
            headers["X-API-Key"] = self.api_key

        body = None
        if data is not None:
            body = json.dumps(data).encode("utf-8")

        request = Request(
            url=f"{self.base_url}{path}",
            data=body,
            headers=headers,
            method=method,
        )

        try:
            with urlopen(request, timeout=8) as response:
                response_body = response.read().decode("utf-8")
                return json.loads(response_body) if response_body else None

        except HTTPError as error:
            try:
                error_body = json.loads(error.read().decode("utf-8"))
                detail = error_body.get("detail", str(error))
            except Exception:
                detail = str(error)

            raise ApiError(f"HTTP {error.code}: {detail}") from error

        except URLError as error:
            raise ApiError(f"Could not connect to the API: {error.reason}") from error

    def get_exercises(self):
        return self.request("GET", "/exercises")

    def get_workouts(self, user_id):
        return self.request("GET", f"/users/{user_id}/workouts")

    def create_workout(self, user_id, workout_date, notes):
        return self.request(
            "POST",
            "/workouts",
            data={
                "user_id": user_id,
                "workout_date": workout_date,
                "notes": notes or None,
            },
            protected=True,
        )

    def add_exercise(self, workout_id, exercise_id, sets, reps, weight):
        return self.request(
            "POST",
            f"/workouts/{workout_id}/exercises",
            data={
                "exercise_id": exercise_id,
                "sets": sets,
                "reps": reps,
                "weight_kg": str(weight),
            },
            protected=True,
        )


class FitTrackerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Fit Tracker")
        self.root.geometry("950x650")
        self.root.minsize(800, 550)

        self.api = None
        self.exercises = []
        self.pending_exercises = []

        self.configure_styles()
        self.show_connection_dialog()

    def configure_styles(self):
        style = ttk.Style()
        style.configure("Title.TLabel", font=("Sans", 18, "bold"))
        style.configure("Heading.TLabel", font=("Sans", 12, "bold"))
        style.configure("Status.TLabel", foreground="#245c2a")

    def clear_window(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def show_connection_dialog(self):
        self.clear_window()

        frame = ttk.Frame(self.root, padding=40)
        frame.place(relx=0.5, rely=0.5, anchor="center")

        ttk.Label(frame, text="Fit Tracker", style="Title.TLabel").grid(
            row=0, column=0, columnspan=2, pady=(0, 25)
        )

        ttk.Label(frame, text="API URL:").grid(
            row=1, column=0, sticky="w", padx=(0, 10), pady=8
        )
        self.api_url_entry = ttk.Entry(frame, width=45)
        self.api_url_entry.insert(0, "http://localhost:8888")
        self.api_url_entry.grid(row=1, column=1, pady=8)

        ttk.Label(frame, text="X-API-Key:").grid(
            row=2, column=0, sticky="w", padx=(0, 10), pady=8
        )
        self.api_key_entry = ttk.Entry(frame, width=45, show="*")
        self.api_key_entry.grid(row=2, column=1, pady=8)

        self.connection_status = ttk.Label(frame, text="", foreground="red")
        self.connection_status.grid(row=3, column=0, columnspan=2, pady=8)

        ttk.Button(frame, text="Connect", command=self.connect).grid(
            row=4, column=0, columnspan=2, pady=15
        )

        self.api_key_entry.focus()

    def connect(self):
        api_url = self.api_url_entry.get().strip()
        api_key = self.api_key_entry.get().strip()

        if not api_url or not api_key:
            self.connection_status.config(
                text="Please enter both the API URL and API key."
            )
            return

        client = ApiClient(api_url, api_key)

        try:
            exercises = client.get_exercises()
        except ApiError as error:
            self.connection_status.config(text=str(error))
            return

        self.api = client
        self.exercises = exercises
        self.build_main_screen()

    def build_main_screen(self):
        self.clear_window()

        header = ttk.Frame(self.root, padding=(15, 10))
        header.pack(fill="x")

        ttk.Label(header, text="Fit Tracker", style="Title.TLabel").pack(side="left")

        ttk.Label(header, text="User ID:").pack(side="left", padx=(30, 5))
        self.user_id_var = tk.StringVar(value="1")
        ttk.Entry(header, textvariable=self.user_id_var, width=6).pack(side="left")

        ttk.Button(header, text="Disconnect", command=self.disconnect).pack(
            side="right"
        )

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=15, pady=(0, 10))

        self.history_tab = ttk.Frame(self.notebook, padding=15)
        self.new_workout_tab = ttk.Frame(self.notebook, padding=15)
        self.exercise_tab = ttk.Frame(self.notebook, padding=15)

        self.notebook.add(self.history_tab, text="Workout History")
        self.notebook.add(self.new_workout_tab, text="Log Workout")
        self.notebook.add(self.exercise_tab, text="Exercise Dictionary")

        self.build_history_tab()
        self.build_new_workout_tab()
        self.build_exercise_tab()

        self.status_var = tk.StringVar(value="Connected to the Fit Tracker API")
        ttk.Label(
            self.root,
            textvariable=self.status_var,
            style="Status.TLabel",
            padding=(15, 5),
        ).pack(fill="x")

        self.load_history()
        self.load_exercise_dictionary()

    def disconnect(self):
        self.api = None
        self.exercises = []
        self.pending_exercises = []
        self.show_connection_dialog()

    def get_user_id(self):
        try:
            user_id = int(self.user_id_var.get())
            if user_id <= 0:
                raise ValueError
            return user_id
        except ValueError as error:
            raise ApiError("User ID must be a positive whole number.") from error

    def build_history_tab(self):
        toolbar = ttk.Frame(self.history_tab)
        toolbar.pack(fill="x", pady=(0, 10))

        ttk.Label(
            toolbar, text="Workout History", style="Heading.TLabel"
        ).pack(side="left")

        ttk.Button(
            toolbar, text="Refresh", command=self.load_history
        ).pack(side="right")

        columns = ("date", "notes", "volume", "exercises")
        self.history_tree = ttk.Treeview(
            self.history_tab, columns=columns, show="headings"
        )

        self.history_tree.heading("date", text="Date")
        self.history_tree.heading("notes", text="Notes")
        self.history_tree.heading("volume", text="Total volume (kg)")
        self.history_tree.heading("exercises", text="Exercises")

        self.history_tree.column("date", width=110, anchor="center")
        self.history_tree.column("notes", width=200)
        self.history_tree.column("volume", width=140, anchor="e")
        self.history_tree.column("exercises", width=430)

        scrollbar = ttk.Scrollbar(
            self.history_tab,
            orient="vertical",
            command=self.history_tree.yview,
        )
        self.history_tree.configure(yscrollcommand=scrollbar.set)

        self.history_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def load_history(self):
        if not self.api:
            return

        try:
            user_id = self.get_user_id()
            workouts = self.api.get_workouts(user_id)
        except ApiError as error:
            messagebox.showerror("Workout history", str(error))
            return

        for item in self.history_tree.get_children():
            self.history_tree.delete(item)

        for workout in workouts:
            exercise_text = ", ".join(
                (
                    f"{entry['name']}: {entry['sets']} × "
                    f"{entry['reps']} @ {entry['weight_kg']} kg"
                )
                for entry in workout["exercises"]
            )

            self.history_tree.insert(
                "",
                "end",
                values=(
                    workout["workout_date"],
                    workout["notes"] or "",
                    workout["total_volume_kg"],
                    exercise_text,
                ),
            )

        self.status_var.set(f"Loaded {len(workouts)} workout session(s)")

    def build_new_workout_tab(self):
        form = ttk.Frame(self.new_workout_tab)
        form.pack(fill="x")

        ttk.Label(form, text="New Workout", style="Heading.TLabel").grid(
            row=0, column=0, columnspan=4, sticky="w", pady=(0, 15)
        )

        ttk.Label(form, text="Date:").grid(row=1, column=0, sticky="w", pady=5)
        self.workout_date_var = tk.StringVar(value=date.today().isoformat())
        ttk.Entry(form, textvariable=self.workout_date_var, width=15).grid(
            row=1, column=1, sticky="w", pady=5
        )

        ttk.Label(form, text="Notes:").grid(
            row=1, column=2, sticky="w", padx=(25, 5), pady=5
        )
        self.notes_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.notes_var, width=40).grid(
            row=1, column=3, sticky="ew", pady=5
        )

        ttk.Separator(form).grid(
            row=2, column=0, columnspan=4, sticky="ew", pady=15
        )

        ttk.Label(form, text="Exercise:").grid(row=3, column=0, sticky="w", pady=5)
        self.exercise_var = tk.StringVar()
        self.exercise_combo = ttk.Combobox(
            form,
            textvariable=self.exercise_var,
            state="readonly",
            width=28,
        )
        self.exercise_combo["values"] = [
            f"{exercise['exercise_id']} - {exercise['name']}"
            for exercise in self.exercises
        ]
        if self.exercises:
            self.exercise_combo.current(0)
        self.exercise_combo.grid(row=3, column=1, sticky="w", pady=5)

        ttk.Label(form, text="Sets:").grid(
            row=3, column=2, sticky="e", padx=(10, 5)
        )
        self.sets_var = tk.StringVar(value="3")
        ttk.Entry(form, textvariable=self.sets_var, width=8).grid(
            row=3, column=3, sticky="w"
        )

        ttk.Label(form, text="Reps:").grid(row=4, column=0, sticky="w", pady=5)
        self.reps_var = tk.StringVar(value="8")
        ttk.Entry(form, textvariable=self.reps_var, width=8).grid(
            row=4, column=1, sticky="w", pady=5
        )

        ttk.Label(form, text="Weight (kg):").grid(
            row=4, column=2, sticky="e", padx=(10, 5)
        )
        self.weight_var = tk.StringVar(value="0")
        ttk.Entry(form, textvariable=self.weight_var, width=10).grid(
            row=4, column=3, sticky="w"
        )

        ttk.Button(
            form,
            text="Add Exercise to Session",
            command=self.add_pending_exercise,
        ).grid(row=5, column=0, columnspan=4, pady=15)

        pending_columns = ("exercise", "sets", "reps", "weight")
        self.pending_tree = ttk.Treeview(
            self.new_workout_tab,
            columns=pending_columns,
            show="headings",
            height=8,
        )

        self.pending_tree.heading("exercise", text="Exercise")
        self.pending_tree.heading("sets", text="Sets")
        self.pending_tree.heading("reps", text="Reps")
        self.pending_tree.heading("weight", text="Weight (kg)")

        self.pending_tree.column("exercise", width=350)
        self.pending_tree.column("sets", width=80, anchor="center")
        self.pending_tree.column("reps", width=80, anchor="center")
        self.pending_tree.column("weight", width=120, anchor="e")

        self.pending_tree.pack(fill="both", expand=True, pady=10)

        buttons = ttk.Frame(self.new_workout_tab)
        buttons.pack(fill="x")

        ttk.Button(
            buttons,
            text="Remove Selected",
            command=self.remove_pending_exercise,
        ).pack(side="left")

        ttk.Button(
            buttons,
            text="Save Workout",
            command=self.save_workout,
        ).pack(side="right")

    def add_pending_exercise(self):
        try:
            selection = self.exercise_var.get()
            if not selection:
                raise ValueError("Select an exercise.")

            exercise_id = int(selection.split(" - ", 1)[0])
            exercise = next(
                item
                for item in self.exercises
                if item["exercise_id"] == exercise_id
            )

            if any(
                item["exercise_id"] == exercise_id
                for item in self.pending_exercises
            ):
                raise ValueError("This exercise is already in the session.")

            sets = int(self.sets_var.get())
            reps = int(self.reps_var.get())
            weight = Decimal(self.weight_var.get())

            if sets <= 0 or reps <= 0 or weight < 0:
                raise ValueError(
                    "Sets and reps must be positive and weight cannot be negative."
                )

        except (ValueError, InvalidOperation, StopIteration) as error:
            messagebox.showerror("Invalid exercise", str(error))
            return

        entry = {
            "exercise_id": exercise_id,
            "name": exercise["name"],
            "sets": sets,
            "reps": reps,
            "weight": weight,
        }
        self.pending_exercises.append(entry)

        self.pending_tree.insert(
            "",
            "end",
            iid=str(exercise_id),
            values=(exercise["name"], sets, reps, f"{weight:.2f}"),
        )

    def remove_pending_exercise(self):
        selected = self.pending_tree.selection()
        if not selected:
            return

        exercise_id = int(selected[0])
        self.pending_exercises = [
            item
            for item in self.pending_exercises
            if item["exercise_id"] != exercise_id
        ]
        self.pending_tree.delete(selected[0])

    def save_workout(self):
        if not self.pending_exercises:
            messagebox.showerror(
                "Workout",
                "Add at least one exercise before saving the workout.",
            )
            return

        try:
            user_id = self.get_user_id()
            workout_date = self.workout_date_var.get().strip()
            date.fromisoformat(workout_date)

            workout = self.api.create_workout(
                user_id=user_id,
                workout_date=workout_date,
                notes=self.notes_var.get().strip(),
            )

            for entry in self.pending_exercises:
                self.api.add_exercise(
                    workout_id=workout["workout_id"],
                    exercise_id=entry["exercise_id"],
                    sets=entry["sets"],
                    reps=entry["reps"],
                    weight=entry["weight"],
                )

        except (ApiError, ValueError) as error:
            messagebox.showerror("Could not save workout", str(error))
            return

        messagebox.showinfo(
            "Workout saved",
            f"Workout {workout['workout_id']} was saved successfully.",
        )

        self.pending_exercises.clear()
        for item in self.pending_tree.get_children():
            self.pending_tree.delete(item)

        self.notes_var.set("")
        self.load_history()
        self.notebook.select(self.history_tab)

    def build_exercise_tab(self):
        ttk.Label(
            self.exercise_tab,
            text="Exercise Dictionary",
            style="Heading.TLabel",
        ).pack(anchor="w", pady=(0, 10))

        columns = ("id", "name", "muscle", "description")
        self.exercise_tree = ttk.Treeview(
            self.exercise_tab, columns=columns, show="headings"
        )

        self.exercise_tree.heading("id", text="ID")
        self.exercise_tree.heading("name", text="Exercise")
        self.exercise_tree.heading("muscle", text="Target muscle")
        self.exercise_tree.heading("description", text="Description")

        self.exercise_tree.column("id", width=60, anchor="center")
        self.exercise_tree.column("name", width=180)
        self.exercise_tree.column("muscle", width=150)
        self.exercise_tree.column("description", width=450)

        self.exercise_tree.pack(fill="both", expand=True)

    def load_exercise_dictionary(self):
        for item in self.exercise_tree.get_children():
            self.exercise_tree.delete(item)

        for exercise in self.exercises:
            self.exercise_tree.insert(
                "",
                "end",
                values=(
                    exercise["exercise_id"],
                    exercise["name"],
                    exercise["target_muscle"],
                    exercise["description"] or "",
                ),
            )


def main():
    root = tk.Tk()
    FitTrackerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
