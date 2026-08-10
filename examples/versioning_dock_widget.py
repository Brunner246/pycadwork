"""A PyQt6 dock widget that drives :class:`ModelVersioning` — run inside cadwork.

A GUI companion to the script-style versioning examples
(:mod:`examples.versioning_in_cadwork`, :mod:`examples.versioning_branch_workflow`).
Instead of a one-shot script it adds a **dock widget to cadwork's own main
window** so you can commit / branch / push / pull / revert the live model
interactively, the way you would in a desktop git client.

It is built **MVVM**, with one strict rule per layer:

* **Model** — :class:`pycadwork.versioning.ModelVersioning`. The whole domain. It
  already owns the model⇄snapshot⇄git pipeline; the GUI adds nothing to it.
* **ViewModel** — :class:`VersioningViewModel` (a ``QObject``). The *only* code
  that calls the model. It exposes commands (``commit``, ``push``, ``checkout``…)
  as plain methods and publishes state back through Qt signals
  (``branch_changed``, ``history_changed``, ``busy_changed``, ``notified``…). It
  imports **no widgets** — so it is unit-testable with a fake ``ModelVersioning``
  and no event loop.
* **View** — :class:`VersioningDockWidget` (a ``QDockWidget``). Pure wiring: it
  builds widgets, forwards their signals to ViewModel commands, and renders
  ViewModel signals back into the UI. It never touches the model directly.

How it hosts itself in cadwork's window:

    hwnd = utility_controller.get_3d_hwnd()        # cadwork's native window handle
    parent = QWidget.find(voidptr(hwnd)).window()  # the QMainWindow behind it
    parent.addDockWidget(area, dock)               # cadwork's window adopts the dock

cadwork's UI *is* a Qt application running in this same process, so the handle
``utility_controller.get_3d_hwnd()`` returns is the ``WId`` of a live widget.
:meth:`QWidget.find` maps that handle straight back to the Qt widget, and
``.window()`` walks up to cadwork's main ``QMainWindow``. That window is injected
as the dock's ``parent``, so the dock — and every dialog it raises — belongs to
cadwork's window. Docking happens on the dock's first ``showEvent``, so the dock
is always docked (never left floating) the moment it becomes visible. The example
runs in the **already-running** Qt application cadwork provides — it never creates
a ``QApplication`` or calls ``exec()``.

No server required: **Add…** next to the remote picker wires a remote from a
local folder or a network share (initialized as a bare repo for you) so
``push`` / ``pull`` work entirely offline over the filesystem — or from an
ordinary server URL when you have one.

⚠️ **Threading.** cadwork's API is not thread-safe and ``commit`` / ``revert``
read and write the *live model*, so every operation here runs on the GUI thread.
A ``push`` / ``pull`` therefore briefly **blocks the cadwork UI** (a wait cursor
is shown) — fast against a local remote, longer against a network one. A
production plugin would move the *pure-git* operations — and only those, never
the model reads/writes — onto a ``QThread`` worker; that is left out here so the
MVVM wiring stays the point.

How to run it inside cadwork (see :mod:`examples.versioning_in_cadwork` for the
full setup): provision pycadwork into cadwork's interpreter, add the git backend
(``pip install 'pycadwork[git]'``) **and PyQt6** (``pip install PyQt6``), put a
``git`` executable on PATH, **save your model**, then call :func:`main` from the
API menu.
"""

from __future__ import annotations

try:
    import pycadwork  # noqa: F401  (import-only check the runtime install is in place)
    from pycadwork import Document
    from pycadwork.versioning import (
        CommitInfo,
        ModelVersioning,
        RepoStatus,
        RepositoryError,
        SmartSwitchReport,
        SyncPlan,
        is_git_available,
        is_lfs_available,
    )
except (
    ImportError
) as exc:  # pragma: no cover - guidance for an un-provisioned interpreter
    raise ImportError(
        "pycadwork is not importable from cadwork's interpreter. From the "
        "pycadwork checkout, run scripts\\Install-PycadworkRuntime.ps1 to link the "
        "package and install its dependencies into cadwork's site-packages, then "
        "install the git backend with: pip install 'pycadwork[git]'."
    ) from exc

