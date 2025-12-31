"""
Arduino Bridge Module
Handles serial communication with Arduino/hardware components.
Currently configured as a simulation for development without hardware.
"""

import time
from typing import Optional

# Uncomment when pyserial is installed and hardware is connected
# import serial


class ArduinoBridge:
    """
    Handles communication with Arduino for hardware control.
    In simulation mode, it logs actions instead of sending to hardware.
    """
    
    def __init__(self, port: str = 'COM3', baud_rate: int = 9600, simulation: bool = True):
        """
        Initialize the Arduino bridge.
        
        Args:
            port: Serial port (e.g., 'COM3' on Windows, '/dev/ttyUSB0' on Linux)
            baud_rate: Serial communication speed
            simulation: If True, simulate hardware instead of real connection
        """
        self.port = port
        self.baud_rate = baud_rate
        self.simulation = simulation
        self.connection = None
        self.is_connected = False
    
    def connect(self) -> bool:
        """
        Establish connection with Arduino.
        
        Returns:
            bool: True if connection successful
        """
        if self.simulation:
            print(f"[SIMULATION] Arduino connected on {self.port}")
            self.is_connected = True
            return True
        
        try:
            # Uncomment for real hardware:
            # self.connection = serial.Serial(self.port, self.baud_rate, timeout=1)
            # time.sleep(2)  # Wait for Arduino to reset
            self.is_connected = True
            print(f"Connected to Arduino on {self.port}")
            return True
        except Exception as e:
            print(f"Failed to connect to Arduino: {e}")
            return False
    
    def disconnect(self):
        """Close the serial connection."""
        if self.simulation:
            print("[SIMULATION] Arduino disconnected")
            self.is_connected = False
            return
        
        if self.connection and self.connection.is_open:
            self.connection.close()
        self.is_connected = False
    
    def send_command(self, command: str) -> Optional[str]:
        """
        Send a command to Arduino and get response.
        
        Args:
            command: Command string to send
        
        Returns:
            str: Response from Arduino or None
        """
        if self.simulation:
            print(f"[SIMULATION] Sending command: {command}")
            return self._simulate_response(command)
        
        if not self.is_connected:
            print("Error: Not connected to Arduino")
            return None
        
        try:
            self.connection.write(f"{command}\n".encode())
            response = self.connection.readline().decode().strip()
            return response
        except Exception as e:
            print(f"Error sending command: {e}")
            return None
    
    def _simulate_response(self, command: str) -> str:
        """
        Simulate Arduino responses for development.
        
        Args:
            command: The command that was "sent"
        
        Returns:
            str: Simulated response
        """
        command = command.upper()
        
        responses = {
            'LED_GREEN': 'OK:LED_GREEN_ON',
            'LED_RED': 'OK:LED_RED_ON',
            'BUZZER_SUCCESS': 'OK:BUZZER_PLAYED',
            'BUZZER_ERROR': 'OK:BUZZER_ERROR_PLAYED',
            'DOOR_OPEN': 'OK:DOOR_OPENED',
            'DOOR_CLOSE': 'OK:DOOR_CLOSED',
            'STATUS': 'OK:SYSTEM_READY',
        }
        
        return responses.get(command, f'OK:RECEIVED_{command}')
    
    # Convenience methods for common hardware actions
    
    def signal_success(self):
        """Signal successful attendance (green LED + success buzzer)."""
        self.send_command('LED_GREEN')
        self.send_command('BUZZER_SUCCESS')
    
    def signal_error(self):
        """Signal error/unrecognized face (red LED + error buzzer)."""
        self.send_command('LED_RED')
        self.send_command('BUZZER_ERROR')
    
    def open_door(self):
        """Open the door/gate for entry."""
        return self.send_command('DOOR_OPEN')
    
    def close_door(self):
        """Close the door/gate."""
        return self.send_command('DOOR_CLOSE')
    
    def get_status(self):
        """Get the current hardware status."""
        return self.send_command('STATUS')


if __name__ == '__main__':
    # Test the Arduino bridge in simulation mode
    print("Testing Arduino Bridge (Simulation Mode)...")
    
    bridge = ArduinoBridge(simulation=True)
    
    # Connect
    bridge.connect()
    
    # Test various commands
    print("\nTesting commands:")
    bridge.signal_success()
    time.sleep(0.5)
    bridge.signal_error()
    time.sleep(0.5)
    bridge.open_door()
    time.sleep(0.5)
    bridge.close_door()
    
    # Get status
    status = bridge.get_status()
    print(f"\nSystem status: {status}")
    
    # Disconnect
    bridge.disconnect()
    print("\nTest complete!")
