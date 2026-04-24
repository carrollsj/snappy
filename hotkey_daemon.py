"""
Hotkey daemon — runs in a child process with NO tkinter/AppKit loaded.
Writes 'QUICK' or 'MARKUP' to stdout when the hotkeys fire.
Isolation from the parent's UI run loop is what prevents the TIS/TSM
concurrent-thread crash (HIToolbox SIGABRT).
"""
import sys
from pynput import keyboard


def _emit(cmd):
    sys.stdout.write(cmd + '\n')
    sys.stdout.flush()


hotkeys = {
    '<cmd>+<shift>+1': lambda: _emit('QUICK'),
    '<cmd>+<shift>+2': lambda: _emit('MARKUP'),
}

with keyboard.GlobalHotKeys(hotkeys) as listener:
    listener.join()
