# modules/display_handler.py
import logging
import st7036
import threading
import time

try:
    from modules.dothat import backlight
except Exception as e:
    backlight = None
    logging.warning(f"⚠️  DotHAT backlight not available: {e}")


class DisplayHandler:
    def __init__(self):
        logging.info("🟢 Initialising ST7036 display")

        self.lcd = st7036.st7036(register_select_pin=25, reset_pin=12)
        self.lcd.set_contrast(50)
        self.clear()

        # --- Backlight ---
        self._pulse_thread = None
        self._pulse_active = False
        self._pulse_color = (0, 0, 255)

        if backlight:
            backlight.sn3218.enable()
            backlight.rgb(0, 0, 255)
            logging.info("💡 DotHAT backlight initialised (blue)")
        else:
            logging.warning("⚠️  No backlight driver found")

    # === LCD Methods ===
    def clear(self):
        self.lcd.clear()
        logging.debug("🧹 LCD cleared")

    def write(self, text: str):
        text = str(text)
        logging.info(f"🖋️ LCD text: {text}")
        self.clear()
        self.lcd.write(text[:32])  # two lines, 16 chars each

    # === Backlight Control ===
    def set_color(self, r: int, g: int, b: int):
        if backlight:
            backlight.rgb(r, g, b)
            logging.info(f"💡 Backlight colour set to RGB({r},{g},{b})")

    def off(self):
        if backlight:
            backlight.off()
            logging.info("💡 Backlight turned off")

    # === Pulse Control ===
    def start_pulse(self, color=(0, 0, 255), speed=2.0):
        """Start a smooth pulsing effect."""
        if not backlight:
            return
        if self._pulse_active:
            return  # already pulsing

        self._pulse_color = color
        self._pulse_active = True

        def _pulse():
            r, g, b = color
            step_time = 0.05
            steps = int(speed / step_time)
            while self._pulse_active:
                # Fade in
                for i in range(steps):
                    if not self._pulse_active: break
                    scale = (i / steps)
                    backlight.rgb(int(r * scale), int(g * scale), int(b * scale))
                    time.sleep(step_time)
                # Fade out
                for i in range(steps, -1, -1):
                    if not self._pulse_active: break
                    scale = (i / steps)
                    backlight.rgb(int(r * scale), int(g * scale), int(b * scale))
                    time.sleep(step_time)
            # Restore steady colour
            backlight.rgb(*color)

        self._pulse_thread = threading.Thread(target=_pulse, daemon=True)
        self._pulse_thread.start()
        logging.info("💓 Backlight pulse started")

    def stop_pulse(self):
        """Stop the pulsing effect."""
        if not backlight:
            return
        self._pulse_active = False
        if self._pulse_thread:
            self._pulse_thread.join(timeout=0.5)
            self._pulse_thread = None
        backlight.rgb(*self._pulse_color)
        logging.info("💤 Backlight pulse stopped")

    # === Fancy effects ===
    def fade_in(self, duration=1.5, steps=30, color=(0, 0, 255)):
        """Softly fade the backlight in."""
        if not backlight:
            return
        r, g, b = color
        for i in range(steps + 1):
            scale = i / steps
            backlight.rgb(int(r * scale), int(g * scale), int(b * scale))
            time.sleep(duration / steps)
        backlight.rgb(*color)
        logging.info("🌅 Fade-in complete")

    def fade_out(self, duration=1.5, steps=30):
        """Softly fade the backlight out."""
        if not backlight:
            return
        current = getattr(self, "_pulse_color", (0, 0, 255))
        r, g, b = current
        for i in range(steps, -1, -1):
            scale = i / steps
            backlight.rgb(int(r * scale), int(g * scale), int(b * scale))
            time.sleep(duration / steps)
        backlight.off()
        logging.info("🌇 Fade-out complete")