try:
    from PyQt6.QtCore import QObject, Qt, pyqtSignal
    from PyQt6.QtGui import QFont
    from PyQt6.QtWidgets import (
        QApplication,
        QComboBox,
        QDialog,
        QDialogButtonBox,
        QDockWidget,
        QFileDialog,
        QFormLayout,
        QHBoxLayout,
        QInputDialog,
        QLabel,
        QLineEdit,
        QListWidget,
        QMainWindow,
        QMessageBox,
        QPlainTextEdit,
        QPushButton,
        QVBoxLayout,
        QWidget,
    )
except ImportError as exc:  # pragma: no cover - PyQt6 is not a pycadwork dependency
    raise ImportError(
        "PyQt6 is not available in this interpreter. Install it into cadwork's "
        "Python (pip install PyQt6) to use the versioning dock widget."
    ) from exc


def _report_summary(report: SmartSwitchReport | object) -> str:
    """A one-line human summary of a reload/switch report, either strategy.

    ``SmartSwitchReport`` (the default ``strategy="smart"``) reports the actual
    delta; the legacy ``ReloadReport`` (``strategy="full"``) only ever reports a
    flat imported count, since a full reimport touches everything regardless.
    """
    if isinstance(report, SmartSwitchReport):
        return (
            f"{report.unchanged} unchanged, {report.added} added, "
            f"{report.removed} removed ({report.total} elements total)"
        )
    return f"{report.imported} elements imported (full reimport)"


