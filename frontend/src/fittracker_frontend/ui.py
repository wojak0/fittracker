from __future__ import annotations

import queue
import threading
import tkinter as tk
from collections.abc import Callable
from datetime import date
from decimal import Decimal, InvalidOperation
from tkinter import messagebox, ttk
from typing import Any

from fittracker_frontend.api import ApiClient, ApiError


class PartialWorkoutError(ApiError):
    """Raised when a workout exists but one of its exercises failed to save."""


class FitTrackerApp(ttk.Frame):
    def __init__(
        self,
        master: tk.Tk,
        api: ApiClient,
        exercises: list[dict[str, Any]],
        on_disconnect: Callable[[], None],
    ) -> None:
        super().__init__(master, padding=0)

        self.root = master
        self.api = api
        self.exercises = exercises
        self.pending_exercises: list[dict[str, Any]] = []
        self.on_disconnect = on_disconnect
        self._alive = True
        self._background_results: queue.Queue[tuple[Any, ...]] = queue.Queue()

        self.root.title("Fit Tracker")
        self.root.geometry("950x650")
        self.root.minsize(800, 550)
        self.pack(fill=tk.BOTH, expand=True)

        self._configure_styles()
        self._build_main_screen()
        self._poll_background_results()

        self.load_history()
        self.load_exercise_dictionary()

    def _configure_styles(self) -> None:
        style = ttk.Style()
        style.configure("Title.TLabel", font=("Sans", 18, "bold"))
        style.configure("Heading.TLabel", font=("Sans", 12, "bold"))
        style.configure("Status.TLabel", foreground="#245c2a")

    def _build_main_screen(self) -> None:
        header = ttk.Frame(self, padding=(15, 10))
        header.pack(fill=tk.X)

        ttk.Label(header, text="Fit Tracker", style="Title.TLabel").pack(
            side=tk.LEFT
        )

        ttk.Label(header, text="User ID:").pack(side=tk.LEFT, padx=(30, 5))
        self.user_id_var = tk.StringVar(value="1")
        ttk.Entry(header, textvariable=self.user_id_var, width=6).pack(side=tk.LEFT)

        ttk.Button(header, text="Disconnect", command=self._disconnect).pack(
            side=tk.RIGHT
        )

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 10))

        self.history_tab = ttk.Frame(self.notebook, padding=15)
        self.new_workout_tab = ttk.Frame(self.notebook, padding=15)
        self.exercise_tab = ttk.Frame(self.notebook, padding=15)

        self.notebook.add(self.history_tab, text="Workout History")
        self.notebook.add(self.new_workout_tab, text="Log Workout")
        self.notebook.add(self.exercise_tab, text="Exercise Dictionary")

        self._build_history_tab()
        self._build_new_workout_tab()
        self._build_exercise_tab()

        self.status_var = tk.StringVar(
            value="API reachable; the API key is checked on the first write."
        )
        ttk.Label(
            self,
            textvariable=self.status_var,
            style="Status.TLabel",
            padding=(15, 5),
        ).pack(fill=tk.X)

    def _disconnect(self) -> None:
        self._alive = False
        self.on_disconnect()

    def destroy(self) -> None:
        self._alive = False
        super().destroy()

    def _get_user_id(self) -> int:
        try:
            user_id = int(self.user_id_var.get())
        except ValueError as error:
            raise ApiError("User ID must be a positive whole number.") from error

        if user_id <= 0:
            raise ApiError("User ID must be a positive whole number.")

        return user_id

    def _run_background(
        self,
        task: Callable[[], Any],
        on_success: Callable[[Any], None],
        *,
        error_title: str,
        button: ttk.Button | None = None,
        working_message: str = "Working...",
    ) -> None:
        if button is not None:
            button.state(["disabled"])
        self.status_var.set(working_message)

        def worker() -> None:
            try:
                result = task()
            except Exception as error:  # passed to the Tk thread for display
                self._background_results.put(
                    ("error", error, error_title, button)
                )
            else:
                self._background_results.put(
                    ("success", result, on_success, button)
                )

        threading.Thread(target=worker, daemon=True).start()

    def _poll_background_results(self) -> None:
        if not self._alive:
            return

        while True:
            try:
                item = self._background_results.get_nowait()
            except queue.Empty:
                break

            outcome = item[0]
            if outcome == "success":
                _, result, callback, button = item
                if button is not None:
                    button.state(["!disabled"])
                callback(result)
            else:
                _, error, title, button = item
                if button is not None:
                    button.state(["!disabled"])
                self.status_var.set("Operation failed")
                messagebox.showerror(title, str(error), parent=self.root)

        self.after(100, self._poll_background_results)

    # ------------------------------------------------------------------
    # Workout history
    # ------------------------------------------------------------------

    def _build_history_tab(self) -> None:
        toolbar = ttk.Frame(self.history_tab)
        toolbar.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(
            toolbar,
            text="Workout History",
            style="Heading.TLabel",
        ).pack(side=tk.LEFT)

        self.history_refresh_button = ttk.Button(
            toolbar,
            text="Refresh",
            command=self.load_history,
        )
        self.history_refresh_button.pack(side=tk.RIGHT)

        table_frame = ttk.Frame(self.history_tab)
        table_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("date", "notes", "volume", "exercises")
        self.history_tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
        )

        self.history_tree.heading("date", text="Date")
        self.history_tree.heading("notes", text="Notes")
        self.history_tree.heading("volume", text="Total volume (kg)")
        self.history_tree.heading("exercises", text="Exercises")

        self.history_tree.column("date", width=110, anchor=tk.CENTER)
        self.history_tree.column("notes", width=200)
        self.history_tree.column("volume", width=140, anchor=tk.E)
        self.history_tree.column("exercises", width=430)

        scrollbar = ttk.Scrollbar(
            table_frame,
            orient=tk.VERTICAL,
            command=self.history_tree.yview,
        )
        self.history_tree.configure(yscrollcommand=scrollbar.set)

        self.history_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def load_history(self) -> None:
        try:
            user_id = self._get_user_id()
        except ApiError as error:
            messagebox.showerror("Workout history", str(error), parent=self.root)
            return

        self._run_background(
            lambda: self.api.get_workouts(user_id),
            self._display_history,
            error_title="Workout history",
            button=self.history_refresh_button,
            working_message="Loading workout history...",
        )

    def _display_history(self, workouts: list[dict[str, Any]]) -> None:
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
                tk.END,
                values=(
                    workout["workout_date"],
                    workout["notes"] or "",
                    workout["total_volume_kg"],
                    exercise_text,
                ),
            )

        self.status_var.set(f"Loaded {len(workouts)} workout session(s)")

    # ------------------------------------------------------------------
    # Log workout
    # ------------------------------------------------------------------

    def _build_new_workout_tab(self) -> None:
        form = ttk.Frame(self.new_workout_tab)
        form.pack(fill=tk.X)
        form.columnconfigure(3, weight=1)

        ttk.Label(form, text="New Workout", style="Heading.TLabel").grid(
            row=0,
            column=0,
            columnspan=4,
            sticky=tk.W,
            pady=(0, 15),
        )

        ttk.Label(form, text="Date:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.workout_date_var = tk.StringVar(value=date.today().isoformat())
        ttk.Entry(form, textvariable=self.workout_date_var, width=15).grid(
            row=1,
            column=1,
            sticky=tk.W,
            pady=5,
        )

        ttk.Label(form, text="Notes:").grid(
            row=1,
            column=2,
            sticky=tk.W,
            padx=(25, 5),
            pady=5,
        )
        self.notes_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.notes_var, width=40).grid(
            row=1,
            column=3,
            sticky=tk.EW,
            pady=5,
        )

        ttk.Separator(form).grid(
            row=2,
            column=0,
            columnspan=4,
            sticky=tk.EW,
            pady=15,
        )

        ttk.Label(form, text="Exercise:").grid(
            row=3,
            column=0,
            sticky=tk.W,
            pady=5,
        )
        self.exercise_var = tk.StringVar()
        self.exercise_combo = ttk.Combobox(
            form,
            textvariable=self.exercise_var,
            state="readonly",
            width=28,
        )
        self._update_exercise_combo()
        self.exercise_combo.grid(row=3, column=1, sticky=tk.W, pady=5)

        ttk.Label(form, text="Sets:").grid(
            row=3,
            column=2,
            sticky=tk.E,
            padx=(10, 5),
        )
        self.sets_var = tk.StringVar(value="3")
        ttk.Entry(form, textvariable=self.sets_var, width=8).grid(
            row=3,
            column=3,
            sticky=tk.W,
        )

        ttk.Label(form, text="Reps:").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.reps_var = tk.StringVar(value="8")
        ttk.Entry(form, textvariable=self.reps_var, width=8).grid(
            row=4,
            column=1,
            sticky=tk.W,
            pady=5,
        )

        ttk.Label(form, text="Weight (kg):").grid(
            row=4,
            column=2,
            sticky=tk.E,
            padx=(10, 5),
        )
        self.weight_var = tk.StringVar(value="0")
        ttk.Entry(form, textvariable=self.weight_var, width=10).grid(
            row=4,
            column=3,
            sticky=tk.W,
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
        self.pending_tree.column("sets", width=80, anchor=tk.CENTER)
        self.pending_tree.column("reps", width=80, anchor=tk.CENTER)
        self.pending_tree.column("weight", width=120, anchor=tk.E)

        self.pending_tree.pack(fill=tk.BOTH, expand=True, pady=10)

        buttons = ttk.Frame(self.new_workout_tab)
        buttons.pack(fill=tk.X)

        ttk.Button(
            buttons,
            text="Remove Selected",
            command=self.remove_pending_exercise,
        ).pack(side=tk.LEFT)

        self.save_button = ttk.Button(
            buttons,
            text="Save Workout",
            command=self.save_workout,
        )
        self.save_button.pack(side=tk.RIGHT)

    def _update_exercise_combo(self) -> None:
        values = [
            f"{exercise['exercise_id']} - {exercise['name']}"
            for exercise in self.exercises
        ]
        self.exercise_combo["values"] = values
        if values:
            self.exercise_combo.current(0)
        else:
            self.exercise_var.set("")

    def add_pending_exercise(self) -> None:
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

            if not 1 <= sets <= 100:
                raise ValueError("Sets must be between 1 and 100.")
            if not 1 <= reps <= 1000:
                raise ValueError("Reps must be between 1 and 1000.")
            if not weight.is_finite() or weight < 0:
                raise ValueError("Weight must be a non-negative number.")
            if weight > Decimal("9999.99"):
                raise ValueError("Weight cannot exceed 9999.99 kg.")

            rounded_weight = weight.quantize(Decimal("0.01"))
            if weight != rounded_weight:
                raise ValueError("Weight can contain at most two decimal places.")

        except (ValueError, InvalidOperation, StopIteration) as error:
            messagebox.showerror("Invalid exercise", str(error), parent=self.root)
            return

        entry = {
            "exercise_id": exercise_id,
            "name": exercise["name"],
            "sets": sets,
            "reps": reps,
            "weight": rounded_weight,
        }
        self.pending_exercises.append(entry)

        self.pending_tree.insert(
            "",
            tk.END,
            iid=str(exercise_id),
            values=(exercise["name"], sets, reps, f"{rounded_weight:.2f}"),
        )

    def remove_pending_exercise(self) -> None:
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

    def save_workout(self) -> None:
        if not self.pending_exercises:
            messagebox.showerror(
                "Workout",
                "Add at least one exercise before saving the workout.",
                parent=self.root,
            )
            return

        try:
            user_id = self._get_user_id()
            workout_date = self.workout_date_var.get().strip()
            date.fromisoformat(workout_date)
            notes = self.notes_var.get().strip()
            if len(notes) > 2000:
                raise ValueError("Notes cannot exceed 2000 characters.")
        except (ApiError, ValueError) as error:
            messagebox.showerror(
                "Could not save workout",
                str(error),
                parent=self.root,
            )
            return

        pending_entries = [dict(entry) for entry in self.pending_exercises]

        def task() -> dict[str, Any]:
            workout = self.api.create_workout(
                user_id=user_id,
                workout_date=workout_date,
                notes=notes,
            )

            try:
                for entry in pending_entries:
                    self.api.add_exercise(
                        workout_id=workout["workout_id"],
                        exercise_id=entry["exercise_id"],
                        sets=entry["sets"],
                        reps=entry["reps"],
                        weight=entry["weight"],
                    )
            except ApiError as error:
                raise PartialWorkoutError(
                    f"Workout {workout['workout_id']} was created, but not all "
                    "exercises could be saved. Review the workout history. "
                    f"Original error: {error}"
                ) from error

            return workout

        self._run_background(
            task,
            self._workout_saved,
            error_title="Could not save workout",
            button=self.save_button,
            working_message="Saving workout...",
        )

    def _workout_saved(self, workout: dict[str, Any]) -> None:
        messagebox.showinfo(
            "Workout saved",
            f"Workout {workout['workout_id']} was saved successfully.",
            parent=self.root,
        )

        self.pending_exercises.clear()
        for item in self.pending_tree.get_children():
            self.pending_tree.delete(item)

        self.notes_var.set("")
        self.status_var.set(f"Workout {workout['workout_id']} saved")
        self.load_history()
        self.notebook.select(self.history_tab)

    # ------------------------------------------------------------------
    # Exercise dictionary
    # ------------------------------------------------------------------

    def _build_exercise_tab(self) -> None:
        toolbar = ttk.Frame(self.exercise_tab)
        toolbar.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(
            toolbar,
            text="Exercise Dictionary",
            style="Heading.TLabel",
        ).pack(side=tk.LEFT)

        self.exercise_refresh_button = ttk.Button(
            toolbar,
            text="Refresh",
            command=self.refresh_exercises,
        )
        self.exercise_refresh_button.pack(side=tk.RIGHT)

        table_frame = ttk.Frame(self.exercise_tab)
        table_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("id", "name", "muscle", "description")
        self.exercise_tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
        )

        self.exercise_tree.heading("id", text="ID")
        self.exercise_tree.heading("name", text="Exercise")
        self.exercise_tree.heading("muscle", text="Target muscle")
        self.exercise_tree.heading("description", text="Description")

        self.exercise_tree.column("id", width=60, anchor=tk.CENTER)
        self.exercise_tree.column("name", width=180)
        self.exercise_tree.column("muscle", width=150)
        self.exercise_tree.column("description", width=450)

        scrollbar = ttk.Scrollbar(
            table_frame,
            orient=tk.VERTICAL,
            command=self.exercise_tree.yview,
        )
        self.exercise_tree.configure(yscrollcommand=scrollbar.set)

        self.exercise_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def load_exercise_dictionary(self) -> None:
        for item in self.exercise_tree.get_children():
            self.exercise_tree.delete(item)

        for exercise in self.exercises:
            self.exercise_tree.insert(
                "",
                tk.END,
                values=(
                    exercise["exercise_id"],
                    exercise["name"],
                    exercise["target_muscle"],
                    exercise["description"] or "",
                ),
            )

    def refresh_exercises(self) -> None:
        self._run_background(
            self.api.get_exercises,
            self._exercises_refreshed,
            error_title="Exercise dictionary",
            button=self.exercise_refresh_button,
            working_message="Refreshing exercise dictionary...",
        )

    def _exercises_refreshed(
        self,
        exercises: list[dict[str, Any]],
    ) -> None:
        self.exercises = exercises
        self._update_exercise_combo()
        self.load_exercise_dictionary()
        self.status_var.set(f"Loaded {len(exercises)} exercise(s)")
