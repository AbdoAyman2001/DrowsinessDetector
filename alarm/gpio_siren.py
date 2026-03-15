import logging

log = logging.getLogger("gpio_siren")

try:
    import RPi.GPIO as GPIO
    _GPIO_AVAILABLE = True
except ImportError:
    _GPIO_AVAILABLE = False
    log.warning("RPi.GPIO not available — siren disabled")


class GpioSiren:
    def __init__(self, pin: int = 17):
        self._pin = pin
        self._active = False
        if _GPIO_AVAILABLE:
            GPIO.setwarnings(False)
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self._pin, GPIO.OUT, initial=GPIO.LOW)

    def on(self):
        if _GPIO_AVAILABLE and not self._active:
            GPIO.output(self._pin, GPIO.HIGH)
            self._active = True

    def off(self):
        if _GPIO_AVAILABLE and self._active:
            GPIO.output(self._pin, GPIO.LOW)
            self._active = False

    def close(self):
        self.off()
        if _GPIO_AVAILABLE:
            GPIO.cleanup(self._pin)
