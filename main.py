"""
Snappy — macOS screenshot and markup tool

Hotkeys (system-wide):
  Cmd+Shift+1  →  Quick capture: select region, copy straight to clipboard
  Cmd+Shift+2  →  Markup capture: select region, open markup editor

First run: grant Accessibility access to Terminal (or your Python interpreter)
  System Settings > Privacy & Security > Accessibility > add Terminal

Install dependencies once:
  python3 -m pip install -r requirements.txt
"""

import subprocess
import threading
import sys
import os
import tkinter as tk


_root = None
_daemon = None


def _quick_capture():
    from capture import CaptureOverlay
    CaptureOverlay(_root, _on_quick_done).start()


def _markup_capture():
    from capture import CaptureOverlay
    CaptureOverlay(_root, _on_markup_done).start()


def _on_quick_done(image):
    if image:
        from clipboard import copy_image_to_clipboard
        copy_image_to_clipboard(image)
        print('Copied to clipboard.')


def _on_markup_done(image):
    if image:
        from editor import EditorWindow
        EditorWindow(_root, image).show()


def _daemon_reader():
    """
    Reads lines from the hotkey daemon child process.
    Runs on a background thread — only does pipe I/O, no macOS UI APIs,
    so it cannot race with the main thread's TIS/TSM calls.
    """
    dispatch = {'QUICK': _quick_capture, 'MARKUP': _markup_capture}
    for raw in _daemon.stdout:
        cmd = raw.strip()
        fn = dispatch.get(cmd)
        if fn:
            _root.after(0, fn)   # hand off to tkinter main thread


def _start_daemon():
    global _daemon
    script = os.path.join(os.path.dirname(__file__), 'hotkey_daemon.py')
    _daemon = subprocess.Popen(
        [sys.executable, script],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    t = threading.Thread(target=_daemon_reader, daemon=True)
    t.start()


def main():
    global _root
    _root = tk.Tk()
    _root.withdraw()
    _root.title('Snappy')
    _root.protocol('WM_DELETE_WINDOW', lambda: None)

    _start_daemon()

    print('Snappy is running.')
    print('  Cmd+Shift+1  →  Quick capture to clipboard')
    print('  Cmd+Shift+2  →  Capture with markup editor')
    print('  Ctrl+C to quit\n')

    try:
        _root.mainloop()
    except KeyboardInterrupt:
        pass
    finally:
        if _daemon:
            _daemon.terminate()


if __name__ == '__main__':
    main()
