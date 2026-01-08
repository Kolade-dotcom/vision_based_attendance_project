"""
ESP32 Bridge Module
Handles WiFi communication with ESP32 hardware components.
Replaces the Arduino serial bridge with HTTP-based communication.
"""

import requests
import time
from typing import Optional


class ESP32Bridge:
    """
    Handles communication with ESP32 for hardware control via WiFi.
    Supports both real hardware and simulation mode for development.
    """
    
    def __init__(self, esp32_ip: str = '192.168.1.100', port: int = 80, simulation: bool = True):
        """
        Initialize the ESP32 bridge.
        
        Args:
            esp32_ip: IP address of the ESP32 on the local network
            port: HTTP port (default 80)
            simulation: If True, simulate hardware instead of real connection
        """
        self.esp32_ip = esp32_ip
        self.port = port
        self.base_url = f"http://{esp32_ip}:{port}"
        self.simulation = simulation
        self.is_connected = False
        self.timeout = 5  # HTTP request timeout in seconds
    
    def connect(self) -> bool:
        """
        Test connection to ESP32.
        
        Returns:
            bool: True if connection successful
        """
        if self.simulation:
            print(f"[SIMULATION] ESP32 connected at {self.base_url}")
            self.is_connected = True
            return True
        
        try:
            response = requests.get(f"{self.base_url}/status", timeout=self.timeout)
            if response.status_code == 200:
                self.is_connected = True
                print(f"Connected to ESP32 at {self.base_url}")
                return True
            return False
        except requests.exceptions.RequestException as e:
            print(f"Failed to connect to ESP32: {e}")
            return False
    
    def disconnect(self):
        """Mark connection as closed."""
        if self.simulation:
            print("[SIMULATION] ESP32 disconnected")
        self.is_connected = False
    
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
            return {'error': f'HTTP {response.status_code}'}
        except requests.exceptions.RequestException as e:
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
            '/status': {'status': 'ok', 'device': 'ESP32', 'uptime': 12345},
            '/lcd': {'status': 'ok', 'message': 'LCD updated'},
            '/lcd/clear': {'status': 'ok', 'message': 'LCD cleared'},
            '/buzzer/success': {'status': 'ok', 'message': 'Success tone played'},
            '/buzzer/error': {'status': 'ok', 'message': 'Error tone played'},
            '/buzzer': {'status': 'ok', 'message': 'Buzzer activated'},
        }
        
        return responses.get(endpoint, {'status': 'ok', 'endpoint': endpoint})
    
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
        return self.send_command('/lcd', {
            'line1': line1[:16],
            'line2': line2[:16]
        })
    
    def clear_display(self):
        """Clear the LCD display."""
        return self.send_command('/lcd/clear')
    
    def signal_success(self, student_name: str = ""):
        """
        Signal successful attendance.
        - Display success message on LCD
        - Play success buzzer tone
        
        Args:
            student_name: Name to display on LCD
        """
        self.display_message("Attendance OK!", student_name[:16] if student_name else "Welcome")
        return self.send_command('/buzzer/success')
    
    def signal_error(self, message: str = "Unknown"):
        """
        Signal error/unrecognized face.
        - Display error message on LCD
        - Play error buzzer tone
        
        Args:
            message: Error message to display
        """
        self.display_message("Not Recognized", message[:16])
        return self.send_command('/buzzer/error')
    
    def signal_late(self, student_name: str = ""):
        """
        Signal late attendance.
        
        Args:
            student_name: Name to display on LCD
        """
        self.display_message("Late Arrival", student_name[:16] if student_name else "")
        return self.send_command('/buzzer/success')
    
    def show_status(self, status: str):
        """
        Show system status on LCD.
        
        Args:
            status: Status message to display
        """
        return self.display_message("System Status:", status[:16])
    
    def get_status(self) -> Optional[dict]:
        """Get the current ESP32 status."""
        return self.send_command('/status')


# ESP32-CAM specific functions
class ESP32CamBridge:
    """
    Handles video stream from ESP32-CAM.
    """
    
    def __init__(self, cam_ip: str = '192.168.1.101', stream_port: int = 81):
        """
        Initialize ESP32-CAM bridge.
        
        Args:
            cam_ip: IP address of ESP32-CAM
            stream_port: Port for video stream (default 81 for ESP32-CAM)
        """
        self.cam_ip = cam_ip
        self.stream_port = stream_port
        self.stream_url = f"http://{cam_ip}:{stream_port}/stream"
        self.snapshot_url = f"http://{cam_ip}/capture"
    
    def get_stream_url(self) -> str:
        """
        Get the video stream URL for OpenCV.
        
        Returns:
            str: URL that can be passed to cv2.VideoCapture()
        """
        return self.stream_url
    
    def get_snapshot_url(self) -> str:
        """
        Get URL for single frame capture.
        
        Returns:
            str: URL for snapshot endpoint
        """
        return self.snapshot_url
    
    def test_connection(self) -> bool:
        """
        Test if ESP32-CAM is accessible.
        
        Returns:
            bool: True if camera is reachable
        """
        try:
            response = requests.get(f"http://{self.cam_ip}/status", timeout=5)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False


if __name__ == '__main__':
    # Test the ESP32 bridge in simulation mode
    print("Testing ESP32 Bridge (Simulation Mode)...")
    print("=" * 50)
    
    bridge = ESP32Bridge(simulation=True)
    
    # Connect
    bridge.connect()
    
    # Test various commands
    print("\nTesting LCD and Buzzer commands:")
    bridge.signal_success("Kolade Salako")
    time.sleep(0.5)
    bridge.signal_error("Face not found")
    time.sleep(0.5)
    bridge.signal_late("Late Student")
    time.sleep(0.5)
    bridge.show_status("Ready")
    
    # Get status
    status = bridge.get_status()
    print(f"\nESP32 status: {status}")
    
    # Disconnect
    bridge.disconnect()
    
    print("\n" + "=" * 50)
    print("Testing ESP32-CAM Bridge...")
    
    cam = ESP32CamBridge()
    print(f"Stream URL: {cam.get_stream_url()}")
    print(f"Snapshot URL: {cam.get_snapshot_url()}")
    
    print("\nTest complete!")
