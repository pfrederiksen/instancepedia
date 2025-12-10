"""Debug logging utility"""

from typing import List, Optional
from textual.widgets import Static
from textual.containers import Container


class DebugLog:
    """Singleton debug log"""
    _instance: Optional['DebugLog'] = None
    _enabled: bool = False
    _messages: List[str] = []
    _max_messages: int = 50

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def enable(cls) -> None:
        """Enable debug logging"""
        cls._enabled = True

    @classmethod
    def disable(cls) -> None:
        """Disable debug logging"""
        cls._enabled = False

    @classmethod
    def is_enabled(cls) -> bool:
        """Check if debug is enabled"""
        return cls._enabled

    @classmethod
    def log(cls, message: str) -> None:
        """Log a debug message"""
        if not cls._enabled:
            return
        
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        log_message = f"[{timestamp}] {message}"
        cls._messages.append(log_message)
        
        # Keep only the last N messages
        if len(cls._messages) > cls._max_messages:
            cls._messages = cls._messages[-cls._max_messages:]
        
        # If there's a debug pane, try to update it
        try:
            if cls._instance and hasattr(cls._instance, '_debug_pane') and cls._instance._debug_pane:
                cls._instance._debug_pane._update_debug_pane()
        except Exception:
            pass  # Ignore errors

    @classmethod
    def get_messages(cls) -> List[str]:
        """Get all debug messages"""
        return cls._messages.copy()

    @classmethod
    def clear(cls) -> None:
        """Clear debug messages"""
        cls._messages.clear()
        if hasattr(cls._instance, '_debug_pane'):
            cls._instance._update_debug_pane()


class DebugPane(Container):
    """Debug pane widget"""

    def __init__(self):
        super().__init__(id="debug-pane")
        self._debug_log = DebugLog()
        # Store reference to this pane in the debug log instance
        if DebugLog._instance:
            DebugLog._instance._debug_pane = self

    CSS = """
    #debug-pane {
        height: 3;
        border-top: solid $primary;
        background: $panel;
        padding: 0 1;
        dock: bottom;
    }
    
    #debug-label {
        text-style: bold;
        color: $primary;
        height: 1;
    }
    
    #debug-content {
        color: $text-muted;
        font-size: 70%;
        height: 2;
        content-align: left top;
    }
    """

    def compose(self):
        from textual.widgets import Static
        yield Static("Debug Log:", id="debug-label")
        yield Static("", id="debug-content")

    def on_mount(self) -> None:
        """Update debug pane when mounted"""
        # Store reference
        if DebugLog._instance:
            DebugLog._instance._debug_pane = self
        self._update_debug_pane()
        # Set up a timer to periodically update
        self.set_interval(0.5, self._update_debug_pane)

    def _update_debug_pane(self) -> None:
        """Update the debug pane content"""
        try:
            messages = self._debug_log.get_messages()
            # Show last 3-4 messages (fewer for smaller pane)
            content = " | ".join(messages[-3:])  # Show last 3 messages on one line
            if not content:
                content = "No debug messages yet..."
            debug_content = self.query_one("#debug-content", Static)
            debug_content.update(content)
        except Exception:
            pass  # Ignore errors during update

