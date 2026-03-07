"""
ESP32 Bridge Module
Handles WiFi communication with ESP32-CAM for hardware control and video streaming.
Supports LCD display, buzzer, LED status indicator, and heartbeat mechanism.
"""

import time
import threading
from typing import Optional

# Optional dependency: only required when ESP32 simulation is disabled.
try:
    import requests
    _REQUESTS_IMPORT_ERROR = None
except ImportError as exc:
    requests = None
    _REQUESTS_IMPORT_ERROR = exc

# Import configuration
try:
    import config
except ImportError:
    config = None


class ESP32Bridge:
    """
    Handles communication with ESP32-CAM for hardware control via WiFi.

    Controls:
    - 16x2 LCD display (I2C)
    - Passive buzzer for audio feedback
    - Status LED (managed via heartbeat)

    The ESP32-CAM runs both the video stream and peripheral control on the same device.
    """

    def __init__(
        self,
        esp32_ip: Optional[str] = None,
        port: int = 80,
        simulation: Optional[bool] = None,
        heartbeat_interval: int = 5,
    ):
        """
        Initialize the ESP32 bridge.

        Args:
            esp32_ip: IP address of the ESP32-CAM (default from config)
            port: HTTP port (default 80)
            simulation: If True, simulate hardware instead of real connection
            heartbeat_interval: Seconds between heartbeat signals
        """
        # Use config values if not specified
        if esp32_ip is None:
            esp32_ip = config.ESP32_CAM_IP if config else "192.168.1.100"
        if simulation is None:
            simulation = config.ESP32_SIMULATION if config else True

        self.esp32_ip = esp32_ip
        self.port = port
        self.base_url = f"http://{esp32_ip}:{port}"
        self.simulation = simulation
        self.is_connected = False
        self.timeout = config.ESP32_TIMEOUT if config else 5
        self.heartbeat_interval = heartbeat_interval

        # Heartbeat thread management
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._heartbeat_running = False

        # Recognition cooldown tracking (prevent duplicate signals)
        self._last_recognition: dict[str, float] = {}
        self._cooldown_seconds = config.RECOGNITION_COOLDOWN if config else 5

    def connect(self) -> bool:
        """
        Test connection to ESP32-CAM and start heartbeat.

        Returns:
            bool: True if connection successful
        """
        if self.simulation:
            print(f"[SIMULATION] ESP32 connected at {self.base_url}")
            self.is_connected = True
            return True

        if requests is None:
            print(
                "Failed to connect to ESP32-CAM: missing 'requests' package. "
                "Install with: pip install -r requirements.txt"
            )
            if _REQUESTS_IMPORT_ERROR:
                print(f"Import error details: {_REQUESTS_IMPORT_ERROR}")
            return False

        try:
            response = requests.get(f"{self.base_url}/status", timeout=self.timeout)
            if response.status_code == 200:
                self.is_connected = True
                data = response.json()
                print(f"Connected to ESP32-CAM at {self.base_url}")
                print(f"  Device: {data.get('device', 'Unknown')}")
                print(f"  Uptime: {data.get('uptime', 0)} seconds")
                print(f"  RSSI: {data.get('rssi', 'N/A')} dBm")
                return True
            return False
        except Exception as e:
            print(f"Failed to connect to ESP32-CAM: {e}")
            return False

    def disconnect(self):
        """Stop heartbeat and mark connection as closed."""
        self.stop_heartbeat()
        if self.simulation:
            print("[SIMULATION] ESP32 disconnected")
        self.is_connected = False

    def start_heartbeat(self):
        """Start the heartbeat thread to keep ESP32 LED solid."""
        if self._heartbeat_running:
            return

        self._heartbeat_running = True
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop, daemon=True
        )
        self._heartbeat_thread.start()
        print("Heartbeat started")

    def stop_heartbeat(self):
        """Stop the heartbeat thread."""
        self._heartbeat_running = False
        if self._heartbeat_thread is not None:
            self._heartbeat_thread.join(timeout=2)
            self._heartbeat_thread = None
        print("Heartbeat stopped")

    def _heartbeat_loop(self):
        """Background thread that sends periodic heartbeat signals."""
        while self._heartbeat_running:
            try:
                self.send_heartbeat()
            except Exception as e:
                print(f"Heartbeat error: {e}")

            # Sleep in small intervals to allow quick shutdown
            for _ in range(self.heartbeat_interval * 10):
                if not self._heartbeat_running:
                    break
                time.sleep(0.1)

    def send_heartbeat(self) -> Optional[dict]:
        """
        Send heartbeat signal to keep ESP32 LED solid.

        Returns:
            dict: Response from ESP32 or None on error
        """
        return self.send_command("/heartbeat")

    def send_command(self, endpoint: str, data: dict = None) -> Optional[dict]:
        """
        Send a command to ESP32 via HTTP.

        Args:
            endpoint: API endpoint (e.g., '/lcd', '/buzzer')
            data: Optional JSON data to send

        Returns:
            dict: Response from ESP32 or None on error
        """
        if self.simulation:
            print(f"[SIMULATION] Sending to {endpoint}: {data}")
            return self._simulate_response(endpoint, data)

        if requests is None:
            print(
                "Error sending command: missing 'requests' package. "
                "Install with: pip install -r requirements.txt"
            )
            if _REQUESTS_IMPORT_ERROR:
                print(f"Import error details: {_REQUESTS_IMPORT_ERROR}")
            return None

        if not self.is_connected:
            print("Error: Not connected to ESP32")
            return None

        try:
            url = f"{self.base_url}{endpoint}"
            if data:
                response = requests.post(url, json=data, timeout=self.timeout)
            else:
                response = requests.get(url, timeout=self.timeout)

            if response.status_code == 200:
                return response.json()
            return {"error": f"HTTP {response.status_code}"}
        except Exception as e:
            print(f"Error sending command: {e}")
            return None

    def _simulate_response(self, endpoint: str, data: dict = None) -> dict:
        """
        Simulate ESP32 responses for development.

        Args:
            endpoint: The endpoint that was "called"
            data: The data that was "sent"

        Returns:
            dict: Simulated response
        """
        responses = {
            "/status": {
                "status": "ok",
                "device": "ESP32-CAM (Simulated)",
                "uptime": 12345,
            },
            "/heartbeat": {"status": "ok", "timestamp": int(time.time() * 1000)},
            "/lcd": {"status": "ok", "message": "LCD updated"},
            "/lcd/clear": {"status": "ok", "message": "LCD cleared"},
            "/buzzer/success": {"status": "ok", "message": "Success tone played"},
            "/buzzer/error": {"status": "ok", "message": "Error tone played"},
            "/buzzer/late": {"status": "ok", "message": "Late tone played"},
            "/buzzer": {"status": "ok", "message": "Buzzer activated"},
        }

        return responses.get(endpoint, {"status": "ok", "endpoint": endpoint})

    def _check_cooldown(self, student_id: str) -> bool:
        """
        Check if a student is in cooldown period.

        Args:
            student_id: The student's ID

        Returns:
            bool: True if NOT in cooldown (signal should be sent)
        """
        now = time.time()
        last_time = self._last_recognition.get(student_id, 0)

        if now - last_time < self._cooldown_seconds:
            return False  # Still in cooldown

        self._last_recognition[student_id] = now
        return True

    # =========================================================================
    # Convenience methods for common hardware actions
    # =========================================================================

    def display_message(self, line1: str, line2: str = ""):
        """
        Display a message on the 16x2 LCD.

        Args:
            line1: Text for first line (max 16 chars)
            line2: Text for second line (max 16 chars)
        """
        return self.send_command("/lcd", {"line1": line1[:16], "line2": line2[:16]})

    def clear_display(self):
        """Clear the LCD display."""
        return self.send_command("/lcd/clear")

    def signal_success(self, student_name: str = "", student_id: str = ""):
        """
        Signal successful attendance.
        - Display success message on LCD
        - Play success buzzer tone

        Args:
            student_name: Name to display on LCD
            student_id: Student ID for cooldown tracking
        """
        # Check cooldown if student_id provided
        if student_id and not self._check_cooldown(student_id):
            return None  # Skip signal, still in cooldown

        self.display_message(
            "Welcome!", student_name[:16] if student_name else "Attendance OK"
        )
        return self.send_command("/buzzer/success")

    def signal_error(self, message: str = "Unknown"):
        """
        Signal error/unrecognized face.
        - Display error message on LCD
        - Play error buzzer tone

        Args:
            message: Error message to display
        """
        self.display_message("Not Recognized", message[:16])
        return self.send_command("/buzzer/error")

    def signal_late(self, student_name: str = "", student_id: str = ""):
        """
        Signal late attendance.

        Args:
            student_name: Name to display on LCD
            student_id: Student ID for cooldown tracking
        """
        # Check cooldown if student_id provided
        if student_id and not self._check_cooldown(student_id):
            return None  # Skip signal, still in cooldown

        self.display_message("Late Arrival", student_name[:16] if student_name else "")
        return self.send_command("/buzzer/late")

    def show_status(self, status: str):
        """
        Show system status on LCD.

        Args:
            status: Status message to display
        """
        return self.display_message("System Status:", status[:16])

    def show_ready(self):
        """Show ready status on LCD."""
        return self.display_message("System Ready", "Waiting...")

    def show_session_started(self, course_code: str = ""):
        """
        Show session started message on LCD.

        Args:
            course_code: Course code to display
        """
        return self.display_message("Session Active", course_code[:16])

    def show_session_ended(self):
        """Show session ended message on LCD."""
        return self.display_message("Session Ended", "Thank you!")

    def get_status(self) -> Optional[dict]:
        """Get the current ESP32 status."""
        return self.send_command("/status")


