# modules/display_handler.py
import st7036

class DisplayHandler:
    def __init__(self):
        self.lcd = st7036.st7036(register_select_pin=25, reset_pin=12)
        self.lcd.set_contrast(50)
        self.clear()

    def clear(self):
        self.lcd.clear()

    def write(self, text: str):
        self.clear()
        self.lcd.write(text[:32])  # two lines, 16 chars each
