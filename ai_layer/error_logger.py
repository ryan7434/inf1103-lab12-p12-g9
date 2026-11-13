from datetime import datetime
from terminal_text import TerminalText

# Records problems so they can be read later, both in a file and on screen.
class ErrorLogger:
    """Appends timestamped lines to a log file and echoes them to the terminal.

    Logging must never be the reason the app crashes, so file errors are ignored.
    """

    def __init__(self, log_file: str = "ai_manager_errors.log", prefix: str = "ai_manager") -> None:
        self._log_file = log_file   # where messages are saved
        self._prefix = prefix   # label shown before each message on screen

    # Read-only access to the log file name (useful for tests).
    @property
    def log_file(self) -> str:
        return self._log_file

    def log(self, message: str) -> None:
        safe_message = TerminalText.escape(
            message,
            allow_layout=False,
        )
        safe_prefix = TerminalText.escape(
            self._prefix,
            allow_layout=False,
        )
        # Append mode ("a") adds to the end of the file instead of overwriting it.
        try:
            with open(self._log_file, "a", encoding="utf-8") as log_file:
                log_file.write(
                    f"[{datetime.now().isoformat()}] {safe_message}\n"
                )
        except OSError:
            #If the file can't be written (permissions, disk full...), skip it quietly
            # so a logging problem never crashes the app.
            pass
        # Always show the message in the terminal too.
        print(f"[{safe_prefix}] {safe_message}")
