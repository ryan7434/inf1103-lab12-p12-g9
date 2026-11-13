class TerminalText:
    #escape control characters while preserving newlines and tabs

    @staticmethod
    def escape(message, allow_layout=True):
        text = str(message)

        allowed = {"\n", "\t"} if allow_layout else set()

        return "".join(
            f"\\x{ord(character):02x}"
            if (
                ord(character) < 32
                and character not in allowed
            ) or 127 <= ord(character) <= 159
            else character
            for character in text
        )