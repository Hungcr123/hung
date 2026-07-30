# Loaded by FUTURE.server_parts.06_process_frontend_runtime into the shared Future server runtime namespace.
# Windows-only local desktop helper for the machine running Server 2.

SERVER_SCREEN_CLIP_HOTKEY_STARTED = False
SERVER_SCREEN_CLIP_HOTKEY_ID = 0x4651


# Added 2026-07-02: reads the virtual desktop bounds used by both the overlay and scaled screen capture.
def _server_screen_clip_virtual_bounds() -> tuple[int, int, int, int]:
    user32 = ctypes.windll.user32
    SM_XVIRTUALSCREEN = 76
    SM_YVIRTUALSCREEN = 77
    SM_CXVIRTUALSCREEN = 78
    SM_CYVIRTUALSCREEN = 79
    left = int(user32.GetSystemMetrics(SM_XVIRTUALSCREEN))
    top = int(user32.GetSystemMetrics(SM_YVIRTUALSCREEN))
    width = max(1, int(user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)))
    height = max(1, int(user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)))
    return left, top, width, height


# Added 2026-07-02: converts overlay coordinates to the real ImageGrab pixel grid under Windows scaling.
def _server_screen_clip_crop_box_for_image(points: list[tuple[int, int]], image_size: tuple[int, int]) -> tuple[int, int, int, int]:
    if len(points) < 2:
        raise RuntimeError("Need 2 screen points.")
    virtual_left, virtual_top, virtual_width, virtual_height = _server_screen_clip_virtual_bounds()
    image_width, image_height = max(1, int(image_size[0])), max(1, int(image_size[1]))
    scale_x = image_width / max(1, virtual_width)
    scale_y = image_height / max(1, virtual_height)
    (x1, y1), (x2, y2) = points[:2]
    left, right = sorted((int(x1), int(x2)))
    top, bottom = sorted((int(y1), int(y2)))
    crop_left = int(round((left - virtual_left) * scale_x))
    crop_right = int(round((right - virtual_left) * scale_x))
    crop_top = int(round((top - virtual_top) * scale_y))
    crop_bottom = int(round((bottom - virtual_top) * scale_y))
    crop_left = max(0, min(image_width, crop_left))
    crop_right = max(0, min(image_width, crop_right))
    crop_top = max(0, min(image_height, crop_top))
    crop_bottom = max(0, min(image_height, crop_bottom))
    if crop_right - crop_left < 3 or crop_bottom - crop_top < 3:
        raise RuntimeError("Selected screen region is too small.")
    return crop_left, crop_top, crop_right, crop_bottom


def _server_screen_clip_write_dib_to_clipboard(image) -> None:
    output = io.BytesIO()
    image.convert("RGB").save(output, "BMP")
    data = output.getvalue()[14:]
    if not data:
        raise RuntimeError("Screen clip is empty.")
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    GMEM_MOVEABLE = 0x0002
    CF_DIB = 8
    kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
    kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalFree.argtypes = [wintypes.HGLOBAL]
    user32.SetClipboardData.restype = wintypes.HANDLE
    user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
    handle = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
    if not handle:
        raise RuntimeError("Could not allocate clipboard memory.")
    locked = kernel32.GlobalLock(handle)
    if not locked:
        kernel32.GlobalFree(handle)
        raise RuntimeError("Could not lock clipboard memory.")
    try:
        ctypes.memmove(locked, data, len(data))
    finally:
        kernel32.GlobalUnlock(handle)
    if not user32.OpenClipboard(None):
        kernel32.GlobalFree(handle)
        raise RuntimeError("Could not open Windows clipboard.")
    try:
        user32.EmptyClipboard()
        if not user32.SetClipboardData(CF_DIB, handle):
            kernel32.GlobalFree(handle)
            raise RuntimeError("Could not write image to clipboard.")
        handle = None
    finally:
        user32.CloseClipboard()


def _server_screen_clip_capture_to_clipboard(points: list[tuple[int, int]]) -> None:
    try:
        from PIL import ImageGrab
    except Exception as exc:
        raise RuntimeError(f"Pillow ImageGrab is not available: {exc}") from exc
    time.sleep(0.08)
    desktop_image = ImageGrab.grab(all_screens=True)
    crop_box = _server_screen_clip_crop_box_for_image(points, desktop_image.size)
    image = desktop_image.crop(crop_box)
    _server_screen_clip_write_dib_to_clipboard(image)
    print(f"[server-screen-clip] copied {image.width}x{image.height} region to clipboard.", flush=True)


