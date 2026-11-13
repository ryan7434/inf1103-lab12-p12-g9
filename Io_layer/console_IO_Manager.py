from terminal_text import TerminalText

class ConsoleIO:
    """Handles reusable console prompts and basic input validation."""

    def __init__(self, input_func=None, output_func=None):
        self._input = input if input_func is None else input_func
        self._raw_output = print if output_func is None else output_func
        self._output = self._safe_output

    def _safe_output(self, message): #escape terminal controls before displaying console outputs
        self._raw_output(TerminalText.escape(message))

    def read(self, prompt):
        return self._input(prompt)

    def write(self, message):
        self._output(message)

    def get_yes_no(self, prompt):
        while True:
            response = self._input(prompt).strip().lower()

            if response in {"y", "yes"}:
                return True

            if response in {"n", "no"}:
                return False

            self._output("Invalid input. Please enter Y or N.")

    def choosing_options(self, title, options, prompt="Enter your choice: "):
        #display a menu of options and return the user's choice.
        while True:
            self._output(f"\n{title}")

            for key, label in options.items():
                self._output(f"{key}. {label}")

            choice = self._input(f"\n{prompt}").strip()

            if choice in options:
                return choice

            self._output(
                f"Invalid input. Enter a number from 1 to {len(options)}."
            )

    def get_whole_number_in_range(self, prompt, minimum, maximum):
        #prompt until a whole number within the specified range is entered
        max_input_characters = 100
        while True:
            user_input = self._input(prompt).strip()
            if not user_input:
                self._output("Input cannot be blank.")
                continue

            #reject excessive input before checking or converting digits
            if len(user_input) > max_input_characters:
                self._output(
                    "Invalid input. Please enter no more than "
                    f"{max_input_characters} characters."
                )
                continue

            if not user_input.isdecimal():
                self._output(
                    "Invalid input. Please enter a whole number "
                    "using digits only."
                )
                continue
            try:
                value = int(user_input)
            except ValueError:
                self._output(
                    "Invalid input. Please enter a valid whole number."
                )
                continue

            if not minimum <= value <= maximum:
                self._output(
                    "Invalid input. Please enter a whole number "
                    f"from {minimum} to {maximum}."
                )
                continue
            return value