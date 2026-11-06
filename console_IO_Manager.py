class ConsoleIO:
    """Handles reusable console prompts and basic input validation."""

    def __init__(self, input_func=None, output_func=None):
        self._input = input if input_func is None else input_func
        self._output = print if output_func is None else output_func

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
        #prompt the user to enter a whole number within a specified range.
        while True:
            user_input = self._input(prompt).strip()

            if not user_input:
                #reject blank input and restart the loop
                self._output("Input cannot be blank.")
                continue

            #digits only (rejects "1_0", "3.5", "-2" and text)
            if not user_input.isdecimal():
                self._output(
                    "Invalid input. Please enter a whole number using digits only."
                )
                continue

            value = int(user_input)

            if not minimum <= value <= maximum:
                self._output(
                    f"Invalid input. Please enter a whole number "
                    f"from {minimum} to {maximum}."
                )
                continue

            return value