"""Markup editor window — highlight, arrow, numbered markers, and text."""

import tkinter as tk
from tkinter import colorchooser, filedialog, simpledialog
from PIL import Image, ImageTk, ImageDraw, ImageFont
import math
import os


# ── Annotation data classes ───────────────────────────────────────────────────

class ArrowAnn:
    def __init__(self, x1, y1, x2, y2, color, width=3):
        self.x1, self.y1, self.x2, self.y2 = x1, y1, x2, y2
        self.color = color
        self.width = width

class HighlightAnn:
    def __init__(self, x1, y1, x2, y2, color):
        self.x1, self.y1, self.x2, self.y2 = x1, y1, x2, y2
        self.color = color

class NumberAnn:
    def __init__(self, x, y, number, color):
        self.x, self.y = x, y
        self.number = number
        self.color = color

class TextAnn:
    def __init__(self, x, y, text, color):
        self.x, self.y = x, y
        self.text = text
        self.color = color


# ── Helpers ───────────────────────────────────────────────────────────────────

def _hex_to_rgba(hex_color, alpha=255):
    h = hex_color.lstrip('#')
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return (r, g, b, alpha)

def _load_font(size):
    candidates = [
        '/System/Library/Fonts/Helvetica.ttc',
        '/Library/Fonts/Arial.ttf',
        '/System/Library/Fonts/Supplemental/Arial.ttf',
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


# ── Editor window ─────────────────────────────────────────────────────────────

class EditorWindow:
    MAX_W, MAX_H = 1100, 750

    def __init__(self, root, image):
        self.root = root
        self.original = image.copy()
        self.annotations = []
        self.tool = 'arrow'
        self.color = '#FF3B30'   # default red
        self.number_seq = 1
        self.drag_start = None
        self.temp_item = None

    def show(self):
        self.win = tk.Toplevel(self.root)
        self.win.title('Snappy — Markup')
        self.win.configure(bg='#1E1E1E')
        self.win.resizable(False, False)
        self.win.attributes('-topmost', True)

        self._compute_scale()
        self._build_toolbar()
        self._build_canvas()
        self._build_actionbar()
        self._render()
        self.win.update_idletasks()
        self.win.focus_force()

    # ── Layout ───────────────────────────────────────────────────────────────

    def _compute_scale(self):
        iw, ih = self.original.size
        self.scale = min(self.MAX_W / iw, self.MAX_H / ih, 1.0)
        self.dw = max(1, int(iw * self.scale))
        self.dh = max(1, int(ih * self.scale))

    def _build_toolbar(self):
        bar = tk.Frame(self.win, bg='#2C2C2E', pady=7, padx=8)
        bar.pack(side=tk.TOP, fill=tk.X)

        self.tool_btns = {}
        for label, tool in [('Arrow', 'arrow'), ('Highlight', 'highlight'),
                             ('Number', 'number'), ('Text', 'text')]:
            b = tk.Button(
                bar, text=label, width=8,
                command=lambda t=tool: self._set_tool(t),
                bg='#3A3A3C', fg='white', activebackground='#0A84FF',
                activeforeground='white', relief=tk.FLAT,
                font=('Helvetica', 12), padx=8, pady=5, bd=0
            )
            b.pack(side=tk.LEFT, padx=3)
            self.tool_btns[tool] = b

        tk.Label(bar, text='|', bg='#2C2C2E', fg='#555',
                 font=('Helvetica', 16)).pack(side=tk.LEFT, padx=6)

        # Color swatch button
        self.color_swatch = tk.Canvas(bar, width=30, height=30,
                                      bg='#2C2C2E', highlightthickness=0,
                                      cursor='hand2')
        self.color_swatch.pack(side=tk.LEFT, padx=4)
        self._draw_swatch()
        self.color_swatch.bind('<Button-1>', lambda e: self._pick_color())

        tk.Label(bar, text='Color', bg='#2C2C2E', fg='#aaa',
                 font=('Helvetica', 11)).pack(side=tk.LEFT)

        tk.Label(bar, text='|', bg='#2C2C2E', fg='#555',
                 font=('Helvetica', 16)).pack(side=tk.LEFT, padx=6)

        tk.Button(
            bar, text='Undo', command=self._undo,
            bg='#3A3A3C', fg='white', activebackground='#636366',
            activeforeground='white', relief=tk.FLAT,
            font=('Helvetica', 12), padx=8, pady=5, bd=0
        ).pack(side=tk.LEFT, padx=3)

        self._update_tool_btns()

    def _draw_swatch(self):
        self.color_swatch.delete('all')
        self.color_swatch.create_oval(
            2, 2, 28, 28, fill=self.color, outline='white', width=2
        )

    def _build_canvas(self):
        frame = tk.Frame(self.win, bg='#1E1E1E', padx=12, pady=8)
        frame.pack()
        self.canvas = tk.Canvas(
            frame, width=self.dw, height=self.dh,
            bg='#3A3A3C', highlightthickness=1,
            highlightbackground='#555', cursor='crosshair'
        )
        self.canvas.pack()
        self.canvas.bind('<ButtonPress-1>',   self._on_press)
        self.canvas.bind('<B1-Motion>',       self._on_drag)
        self.canvas.bind('<ButtonRelease-1>', self._on_release)

    def _build_actionbar(self):
        bar = tk.Frame(self.win, bg='#2C2C2E', pady=8, padx=8)
        bar.pack(side=tk.BOTTOM, fill=tk.X)

        def _btn(text, cmd, primary=False):
            return tk.Button(
                bar, text=text, command=cmd,
                bg='#0A84FF' if primary else '#3A3A3C',
                fg='white',
                activebackground='#006FD6' if primary else '#636366',
                activeforeground='white', relief=tk.FLAT,
                font=('Helvetica', 13, 'bold' if primary else 'normal'),
                padx=14, pady=7, bd=0
            )

        _btn('Copy to Clipboard', self._copy, primary=True).pack(side=tk.LEFT, padx=4)
        _btn('Save As...', self._save).pack(side=tk.LEFT, padx=4)
        _btn('Send via iMessage', self._imessage).pack(side=tk.LEFT, padx=4)
        _btn('Close', self.win.destroy).pack(side=tk.RIGHT, padx=4)

    # ── Tool management ───────────────────────────────────────────────────────

    def _set_tool(self, tool):
        self.tool = tool
        cursors = {
            'arrow': 'crosshair', 'highlight': 'crosshair',
            'number': 'hand2',    'text': 'xterm',
        }
        self.canvas.configure(cursor=cursors.get(tool, 'crosshair'))
        self._update_tool_btns()

    def _update_tool_btns(self):
        for t, b in self.tool_btns.items():
            b.configure(bg='#0A84FF' if t == self.tool else '#3A3A3C')

    def _pick_color(self):
        result = colorchooser.askcolor(color=self.color,
                                       title='Pick color', parent=self.win)
        if result[1]:
            self.color = result[1]
            self._draw_swatch()

    def _undo(self):
        if not self.annotations:
            return
        self.annotations.pop()
        nums = [a.number for a in self.annotations if isinstance(a, NumberAnn)]
        self.number_seq = (max(nums) + 1) if nums else 1
        self._render()

    # ── Mouse events ──────────────────────────────────────────────────────────

    def _on_press(self, event):
        self.drag_start = (event.x, event.y)
        if self.temp_item:
            self.canvas.delete(self.temp_item)
            self.temp_item = None

        if self.tool == 'number':
            ix, iy = event.x / self.scale, event.y / self.scale
            self.annotations.append(NumberAnn(ix, iy, self.number_seq, self.color))
            self.number_seq += 1
            self._render()

        elif self.tool == 'text':
            text = simpledialog.askstring('Add Text', 'Enter text:', parent=self.win)
            if text:
                ix, iy = event.x / self.scale, event.y / self.scale
                self.annotations.append(TextAnn(ix, iy, text, self.color))
                self._render()

    def _on_drag(self, event):
        if self.tool not in ('arrow', 'highlight') or not self.drag_start:
            return
        if self.temp_item:
            self.canvas.delete(self.temp_item)
        sx, sy = self.drag_start
        if self.tool == 'arrow':
            self.temp_item = self.canvas.create_line(
                sx, sy, event.x, event.y,
                fill=self.color, width=2, arrow=tk.LAST,
                arrowshape=(12, 16, 6)
            )
        else:  # highlight
            self.temp_item = self.canvas.create_rectangle(
                sx, sy, event.x, event.y,
                outline=self.color, width=2,
                fill=self.color, stipple='gray50'
            )

    def _on_release(self, event):
        if self.tool not in ('arrow', 'highlight') or not self.drag_start:
            return
        if self.temp_item:
            self.canvas.delete(self.temp_item)
            self.temp_item = None

        sx, sy = self.drag_start
        if abs(event.x - sx) < 4 and abs(event.y - sy) < 4:
            return  # accidental click, ignore

        x1, y1 = sx / self.scale, sy / self.scale
        x2, y2 = event.x / self.scale, event.y / self.scale

        if self.tool == 'arrow':
            self.annotations.append(ArrowAnn(x1, y1, x2, y2, self.color))
        else:
            self.annotations.append(HighlightAnn(
                min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2), self.color
            ))
        self._render()

    # ── Rendering ─────────────────────────────────────────────────────────────

    def _render(self):
        img = self._compose()
        display = img.resize((self.dw, self.dh), Image.LANCZOS)
        self.photo = ImageTk.PhotoImage(display)
        self.canvas.delete('all')
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)

    def _compose(self):
        """Return the original image with all annotations flattened in."""
        img = self.original.convert('RGBA')

        for ann in self.annotations:
            if isinstance(ann, HighlightAnn):
                overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
                d = ImageDraw.Draw(overlay)
                r, g, b, _ = _hex_to_rgba(ann.color)
                d.rectangle(
                    [int(ann.x1), int(ann.y1), int(ann.x2), int(ann.y2)],
                    fill=(r, g, b, 110)
                )
                img = Image.alpha_composite(img, overlay)
            else:
                d = ImageDraw.Draw(img)
                if isinstance(ann, ArrowAnn):
                    self._draw_arrow(d, ann)
                elif isinstance(ann, NumberAnn):
                    self._draw_number(d, ann)
                elif isinstance(ann, TextAnn):
                    self._draw_text(d, ann)

        return img.convert('RGB')

    def _draw_arrow(self, d, ann):
        color = _hex_to_rgba(ann.color)
        x1, y1, x2, y2 = ann.x1, ann.y1, ann.x2, ann.y2
        w = ann.width

        d.line([(x1, y1), (x2, y2)], fill=color, width=w)

        dx, dy = x2 - x1, y2 - y1
        length = math.hypot(dx, dy)
        if length < 1:
            return

        ux, uy = dx / length, dy / length
        head_len = max(16, w * 5)
        head_w   = max(10, w * 3)
        px = x2 - ux * head_len
        py = y2 - uy * head_len
        perp_x = -uy * head_w / 2
        perp_y =  ux * head_w / 2

        d.polygon([
            (x2, y2),
            (px + perp_x, py + perp_y),
            (px - perp_x, py - perp_y),
        ], fill=color)

    def _draw_number(self, d, ann):
        color = _hex_to_rgba(ann.color)
        radius = 15
        x, y = int(ann.x), int(ann.y)

        d.ellipse(
            [(x - radius, y - radius), (x + radius, y + radius)],
            fill=color, outline=(255, 255, 255, 255), width=2
        )

        font = _load_font(16)
        text = str(ann.number)
        bbox = d.textbbox((0, 0), text, font=font)
        # Correct centering accounting for font metrics offset
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        tx = x - tw // 2 - bbox[0]
        ty = y - th // 2 - bbox[1]
        d.text((tx, ty), text, fill=(255, 255, 255, 255), font=font)

    def _draw_text(self, d, ann):
        font = _load_font(20)
        color = _hex_to_rgba(ann.color)
        # Drop shadow for readability
        d.text((int(ann.x) + 1, int(ann.y) + 1), ann.text,
               fill=(0, 0, 0, 180), font=font)
        d.text((int(ann.x), int(ann.y)), ann.text, fill=color, font=font)

    # ── Actions ───────────────────────────────────────────────────────────────

    def _copy(self):
        from clipboard import copy_image_to_clipboard
        copy_image_to_clipboard(self._compose())
        self.win.destroy()

    def _save(self):
        path = filedialog.asksaveasfilename(
            parent=self.win,
            defaultextension='.png',
            filetypes=[('PNG image', '*.png'), ('JPEG image', '*.jpg')],
            title='Save Screenshot'
        )
        if path:
            self._compose().save(path)

    def _imessage(self):
        contact = simpledialog.askstring(
            'Send via iMessage',
            'Phone number or Apple ID email:',
            parent=self.win
        )
        if contact:
            from clipboard import send_via_imessage
            send_via_imessage(self._compose(), contact)
            self.win.destroy()