def _server_screen_clip_select_points(timeout_seconds: float = 20.0) -> list[tuple[int, int]]:
    try:
        import tkinter as tk
    except Exception as exc:
        raise RuntimeError(f"Tk overlay is not available: {exc}") from exc

    left, top, width, height = _server_screen_clip_virtual_bounds()
    points: list[tuple[int, int]] = []
    result: dict[str, object] = {"points": None, "error": "Screen clip selection timed out."}
    deadline_ms = max(3000, int(float(timeout_seconds or 20.0) * 1000))
    root = tk.Tk()
    root.withdraw()
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    try:
        root.attributes("-alpha", 0.28)
    except Exception:
        pass
    root.configure(bg="#120008", cursor="crosshair")
    root.geometry(f"{width}x{height}+{left}+{top}")
    canvas = tk.Canvas(root, width=width, height=height, highlightthickness=0, bg="#120008", cursor="crosshair")
    canvas.pack(fill="both", expand=True)
    label = canvas.create_text(
        26,
        24,
        anchor="nw",
        fill="#ffe78a",
        font=("Segoe UI", 13, "bold"),
        text="Alt+Q screen clip: click point 1, then click point 2. Esc cancels.",
    )
    rect_id = canvas.create_rectangle(0, 0, 0, 0, outline="#ffe78a", width=3, dash=(9, 5), state="hidden")
    shade_id = canvas.create_rectangle(0, 0, 0, 0, outline="", fill="#ff3b30", stipple="gray25", state="hidden")
    size_id = canvas.create_text(0, 0, anchor="sw", fill="#ffffff", font=("Segoe UI", 11, "bold"), text="", state="hidden")

    def local_xy(abs_x: int, abs_y: int) -> tuple[int, int]:
        return int(abs_x - left), int(abs_y - top)

    def update_preview(abs_x: int, abs_y: int) -> None:
        if not points:
            return
        x1, y1 = points[0]
        lx1, ly1 = local_xy(x1, y1)
        lx2, ly2 = local_xy(abs_x, abs_y)
        x_min, x_max = sorted((lx1, lx2))
        y_min, y_max = sorted((ly1, ly2))
        canvas.coords(shade_id, x_min, y_min, x_max, y_max)
        canvas.coords(rect_id, x_min, y_min, x_max, y_max)
        canvas.itemconfigure(shade_id, state="normal")
        canvas.itemconfigure(rect_id, state="normal")
        canvas.coords(size_id, x_min + 8, max(22, y_min - 8))
        canvas.itemconfigure(size_id, text=f"{abs(x_max - x_min)} x {abs(y_max - y_min)}", state="normal")

    def cancel(_event=None) -> None:
        result["points"] = None
        result["error"] = "Screen clip selection cancelled."
        root.quit()

    def motion(event) -> None:
        update_preview(int(event.x_root), int(event.y_root))

    def click(event) -> None:
        abs_point = (int(event.x_root), int(event.y_root))
        points.append(abs_point)
        print(f"[server-screen-clip] point {len(points)}/2: {abs_point[0]},{abs_point[1]}", flush=True)
        if len(points) == 1:
            canvas.itemconfigure(label, text="Point 1 set. Move mouse to preview; click point 2 to copy. Esc cancels.")
            update_preview(*abs_point)
            return
        result["points"] = points[:2]
        result["error"] = ""
        root.quit()

    root.bind("<Escape>", cancel)
    canvas.bind("<Motion>", motion)
    canvas.bind("<Button-1>", click)
    root.after(deadline_ms, cancel)
    print("[server-screen-clip] Alt+Q active: overlay shown. Left-click 2 screen points.", flush=True)
    root.deiconify()
    root.lift()
    root.focus_force()
    try:
        root.mainloop()
    finally:
        try:
            root.destroy()
        except Exception:
            pass
    selected = result.get("points")
    if not selected:
        raise RuntimeError(clean(result.get("error", "")) or "Screen clip selection cancelled.")
    return selected


def _server_screen_clip_run_once() -> None:
    try:
        points = _server_screen_clip_select_points()
        _server_screen_clip_capture_to_clipboard(points)
    except Exception as exc:
        print(f"[server-screen-clip] failed: {exc}", flush=True)


# Added 2026-07-02: Alt+Q local Server 2 screen-region capture for the admin machine.
def start_server_screen_clip_hotkey() -> None:
    global SERVER_SCREEN_CLIP_HOTKEY_STARTED
    if SERVER_SCREEN_CLIP_HOTKEY_STARTED:
        return
    if sys.platform != "win32":
        return
    if clean(os.environ.get("FUTURE_DISABLE_SCREEN_CLIP_HOTKEY", "")).lower() in {"1", "true", "yes", "on"}:
        return
    SERVER_SCREEN_CLIP_HOTKEY_STARTED = True

    def worker() -> None:
        user32 = ctypes.windll.user32
        MOD_ALT = 0x0001
        MOD_NOREPEAT = 0x4000
        WM_HOTKEY = 0x0312

        class POINT(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

        class MSG(ctypes.Structure):
            _fields_ = [
                ("hwnd", wintypes.HWND),
                ("message", wintypes.UINT),
                ("wParam", wintypes.WPARAM),
                ("lParam", wintypes.LPARAM),
                ("time", wintypes.DWORD),
                ("pt", POINT),
            ]

        if not user32.RegisterHotKey(None, SERVER_SCREEN_CLIP_HOTKEY_ID, MOD_ALT | MOD_NOREPEAT, ord("Q")):
            print("[server-screen-clip] Alt+Q hotkey unavailable.", flush=True)
            return
        print("[server-screen-clip] Alt+Q hotkey ready.", flush=True)
        try:
            msg = MSG()
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
                if msg.message == WM_HOTKEY and int(msg.wParam) == SERVER_SCREEN_CLIP_HOTKEY_ID:
                    threading.Thread(target=_server_screen_clip_run_once, daemon=True, name="future-screen-clip-select").start()
                else:
                    user32.TranslateMessage(ctypes.byref(msg))
                    user32.DispatchMessageW(ctypes.byref(msg))
        finally:
            user32.UnregisterHotKey(None, SERVER_SCREEN_CLIP_HOTKEY_ID)

    threading.Thread(target=worker, daemon=True, name="future-screen-clip-hotkey").start()
