from datetime import datetime


class ErrorLogger:
    """Appends timestamped lines to a log file and echoes them to the terminal.

    Logging must never be the reason the app crashes, so file errors are ignored.
    """

    def __init__(self, log_file: str = "ai_manager_errors.log", prefix: str = "ai_manager") -> None:
        self._log_file = log_file
        self._prefix = prefix

    @property
    def log_file(self) -> str:
        return self._log_file

    def log(self, message: str) -> None:
        try:
            with open(self._log_file, "a", encoding="utf-8") as log_file:
                log_file.write(f"[{datetime.now().isoformat()}] {message}\n")
        except OSError:
            pass
        print(f"[{self._prefix}] {message}")
