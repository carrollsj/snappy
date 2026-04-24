"""Full-screen region-selection overlay."""

import tkinter as tk
from PIL import Image, ImageTk, ImageEnhance
import subprocess
import tempfile
import os


class CaptureOverlay:
    def __init__(self, root, callback):
        self.root = root
        self.callback = callback
        self.start_x = 0
        self.start_y = 0
        self.rect_id = None
        self.screenshot_path = None
        self.screenshot = None

    def start(self):
        fd, self.screenshot_path = tempfile.mkstemp(suffix='.png')
        os.close(fd)
        # -x = no sound, -t png = force PNG format
        subprocess.run(
            ['screencapture', '-x', '-t', 'png', self.screenshot_path],
            check=True
        )
        self.screenshot = Image.open(self.screenshot_path)
        self._open_overlay()

    def _open_overlay(self):
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()

        # Darken screenshot so the selection stands out
        darkened = ImageEnhance.Brightness(self.screenshot).enhance(0.45)
        display = darkened.resize((screen_w, screen_h), Image.LANCZOS)

        self.win = tk.Toplevel(self.root)
        self.win.overrideredirect(True)
        self.win.geometry(f'{screen_w}x{screen_h}+0+0')
        self.win.attributes('-topmost', True)

        self.canvas = tk.Canvas(
            self.win, width=screen_w, height=screen_h,
            bg='black', highlightthickness=0, cursor='crosshair'
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.bg_photo = ImageTk.PhotoImage(display)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.bg_photo)

        self.canvas.create_text(
            screen_w // 2, 36,
            text='Drag to select area  •  Esc to cancel',
            fill='white', font=('Helvetica', 15),
            tags='hint'
        )

        self.canvas.bind('<ButtonPress-1>',   self._on_press)
        self.canvas.bind('<B1-Motion>',       self._on_drag)
        self.canvas.bind('<ButtonRelease-1>', self._on_release)
        self.win.bind('<Escape>', self._cancel)

        self.win.lift()
        self.win.focus_force()

    def _on_press(self, event):
        self.start_x, self.start_y = event.x, event.y
        self.canvas.delete('hint')
        if self.rect_id:
            self.canvas.delete(self.rect_id)

    def _on_drag(self, event):
        if self.rect_id:
            self.canvas.delete(self.rect_id)
        self.rect_id = self.canvas.create_rectangle(
            self.start_x, self.start_y, event.x, event.y,
            outline='#4FC3F7', width=2, fill=''
        )

    def _on_release(self, event):
        x1 = min(self.start_x, event.x)
        y1 = min(self.start_y, event.y)
        x2 = max(self.start_x, event.x)
        y2 = max(self.start_y, event.y)

        self.win.destroy()

        if x2 - x1 < 5 or y2 - y1 < 5:
            self._cleanup()
            self.callback(None)
            return

        # Map display coords → actual screenshot pixels (handles Retina 2x)
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        img_w, img_h = self.screenshot.size
        sx = img_w / screen_w
        sy = img_h / screen_h

        crop = self.screenshot.crop((
            int(x1 * sx), int(y1 * sy),
            int(x2 * sx), int(y2 * sy),
        ))
        self._cleanup()
        self.callback(crop)

    def _cancel(self, event=None):
        self.win.destroy()
        self._cleanup()
        self.callback(None)

    def _cleanup(self):
        if self.screenshot_path and os.path.exists(self.screenshot_path):
            try:
                os.unlink(self.screenshot_path)
            except OSError:
                pass
