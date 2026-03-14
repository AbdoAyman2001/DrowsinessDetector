import logging
import time
import threading

log = logging.getLogger("gsm_alarm")

try:
    import serial
    _SERIAL_AVAILABLE = True
except ImportError:
    _SERIAL_AVAILABLE = False
    log.warning("pyserial not available — GSM alarm disabled")


class GsmAlarm:
    def __init__(self, port: str, baud: int, phone_number: str, driver_name: str):
        self._port = port
        self._baud = baud
        self._phone_number = phone_number
        self._driver_name = driver_name
        self._ser = None
        self._lock = threading.Lock()
        self._last_alert_time = 0.0
        self._cooldown = 60.0  # seconds between alerts

        if _SERIAL_AVAILABLE:
            try:
                self._ser = serial.Serial(port, baud, timeout=1)
                time.sleep(0.5)
                self._ser.reset_input_buffer()
                resp = self._send_at("AT")
                if "OK" in resp:
                    log.info(f"GSM module ready on {port}")
                else:
                    log.warning(f"GSM module not responding on {port}")
            except Exception as e:
                log.error(f"Failed to open GSM serial port: {e}")
                self._ser = None

    def _send_at(self, command: str, timeout: float = 2) -> str:
        if not self._ser:
            return ""
        self._ser.reset_input_buffer()
        self._ser.write((command + "\r\n").encode())
        time.sleep(timeout)
        return self._ser.read(self._ser.in_waiting).decode(errors="replace").strip()

    def send_alert(self, photo_path: str = ""):
        """Send SMS + call in a background thread. Non-blocking."""
        now = time.time()
        if now - self._last_alert_time < self._cooldown:
            log.info("GSM alert skipped (cooldown)")
            return
        self._last_alert_time = now
        threading.Thread(target=self._do_alert, args=(photo_path,), daemon=True).start()

    def _do_alert(self, photo_path: str):
        if not self._ser:
            log.warning("GSM serial not available, skipping alert")
            return

        with self._lock:
            try:
                self._send_sms()
                time.sleep(2)
                self._make_call()
            except Exception as e:
                log.error(f"GSM alert failed: {e}")

    def _send_sms(self):
        msg = f"تنبيه: السائق {self._driver_name} يغلبه النعاس، رجاء اتصل عليه واطلب منه الراحه"
        # UCS2 SMS limit is 70 chars — truncate if needed
        if len(msg) > 70:
            msg = msg[:70]
        log.info(f"Sending SMS to {self._phone_number}")

        # PDU mode for Arabic (UCS2)
        self._send_at("AT+CMGF=0", 1)

        pdu = self._build_pdu(self._phone_number, msg)
        pdu_len = (len(pdu) - 2) // 2  # exclude SMSC length byte

        self._ser.reset_input_buffer()
        self._ser.write(f"AT+CMGS={pdu_len}\r".encode())
        time.sleep(1)

        self._ser.write((pdu + "\x1a").encode())
        time.sleep(10)
        resp = self._ser.read(self._ser.in_waiting).decode(errors="replace").strip()

        if "+CMGS:" in resp:
            log.info(f"SMS sent successfully: {resp}")
        else:
            log.error(f"SMS send failed: {resp}")

    def _make_call(self, duration: int = 15):
        log.info(f"Calling {self._phone_number} for {duration}s")
        resp = self._send_at(f"ATD{self._phone_number};", 3)
        log.info(f"Call response: {resp}")
        time.sleep(duration)
        resp = self._send_at("ATH", 2)
        log.info(f"Hangup response: {resp}")

    @staticmethod
    def _build_pdu(phone: str, message: str) -> str:
        smsc = "00"
        first_octet = "11"
        mr = "00"

        # Encode phone number
        num = phone.lstrip("+")
        num_type = "91"  # international
        padded = num + ("F" if len(num) % 2 else "")
        swapped = "".join(padded[i + 1] + padded[i] for i in range(0, len(padded), 2))
        phone_field = f"{len(num):02X}{num_type}{swapped}"

        pid = "00"
        dcs = "08"  # UCS2
        vp = "AA"

        msg_bytes = message.encode("utf-16-be")
        udl = f"{len(msg_bytes):02X}"
        ud = msg_bytes.hex().upper()

        return f"{smsc}{first_octet}{mr}{phone_field}{pid}{dcs}{vp}{udl}{ud}"

    def close(self):
        if self._ser:
            try:
                self._ser.close()
            except Exception:
                pass
            self._ser = None
