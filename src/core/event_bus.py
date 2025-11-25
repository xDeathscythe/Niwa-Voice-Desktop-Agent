"""Thread-safe Event Bus implementation for VoiceType."""

import threading
import queue
import weakref
import logging
from typing import Callable, Dict, List, Optional, Any, Set
from dataclasses import dataclass, field

from .events import Event, EventType, create_event

logger = logging.getLogger(__name__)


@dataclass
class Subscription:
    """Represents a single event subscription."""

    callback: Callable[[Event], None]
    priority: int = 0
    weak: bool = False
    _weak_ref: Optional[weakref.ref] = None

    def get_callback(self) -> Optional[Callable]:
        """Get the callback, handling weak references."""
        if self.weak and self._weak_ref:
            return self._weak_ref()
        return self.callback


class EventBus:
    """
    Thread-safe publish/subscribe event bus.

    Features:
    - Priority-based callback ordering
    - Weak reference support (prevents memory leaks)
    - Thread-safe publishing from any thread
    - Main thread dispatching for GUI updates
    - Debug mode for event tracing

    Usage:
        bus = EventBus()
        bus.subscribe(EventType.HOTKEY_PRESSED, my_handler)
        bus.publish(create_event(EventType.HOTKEY_PRESSED, key="ctrl+t"))
    """

    _instance: Optional['EventBus'] = None
    _lock = threading.Lock()

    def __new__(cls):
        """Singleton pattern for global event bus."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self._subscriptions: Dict[EventType, List[Subscription]] = {}
        self._sub_lock = threading.RLock()
        self._tk_root = None
        self._debug_mode = False
        self._event_history: List[Event] = []
        self._history_limit = 100

        logger.debug("EventBus initialized")

    @classmethod
    def get_instance(cls) -> 'EventBus':
        """Get singleton instance."""
        return cls()

    @classmethod
    def reset_instance(cls):
        """Reset singleton (for testing)."""
        with cls._lock:
            if cls._instance:
                cls._instance.clear()
            cls._instance = None

    def set_tk_root(self, root) -> None:
        """
        Set Tkinter/CustomTkinter root for main thread dispatching.

        This enables automatic marshaling of events to the main thread
        when published from worker threads.
        """
        self._tk_root = root
        logger.debug("Tk root set for main thread dispatching")

    def subscribe(
        self,
        event_type: EventType,
        callback: Callable[[Event], None],
        priority: int = 0,
        weak: bool = False
    ) -> Callable[[], None]:
        """
        Subscribe to an event type.

        Args:
            event_type: The event to subscribe to
            callback: Function to call when event occurs
            priority: Higher priority = called first (default 0)
            weak: Use weak reference (auto-cleanup when object deleted)

        Returns:
            Unsubscribe function
        """
        with self._sub_lock:
            if event_type not in self._subscriptions:
                self._subscriptions[event_type] = []

            sub = Subscription(
                callback=callback,
                priority=priority,
                weak=weak,
                _weak_ref=weakref.ref(callback) if weak else None
            )

            self._subscriptions[event_type].append(sub)

            # Sort by priority (descending)
            self._subscriptions[event_type].sort(
                key=lambda s: s.priority,
                reverse=True
            )

            if self._debug_mode:
                logger.debug(f"Subscribed to {event_type.value}: {callback.__name__}")

        # Return unsubscribe function
        def unsubscribe():
            self.unsubscribe(event_type, callback)

        return unsubscribe

    def subscribe_many(
        self,
        event_types: List[EventType],
        callback: Callable[[Event], None],
        priority: int = 0
    ) -> Callable[[], None]:
        """Subscribe to multiple event types with same callback."""
        unsubscribers = []
        for event_type in event_types:
            unsub = self.subscribe(event_type, callback, priority)
            unsubscribers.append(unsub)

        def unsubscribe_all():
            for unsub in unsubscribers:
                unsub()

        return unsubscribe_all

    def unsubscribe(
        self,
        event_type: EventType,
        callback: Callable[[Event], None]
    ) -> bool:
        """
        Unsubscribe from an event type.

        Returns:
            True if subscription was found and removed
        """
        with self._sub_lock:
            if event_type not in self._subscriptions:
                return False

            original_len = len(self._subscriptions[event_type])
            self._subscriptions[event_type] = [
                s for s in self._subscriptions[event_type]
                if s.callback != callback
            ]

            removed = len(self._subscriptions[event_type]) < original_len

            if removed and self._debug_mode:
                logger.debug(f"Unsubscribed from {event_type.value}")

            return removed

    def publish(self, event: Event) -> None:
        """
        Publish an event (thread-safe, async dispatch).

        If tk_root is set and called from worker thread,
        automatically dispatches to main thread.
        """
        if self._debug_mode:
            logger.debug(f"Publishing: {event}")
            self._event_history.append(event)
            if len(self._event_history) > self._history_limit:
                self._event_history.pop(0)

        # Check if we need to marshal to main thread
        if self._tk_root and threading.current_thread() != threading.main_thread():
            self._tk_root.after(0, lambda: self._dispatch(event))
        else:
            self._dispatch(event)

    def publish_sync(self, event: Event) -> None:
        """Publish event synchronously (blocking)."""
        if self._debug_mode:
            logger.debug(f"Publishing (sync): {event}")
        self._dispatch(event)

    def _dispatch(self, event: Event) -> None:
        """Dispatch event to all subscribers."""
        with self._sub_lock:
            subscribers = self._subscriptions.get(event.type, []).copy()

        dead_refs = []

        for sub in subscribers:
            try:
                callback = sub.get_callback()
                if callback is None:
                    dead_refs.append((event.type, sub))
                    continue

                callback(event)

            except Exception as e:
                logger.error(
                    f"Error in event handler for {event.type.value}: {e}",
                    exc_info=True
                )

        # Clean up dead weak references
        if dead_refs:
            with self._sub_lock:
                for event_type, sub in dead_refs:
                    subs = self._subscriptions.get(event_type, [])
                    if sub in subs:
                        subs.remove(sub)

    def emit(self, event_type: EventType, **kwargs) -> None:
        """Convenience method to create and publish event."""
        self.publish(create_event(event_type, **kwargs))

    def clear(self) -> None:
        """Remove all subscriptions."""
        with self._sub_lock:
            self._subscriptions.clear()
            logger.debug("All subscriptions cleared")

    def clear_event(self, event_type: EventType) -> None:
        """Remove all subscriptions for specific event type."""
        with self._sub_lock:
            if event_type in self._subscriptions:
                del self._subscriptions[event_type]

    def set_debug(self, enabled: bool) -> None:
        """Enable/disable debug logging and event history."""
        self._debug_mode = enabled
        logger.info(f"EventBus debug mode: {enabled}")

    def get_history(self, limit: int = 50) -> List[Event]:
        """Get recent event history (only in debug mode)."""
        return self._event_history[-limit:]

    def get_subscriber_count(self, event_type: EventType) -> int:
        """Get number of subscribers for an event type."""
        with self._sub_lock:
            return len(self._subscriptions.get(event_type, []))

    def get_all_subscriber_counts(self) -> Dict[str, int]:
        """Get subscriber counts for all event types."""
        with self._sub_lock:
            return {
                et.value: len(subs)
                for et, subs in self._subscriptions.items()
            }


# Convenience functions
def get_event_bus() -> EventBus:
    """Get the global event bus instance."""
    return EventBus.get_instance()


def subscribe(event_type: EventType, callback: Callable[[Event], None], **kwargs):
    """Subscribe to an event on the global bus."""
    return get_event_bus().subscribe(event_type, callback, **kwargs)


def publish(event: Event) -> None:
    """Publish an event to the global bus."""
    get_event_bus().publish(event)


def emit(event_type: EventType, **kwargs) -> None:
    """Create and publish an event to the global bus."""
    get_event_bus().emit(event_type, **kwargs)
