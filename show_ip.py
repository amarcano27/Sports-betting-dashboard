"""
Helper script to show your IP address for remote access
"""
import socket

def get_local_ip():
    """Get the local IP address of this machine."""
    try:
        # Connect to a remote address to determine local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "Unable to determine IP"

if __name__ == "__main__":
    ip = get_local_ip()
    print("="*60)
    print("SPORTS BETTING DASHBOARD - NETWORK ACCESS")
    print("="*60)
    print(f"\nYour IP Address: {ip}")
    print(f"\nAccess the dashboard from other devices:")
    print(f"  http://{ip}:8501")
    print(f"\nMake sure:")
    print("  1. Dashboard is running (start_remote.bat)")
    print("  2. Both devices are on the same Wi-Fi/network")
    print("  3. Firewall allows port 8501")
    print("="*60)

