#!/bin/bash
set -e

AP_SSID="DrowsinessDetector"
AP_PASSWORD="${1:-DriveAlert2024}"
AP_IP="192.168.4.1"
DHCP_START="192.168.4.10"
DHCP_END="192.168.4.50"

echo "=== Drowsiness Detector WiFi Hotspot Setup ==="
echo "SSID: $AP_SSID"
echo "Password: $AP_PASSWORD"
echo "Pi IP: $AP_IP"
echo ""

# Install packages
echo "[1/6] Installing hostapd and dnsmasq..."
sudo apt-get update -qq
sudo apt-get install -y hostapd dnsmasq

# Stop services during configuration
echo "[2/6] Stopping services..."
sudo systemctl stop hostapd 2>/dev/null || true
sudo systemctl stop dnsmasq 2>/dev/null || true
sudo systemctl unmask hostapd

# Configure hostapd
echo "[3/6] Configuring hostapd..."
sudo tee /etc/hostapd/hostapd.conf > /dev/null <<EOF
interface=wlan0
driver=nl80211
ssid=${AP_SSID}
hw_mode=g
channel=6
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase=${AP_PASSWORD}
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
EOF

# Point hostapd daemon to config
sudo sed -i 's|#\?DAEMON_CONF=.*|DAEMON_CONF="/etc/hostapd/hostapd.conf"|' /etc/default/hostapd 2>/dev/null || true

# Configure dnsmasq
echo "[4/6] Configuring dnsmasq..."
sudo tee /etc/dnsmasq.d/hotspot.conf > /dev/null <<EOF
interface=wlan0
dhcp-range=${DHCP_START},${DHCP_END},255.255.255.0,12h
domain=local
no-resolv
bogus-priv
EOF

# Configure static IP for wlan0
echo "[5/6] Configuring static IP..."
if ! grep -q "interface wlan0" /etc/dhcpcd.conf 2>/dev/null; then
    sudo tee -a /etc/dhcpcd.conf > /dev/null <<EOF

# Drowsiness Detector hotspot
interface wlan0
    static ip_address=${AP_IP}/24
    nohook wpa_supplicant
EOF
else
    echo "  wlan0 config already exists in dhcpcd.conf, skipping"
fi

# Enable and start services
echo "[6/6] Enabling services..."
sudo systemctl enable hostapd
sudo systemctl enable dnsmasq
sudo systemctl start hostapd
sudo systemctl start dnsmasq

echo ""
echo "=== Hotspot configured successfully ==="
echo "SSID: $AP_SSID"
echo "Password: $AP_PASSWORD"
echo "Pi IP: $AP_IP"
echo "Dashboard: http://${AP_IP}:5000"
echo ""
echo "Reboot recommended: sudo reboot"
