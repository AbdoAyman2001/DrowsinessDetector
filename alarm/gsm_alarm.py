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

# Responses that indicate a completed AT command
_TERMINATORS = ("OK", "ERROR", ">", "NO CARRIER", "NO ANSWER", "BUSY", "NO DIALTONE", "CONNECT")


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
        self._busy = False

        if _SERIAL_AVAILABLE:
            try:
                self._ser = serial.Serial(port, baud, timeout=1)
                time.sleep(0.5)
                self._ser.reset_input_buffer()
                resp = self._send_at("AT")
                if "OK" in resp:
                    self._send_at("ATE0", 1)  # disable command echo
                    log.info(f"GSM module ready on {port}")
                else:
                    log.warning(f"GSM module not responding on {port}")
            except Exception as e:
                log.error(f"Failed to open GSM serial port: {e}")
                self._ser = None

    def _send_at(self, command: str, timeout: float = 2) -> str:
        """Send an AT command and poll for a response until a terminator or timeout."""
        if not self._ser:
            return ""
        self._ser.reset_input_buffer()
        self._ser.write((command + "\r\n").encode())
        response = ""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self._ser.in_waiting:
                response += self._ser.read(self._ser.in_waiting).decode(errors="replace")
                if any(t in response for t in _TERMINATORS):
                    break
            time.sleep(0.1)
        return response.strip()

    def _reset_module(self):
        """Ensure module is in command mode (cancel any pending PDU input)."""
        if not self._ser:
            return
        self._ser.write(b"\x1b")  # ESC — cancel any pending PDU input
        time.sleep(0.3)
        self._ser.reset_input_buffer()
        self._send_at("AT", 1)

    def send_alert(self, photo_path: str = ""):
        """Send SMS + call in a background thread. Non-blocking."""
        now = time.time()
        if now - self._last_alert_time < self._cooldown:
            log.info("GSM alert skipped (cooldown)")
            return
        if self._busy:
            log.info("GSM alert skipped (busy)")
            return
        self._busy = True
        threading.Thread(target=self._do_alert, args=(photo_path,), daemon=True).start()

    def _do_alert(self, photo_path: str):
        if not self._ser:
            log.warning("GSM serial not available, skipping alert")
            self._busy = False
            return

        with self._lock:
            try:
                self._send_sms()
            except Exception as e:
                log.error(f"SMS failed: {e}")

            # Always reset module state before calling, even if SMS failed
            self._reset_module()

            try:
                self._make_call()
            except Exception as e:
                log.error(f"Call failed: {e}")

        self._last_alert_time = time.time()  # cooldown starts AFTER completion
        self._busy = False

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

        # Send CMGS command and poll for '>' prompt
        self._ser.reset_input_buffer()
        self._ser.write(f"AT+CMGS={pdu_len}\r".encode())

        deadline = time.monotonic() + 5
        got_prompt = False
        while time.monotonic() < deadline:
            if self._ser.in_waiting:
                data = self._ser.read(self._ser.in_waiting).decode(errors="replace")
                if ">" in data:
                    got_prompt = True
                    break
                if "ERROR" in data:
                    log.error(f"CMGS rejected: {data}")
                    return
            time.sleep(0.1)

        if not got_prompt:
            log.error("No '>' prompt from CMGS, aborting SMS")
            self._ser.write(b"\x1b")  # cancel
            time.sleep(0.5)
            return

        # Send PDU body + Ctrl-Z to commit
        self._ser.write((pdu + "\x1a").encode())

        # Poll for SMS confirmation (up to 15 seconds — network can be slow)
        response = ""
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if self._ser.in_waiting:
                response += self._ser.read(self._ser.in_waiting).decode(errors="replace")
                if "+CMGS:" in response or "ERROR" in response:
                    break
            time.sleep(0.2)

        if "+CMGS:" in response:
            log.info(f"SMS sent successfully: {response.strip()}")
        else:
            log.error(f"SMS send failed: {response.strip()}")

    def _make_call(self, duration: int = 15, retries: int = 2):
        _CALL_ERRORS = ("ERROR", "NO CARRIER", "NO ANSWER", "BUSY", "NO DIALTONE")

        for attempt in range(retries + 1):
            log.info(f"Calling {self._phone_number} (attempt {attempt + 1}/{retries + 1})")
            resp = self._send_at(f"ATD{self._phone_number};", 10)
            log.info(f"Call response: {resp}")

            if not any(e in resp for e in _CALL_ERRORS):
                # Call appears to be connecting — wait for ring/talk duration
                time.sleep(duration)
                hangup = self._send_at("ATH", 2)
                log.info(f"Call completed. Hangup: {hangup}")
                return

            log.warning(f"Call attempt {attempt + 1} failed: {resp}")
            if attempt < retries:
                time.sleep(3)
                self._reset_module()

        log.error(f"Call failed after {retries + 1} attempts")

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
