#!/usr/bin/env python3
"""
SIM800L GSM Module Diagnostic & Interactive Terminal

Usage:
    python tools/gsm_diag.py [--port /dev/serial0] [--baud 115200]

Runs auto-diagnostic AT commands, then drops into interactive mode.
"""

import sys
import time
import argparse

try:
    import serial
except ImportError:
    print("ERROR: pyserial not installed. Run: pip install pyserial")
    sys.exit(1)


def send_at(ser, command, timeout=2):
    """Send AT command and return response lines."""
    ser.reset_input_buffer()
    ser.write((command + "\r\n").encode())
    time.sleep(timeout)
    response = ser.read(ser.in_waiting).decode(errors="replace").strip()
    return response


def parse_csq(response):
    """Parse signal quality from AT+CSQ response."""
    for line in response.splitlines():
        if "+CSQ:" in line:
            parts = line.split(":")[1].strip().split(",")
            rssi = int(parts[0])
            if rssi == 99:
                return "No signal (99)"
            dbm = -113 + 2 * rssi
            if rssi < 10:
                quality = "Marginal"
            elif rssi < 15:
                quality = "OK"
            elif rssi < 20:
                quality = "Good"
            else:
                quality = "Excellent"
            return f"RSSI={rssi} ({dbm} dBm) — {quality}"
    return "Could not parse"


def parse_creg(response):
    """Parse network registration from AT+CREG? response."""
    status_map = {
        "0": "Not registered, not searching",
        "1": "Registered, home network",
        "2": "Not registered, searching...",
        "3": "Registration denied",
        "4": "Unknown",
        "5": "Registered, roaming",
    }
    for line in response.splitlines():
        if "+CREG:" in line:
            parts = line.split(":")[1].strip().split(",")
            stat = parts[1].strip() if len(parts) > 1 else parts[0].strip()
            return status_map.get(stat, f"Unknown status ({stat})")
    return "Could not parse"


def parse_cpin(response):
    """Parse SIM status from AT+CPIN? response."""
    for line in response.splitlines():
        if "+CPIN:" in line:
            status = line.split(":")[1].strip()
            explanations = {
                "READY": "SIM is ready (no PIN required)",
                "SIM PIN": "SIM requires PIN code — use AT+CPIN=\"xxxx\"",
                "SIM PUK": "SIM is PUK-locked — needs PUK code",
                "NOT INSERTED": "No SIM card detected",
            }
            return explanations.get(status, f"Status: {status}")
    if "ERROR" in response:
        return "ERROR — SIM not detected or not responding"
    return "Could not parse"


def parse_cbc(response):
    """Parse battery/voltage from AT+CBC response."""
    for line in response.splitlines():
        if "+CBC:" in line:
            parts = line.split(":")[1].strip().split(",")
            if len(parts) >= 3:
                voltage_mv = int(parts[2])
                return f"{voltage_mv} mV ({voltage_mv/1000:.2f} V)"
    return "Could not parse"


def run_diagnostic(ser):
    """Run auto-diagnostic sequence."""
    print("=" * 60)
    print("  SIM800L Auto-Diagnostic")
    print("=" * 60)

    tests = [
        ("AT", "Basic communication", None),
        ("ATI", "Module identification", None),
        ("AT+CFUN?", "Functionality mode (1=full, 0=minimum, 4=flight)", None),
        ("AT+CPIN?", "SIM card status", parse_cpin),
        ("AT+CSQ", "Signal quality", parse_csq),
        ("AT+CREG?", "Network registration", parse_creg),
        ("AT+COPS?", "Current operator", None),
        ("AT+CBC", "Voltage level", parse_cbc),
    ]

    results = {}
    for cmd, description, parser in tests:
        print(f"\n--- {description} [{cmd}] ---")
        response = send_at(ser, cmd)
        print(f"  Raw: {response}")
        if parser:
            parsed = parser(response)
            print(f"  >>> {parsed}")
            results[cmd] = parsed
        elif "OK" in response:
            print("  >>> OK")
        elif "ERROR" in response:
            print("  >>> FAILED")

    # Summary
    print("\n" + "=" * 60)
    print("  Diagnostic Summary")
    print("=" * 60)

    if "ERROR" in results.get("AT+CPIN?", ""):
        print("  [!] SIM card not detected — check SIM is inserted correctly")
    elif "PIN" in results.get("AT+CPIN?", ""):
        print("  [!] SIM requires PIN — unlock it first")

    if "No signal" in results.get("AT+CSQ", ""):
        print("  [!] No signal — check antenna connection")
        print("      Also check: is the SIM card active? Does it have service?")

    if "searching" in results.get("AT+CREG?", "").lower():
        print("  [!] Module is searching for network — may need more time")
        print("      Or signal is too weak / SIM has no service plan")
    elif "denied" in results.get("AT+CREG?", "").lower():
        print("  [!] Registration DENIED by network")
        print("      SIM may be blocked, expired, or incompatible with local networks")
    elif "home" in results.get("AT+CREG?", "").lower() or "roaming" in results.get("AT+CREG?", "").lower():
        print("  [OK] Module is registered on network!")

    # Offer operator scan
    print("\n--- Scanning available operators [AT+COPS=?] (takes ~30s) ---")
    response = send_at(ser, "AT+COPS=?", timeout=45)
    print(f"  Raw: {response}")


def interactive_mode(ser):
    """Interactive AT command terminal."""
    print("\n" + "=" * 60)
    print("  Interactive AT Terminal")
    print("  Type AT commands. Press Ctrl+C to exit.")
    print("=" * 60)

    while True:
        try:
            cmd = input("\nAT> ").strip()
            if not cmd:
                continue
            response = send_at(ser, cmd, timeout=3)
            print(response)
        except KeyboardInterrupt:
            print("\n\nExiting.")
            break


def main():
    parser = argparse.ArgumentParser(description="SIM800L GSM Diagnostic Tool")
    parser.add_argument("--port", default="/dev/serial0", help="Serial port (default: /dev/serial0)")
    parser.add_argument("--baud", type=int, default=115200, help="Baud rate (default: 115200)")
    args = parser.parse_args()

    print(f"Opening {args.port} at {args.baud} baud...")

    try:
        ser = serial.Serial(args.port, args.baud, timeout=1)
    except serial.SerialException as e:
        print(f"ERROR: Cannot open {args.port}: {e}")
        print("\nTroubleshooting:")
        print("  1. Check port exists: ls -la /dev/serial*")
        print("  2. Check permissions: sudo usermod -aG dialout $USER")
        print("  3. Disable serial console: sudo raspi-config -> Interface -> Serial")
        print("     -> Disable login shell, Enable serial port hardware")
        print("  4. Reboot after changes")
        sys.exit(1)

    try:
        # Flush any stale data
        time.sleep(0.5)
        ser.reset_input_buffer()

        run_diagnostic(ser)
        interactive_mode(ser)
    finally:
        ser.close()
        print("Serial port closed.")


if __name__ == "__main__":
    main()
