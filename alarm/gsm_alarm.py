"""
GSM Alarm Stub — Future SIM800 SMS/Call Integration

To implement:
1. Connect SIM800 module to RPi UART (TX/RX) or USB
2. Use pyserial to send AT commands:
   - AT+CMGS to send SMS
   - ATD<number>; to make a voice call
3. Integrate with AlarmManager as a backend alongside AudioAlarm

Example AT command flow for SMS:
    ser.write(b'AT+CMGF=1\\r')       # Text mode
    ser.write(b'AT+CMGS="<number>"\\r')
    ser.write(b'DROWSINESS ALERT!\\x1a')

Example AT command flow for call:
    ser.write(b'ATD<number>;\\r')     # Voice call
    time.sleep(15)
    ser.write(b'ATH\\r')              # Hang up
"""


class GsmAlarm:
    def __init__(self, port: str, baud: int, phone_number: str):
        self._port = port
        self._baud = baud
        self._phone_number = phone_number

    def send_sms(self, message: str):
        raise NotImplementedError("GSM SMS not yet implemented")

    def make_call(self, duration_seconds: int = 15):
        raise NotImplementedError("GSM call not yet implemented")
