"""Tkinter GUI prototype for the shared Space PDF package builder."""

from __future__ import annotations

import os
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from future_space_pdf_package import build_space_pdf_package
from future_lesson_builder_gui import builder_server2_build_begin, builder_server2_build_end


class SpacePdfBuilderGui:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Future Space PDF Builder")
        self.root.geometry("820x580")
        self.source_var = tk.StringVar()
        self.title_var = tk.StringVar()
        self.output_dir_var = tk.StringVar()
        self.output_name_var = tk.StringVar()
        self.scope_var = tk.StringVar(value="common")
        self.thumbnail_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="Choose a PDF to begin.")
        self.lesson_id_var = tk.StringVar()
        self.document_id_var = tk.StringVar()
        self.output_var = tk.StringVar()
        self.size_var = tk.StringVar()
        self._build_ui()

    def _build_ui(self) -> None:
        frame = ttk.Frame(self.root, padding=18)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(1, weight=1)
        rows = [
            ("Source PDF", self.source_var, self._choose_pdf, "Open PDF"),
            ("Lesson title", self.title_var, None, ""),
            ("Output folder", self.output_dir_var, self._choose_output, "Choose"),
            ("Output filename", self.output_name_var, None, ""),
            ("Owner/scope", self.scope_var, None, ""),
        ]
        for index, (label, variable, command, button_text) in enumerate(rows):
            ttk.Label(frame, text=label).grid(row=index, column=0, sticky="w", pady=7)
            ttk.Entry(frame, textvariable=variable).grid(row=index, column=1, sticky="ew", padx=10, pady=7)
            if command:
                ttk.Button(frame, text=button_text, command=command).grid(row=index, column=2, pady=7)
        options = ttk.LabelFrame(frame, text="Build options", padding=10)
        options.grid(row=5, column=0, columnspan=3, sticky="ew", pady=12)
        ttk.Checkbutton(options, text="Create first-page thumbnail", variable=self.thumbnail_var).pack(anchor="w")
        ttk.Checkbutton(options, text="Run OCR now (integration phase)", state="disabled").pack(anchor="w")
        ttk.Checkbutton(options, text="Delete source after registry commit (integration phase)", state="disabled").pack(anchor="w")
        self.build_button = ttk.Button(frame, text="Build and verify package", command=self._start_build)
        self.build_button.grid(row=6, column=0, columnspan=3, sticky="ew", pady=8)
        result = ttk.LabelFrame(frame, text="Verified result", padding=12)
        result.grid(row=7, column=0, columnspan=3, sticky="nsew", pady=10)
        frame.rowconfigure(7, weight=1)
        result.columnconfigure(1, weight=1)
        for row, (label, variable) in enumerate((
            ("Status", self.status_var),
            ("Output", self.output_var),
            ("Lesson ID", self.lesson_id_var),
            ("Document ID", self.document_id_var),
            ("Package size", self.size_var),
        )):
            ttk.Label(result, text=label).grid(row=row, column=0, sticky="nw", pady=4)
            ttk.Label(result, textvariable=variable, wraplength=610).grid(row=row, column=1, sticky="nw", padx=10, pady=4)
        actions = ttk.Frame(result)
        actions.grid(row=5, column=0, columnspan=2, sticky="ew", pady=10)
        ttk.Button(actions, text="Open package", command=self._open_package).pack(side="left", padx=4)
        ttk.Button(actions, text="Open output folder", command=self._open_output_folder).pack(side="left", padx=4)
        ttk.Button(actions, text="Copy lesson ID", command=self._copy_lesson_id).pack(side="left", padx=4)
        ttk.Button(actions, text="Build another", command=self._reset).pack(side="left", padx=4)

    def _choose_pdf(self) -> None:
        selected = filedialog.askopenfilename(title="Choose PDF", filetypes=[("PDF files", "*.pdf")])
        if not selected:
            return
        source = Path(selected)
        self.source_var.set(str(source))
        self.title_var.set(source.stem)
        self.output_dir_var.set(str(source.parent))
        self.output_name_var.set(f"{source.stem}.space_pdf")

    def _choose_output(self) -> None:
        selected = filedialog.askdirectory(title="Choose output folder")
        if selected:
            self.output_dir_var.set(selected)

    def _start_build(self) -> None:
        source = Path(self.source_var.get().strip())
        output = Path(self.output_dir_var.get().strip()) / self.output_name_var.get().strip()
        if output.exists() and not messagebox.askyesno("Replace package", "The output exists. Replace it?"):
            return
        self.build_button.configure(state="disabled")
        self.status_var.set("Building temporary package and verifying source fingerprint...")

        def worker() -> None:
            build_session = builder_server2_build_begin("Space_PDF", output)
            result = None
            session_finished = False
            try:
                result = build_space_pdf_package(
                    source,
                    output,
                    title=self.title_var.get(),
                    owner_scope=self.scope_var.get(),
                    create_thumbnail=self.thumbnail_var.get(),
                    overwrite=True,
                )
                bridge = builder_server2_build_end(build_session, "Space_PDF", output, True)
                session_finished = True
                publication = bridge.get("build_hold") if isinstance(bridge.get("build_hold"), dict) else {}
                if not publication.get("published"):
                    reason = publication.get("error") or publication.get("reason") or "Server 2 did not acknowledge manifest publication."
                    raise RuntimeError(f"Package was built, but Server 2 publish failed: {reason}")
                if publication.get("lesson_id") != result.lesson_id:
                    raise RuntimeError("Package was built, but Server 2 returned a different lesson ID.")
                self.root.after(0, lambda result=result, publication=publication: self._show_result(result, publication))
            except Exception as exc:
                if not session_finished:
                    builder_server2_build_end(build_session, "Space_PDF", output, False)
                message = str(exc)
                if result is not None:
                    self.root.after(0, lambda result=result, message=message: self._show_publish_error(result, message))
                else:
                    self.root.after(0, lambda message=message: self._show_error(message))

        threading.Thread(target=worker, daemon=True, name="space-pdf-builder").start()

    def _show_result(self, result, publication: dict) -> None:
        self.build_button.configure(state="normal")
        self.status_var.set(f"Published to Server 2 RAM/manifest: {publication.get('path', result.output_path)}")
        self.output_var.set(result.output_path)
        self.lesson_id_var.set(result.lesson_id)
        self.document_id_var.set(result.document_id)
        self.size_var.set(f"{result.package_bytes:,} bytes")

    def _show_publish_error(self, result, message: str) -> None:
        self.build_button.configure(state="normal")
        self.output_var.set(result.output_path)
        self.lesson_id_var.set(result.lesson_id)
        self.document_id_var.set(result.document_id)
        self.size_var.set(f"{result.package_bytes:,} bytes")
        self.status_var.set(message)
        messagebox.showerror("Space PDF server publish failed", message)

    def _show_error(self, message: str) -> None:
        self.build_button.configure(state="normal")
        self.status_var.set(f"Build failed: {message}")
        messagebox.showerror("Space PDF build failed", message)

    def _open_package(self) -> None:
        if self.output_var.get() and Path(self.output_var.get()).is_file():
            os.startfile(self.output_var.get())

    def _open_output_folder(self) -> None:
        path = Path(self.output_var.get()).parent if self.output_var.get() else Path(self.output_dir_var.get())
        if path.is_dir():
            os.startfile(str(path))

    def _copy_lesson_id(self) -> None:
        if self.lesson_id_var.get():
            self.root.clipboard_clear()
            self.root.clipboard_append(self.lesson_id_var.get())

    def _reset(self) -> None:
        for variable in (self.source_var, self.title_var, self.output_name_var, self.lesson_id_var, self.document_id_var, self.output_var, self.size_var):
            variable.set("")
        self.status_var.set("Choose a PDF to begin.")


def main() -> int:
    root = tk.Tk()
    SpacePdfBuilderGui(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