# =============================================================================
# Global singleton instance
# =============================================================================

_esp32_bridge_instance: Optional[ESP32Bridge] = None


def get_esp32_bridge(force_new: bool = False, esp32_ip: Optional[str] = None) -> ESP32Bridge:
    """
    Get or create the global ESP32Bridge instance.

    Args:
        force_new: If True, create a new instance even if one exists
        esp32_ip: IP address of the ESP32-CAM (overrides config if provided)

    Returns:
        ESP32Bridge instance
    """
    global _esp32_bridge_instance

    if force_new and _esp32_bridge_instance is not None:
        _esp32_bridge_instance.disconnect()
        _esp32_bridge_instance = None

    if _esp32_bridge_instance is None:
        _esp32_bridge_instance = ESP32Bridge(esp32_ip=esp32_ip)

    return _esp32_bridge_instance


def reset_esp32_bridge():
    """Reset the global ESP32Bridge instance."""
    global _esp32_bridge_instance
    if _esp32_bridge_instance is not None:
        _esp32_bridge_instance.disconnect()
        _esp32_bridge_instance = None


if __name__ == "__main__":
    # Test the ESP32 bridge
    print("Testing ESP32 Bridge...")
    print("=" * 50)

    # Check if running in simulation mode
    sim_mode = config.ESP32_SIMULATION if config else True
    print(f"Simulation mode: {sim_mode}")
    print()

    bridge = ESP32Bridge()

    # Connect
    if bridge.connect():
        print("\nTesting LCD and Buzzer commands:")

        bridge.signal_success("John Doe", "STU001")
        time.sleep(1)

        bridge.signal_late("Jane Smith", "STU002")
        time.sleep(1)

        bridge.signal_error("Unknown face")
        time.sleep(1)

        bridge.show_ready()

        # Get status
        status = bridge.get_status()
        print(f"\nESP32 status: {status}")

        # Test heartbeat
        print("\nTesting heartbeat (5 seconds)...")
        bridge.start_heartbeat()
        time.sleep(5)
        bridge.stop_heartbeat()

        # Disconnect
        bridge.disconnect()
    else:
        print("Failed to connect to ESP32")

    print("\n" + "=" * 50)
    print("Test complete!")
