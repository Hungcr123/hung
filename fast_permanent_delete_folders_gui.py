from __future__ import annotations

import os
import shutil
import sys
import threading
import time
from pathlib import Path

from PyQt5.QtCore import QObject, Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)


BLOCKED_ROOTS = {
    Path("C:/").resolve(),
    Path.home().anchor and Path(Path.home().anchor).resolve(),
}


# Added 2026-07-08: keeps path display compact while preserving the full tooltip.
def display_path(path: Path) -> str:
    text = str(path)
    return text if len(text) <= 120 else "..." + text[-117:]


# Added 2026-07-08: blocks obvious high-risk permanent delete targets.
def validate_delete_target(path: Path) -> tuple[bool, str]:
    try:
        resolved = path.resolve()
    except OSError as exc:
        return False, f"Không đọc được path: {exc}"
    if not resolved.exists():
        return False, "Folder không tồn tại."
    if not resolved.is_dir():
        return False, "Path này không phải folder."
    if resolved in BLOCKED_ROOTS:
        return False, "Không cho xóa root ổ đĩa."
    if resolved.parent == resolved:
        return False, "Không cho xóa root filesystem."
    parts = {part.lower() for part in resolved.parts}
    blocked_names = {"windows", "program files", "program files (x86)", "programdata"}
    if resolved.name.lower() in blocked_names or parts.intersection(blocked_names) and len(resolved.parts) <= 3:
        return False, "Folder hệ thống quá nguy hiểm để xóa bằng tool này."
    return True, ""


# Added 2026-07-08: clears readonly attributes so Windows folders delete without Explorer prompts.
def on_remove_error(func, path, _exc_info) -> None:
    try:
        os.chmod(path, 0o700)
        func(path)
    except Exception:
        raise


# Added 2026-07-08: permanently deletes a folder tree without sending it to Recycle Bin.
def permanent_delete_folder(path: Path) -> None:
    shutil.rmtree(path, onerror=on_remove_error)


class DeleteWorker(QObject):
    progress = pyqtSignal(int, int, str)
    log = pyqtSignal(str)
    finished = pyqtSignal(int, int)

    # Added 2026-07-08: stores immutable delete targets for a background worker.
    def __init__(self, folders: list[Path]) -> None:
        super().__init__()
        self.folders = folders
        self.cancel_requested = False

    # Added 2026-07-08: lets the GUI ask the worker to stop before the next folder.
    def cancel(self) -> None:
        self.cancel_requested = True

    # Added 2026-07-08: deletes selected folders sequentially while keeping the UI responsive.
    def run(self) -> None:
        total = len(self.folders)
        deleted = 0
        failed = 0
        for index, folder in enumerate(self.folders, start=1):
            if self.cancel_requested:
                self.log.emit("Đã dừng trước folder tiếp theo.")
                break
            self.progress.emit(index - 1, total, str(folder))
            start = time.perf_counter()
            try:
                permanent_delete_folder(folder)
                elapsed = time.perf_counter() - start
                deleted += 1
                self.log.emit(f"OK  | {elapsed:.2f}s | {folder}")
            except Exception as exc:
                failed += 1
                self.log.emit(f"ERR | {folder} | {exc}")
            self.progress.emit(index, total, str(folder))
        self.finished.emit(deleted, failed)