# --------------------------------------------------------------------------- #
# ViewModel — the only layer that talks to ModelVersioning. No widgets here.   #
# --------------------------------------------------------------------------- #
class VersioningViewModel(QObject):
    """Commands + observable state over a :class:`ModelVersioning`.

    Every command is a plain method that catches :class:`RepositoryError`, emits
    a human-readable :attr:`notified` message, and (on success) re-publishes the
    repository state through the typed signals below. The View subscribes to the
    signals and calls the commands — it never reaches the model itself.
    """

    #: The checked-out branch name changed.
    branch_changed = pyqtSignal(str)
    #: The full local-branch list changed — ``tuple[str, ...]``.
    branches_changed = pyqtSignal(tuple)
    #: The configured-remote list changed — ``tuple[str, ...]``.
    remotes_changed = pyqtSignal(tuple)
    #: Recent history changed — ``tuple[CommitInfo, ...]``, newest first.
    history_changed = pyqtSignal(tuple)
    #: The working-tree :class:`RepoStatus` changed (emitted as ``object``).
    status_changed = pyqtSignal(object)
    #: An operation started/finished — the View disables controls while ``True``.
    busy_changed = pyqtSignal(bool)
    #: A user-facing result: ``(message, is_error)``.
    notified = pyqtSignal(str, bool)

    def __init__(self, versioning: ModelVersioning, *, history_limit: int = 30) -> None:
        super().__init__()
        self._vcs = versioning
        self._history_limit = history_limit

    # ---- read-only state the View may query directly on demand ----

    @property
    def current_branch(self) -> str:
        return self._vcs.current_branch()

    @property
    def branches(self) -> tuple[str, ...]:
        return self._vcs.branches()

    # ---- commands (model → repo) ----

    def commit(self, message: str) -> None:
        """Capture the live model and commit it on the current branch."""
        message = message.strip()
        if not message:
            self.notified.emit("Enter a commit message first.", True)
            return
        ok, report = self._run("Commit", lambda: self._vcs.commit(message))
        if not ok:
            return
        if report.nothing_to_commit:
            self.notified.emit("Nothing to commit — the model matches HEAD.", False)
        else:
            self.notified.emit(
                f"Committed {report.commit.sha[:8]} "
                f"({report.files_changed} files changed).",
                False,
            )

    def reload_model(self, *, strategy: str = "smart") -> None:
        """Load the checked-out version's committed ``.3dc`` into the live model.

        Both strategies are full-fidelity (``ModelVersioning.reload_model``) —
        even a *moved* element comes back exactly, unlike the legacy JSON
        write-back. The default ``strategy="smart"`` reconciles by content
        fingerprint: unchanged elements keep their existing cadwork id/GUID.
        ``strategy="full"`` is the legacy escape hatch — every element gets a
        fresh id/GUID. The View confirms before calling either (both can
        replace parts of the live model).
        """
        ok, report = self._run(
            "Load model", lambda: self._vcs.reload_model(strategy=strategy)
        )
        if ok:
            self.notified.emit(
                f"Loaded {self._safe_branch()} into the model — "
                f"{_report_summary(report)}.",
                False,
            )

    # ---- commands (git + model) ----

    def checkout(self, branch: str, *, strategy: str = "smart") -> None:
        """Switch to ``branch`` *and* load its model — git checkout, fully.

        Uses ``ModelVersioning.switch_to`` so a branch pick lands the live model
        on that version in one step. The default ``strategy="smart"`` only
        touches the elements that actually differ; ``strategy="full"`` is the
        legacy full reimport. Either way the View confirms before this runs.
        """
        ok, report = self._run(
            "Switch", lambda: self._vcs.switch_to(branch, strategy=strategy)
        )
        if ok:
            self.notified.emit(
                f"Switched to {branch!r} — {_report_summary(report)}.",
                False,
            )

    def preview_switch(self, branch: str) -> SyncPlan | None:
        """Classify the live model against ``branch``'s committed snapshot.

        A true *pre-checkout* preview (``ModelVersioning.preview_switch``): it
        reads ``branch``'s JSONL straight out of git without switching any
        tracked files, so the View can show accurate counts in the confirmation
        dialog before anything happens. Returns ``None`` (with a notice
        emitted) if the preview itself fails.
        """
        ok, plan = self._run(
            "Preview switch", lambda: self._vcs.preview_switch(branch), refresh=False
        )
        return plan if ok else None

    def sync_status(self) -> SyncPlan | None:
        """Classify the live model against the checked-out version (no git).

        The smart-switch analogue of a diff preview for "Load model to
        version" — used by the View to show accurate counts before reverting.
        """
        ok, plan = self._run(
            "Sync status", lambda: self._vcs.sync_status(), refresh=False
        )
        return plan if ok else None

    def create_branch(self, name: str) -> None:
        name = name.strip()
        if not name:
            self.notified.emit("Enter a branch name.", True)
            return
        ok, _ = self._run("Create branch", lambda: self._vcs.create_branch(name))
        if ok:
            self.notified.emit(f"Created and checked out {name!r}.", False)

    def delete_branch(self, name: str) -> None:
        ok, _ = self._run("Delete branch", lambda: self._vcs.delete_branch(name))
        if ok:
            self.notified.emit(f"Deleted branch {name!r}.", False)

    def merge(self, ref: str) -> None:
        ok, _ = self._run("Merge", lambda: self._vcs.merge(ref))
        if ok:
            self.notified.emit(
                f"Merged {ref!r} into {self._safe_branch()}. Use “Load model to "
                "version” to bring the merged model into cadwork.",
                False,
            )

    def add_remote(self, name: str, location: str) -> None:
        """Configure a remote so push/pull have a target.

        ``location`` may be a server URL (wired verbatim) or a local filesystem
        path / UNC share — the latter is initialized as a bare repo via
        :meth:`ModelVersioning.ensure_local_remote`, so push/pull work offline with
        no server. The repository state is re-published, so the remote combo
        repopulates and the Push/Pull buttons enable themselves.
        """
        name = name.strip()
        location = location.strip()
        if not name or not location:
            self.notified.emit("Enter a remote name and a path or URL.", True)
            return
        if _is_remote_url(location):
            ok, _ = self._run(
                "Add remote", lambda: self._vcs.add_remote(name, location)
            )
        else:
            ok, _ = self._run(
                "Add remote", lambda: self._vcs.ensure_local_remote(location, name)
            )
        if ok:
            self.notified.emit(f"Remote {name!r} → {location}.", False)

    def push(self, remote: str) -> None:
        ok, _ = self._run("Push", lambda: self._vcs.push(remote))
        if ok:
            self.notified.emit(f"Pushed {self._safe_branch()} to {remote!r}.", False)

    def pull(self, remote: str) -> None:
        ok, _ = self._run("Pull", lambda: self._vcs.pull(remote))
        if ok:
            self.notified.emit(
                f"Pulled {remote!r} into {self._safe_branch()}. Use “Load model to "
                "version” to load it into the model.",
                False,
            )

    def working_diff(self) -> str | None:
        """The textual JSONL diff of the working tree vs HEAD (for the diff dialog)."""
        ok, text = self._run("Diff", lambda: self._vcs.diff(stat=False), refresh=False)
        return text if ok else None

    # ---- state publication ----

    def refresh(self) -> None:
        """Re-read the repository and emit every state signal (with the busy cursor)."""
        self.busy_changed.emit(True)
        try:
            self._publish()
        finally:
            self.busy_changed.emit(False)

    def _publish(self) -> None:
        try:
            branch = self._vcs.current_branch()
            branches = self._vcs.branches()
            remotes = self._vcs.remotes()
            history = self._vcs.log(max_count=self._history_limit)
            status = self._vcs.status()
        except RepositoryError as exc:
            self.notified.emit(f"Refresh failed: {exc}", True)
            return
        self.branch_changed.emit(branch)
        self.branches_changed.emit(branches)
        self.remotes_changed.emit(remotes)
        self.history_changed.emit(history)
        self.status_changed.emit(status)

    # ---- shared command runner ----

    def _run(self, label: str, func, *, refresh: bool = True) -> tuple[bool, object]:
        """Run ``func`` under the busy flag; surface RepositoryError as a notice.

        Returns ``(ok, result)``. On success the repository state is re-published
        so the View redraws branch/history/status from one place — unless
        ``refresh=False`` (a pure read, e.g. a diff, changes no state).
        """
        self.busy_changed.emit(True)
        ok, result = False, None
        try:
            result = func()
            ok = True
        except RepositoryError as exc:
            self.notified.emit(f"{label} failed: {exc}", True)
        finally:
            self.busy_changed.emit(False)
        if ok and refresh:
            self._publish()
        return ok, result

    def _safe_branch(self) -> str:
        try:
            return self._vcs.current_branch()
        except RepositoryError:
            return "?"


