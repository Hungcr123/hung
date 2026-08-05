from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


SETTINGS_PATH = Path(r"C:\programe\programe_cache\collect_txt_to_clipboard_gui\settings.json")
HISTORY_LIMIT = 20


def natural_key(path: Path) -> list[object]:
    text = str(path).lower()
    return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", text)]


def read_text_file(path: Path) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp1258", "cp1252"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


# Added 2026-07-08: keeps the text collector's last folders and prompt controls across app restarts.
def load_settings() -> dict:
    try:
        if SETTINGS_PATH.is_file():
            data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8-sig"))
            if isinstance(data, dict):
                return data
    except Exception:
        return {}
    return {}


# Added 2026-07-08: writes small GUI state without touching lesson/server data.
def save_settings(payload: dict) -> None:
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


# Added 2026-07-08: normalizes persisted open history for folders and multi-file selections.
def normalize_recent_entries(value: object) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    if not isinstance(value, list):
        return entries
    for item in value:
        if not isinstance(item, dict):
            continue
        kind = str(item.get("kind") or "").strip().lower()
        if kind == "folder":
            path = str(item.get("path") or "").strip()
            if path:
                entries.append({"kind": "folder", "path": path})
        elif kind == "files":
            paths = [str(path).strip() for path in item.get("paths") or [] if str(path).strip()]
            if paths:
                entries.append({"kind": "files", "paths": paths})
    return entries[:HISTORY_LIMIT]


class TxtClipboardWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("TXT Prompt Split Clipboard")
        self.resize(980, 720)
        self.setMinimumSize(820, 560)
        self.selected_file_paths: list[Path] = []
        self.file_block_paths: list[Path] = []
        self.file_blocks_layout: QHBoxLayout | None = None
        self.copy_buttons_layout: QVBoxLayout | None = None
        self.current_chunks: list[str] = []
        self.settings = load_settings()
        self.recent_entries = normalize_recent_entries(self.settings.get("recent_entries"))
        self._build_ui()
        self.restore_settings()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        top = QHBoxLayout()
        self.folder_edit = QLineEdit()
        self.folder_edit.setPlaceholderText("Chọn folder chứa file .txt hoặc bấm Open Files để chọn nhiều file")
        open_button = QPushButton("Open")
        open_files_button = QPushButton("Open Files")
        open_button.clicked.connect(self.choose_folder)
        open_files_button.clicked.connect(self.choose_files)
        top.addWidget(self.folder_edit, 1)
        top.addWidget(open_button)
        top.addWidget(open_files_button)
        layout.addLayout(top)

        option_row = QHBoxLayout()
        self.recursive_check = QCheckBox("Quét cả thư mục con")
        self.recursive_check.setChecked(True)
        self.header_check = QCheckBox("Thêm tiêu đề tên file")
        option_row.addWidget(self.recursive_check)
        option_row.addWidget(self.header_check)
        option_row.addStretch(1)
        layout.addLayout(option_row)

        history_label = QLabel("Lịch sử mở file/folder:")
        layout.addWidget(history_label)
        self.history_list = QListWidget()
        self.history_list.setFixedHeight(120)
        self.history_list.itemClicked.connect(self.open_history_item)
        self.history_list.itemDoubleClicked.connect(self.open_history_item)
        layout.addWidget(self.history_list)

        block_header = QHBoxLayout()
        block_header.addWidget(QLabel("File blocks:"))
        select_all_blocks_button = QPushButton("Select All")
        select_all_blocks_button.clicked.connect(self.select_all_file_blocks)
        block_header.addStretch(1)
        block_header.addWidget(select_all_blocks_button)
        layout.addLayout(block_header)

        file_block_scroll = QScrollArea()
        file_block_scroll.setWidgetResizable(True)
        file_block_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        file_block_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        file_block_panel = QWidget()
        self.file_blocks_layout = QHBoxLayout(file_block_panel)
        self.file_blocks_layout.setContentsMargins(4, 4, 4, 4)
        self.file_blocks_layout.setSpacing(6)
        self.file_blocks_layout.addWidget(QLabel("Mở folder hoặc file để hiện block tên file."))
        self.file_blocks_layout.addStretch(1)
        file_block_scroll.setWidget(file_block_panel)
        file_block_scroll.setFixedHeight(58)
        layout.addWidget(file_block_scroll)

        prompt_label = QLabel("Prompt ở đầu mỗi phần:")
        layout.addWidget(prompt_label)
        self.prompt_edit = QTextEdit()
        self.prompt_edit.setPlaceholderText("Nhập prompt. Khi copy từng phần, prompt này sẽ đứng trước text đã bọc ngoặc.")
        self.prompt_edit.setFixedHeight(90)
        layout.addWidget(self.prompt_edit)

        split_row = QHBoxLayout()
        self.open_wrapper_edit = QLineEdit('"')
        self.open_wrapper_edit.setMaxLength(20)
        self.close_wrapper_edit = QLineEdit('"')
        self.close_wrapper_edit.setMaxLength(20)
        self.split_mode_combo = QComboBox()
        self.split_mode_combo.addItem("Không split", "none")
        self.split_mode_combo.addItem("Split theo số ký tự", "chars")
        self.split_mode_combo.addItem("Split theo số dòng", "lines")
        self.split_amount_spin = QSpinBox()
        self.split_amount_spin.setRange(1, 1_000_000)
        self.split_amount_spin.setValue(4000)
        self.split_amount_spin.setSingleStep(100)
        split_button = QPushButton("Split")
        split_button.clicked.connect(self.update_preview)
        split_row.addWidget(QLabel("Ngoặc mở:"))
        split_row.addWidget(self.open_wrapper_edit)
        split_row.addWidget(QLabel("Ngoặc đóng:"))
        split_row.addWidget(self.close_wrapper_edit)
        split_row.addWidget(QLabel("Kiểu split:"))
        split_row.addWidget(self.split_mode_combo)
        split_row.addWidget(QLabel("Số lượng:"))
        split_row.addWidget(self.split_amount_spin)
        split_row.addWidget(split_button)
        layout.addLayout(split_row)

        self.preview = QTextEdit()
        self.preview.setReadOnly(False)
        self.preview.setFont(QFont("Consolas", 10))
        layout.addWidget(self.preview, 1)

        copy_scroll = QScrollArea()
        copy_scroll.setWidgetResizable(True)
        copy_panel = QWidget()
        self.copy_buttons_layout = QVBoxLayout(copy_panel)
        self.copy_buttons_layout.setContentsMargins(4, 4, 4, 4)
        self.copy_buttons_layout.setSpacing(6)
        self.copy_buttons_layout.addWidget(QLabel("Bấm Preview/Split để tạo nút copy từng phần."))
        self.copy_buttons_layout.addStretch(1)
        copy_scroll.setWidget(copy_panel)
        copy_scroll.setMinimumHeight(120)
        layout.addWidget(copy_scroll)

        bottom = QHBoxLayout()
        self.status = QLabel("Chọn folder hoặc nhiều file .txt, sau đó bấm Preview/Split hoặc Save.")
        self.status.setTextInteractionFlags(Qt.TextSelectableByMouse)
        preview_button = QPushButton("Preview")
        save_button = QPushButton("Save")
        preview_button.clicked.connect(self.update_preview)
        save_button.clicked.connect(self.copy_to_clipboard)
        bottom.addWidget(self.status, 1)
        bottom.addWidget(preview_button)
        bottom.addWidget(save_button)
        layout.addLayout(bottom)

    # Added 2026-07-08: restores the last used folder/prompt/split controls on startup.
    def restore_settings(self) -> None:
        folder = str(self.settings.get("last_folder") or "").strip()
        if folder:
            self.folder_edit.setText(folder)
        self.prompt_edit.setPlainText(str(self.settings.get("prompt") or ""))
        self.open_wrapper_edit.setText(str(self.settings.get("open_wrapper", '"')))
        self.close_wrapper_edit.setText(str(self.settings.get("close_wrapper", '"')))
        split_mode = str(self.settings.get("split_mode") or "none")
        split_index = self.split_mode_combo.findData(split_mode)
        if split_index >= 0:
            self.split_mode_combo.setCurrentIndex(split_index)
        try:
            self.split_amount_spin.setValue(int(self.settings.get("split_amount") or self.split_amount_spin.value()))
        except (TypeError, ValueError):
            pass
        self.refresh_history_view()
        if self.recent_entries:
            self.restore_recent_entry_as_current(self.recent_entries[0], update_preview=False)
        elif folder and Path(folder).is_dir():
            self.set_file_blocks(self.files_from_folder(Path(folder)))

    # Added 2026-07-08: snapshots current GUI state for the next launch.
    def save_current_settings(self) -> None:
        payload = {
            "last_folder": self.settings.get("last_folder") or "",
            "last_files_folder": self.settings.get("last_files_folder") or "",
            "prompt": self.prompt_edit.toPlainText(),
            "open_wrapper": self.open_wrapper_edit.text(),
            "close_wrapper": self.close_wrapper_edit.text(),
            "split_mode": self.split_mode_combo.currentData(),
            "split_amount": int(self.split_amount_spin.value()),
            "recent_entries": self.recent_entries[:HISTORY_LIMIT],
        }
        folder_text = self.folder_edit.text().strip()
        if folder_text and Path(folder_text).is_dir():
            payload["last_folder"] = folder_text
        if self.selected_file_paths:
            payload["last_files_folder"] = str(self.selected_file_paths[0].parent)
        self.settings = payload
        save_settings(payload)

    # Added 2026-07-08: returns the TXT files represented by a folder block source.
    def files_from_folder(self, folder: Path) -> list[Path]:
        if not folder.is_dir():
            return []
        pattern = "**/*.txt" if self.recursive_check.isChecked() else "*.txt"
        return sorted((path for path in folder.glob(pattern) if path.is_file()), key=natural_key)

    # Added 2026-07-08: turns each currently opened TXT file into a horizontal clickable block.
    def set_file_blocks(self, paths: list[Path]) -> None:
        self.file_block_paths = sorted((path for path in paths if path.is_file()), key=natural_key)
        self.refresh_file_blocks()

    # Added 2026-07-08: redraws file-name blocks in one horizontally scrollable row.
    def refresh_file_blocks(self) -> None:
        if self.file_blocks_layout is None:
            return
        while self.file_blocks_layout.count():
            item = self.file_blocks_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        if not self.file_block_paths:
            self.file_blocks_layout.addWidget(QLabel("Chưa có file block."))
            self.file_blocks_layout.addStretch(1)
            return
        for path in self.file_block_paths:
            button = QPushButton(path.name)
            button.setMinimumHeight(34)
            button.setStyleSheet(
                "QPushButton {"
                "  background: #e0f2fe;"
                "  border: 1px solid #0284c7;"
                "  border-radius: 6px;"
                "  color: #0f172a;"
                "  padding: 6px 10px;"
                "  font-weight: 600;"
                "}"
                "QPushButton:hover { background: #bae6fd; }"
                "QPushButton:pressed { background: #7dd3fc; }"
            )
            button.setToolTip(str(path))
            button.clicked.connect(lambda _checked=False, block_path=path: self.select_file_block(block_path))
            self.file_blocks_layout.addWidget(button)
        self.file_blocks_layout.addStretch(1)

    # Added 2026-07-08: clicking a file block replaces the working content with that single file.
    def select_file_block(self, path: Path) -> None:
        if not path.is_file():
            QMessageBox.warning(self, "File không còn tồn tại", str(path))
            return
        self.selected_file_paths = [path]
        self.folder_edit.setText("1 file đã chọn")
        self.update_preview()

    # Added 2026-07-08: restores the working content to all currently visible file blocks.
    def select_all_file_blocks(self) -> None:
        paths = [path for path in self.file_block_paths if path.is_file()]
        if not paths:
            QMessageBox.warning(self, "Chưa có block", "Chưa có file block nào để chọn.")
            return
        self.selected_file_paths = list(paths)
        self.folder_edit.setText(f"{len(self.selected_file_paths)} file đã chọn")
        self.update_preview()

    # Added 2026-07-08: builds a readable one-line label for history rows.
    def history_label_for_entry(self, entry: dict[str, object]) -> str:
        if entry.get("kind") == "folder":
            return f"Folder | {entry.get('path')}"
        paths = [str(path) for path in entry.get("paths") or []]
        if not paths:
            return "Files | 0 file"
        first = Path(paths[0]).name
        suffix = "" if len(paths) == 1 else f" + {len(paths) - 1} file"
        return f"Files | {len(paths)} file | {first}{suffix}"

    # Added 2026-07-08: refreshes the visible open history list.
    def refresh_history_view(self) -> None:
        self.history_list.clear()
        if not self.recent_entries:
            item = QListWidgetItem("Chưa có lịch sử mở file/folder.")
            item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
            self.history_list.addItem(item)
            return
        for entry in self.recent_entries:
            item = QListWidgetItem(self.history_label_for_entry(entry))
            item.setData(Qt.UserRole, entry)
            if entry.get("kind") == "folder":
                item.setToolTip(str(entry.get("path") or ""))
            else:
                item.setToolTip("\n".join(str(path) for path in entry.get("paths") or []))
            self.history_list.addItem(item)

    # Added 2026-07-08: stores a folder choice at the top of history without duplicates.
    def add_recent_folder(self, folder: str) -> None:
        entry = {"kind": "folder", "path": str(folder)}
        self.recent_entries = [item for item in self.recent_entries if not (item.get("kind") == "folder" and item.get("path") == folder)]
        self.recent_entries.insert(0, entry)
        self.recent_entries = self.recent_entries[:HISTORY_LIMIT]
        self.refresh_history_view()

    # Added 2026-07-08: stores a multi-file choice at the top of history without duplicates.
    def add_recent_files(self, paths: list[Path]) -> None:
        clean_paths = [str(path) for path in paths if path.is_file()]
        if not clean_paths:
            return
        entry = {"kind": "files", "paths": clean_paths}
        key = tuple(clean_paths)
        self.recent_entries = [
            item
            for item in self.recent_entries
            if not (item.get("kind") == "files" and tuple(str(path) for path in item.get("paths") or []) == key)
        ]
        self.recent_entries.insert(0, entry)
        self.recent_entries = self.recent_entries[:HISTORY_LIMIT]
        self.refresh_history_view()

    # Added 2026-07-08: double-clicking history reloads that folder or file selection.
    def open_history_item(self, item: QListWidgetItem) -> None:
        entry = item.data(Qt.UserRole)
        if not isinstance(entry, dict):
            return
        self.restore_recent_entry_as_current(entry, update_preview=True)

    # Added 2026-07-08: loads a recent folder/file group into visible blocks and the active selection.
    def restore_recent_entry_as_current(self, entry: dict[str, object], update_preview: bool = True) -> None:
        if entry.get("kind") == "folder":
            folder = str(entry.get("path") or "")
            if not Path(folder).is_dir():
                if update_preview:
                    QMessageBox.warning(self, "Folder không còn tồn tại", folder)
                return
            self.selected_file_paths = []
            self.folder_edit.setText(folder)
            self.settings["last_folder"] = folder
            self.set_file_blocks(self.files_from_folder(Path(folder)))
        elif entry.get("kind") == "files":
            paths = [Path(path) for path in entry.get("paths") or [] if Path(path).is_file()]
            if not paths:
                if update_preview:
                    QMessageBox.warning(self, "File không còn tồn tại", "Nhóm file này không còn file hợp lệ để mở.")
                return
            self.selected_file_paths = sorted(paths, key=natural_key)
            self.set_file_blocks(self.selected_file_paths)
            self.folder_edit.setText(f"{len(self.selected_file_paths)} file đã chọn")
            self.settings["last_files_folder"] = str(self.selected_file_paths[0].parent)
        self.save_current_settings()
        if update_preview:
            self.update_preview()

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self.save_current_settings()
        super().closeEvent(event)

    def choose_folder(self) -> None:
        start = self.folder_edit.text().strip() or str(self.settings.get("last_folder") or "") or str(Path.home())
        folder = QFileDialog.getExistingDirectory(self, "Chọn folder chứa file TXT", start)
        if folder:
            self.selected_file_paths = []
            self.folder_edit.setText(folder)
            self.settings["last_folder"] = folder
            self.set_file_blocks(self.files_from_folder(Path(folder)))
            self.add_recent_folder(folder)
            self.save_current_settings()
            self.update_preview()

    # Added 2026-07-08: lets the collector merge an arbitrary multi-file TXT selection.
    def choose_files(self) -> None:
        start = self.folder_edit.text().strip() or str(self.settings.get("last_files_folder") or "") or str(Path.home())
        if not Path(start).is_dir():
            start = str(self.settings.get("last_files_folder") or Path.home())
        if self.selected_file_paths:
            start = str(self.selected_file_paths[0].parent)
        paths, _filter = QFileDialog.getOpenFileNames(
            self,
            "Chọn nhiều file TXT để gộp",
            start,
            "Text files (*.txt);;All files (*.*)",
        )
        if not paths:
            return
        self.selected_file_paths = sorted((Path(path) for path in paths), key=natural_key)
        self.set_file_blocks(self.selected_file_paths)
        self.settings["last_files_folder"] = str(self.selected_file_paths[0].parent)
        self.folder_edit.setText(f"{len(self.selected_file_paths)} file đã chọn")
        self.add_recent_files(self.selected_file_paths)
        self.save_current_settings()
        self.update_preview()

    def txt_files(self) -> list[Path]:
        if self.selected_file_paths:
            return [path for path in self.selected_file_paths if path.is_file()]
        folder = Path(self.folder_edit.text().strip())
        if not folder.is_dir():
            raise ValueError("Folder không hợp lệ.")
        return self.files_from_folder(folder)

    def combined_text(self) -> tuple[str, list[Path]]:
        files = self.txt_files()
        base = Path(self.folder_edit.text().strip()) if not self.selected_file_paths else None
        parts: list[str] = []
        for path in files:
            text = read_text_file(path).strip()
            if not text:
                continue
            if self.header_check.isChecked():
                label = path.name
                if base is not None:
                    label = str(path.relative_to(base))
                parts.append(f"===== {label} =====\n{text}")
            else:
                parts.append(text)
        return "\n\n".join(parts).strip(), files

    # Added 2026-07-08: splits collected text by selected character or line limits.
    def split_text(self, text: str) -> list[str]:
        mode = self.split_mode_combo.currentData()
        amount = max(1, int(self.split_amount_spin.value()))
        if not text:
            return []
        if mode == "chars":
            chunks: list[str] = []
            remaining = text
            while remaining:
                if len(remaining) <= amount:
                    chunks.append(remaining.strip())
                    break
                cut = remaining.rfind("\n", 0, amount + 1)
                if cut < max(1, amount // 2):
                    cut = remaining.rfind(" ", 0, amount + 1)
                if cut < max(1, amount // 2):
                    cut = amount
                chunks.append(remaining[:cut].strip())
                remaining = remaining[cut:].lstrip()
            return [chunk for chunk in chunks if chunk]
        if mode == "lines":
            lines = text.splitlines()
            return ["\n".join(lines[index : index + amount]).strip() for index in range(0, len(lines), amount) if lines[index : index + amount]]
        return [text.strip()]

    # Added 2026-07-08: wraps a split chunk with the prompt and editable quote markers.
    def prompt_payload_for_chunk(self, chunk: str) -> str:
        prompt = self.prompt_edit.toPlainText().strip()
        open_wrapper = self.open_wrapper_edit.text()
        close_wrapper = self.close_wrapper_edit.text()
        wrapped = f"{open_wrapper}{chunk.strip()}{close_wrapper}"
        return f"{prompt}\n{wrapped}".strip() if prompt else wrapped

    # Added 2026-07-08: rebuilds one clipboard button for each split output part.
    def refresh_copy_buttons(self, chunks: list[str]) -> None:
        self.current_chunks = list(chunks)
        if self.copy_buttons_layout is None:
            return
        while self.copy_buttons_layout.count():
            item = self.copy_buttons_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        if not chunks:
            self.copy_buttons_layout.addWidget(QLabel("Chưa có phần nào để copy."))
            self.copy_buttons_layout.addStretch(1)
            return
        for index, chunk in enumerate(chunks, start=1):
            payload_len = len(self.prompt_payload_for_chunk(chunk))
            line_count = len(chunk.splitlines()) or 1
            button = QPushButton(f"Copy phần {index} | {len(chunk):,} ký tự | {line_count:,} dòng | payload {payload_len:,}")
            button.clicked.connect(lambda _checked=False, chunk_text=chunk, part=index: self.copy_chunk_to_clipboard(chunk_text, part))
            self.copy_buttons_layout.addWidget(button)
        self.copy_buttons_layout.addStretch(1)

    # Added 2026-07-08: copies one prompt-wrapped split part to the clipboard.
    def copy_chunk_to_clipboard(self, chunk: str, part_index: int) -> None:
        payload = self.prompt_payload_for_chunk(chunk)
        QApplication.clipboard().setText(payload)
        self.status.setText(f"Đã copy phần {part_index}: {len(payload):,} ký tự gồm prompt + text đã bọc ngoặc.")

    def update_preview(self) -> None:
        self.save_current_settings()
        try:
            text, files = self.combined_text()
        except Exception as exc:
            self.preview.clear()
            self.status.setText(str(exc))
            self.refresh_copy_buttons([])
            return
        chunks = self.split_text(text)
        self.refresh_copy_buttons(chunks)
        preview_text = text[:20000]
        self.preview.setPlainText(preview_text)
        suffix = " Preview bị cắt còn 20,000 ký tự." if len(text) > len(preview_text) else ""
        self.status.setText(f"Đã tìm thấy {len(files)} file .txt, tổng {len(text):,} ký tự, tạo {len(chunks)} phần copy.{suffix}")

    def copy_to_clipboard(self) -> None:
        self.save_current_settings()
        try:
            text, files = self.combined_text()
        except Exception as exc:
            QMessageBox.critical(self, "Lỗi", str(exc))
            return
        if not files:
            QMessageBox.warning(self, "Chưa có file", "Không tìm thấy file .txt nào trong folder này.")
            return
        if not text:
            QMessageBox.warning(self, "Không có text", "Các file .txt đang rỗng hoặc không đọc được nội dung.")
            return
        chunks = self.split_text(text)
        payload = "\n\n".join(self.prompt_payload_for_chunk(chunk) for chunk in chunks)
        QApplication.clipboard().setText(payload)
        self.refresh_copy_buttons(chunks)
        self.status.setText(f"Đã copy {len(payload):,} ký tự từ {len(files)} file .txt vào clipboard.")
        QMessageBox.information(self, "Xong", "Đã lưu prompt + toàn bộ phần đã split vào clipboard.")


def main() -> int:
    app = QApplication(sys.argv)
    window = TxtClipboardWindow()
    window.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
