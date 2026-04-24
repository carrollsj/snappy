"""macOS clipboard and iMessage helpers."""

import subprocess
import tempfile
import os


def copy_image_to_clipboard(image):
    """Copy a PIL Image to the macOS clipboard as PNG."""
    fd, path = tempfile.mkstemp(suffix='.png')
    os.close(fd)
    try:
        image.save(path, 'PNG')
        script = (
            f'set posixPath to "{path}"\n'
            f'set theFile to POSIX file posixPath\n'
            f'set the clipboard to (read theFile as «class PNGf»)\n'
        )
        subprocess.run(['osascript', '-e', script], check=True, capture_output=True)
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def send_via_imessage(image, contact):
    """Send a PIL Image via iMessage. Returns True on success."""
    # Save to home dir — temp dirs can be sandboxed and unreadable by Messages
    fd, path = tempfile.mkstemp(suffix='.png', dir=os.path.expanduser('~'))
    os.close(fd)
    image.save(path, 'PNG')

    script = f'''
tell application "Messages"
    set targetAddress to "{contact}"
    set targetService to first service whose service type is iMessage
    send POSIX file "{path}" to buddy targetAddress of targetService
end tell
'''
    result = subprocess.run(
        ['osascript', '-e', script],
        capture_output=True, text=True
    )

    # Delete after 30 s — Messages needs time to read the file
    subprocess.Popen(
        ['bash', '-c', f'sleep 30 && rm -f "{path}"'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )

    return result.returncode == 0