# --------------------------------------------------------------------------- #
# View — a QDockWidget. Wiring only: widgets ⇄ ViewModel signals/commands.     #
# --------------------------------------------------------------------------- #
class VersioningDockWidget(QDockWidget):
    """The dock UI. Forwards widget events to the ViewModel and renders its signals.

    cadwork's main :class:`QMainWindow` is injected as the dock's ``parent`` at
    construction; on its first ``showEvent`` the dock docks into that parent so
    it lands docked (never floating) the moment it becomes visible.
    """

    def __init__(
        self, view_model: VersioningViewModel, parent: QWidget | None = None
    ) -> None:
        super().__init__("Model Versioning", parent)
        self.setObjectName("PycadworkVersioningDock")
        self._vm = view_model
        self._host: QMainWindow | None = None  # set once we dock into cadwork's window
        self._build_ui()
        self._bind()
        self._vm.refresh()

    # ---- lifecycle: host the dock in cadwork's window ----

    def showEvent(self, event) -> None:  # noqa: N802 (Qt override name)
        """Dock into cadwork's main window the first time we become visible."""
        super().showEvent(event)
        self._dock_into_main_window()

    def _dock_into_main_window(self) -> None:
        """Dock into the injected cadwork QMainWindow and pin docked — runs once."""
        if self._host is not None:
            return  # already docked; addDockWidget() must not re-run
        host = self.parent()  # the cadwork main window injected at construction
        if not isinstance(host, QMainWindow):
            return  # no cadwork window (e.g. run outside cadwork) — stay floating
        self._host = host
        host.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self)
        self.setFloating(False)  # guarantee it lands docked, never as a floating window

    # ---- construction ----

    def _build_ui(self) -> None:
        root = QWidget(self)
        layout = QVBoxLayout(root)

        # Branch row: pick / new / delete / merge.
        self._branch_combo = QComboBox()
        self._new_branch_button = QPushButton("New…")
        self._delete_branch_button = QPushButton("Delete")
        self._merge_button = QPushButton("Merge…")
        branch_row = QHBoxLayout()
        branch_row.addWidget(QLabel("Branch:"))
        branch_row.addWidget(self._branch_combo, 1)
        branch_row.addWidget(self._new_branch_button)
        branch_row.addWidget(self._delete_branch_button)
        branch_row.addWidget(self._merge_button)
        layout.addLayout(branch_row)

        self._status_label = QLabel("—")
        layout.addWidget(self._status_label)

        # Commit box.
        self._message_edit = QPlainTextEdit()
        self._message_edit.setPlaceholderText("Commit message…")
        self._message_edit.setFixedHeight(60)
        layout.addWidget(self._message_edit)
        self._commit_button = QPushButton("Commit model")
        layout.addWidget(self._commit_button)

        # Remote row: pick / add / push / pull. "Add…" wires a remote (a local
        # folder/share for offline push-pull, or a server URL).
        self._remote_combo = QComboBox()
        self._add_remote_button = QPushButton("Add…")
        self._push_button = QPushButton("Push")
        self._pull_button = QPushButton("Pull")
        remote_row = QHBoxLayout()
        remote_row.addWidget(QLabel("Remote:"))
        remote_row.addWidget(self._remote_combo, 1)
        remote_row.addWidget(self._add_remote_button)
        remote_row.addWidget(self._push_button)
        remote_row.addWidget(self._pull_button)
        layout.addLayout(remote_row)

        # Load + diff + refresh row.
        self._revert_button = QPushButton("Load model to version")
        self._diff_button = QPushButton("Show diff")
        self._refresh_button = QPushButton("Refresh")
        action_row = QHBoxLayout()
        action_row.addWidget(self._revert_button)
        action_row.addWidget(self._diff_button)
        action_row.addWidget(self._refresh_button)
        layout.addLayout(action_row)

        # History.
        layout.addWidget(QLabel("History (newest first):"))
        self._history_list = QListWidget()
        self._history_list.setFont(_monospace())
        layout.addWidget(self._history_list, 1)

        self._message_label = QLabel("")
        self._message_label.setWordWrap(True)
        layout.addWidget(self._message_label)

        self.setWidget(root)

        #: Controls disabled while an operation runs (set via busy_changed).
        self._action_widgets = (
            self._branch_combo,
            self._new_branch_button,
            self._delete_branch_button,
            self._merge_button,
            self._commit_button,
            self._add_remote_button,
            self._push_button,
            self._pull_button,
            self._revert_button,
            self._diff_button,
            self._refresh_button,
        )

    def _bind(self) -> None:
        # ViewModel → View.
        self._vm.branch_changed.connect(self._on_branch)
        self._vm.branches_changed.connect(self._on_branches)
        self._vm.remotes_changed.connect(self._on_remotes)
        self._vm.history_changed.connect(self._on_history)
        self._vm.status_changed.connect(self._on_status)
        self._vm.busy_changed.connect(self._on_busy)
        self._vm.notified.connect(self._on_notified)

        # View → ViewModel. `textActivated` fires on *user* selection only, so
        # programmatic combo repopulation never triggers a switch (no re-entrancy).
        # A switch replaces the live model, so it is confirmed first.
        self._branch_combo.textActivated.connect(self._confirm_switch_branch)
        self._commit_button.clicked.connect(
            lambda: self._vm.commit(self._message_edit.toPlainText())
        )
        self._new_branch_button.clicked.connect(self._prompt_new_branch)
        self._delete_branch_button.clicked.connect(self._confirm_delete_branch)
        self._merge_button.clicked.connect(self._prompt_merge)
        self._add_remote_button.clicked.connect(self._prompt_add_remote)
        self._push_button.clicked.connect(
            lambda: self._vm.push(self._remote_combo.currentText())
        )
        self._pull_button.clicked.connect(
            lambda: self._vm.pull(self._remote_combo.currentText())
        )
        self._revert_button.clicked.connect(self._confirm_revert)
        self._diff_button.clicked.connect(self._show_diff)
        self._refresh_button.clicked.connect(self._vm.refresh)

    # ---- ViewModel → View slots ----

    def _on_branch(self, branch: str) -> None:
        combo = self._branch_combo
        combo.blockSignals(True)
        index = combo.findText(branch)
        if index >= 0:
            combo.setCurrentIndex(index)
        combo.blockSignals(False)

    def _on_branches(self, branches: tuple[str, ...]) -> None:
        combo = self._branch_combo
        combo.blockSignals(True)
        combo.clear()
        combo.addItems(branches)
        combo.blockSignals(False)

    def _on_remotes(self, remotes: tuple[str, ...]) -> None:
        combo = self._remote_combo
        current = combo.currentText()
        combo.blockSignals(True)
        combo.clear()
        combo.addItems(remotes)
        if current:
            keep = combo.findText(current)
            if keep >= 0:
                combo.setCurrentIndex(keep)
        combo.blockSignals(False)
        has_remote = bool(remotes)
        self._push_button.setEnabled(has_remote)
        self._pull_button.setEnabled(has_remote)

    def _on_history(self, history: tuple[CommitInfo, ...]) -> None:
        self._history_list.clear()
        for entry in history:
            self._history_list.addItem(
                f"{entry.sha[:8]}  {entry.committed_at}  {entry.message}"
            )

    def _on_status(self, status: RepoStatus) -> None:
        state = "modified" if status.is_dirty else "clean"
        self._status_label.setText(
            f"{status.branch} — {state} "
            f"(untracked {len(status.untracked)}, modified {len(status.modified)})"
        )

    def _on_busy(self, busy: bool) -> None:
        for widget in self._action_widgets:
            widget.setEnabled(not busy)
        if busy:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        else:
            QApplication.restoreOverrideCursor()
            # Re-apply the remote-dependent enablement undone by the blanket enable.
            has_remote = self._remote_combo.count() > 0
            self._push_button.setEnabled(has_remote)
            self._pull_button.setEnabled(has_remote)

    def _on_notified(self, message: str, is_error: bool) -> None:
        color = "#b00020" if is_error else "#33691e"
        self._message_label.setText(f"<span style='color:{color}'>{message}</span>")
        if is_error:
            QMessageBox.warning(self, "Model Versioning", message)

    # ---- View-side prompts (UI concerns; the VM stays widget-free) ----

    def _prompt_new_branch(self) -> None:
        name, ok = QInputDialog.getText(self, "New branch", "Branch name:")
        if ok and name:
            self._vm.create_branch(name)

    def _confirm_delete_branch(self) -> None:
        name = self._branch_combo.currentText()
        if not name:
            return
        confirmed = QMessageBox.question(
            self,
            "Delete branch",
            f"Delete local branch {name!r}?",
        )
        if confirmed == QMessageBox.StandardButton.Yes:
            self._vm.delete_branch(name)

    def _prompt_merge(self) -> None:
        others = [b for b in self._vm.branches if b != self._vm.current_branch]
        if not others:
            self._on_notified("No other branch to merge.", True)
            return
        ref, ok = QInputDialog.getItem(
            self,
            "Merge",
            f"Merge into {self._vm.current_branch!r}:",
            others,
            editable=False,
        )
        if ok and ref:
            self._vm.merge(ref)

    def _prompt_add_remote(self) -> None:
        result = _AddRemoteDialog.get_remote(self)
        if result is not None:
            name, location = result
            self._vm.add_remote(name, location)

    def _confirm_switch_branch(self, branch: str) -> None:
        """Preview a branch switch, confirm with accurate counts, then run it.

        A pre-checkout preview (``preview_switch``) shows exactly what a smart
        switch would touch *before* anything happens — unchanged elements keep
        their id, so the old blanket "unsaved edits will be lost" wording would
        overstate the risk. A secondary "Full reimport (legacy)" button is
        offered for anyone who wants a clean id/GUID reset instead. On decline,
        re-publish state so the combo snaps back to the still-current branch.
        """
        if branch == self._vm.current_branch:
            return
        plan = self._vm.preview_switch(branch)
        if plan is None:
            self._vm.refresh()
            return

        box = QMessageBox(self)
        box.setWindowTitle("Switch branch")
        box.setText(
            f"Switch to {branch!r}?\n\n"
            f"{len(plan.unchanged)} unchanged, {len(plan.missing)} to add, "
            f"{len(plan.stale)} to remove — unchanged elements keep their "
            "current id. Any unsaved edit to a changed or removed element "
            "will be lost."
        )
        smart_button = box.addButton(
            "Switch (smart)", QMessageBox.ButtonRole.AcceptRole
        )
        full_button = box.addButton(
            "Full reimport (legacy)", QMessageBox.ButtonRole.DestructiveRole
        )
        box.addButton(QMessageBox.StandardButton.Cancel)
        box.setDefaultButton(smart_button)
        box.exec()

        clicked = box.clickedButton()
        if clicked is smart_button:
            self._vm.checkout(branch, strategy="smart")
        elif clicked is full_button:
            self._vm.checkout(branch, strategy="full")
        else:
            self._vm.refresh()  # snap the combo back to the actual branch

    def _confirm_revert(self) -> None:
        """Preview reloading the checked-out version, confirm, then run it.

        Mirrors ``_confirm_switch_branch``: ``sync_status`` previews exactly
        what a smart reload would touch, and a secondary "Full reimport
        (legacy)" button is offered for a clean id/GUID reset.
        """
        plan = self._vm.sync_status()
        if plan is None:
            return

        box = QMessageBox(self)
        box.setWindowTitle("Load model to version")
        box.setText(
            "Reload the checked-out version into the live model?\n\n"
            f"{len(plan.unchanged)} unchanged, {len(plan.missing)} to add, "
            f"{len(plan.stale)} to remove — unchanged elements keep their "
            "current id."
        )
        smart_button = box.addButton("Load (smart)", QMessageBox.ButtonRole.AcceptRole)
        full_button = box.addButton(
            "Full reimport (legacy)", QMessageBox.ButtonRole.DestructiveRole
        )
        box.addButton(QMessageBox.StandardButton.Cancel)
        box.setDefaultButton(smart_button)
        box.exec()

        clicked = box.clickedButton()
        if clicked is smart_button:
            self._vm.reload_model(strategy="smart")
        elif clicked is full_button:
            self._vm.reload_model(strategy="full")

    def _show_diff(self) -> None:
        text = self._vm.working_diff()
        if text is None:
            return
        _TextDialog("Working tree diff (vs HEAD)", text or "(no changes)", self).exec()

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt override name)
        QApplication.restoreOverrideCursor()
        super().closeEvent(event)


