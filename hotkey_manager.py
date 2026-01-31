# -*- coding: utf-8 -*-
"""
Global hotkey manager for the Work OCR application.
Uses the 'keyboard' library to listen for global hotkeys even when the app is not focused.
"""

import threading
import keyboard
from PySide6.QtCore import QObject, Signal


class HotkeyManager(QObject):
    """
    Manages global hotkey registration and handling.
    Emits signals when hotkeys are pressed.
    """
    screenshot_hotkey_pressed = Signal()
    
    def __init__(self):
        super().__init__()
        self._registered_hotkey = None
        self._hotkey_handler = None
        self._is_listening = False
        self._listen_thread = None
        
    def register_screenshot_hotkey(self, hotkey_str: str) -> bool:
        """
        Register a global hotkey for screenshot.
        
        Args:
            hotkey_str: Hotkey combination string (e.g., "ctrl+alt+s", "f1", "ctrl+shift+a")
        
        Returns:
            True if registration succeeded, False otherwise
        """
        # Unregister previous hotkey if exists
        self.unregister_all()
        
        if not hotkey_str or hotkey_str.strip() == "":
            return False
            
        try:
            # Register the hotkey
            self._hotkey_handler = keyboard.add_hotkey(hotkey_str, self._on_screenshot_hotkey)
            self._registered_hotkey = hotkey_str
            
            # Start listening in a separate thread if not already
            if not self._is_listening:
                self._start_listening()
                
            return True
        except Exception as e:
            print(f"Failed to register hotkey '{hotkey_str}': {e}")
            return False
    
    def _on_screenshot_hotkey(self):
        """Callback when screenshot hotkey is pressed."""
        self.screenshot_hotkey_pressed.emit()
    
    def _start_listening(self):
        """Start the keyboard listener thread."""
        self._is_listening = True
        self._listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._listen_thread.start()
    
    def _listen_loop(self):
        """Main loop for keyboard listening."""
        # keyboard.wait() blocks until stop() is called
        keyboard.wait()
    
    def unregister_all(self):
        """Unregister all hotkeys."""
        if self._hotkey_handler:
            try:
                keyboard.remove_hotkey(self._hotkey_handler)
            except Exception:
                pass
            self._hotkey_handler = None
        self._registered_hotkey = None
    
    def stop(self):
        """Stop the hotkey manager and clean up."""
        self.unregister_all()
        self._is_listening = False
        try:
            keyboard.unhook_all()
        except Exception:
            pass
    
    def get_registered_hotkey(self) -> str | None:
        """Get the currently registered hotkey string."""
        return self._registered_hotkey
    
    @staticmethod
    def validate_hotkey(hotkey_str: str) -> bool:
        """
        Validate if a hotkey string is valid.
        
        Args:
            hotkey_str: Hotkey combination string
        
        Returns:
            True if valid, False otherwise
        """
        if not hotkey_str or hotkey_str.strip() == "":
            return False
        
        try:
            # Try to parse the hotkey
            keyboard.parse_hotkey(hotkey_str)
            return True
        except Exception:
            return False
    
    @staticmethod
    def format_hotkey_display(hotkey_str: str) -> str:
        """
        Format a hotkey string for display (capitalize, etc.).
        
        Args:
            hotkey_str: Raw hotkey string
        
        Returns:
            Formatted hotkey string
        """
        if not hotkey_str:
            return ""
        
        parts = hotkey_str.lower().split('+')
        formatted_parts = []
        
        for part in parts:
            part = part.strip()
            if part in ('ctrl', 'alt', 'shift', 'win', 'cmd'):
                formatted_parts.append(part.capitalize())
            elif len(part) == 1:
                formatted_parts.append(part.upper())
            else:
                formatted_parts.append(part.capitalize())
        
        return '+'.join(formatted_parts)
