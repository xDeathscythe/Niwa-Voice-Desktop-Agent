"""Language Picker Dialog for multi-language selection."""

import customtkinter as ctk
from typing import Callable, List, Optional
import logging

from .styles.theme import COLORS, FONTS, RADIUS

logger = logging.getLogger(__name__)

# Common languages sorted by usage
COMMON_LANGUAGES = [
    ("auto", "Auto-detect"),
    ("en", "English"),
    ("sr", "Serbian"),
    ("hr", "Croatian"),
    ("bs", "Bosnian"),
    ("sl", "Slovenian"),
    ("de", "German"),
    ("fr", "French"),
    ("es", "Spanish"),
    ("it", "Italian"),
    ("pt", "Portuguese"),
    ("nl", "Dutch"),
    ("pl", "Polish"),
    ("ru", "Russian"),
    ("uk", "Ukrainian"),
    ("cs", "Czech"),
    ("sk", "Slovak"),
    ("hu", "Hungarian"),
    ("ro", "Romanian"),
    ("bg", "Bulgarian"),
    ("el", "Greek"),
    ("tr", "Turkish"),
    ("ar", "Arabic"),
    ("he", "Hebrew"),
    ("hi", "Hindi"),
    ("ja", "Japanese"),
    ("ko", "Korean"),
    ("zh", "Chinese"),
    ("vi", "Vietnamese"),
    ("th", "Thai"),
    ("id", "Indonesian"),
    ("ms", "Malay"),
    ("sv", "Swedish"),
    ("da", "Danish"),
    ("no", "Norwegian"),
    ("fi", "Finnish"),
]


def get_language_name(code: str) -> str:
    """Get language name from code."""
    for c, name in COMMON_LANGUAGES:
        if c == code:
            return name
    return code.upper()


def get_language_code(name: str) -> str:
    """Get language code from name."""
    for code, n in COMMON_LANGUAGES:
        if n == name:
            return code
    return name.lower()


class LanguagePickerDialog(ctk.CTkToplevel):
    """Dialog for selecting a language."""

    def __init__(
        self,
        parent,
        excluded_languages: Optional[List[str]] = None,
        on_select: Optional[Callable[[str], None]] = None,
        title: str = "Select Language",
        include_auto: bool = False
    ):
        super().__init__(parent)

        self._excluded = set(excluded_languages or [])
        self._on_select = on_select
        self._include_auto = include_auto
        self._selected = None

        self._setup_window(title)
        self._create_ui()

    def _setup_window(self, title: str):
        """Configure window."""
        self.title(title)
        self.geometry("320x450")
        self.configure(fg_color=COLORS["bg_primary"])
        self.resizable(False, False)

        # Center on parent
        self.transient(self.master)
        self.grab_set()

        x = self.master.winfo_x() + (self.master.winfo_width() - 320) // 2
        y = self.master.winfo_y() + (self.master.winfo_height() - 450) // 2
        self.geometry(f"+{x}+{y}")

    def _create_ui(self):
        """Create dialog UI."""
        # Header
        header = ctk.CTkLabel(
            self,
            text="Select Language",
            font=(FONTS["family"], 18, "bold"),
            text_color=COLORS["text_primary"]
        )
        header.pack(pady=(16, 8))

        # Search
        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", self._filter_languages)

        search_entry = ctk.CTkEntry(
            self,
            placeholder_text="Search...",
            textvariable=self.search_var,
            font=(FONTS["family"], FONTS["size_sm"]),
            fg_color=COLORS["bg_secondary"],
            border_width=1,
            border_color=COLORS["border"],
            height=36
        )
        search_entry.pack(fill="x", padx=16, pady=(0, 12))

        # Language list
        self.list_frame = ctk.CTkScrollableFrame(
            self,
            fg_color=COLORS["bg_secondary"],
            corner_radius=RADIUS["lg"],
            border_width=1,
            border_color=COLORS["border"]
        )
        self.list_frame.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        self._render_languages()

        # Cancel button
        cancel_btn = ctk.CTkButton(
            self,
            text="Cancel",
            font=(FONTS["family"], FONTS["size_sm"]),
            fg_color=COLORS["bg_tertiary"],
            hover_color=COLORS["bg_hover"],
            corner_radius=RADIUS["lg"],
            height=36,
            text_color=COLORS["text_primary"],
            command=self.destroy
        )
        cancel_btn.pack(fill="x", padx=16, pady=(0, 16))

    def _render_languages(self, filter_text: str = ""):
        """Render language list."""
        # Clear existing
        for widget in self.list_frame.winfo_children():
            widget.destroy()

        filter_lower = filter_text.lower()

        for code, name in COMMON_LANGUAGES:
            # Skip auto if not included
            if code == "auto" and not self._include_auto:
                continue

            # Skip excluded
            if code in self._excluded:
                continue

            # Apply filter
            if filter_lower and filter_lower not in name.lower() and filter_lower not in code.lower():
                continue

            self._create_language_item(code, name)

    def _create_language_item(self, code: str, name: str):
        """Create a language list item."""
        item = ctk.CTkButton(
            self.list_frame,
            text=f"{name}  ({code})" if code != "auto" else name,
            font=(FONTS["family"], FONTS["size_sm"]),
            fg_color="transparent",
            hover_color=COLORS["bg_hover"],
            anchor="w",
            height=40,
            text_color=COLORS["text_primary"],
            command=lambda: self._select(code)
        )
        item.pack(fill="x", pady=1, padx=4)

    def _filter_languages(self, *args):
        """Filter languages based on search."""
        self._render_languages(self.search_var.get())

    def _select(self, code: str):
        """Select a language."""
        self._selected = code
        if self._on_select:
            self._on_select(code)
        self.destroy()

    def get_selected(self) -> Optional[str]:
        """Get selected language code."""
        return self._selected


class LanguageChip(ctk.CTkFrame):
    """A chip/tag showing a selected language with remove button."""

    def __init__(
        self,
        parent,
        language_code: str,
        on_remove: Optional[Callable[[str], None]] = None
    ):
        super().__init__(
            parent,
            fg_color=COLORS["bg_tertiary"],
            corner_radius=RADIUS["lg"]
        )

        self._code = language_code
        self._on_remove = on_remove

        # Language name
        name = get_language_name(language_code)
        label = ctk.CTkLabel(
            self,
            text=f"{name} ({language_code})",
            font=(FONTS["family"], FONTS["size_xs"]),
            text_color=COLORS["text_primary"]
        )
        label.pack(side="left", padx=(10, 4), pady=6)

        # Remove button
        remove_btn = ctk.CTkButton(
            self,
            text="×",
            width=20,
            height=20,
            font=(FONTS["family"], 14),
            fg_color="transparent",
            hover_color=COLORS["error"],
            text_color=COLORS["text_muted"],
            corner_radius=RADIUS["sm"],
            command=self._remove
        )
        remove_btn.pack(side="right", padx=(0, 4), pady=4)

    def _remove(self):
        """Remove this chip."""
        if self._on_remove:
            self._on_remove(self._code)
        self.destroy()

    def get_code(self) -> str:
        """Get language code."""
        return self._code
