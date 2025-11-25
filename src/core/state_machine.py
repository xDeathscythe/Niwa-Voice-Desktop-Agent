"""Finite State Machine for VoiceType application flow control."""

from enum import Enum, auto
from typing import Dict, List, Optional, Callable, Set, Any
from dataclasses import dataclass
import threading
import logging

from .event_bus import EventBus, create_event
from .events import EventType, StateChangedEvent

logger = logging.getLogger(__name__)


class State(Enum):
    """Application states."""

    IDLE = auto()           # Waiting for hotkey
    RECORDING = auto()      # Recording audio
    TRANSCRIBING = auto()   # Sending to Whisper API
    PROCESSING = auto()     # LLM cleanup (optional)
    INJECTING = auto()      # Copying/pasting text
    ERROR = auto()          # Error state


@dataclass
class Transition:
    """Represents a valid state transition."""

    from_state: State
    to_state: State
    trigger: str
    guard: Optional[Callable[[], bool]] = None
    action: Optional[Callable[[], None]] = None


class StateMachine:
    """
    Finite State Machine for application flow control.

    Thread-safe state management with event emission.

    State Flow:
        IDLE --[start_recording]--> RECORDING
        RECORDING --[stop_recording]--> TRANSCRIBING
        RECORDING --[cancel]--> IDLE
        TRANSCRIBING --[success]--> PROCESSING (if LLM enabled)
        TRANSCRIBING --[success]--> INJECTING (if LLM disabled)
        TRANSCRIBING --[error]--> ERROR
        PROCESSING --[success]--> INJECTING
        PROCESSING --[error]--> ERROR
        INJECTING --[complete]--> IDLE
        ERROR --[acknowledge]--> IDLE
    """

    # Valid transitions
    TRANSITIONS: List[Transition] = [
        # Start recording from idle
        Transition(State.IDLE, State.RECORDING, "start_recording"),

        # Stop recording -> transcribe
        Transition(State.RECORDING, State.TRANSCRIBING, "stop_recording"),

        # Cancel recording -> back to idle
        Transition(State.RECORDING, State.IDLE, "cancel"),

        # Transcription complete -> LLM processing
        Transition(State.TRANSCRIBING, State.PROCESSING, "transcription_complete"),

        # Transcription complete -> direct inject (skip LLM)
        Transition(State.TRANSCRIBING, State.INJECTING, "transcription_complete_direct"),

        # Transcription error
        Transition(State.TRANSCRIBING, State.ERROR, "error"),

        # LLM processing complete
        Transition(State.PROCESSING, State.INJECTING, "processing_complete"),

        # LLM processing error
        Transition(State.PROCESSING, State.ERROR, "error"),

        # Injection complete
        Transition(State.INJECTING, State.IDLE, "complete"),

        # Injection error
        Transition(State.INJECTING, State.ERROR, "error"),

        # Error acknowledged -> reset
        Transition(State.ERROR, State.IDLE, "acknowledge"),

        # Force reset from any state
        Transition(State.RECORDING, State.IDLE, "force_reset"),
        Transition(State.TRANSCRIBING, State.IDLE, "force_reset"),
        Transition(State.PROCESSING, State.IDLE, "force_reset"),
        Transition(State.INJECTING, State.IDLE, "force_reset"),
        Transition(State.ERROR, State.IDLE, "force_reset"),
    ]

    def __init__(self, event_bus: Optional[EventBus] = None):
        """
        Initialize state machine.

        Args:
            event_bus: EventBus instance for state change events
        """
        self._state = State.IDLE
        self._lock = threading.RLock()
        self._event_bus = event_bus or EventBus.get_instance()
        self._history: List[tuple] = []
        self._history_limit = 50

        # Callbacks for state entry/exit
        self._on_enter_callbacks: Dict[State, List[Callable]] = {
            state: [] for state in State
        }
        self._on_exit_callbacks: Dict[State, List[Callable]] = {
            state: [] for state in State
        }

        # Build transition map for fast lookup
        self._transition_map: Dict[tuple, Transition] = {}
        for t in self.TRANSITIONS:
            key = (t.from_state, t.trigger)
            self._transition_map[key] = t

        logger.info("StateMachine initialized in IDLE state")

    @property
    def state(self) -> State:
        """Current state (thread-safe read)."""
        with self._lock:
            return self._state

    @property
    def is_idle(self) -> bool:
        """Check if in IDLE state."""
        return self.state == State.IDLE

    @property
    def is_recording(self) -> bool:
        """Check if in RECORDING state."""
        return self.state == State.RECORDING

    @property
    def is_busy(self) -> bool:
        """Check if processing (not IDLE or ERROR)."""
        return self.state not in (State.IDLE, State.ERROR)

    def can_transition(self, trigger: str) -> bool:
        """Check if transition is valid from current state."""
        with self._lock:
            return (self._state, trigger) in self._transition_map

    def get_valid_triggers(self) -> List[str]:
        """Get list of valid triggers from current state."""
        with self._lock:
            return [
                trigger for (state, trigger) in self._transition_map.keys()
                if state == self._state
            ]

    def transition(self, trigger: str, **kwargs) -> bool:
        """
        Attempt state transition.

        Args:
            trigger: The trigger name for the transition
            **kwargs: Additional data to pass with state change event

        Returns:
            True if transition successful, False otherwise
        """
        with self._lock:
            key = (self._state, trigger)

            if key not in self._transition_map:
                logger.warning(
                    f"Invalid transition: {self._state.name} --[{trigger}]--> ?"
                )
                return False

            trans = self._transition_map[key]

            # Check guard condition
            if trans.guard and not trans.guard():
                logger.debug(f"Transition guard failed for: {trigger}")
                return False

            old_state = self._state
            new_state = trans.to_state

            # Call exit callbacks for old state
            for callback in self._on_exit_callbacks[old_state]:
                try:
                    callback()
                except Exception as e:
                    logger.error(f"Exit callback error: {e}")

            # Execute transition action
            if trans.action:
                try:
                    trans.action()
                except Exception as e:
                    logger.error(f"Transition action error: {e}")

            # Update state
            self._state = new_state

            # Record in history
            self._history.append((old_state, trigger, new_state))
            if len(self._history) > self._history_limit:
                self._history.pop(0)

            logger.info(f"State: {old_state.name} --[{trigger}]--> {new_state.name}")

            # Call entry callbacks for new state
            for callback in self._on_enter_callbacks[new_state]:
                try:
                    callback()
                except Exception as e:
                    logger.error(f"Entry callback error: {e}")

            # Emit state change event
            self._event_bus.publish(create_event(
                EventType.STATE_CHANGED,
                old_state=old_state,
                new_state=new_state,
                trigger=trigger,
                **kwargs
            ))

            return True

    def on_enter(self, state: State, callback: Callable[[], None]) -> Callable[[], None]:
        """
        Register callback for state entry.

        Returns:
            Unregister function
        """
        self._on_enter_callbacks[state].append(callback)

        def unregister():
            if callback in self._on_enter_callbacks[state]:
                self._on_enter_callbacks[state].remove(callback)

        return unregister

    def on_exit(self, state: State, callback: Callable[[], None]) -> Callable[[], None]:
        """
        Register callback for state exit.

        Returns:
            Unregister function
        """
        self._on_exit_callbacks[state].append(callback)

        def unregister():
            if callback in self._on_exit_callbacks[state]:
                self._on_exit_callbacks[state].remove(callback)

        return unregister

    def reset(self) -> None:
        """Force reset to IDLE state."""
        with self._lock:
            old_state = self._state
            if old_state != State.IDLE:
                self.transition("force_reset")

    def get_history(self, limit: int = 10) -> List[tuple]:
        """Get recent transition history."""
        return self._history[-limit:]

    # Convenience transition methods
    def start_recording(self) -> bool:
        """Transition to RECORDING state."""
        return self.transition("start_recording")

    def stop_recording(self) -> bool:
        """Transition from RECORDING to TRANSCRIBING."""
        return self.transition("stop_recording")

    def cancel(self) -> bool:
        """Cancel current operation and return to IDLE."""
        return self.transition("cancel")

    def transcription_complete(self, use_llm: bool = True) -> bool:
        """Handle transcription completion."""
        trigger = "transcription_complete" if use_llm else "transcription_complete_direct"
        return self.transition(trigger)

    def processing_complete(self) -> bool:
        """Handle LLM processing completion."""
        return self.transition("processing_complete")

    def complete(self) -> bool:
        """Mark operation as complete."""
        return self.transition("complete")

    def error(self, error_info: Any = None) -> bool:
        """Transition to ERROR state."""
        return self.transition("error", error_info=error_info)

    def acknowledge_error(self) -> bool:
        """Acknowledge error and return to IDLE."""
        return self.transition("acknowledge")