class FastPermanentDeleteWindow(QWidget):
    # Added 2026-07-08: builds a focused GUI for permanent multi-folder deletion.
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Fast Permanent Delete Folders")
        self.resize(900, 620)
        self.setMinimumSize(760, 500)
        self.worker_thread: QThread | None = None
        self.worker: DeleteWorker | None = None
        self._build_ui()

    # Added 2026-07-08: lays out folder selection, confirmation, progress, and logs.
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QLabel("Xóa folder vĩnh viễn, không qua Recycle Bin")
        title.setStyleSheet("font-size: 18px; font-weight: 700;")
        layout.addWidget(title)

        note = QLabel("Chọn folder cần xóa, kiểm tra danh sách, nhập DELETE rồi bấm nút xóa. Tool này không tự khôi phục được dữ liệu.")
        note.setWordWrap(True)
        layout.addWidget(note)

        button_row = QHBoxLayout()
        add_button = QPushButton("Add Folders")
        remove_button = QPushButton("Remove Selected")
        clear_button = QPushButton("Clear")
        add_button.clicked.connect(self.add_folders)
        remove_button.clicked.connect(self.remove_selected)
        clear_button.clicked.connect(self.clear_folders)
        button_row.addWidget(add_button)
        button_row.addWidget(remove_button)
        button_row.addWidget(clear_button)
        button_row.addStretch(1)
        layout.addLayout(button_row)

        self.folder_list = QListWidget()
        self.folder_list.setSelectionMode(QListWidget.ExtendedSelection)
        layout.addWidget(self.folder_list, 1)

        confirm_row = QHBoxLayout()
        confirm_row.addWidget(QLabel("Nhập DELETE để xác nhận:"))
        self.confirm_edit = QLineEdit()
        self.confirm_edit.setPlaceholderText("DELETE")
        confirm_row.addWidget(self.confirm_edit, 1)
        self.delete_button = QPushButton("PERMANENT DELETE")
        self.delete_button.setStyleSheet("background: #b91c1c; color: white; font-weight: 700; padding: 8px;")
        self.delete_button.clicked.connect(self.start_delete)
        confirm_row.addWidget(self.delete_button)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_delete)
        confirm_row.addWidget(self.cancel_button)
        layout.addLayout(confirm_row)

        self.progress = QProgressBar()
        layout.addWidget(self.progress)

        self.status = QLabel("Chưa chọn folder.")
        self.status.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self.status)

        self.log_box = QPlainTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setMaximumBlockCount(2000)
        layout.addWidget(self.log_box, 1)

    # Added 2026-07-08: opens a Windows folder picker repeatedly for multiple delete targets.
    def add_folders(self) -> None:
        while True:
            folder = QFileDialog.getExistingDirectory(self, "Chọn folder cần xóa vĩnh viễn", str(Path.home()))
            if not folder:
                break
            self.add_folder_path(Path(folder))
            answer = QMessageBox.question(
                self,
                "Thêm folder khác?",
                "Bạn muốn chọn thêm folder khác không?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
            if answer != QMessageBox.Yes:
                break
        self.update_status()

    # Added 2026-07-08: validates and appends one folder path to the delete list.
    def add_folder_path(self, path: Path) -> None:
        ok, message = validate_delete_target(path)
        if not ok:
            QMessageBox.warning(self, "Không thêm được folder", f"{path}\n\n{message}")
            return
        resolved = path.resolve()
        for index in range(self.folder_list.count()):
            existing = Path(self.folder_list.item(index).data(Qt.UserRole))
            if existing == resolved:
                return
        item = QListWidgetItem(display_path(resolved))
        item.setToolTip(str(resolved))
        item.setData(Qt.UserRole, str(resolved))
        self.folder_list.addItem(item)

    # Added 2026-07-08: removes highlighted rows from the pending delete list.
    def remove_selected(self) -> None:
        for item in self.folder_list.selectedItems():
            row = self.folder_list.row(item)
            self.folder_list.takeItem(row)
        self.update_status()

    # Added 2026-07-08: clears every pending delete target.
    def clear_folders(self) -> None:
        self.folder_list.clear()
        self.update_status()

    # Added 2026-07-08: returns the currently validated folder targets.
    def selected_folders(self) -> list[Path]:
        folders: list[Path] = []
        for index in range(self.folder_list.count()):
            path = Path(self.folder_list.item(index).data(Qt.UserRole))
            ok, message = validate_delete_target(path)
            if not ok:
                raise RuntimeError(f"{path}\n{message}")
            folders.append(path)
        return folders

    # Added 2026-07-08: updates the visible pending delete count.
    def update_status(self) -> None:
        self.status.setText(f"Đang chọn {self.folder_list.count()} folder.")

    # Added 2026-07-08: starts permanent deletion only after explicit typed confirmation.
    def start_delete(self) -> None:
        if self.confirm_edit.text().strip() != "DELETE":
            QMessageBox.warning(self, "Thiếu xác nhận", "Bạn phải nhập DELETE để xóa vĩnh viễn.")
            return
        try:
            folders = self.selected_folders()
        except Exception as exc:
            QMessageBox.critical(self, "Danh sách chưa hợp lệ", str(exc))
            return
        if not folders:
            QMessageBox.warning(self, "Chưa chọn folder", "Bạn chưa chọn folder nào.")
            return
        names = "\n".join(str(folder) for folder in folders[:8])
        if len(folders) > 8:
            names += f"\n... và {len(folders) - 8} folder khác"
        answer = QMessageBox.warning(
            self,
            "Xóa vĩnh viễn?",
            f"Sẽ xóa vĩnh viễn {len(folders)} folder, không qua Recycle Bin:\n\n{names}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        self.delete_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.progress.setRange(0, len(folders))
        self.progress.setValue(0)
        self.log_box.clear()

        self.worker_thread = QThread(self)
        self.worker = DeleteWorker(folders)
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.on_progress)
        self.worker.log.connect(self.log_box.appendPlainText)
        self.worker.finished.connect(self.on_finished)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)
        self.worker_thread.start()

    # Added 2026-07-08: requests cancellation before the next folder delete begins.
    def cancel_delete(self) -> None:
        if self.worker is not None:
            self.worker.cancel()
            self.status.setText("Đang yêu cầu dừng sau folder hiện tại...")

    # Added 2026-07-08: reflects worker progress in the UI.
    def on_progress(self, done: int, total: int, current: str) -> None:
        self.progress.setRange(0, total)
        self.progress.setValue(done)
        self.status.setText(f"{done}/{total} | {current}")

    # Added 2026-07-08: resets controls after a delete run completes.
    def on_finished(self, deleted: int, failed: int) -> None:
        self.delete_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.worker = None
        self.worker_thread = None
        self.confirm_edit.clear()
        self.status.setText(f"Xong: đã xóa {deleted} folder, lỗi {failed}.")
        for index in reversed(range(self.folder_list.count())):
            path = Path(self.folder_list.item(index).data(Qt.UserRole))
            if not path.exists():
                self.folder_list.takeItem(index)
        self.update_status()


# Added 2026-07-08: launches the permanent-delete GUI as a standalone utility.
def main() -> int:
    app = QApplication(sys.argv)
    window = FastPermanentDeleteWindow()
    window.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