class _TextDialog(QDialog):
    """A simple read-only monospace viewer for the JSONL diff."""

    def __init__(self, title: str, body: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(720, 480)
        layout = QVBoxLayout(self)
        view = QPlainTextEdit()
        view.setReadOnly(True)
        view.setFont(_monospace())
        view.setPlainText(body)
        layout.addWidget(view)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)


class _AddRemoteDialog(QDialog):
    """Collect a remote ``name`` + ``location`` — a local path/share or a server URL.

    A local destination gets a *Browse…* folder picker; the ViewModel turns it
    into a bare repo for offline push/pull. A URL is used as-is. The classmethod
    :meth:`get_remote` runs the dialog and returns ``(name, location)`` or ``None``
    if cancelled.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add remote")
        self._name_edit = QLineEdit("origin")
        self._location_edit = QLineEdit()
        self._location_edit.setPlaceholderText(
            r"local folder, \\share\model.git, or https://…"
        )
        browse_button = QPushButton("Browse…")
        browse_button.clicked.connect(self._browse)

        location_row = QHBoxLayout()
        location_row.addWidget(self._location_edit, 1)
        location_row.addWidget(browse_button)

        form = QFormLayout()
        form.addRow("Name:", self._name_edit)
        form.addRow("Location:", location_row)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(
            QLabel(
                "A local folder or network share works offline (no server) — it is "
                "initialized as a bare git repo."
            )
        )
        layout.addWidget(buttons)

    def _browse(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, "Choose a folder for the local remote"
        )
        if folder:
            self._location_edit.setText(folder)

    @classmethod
    def get_remote(cls, parent: QWidget | None = None) -> tuple[str, str] | None:
        dialog = cls(parent)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        return dialog._name_edit.text(), dialog._location_edit.text()


def _is_remote_url(location: str) -> bool:
    """True if ``location`` is a server/network git URL rather than a local path.

    URLs (``https://…``, ``ssh://…``, ``git://…``, ``file://…`` or scp-style
    ``git@host:repo.git``) are configured verbatim; everything else is treated as a
    local filesystem path (``C:\\repo.git``, ``\\\\nas\\share``, ``/srv/repo``) and
    initialized as a bare repo for offline push/pull. A Windows drive letter
    (``C:\\``) is not mistaken for a URL — it carries no ``@`` host.
    """
    if "://" in location:
        return True
    head = location.split("/", 1)[0]  # the part before any path separator
    return "@" in head and ":" in head


def _monospace() -> QFont:
    font = QFont("Consolas")
    font.setStyleHint(QFont.StyleHint.Monospace)
    return font


# --------------------------------------------------------------------------- #
# Hosting in cadwork's window + entry point.                                   #
# --------------------------------------------------------------------------- #
def _cadwork_main_window() -> QWidget | None:
    """Resolve cadwork's main window straight from its native window handle.

    cadwork's UI is itself a Qt application running in *this* process, so the
    handle returned by ``utility_controller.get_3d_hwnd()`` is the ``WId`` of a
    live widget. :meth:`QWidget.find` maps that handle directly back to the Qt
    widget that owns it — no scanning of top-level widgets needed. We then take
    its top-level :meth:`~QWidget.window` so callers always get cadwork's main
    window even if the handle belongs to a child view. Returns ``None`` outside
    cadwork, so the dock falls back to a normal floating window.
    """
    try:
        import utility_controller
        from PyQt6.sip import voidptr
    except ImportError:  # pragma: no cover - only available inside cadwork / PyQt6
        return None
    try:
        hwnd = int(utility_controller.get_3d_hwnd())
    except Exception:  # pragma: no cover - defensive: API shape varies across hosts
        return None
    if not hwnd:
        return None
    widget = QWidget.find(voidptr(hwnd))
    return widget.window() if widget is not None else None


def create_versioning_dock() -> VersioningDockWidget:
    """Build the Model/ViewModel/View stack and dock it into cadwork's window.

    Resolves cadwork's main window (via :func:`_cadwork_main_window`) and injects
    it as the dock's parent, so the dock — and every dialog it raises — belongs
    to cadwork's window. Returns the dock — **keep the reference alive** or Qt
    will garbage-collect and close it.
    """
    vcs = ModelVersioning.open()  # repo in the model's directory (init on first run)
    view_model = VersioningViewModel(vcs)
    dock = VersioningDockWidget(view_model, _cadwork_main_window())
    dock.show()  # showEvent docks it into cadwork's main window
    return dock


def _preflight() -> bool:
    """Check the environment is ready; print clear guidance and return False if not."""
    if not Document().file_path:
        print(
            "The model is unsaved. Save the 3d file (File ▸ Save) so it has a "
            "path on disk, then run this again."
        )
        return False
    if not is_git_available():
        print(
            "git is not available. Install the backend into cadwork's interpreter "
            "(pip install 'pycadwork[git]') and put a `git` executable on PATH."
        )
        return False
    if not is_lfs_available():
        print(
            "warning: git-lfs is not installed — the model file will be committed "
            "as an ordinary (large) git blob. Install git-lfs for efficient "
            "versioning."
        )
    return True


#: Module-level reference so the dock survives past :func:`main` (Qt would
#: otherwise garbage-collect a dock nothing holds onto).
_DOCK: VersioningDockWidget | None = None


def main() -> None:
    """Entry point — preflight, then dock the versioning panel in cadwork's window."""
    if not _preflight():
        return
    if QApplication.instance() is None:
        print(
            "No running QApplication found. This example attaches to cadwork's "
            "existing Qt application — run it from inside cadwork's API menu."
        )
        return
    global _DOCK
    try:
        _DOCK = create_versioning_dock()
    except RepositoryError as exc:
        print(f"versioning failed: {exc}")


if __name__ == "__main__":
    main()
