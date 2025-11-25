"""
Architects Tool No.1 - Modern Settings Window

Professional compact design with Voice Notes functionality.
"""

import customtkinter as ctk
from typing import Optional, Callable
from PIL import Image, ImageTk
import logging
import urllib.request
import io
import os
import json
from datetime import datetime

from .styles.theme import COLORS, FONTS, SPACING, RADIUS, apply_theme
from ..services.settings_service import SettingsService
from ..services.audio_service import AudioService
from ..services.transcription_service import SUPPORTED_LANGUAGES

logger = logging.getLogger(__name__)


class MainWindow(ctk.CTk):
    """Modern settings window with Voice Notes."""

    WIDTH = 1100
    HEIGHT = 640

    def __init__(
        self,
        settings_service: Optional[SettingsService] = None,
        audio_service: Optional[AudioService] = None,
        on_start: Optional[Callable] = None,
        on_stop: Optional[Callable] = None
    ):
        super().__init__()

        self._settings = settings_service or SettingsService()
        self._audio = audio_service
        self._on_start = on_start
        self._on_stop = on_stop
        self._is_running = False
        self._notes = []  # Voice notes storage

        apply_theme()
        self._setup_window()
        self._create_ui()
        self._load_settings()
        self._load_notes()

    def _setup_window(self):
        """Configure window."""
        self.title("Architects Tool No.1")
        self.geometry(f"{self.WIDTH}x{self.HEIGHT}")
        self.minsize(self.WIDTH, self.HEIGHT)
        self.configure(fg_color=COLORS["bg_primary"])
        self.resizable(False, False)

        # Set icon
        try:
            icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets", "icon.ico")
            if os.path.exists(icon_path):
                self.iconbitmap(icon_path)
        except Exception as e:
            logger.warning(f"Could not set icon: {e}")

        # Center window
        x = (self.winfo_screenwidth() - self.WIDTH) // 2
        y = (self.winfo_screenheight() - self.HEIGHT) // 2
        self.geometry(f"+{x}+{y}")

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _create_ui(self):
        """Create modern UI with settings and voice notes."""
        # Main container
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=24, pady=24)

        # Left panel - Settings
        self.left_panel = ctk.CTkFrame(main, fg_color="transparent")
        self.left_panel.pack(side="left", fill="both", expand=True, padx=(0, 12))

        # Right panel - Voice Notes
        self.right_panel = ctk.CTkFrame(main, fg_color="transparent", width=380)
        self.right_panel.pack(side="right", fill="both", expand=False, padx=(12, 0))
        self.right_panel.pack_propagate(False)

        # Create content
        self._create_left_content()
        self._create_right_content()

    def _create_left_content(self):
        """Create settings panel."""
        # Header
        header = ctk.CTkLabel(
            self.left_panel,
            text="Settings",
            font=(FONTS["family"], 24, "bold"),
            text_color=COLORS["text_primary"],
            anchor="w"
        )
        header.pack(anchor="w", pady=(0, 16))

        # API Key
        self._create_api_section()

        # Settings grid
        self._create_settings_grid()

        # Options
        self._create_options()

        # Footer with buttons
        self._create_footer()

    def _create_right_content(self):
        """Create Voice Notes panel."""
        # Header
        header = ctk.CTkLabel(
            self.right_panel,
            text="Voice Notes",
            font=(FONTS["family"], 20, "bold"),
            text_color=COLORS["text_primary"],
            anchor="w"
        )
        header.pack(anchor="w", pady=(0, 12))

        # Text input card
        input_card = ctk.CTkFrame(
            self.right_panel,
            fg_color=COLORS["bg_secondary"],
            corner_radius=RADIUS["xl"],
            border_width=1,
            border_color=COLORS["border"]
        )
        input_card.pack(fill="x", pady=(0, 12))

        inner = ctk.CTkFrame(input_card, fg_color="transparent")
        inner.pack(fill="x", padx=14, pady=12)

        # Label
        label = ctk.CTkLabel(
            inner,
            text="Current Note",
            font=(FONTS["family"], FONTS["size_sm"]),
            text_color=COLORS["text_secondary"],
            anchor="w"
        )
        label.pack(anchor="w", pady=(0, 6))

        # Text box
        self.note_text = ctk.CTkTextbox(
            inner,
            height=80,
            font=(FONTS["family"], FONTS["size_sm"]),
            fg_color=COLORS["bg_tertiary"],
            border_width=0,
            corner_radius=RADIUS["lg"],
            text_color=COLORS["text_primary"]
        )
        self.note_text.pack(fill="x", pady=(0, 8))

        # Save button
        save_btn = ctk.CTkButton(
            inner,
            text="Save Note",
            height=36,
            font=(FONTS["family"], FONTS["size_sm"]),
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            corner_radius=RADIUS["lg"],
            command=self._save_note
        )
        save_btn.pack(fill="x")

        # Notes list header
        list_header = ctk.CTkLabel(
            self.right_panel,
            text="Saved Notes",
            font=(FONTS["family"], FONTS["size_md"], "bold"),
            text_color=COLORS["text_secondary"],
            anchor="w"
        )
        list_header.pack(anchor="w", pady=(8, 8))

        # Scrollable notes list
        self.notes_list = ctk.CTkScrollableFrame(
            self.right_panel,
            fg_color=COLORS["bg_secondary"],
            corner_radius=RADIUS["xl"],
            border_width=1,
            border_color=COLORS["border"]
        )
        self.notes_list.pack(fill="both", expand=True)

    def _create_api_section(self):
        """Create API key section."""
        card = ctk.CTkFrame(
            self.left_panel,
            fg_color=COLORS["bg_secondary"],
            corner_radius=RADIUS["lg"],
            border_width=1,
            border_color=COLORS["border"]
        )
        card.pack(fill="x", pady=(0, 12))

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=14, pady=12)

        label = ctk.CTkLabel(
            inner,
            text="OpenAI API Key",
            font=(FONTS["family"], FONTS["size_sm"]),
            text_color=COLORS["text_secondary"],
            anchor="w"
        )
        label.pack(anchor="w", pady=(0, 6))

        input_row = ctk.CTkFrame(inner, fg_color="transparent")
        input_row.pack(fill="x")

        self.api_entry = ctk.CTkEntry(
            input_row,
            placeholder_text="sk-...",
            show="*",
            font=(FONTS["family_mono"], FONTS["size_sm"]),
            fg_color=COLORS["bg_tertiary"],
            border_width=0,
            height=36,
            text_color=COLORS["text_primary"]
        )
        self.api_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.show_btn = ctk.CTkButton(
            input_row,
            text="Show",
            width=60,
            height=36,
            font=(FONTS["family"], FONTS["size_xs"]),
            fg_color=COLORS["bg_hover"],
            hover_color=COLORS["bg_active"],
            corner_radius=RADIUS["lg"],
            text_color=COLORS["accent"],
            command=self._toggle_api
        )
        self.show_btn.pack(side="right")

        self.api_status = ctk.CTkLabel(
            inner,
            text="",
            font=(FONTS["family"], FONTS["size_xs"]),
            text_color=COLORS["text_muted"],
            anchor="w"
        )
        self.api_status.pack(anchor="w", pady=(6, 0))

    def _create_settings_grid(self):
        """Create settings grid."""
        card = ctk.CTkFrame(
            self.left_panel,
            fg_color=COLORS["bg_secondary"],
            corner_radius=RADIUS["lg"],
            border_width=1,
            border_color=COLORS["border"]
        )
        card.pack(fill="x", pady=(0, 12))

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=14, pady=12)

        inner.columnconfigure(0, weight=1)
        inner.columnconfigure(1, weight=1)

        # Row 0
        self._create_dropdown(inner, "Microphone", "mic_dropdown", ["Loading..."], row=0, col=0)
        languages = list(SUPPORTED_LANGUAGES.values())
        self._create_dropdown(inner, "Language", "lang_dropdown", languages, "Auto-detect", row=0, col=1)

        # Row 1
        self._create_hotkey_input(inner, row=1, col=0)
        models = ["None (fastest)", "gpt-3.5-turbo (fast)", "gpt-4o-mini (balanced)", "gpt-4o (best)"]
        self._create_dropdown(inner, "AI Model", "model_dropdown", models, "gpt-4o-mini (balanced)", row=1, col=1)

        self._load_mics()

    def _create_dropdown(self, parent, label_text, attr_name, values, default=None, row=0, col=0):
        """Create dropdown."""
        container = ctk.CTkFrame(parent, fg_color="transparent")
        container.grid(row=row, column=col, sticky="ew", padx=(0, 8) if col == 0 else (8, 0), pady=5)

        label = ctk.CTkLabel(
            container,
            text=label_text,
            font=(FONTS["family"], FONTS["size_xs"]),
            text_color=COLORS["text_secondary"],
            anchor="w"
        )
        label.pack(anchor="w", pady=(0, 4))

        dropdown = ctk.CTkComboBox(
            container,
            values=values,
            font=(FONTS["family"], FONTS["size_sm"]),
            fg_color=COLORS["bg_tertiary"],
            border_width=0,
            button_color=COLORS["bg_hover"],
            button_hover_color=COLORS["bg_active"],
            dropdown_fg_color=COLORS["bg_secondary"],
            dropdown_hover_color=COLORS["bg_hover"],
            corner_radius=RADIUS["lg"],
            height=36,
            text_color=COLORS["text_primary"],
            dropdown_text_color=COLORS["text_primary"]
        )
        dropdown.pack(fill="x")

        if default:
            dropdown.set(default)

        setattr(self, attr_name, dropdown)

    def _create_hotkey_input(self, parent, row=0, col=0):
        """Create hotkey input."""
        container = ctk.CTkFrame(parent, fg_color="transparent")
        container.grid(row=row, column=col, sticky="ew", padx=(0, 8) if col == 0 else (8, 0), pady=5)

        label = ctk.CTkLabel(
            container,
            text="Hotkey (click to change)",
            font=(FONTS["family"], FONTS["size_xs"]),
            text_color=COLORS["text_secondary"],
            anchor="w"
        )
        label.pack(anchor="w", pady=(0, 4))

        self._hotkey_string = "ctrl+alt"
        self._capturing_hotkey = False
        self._pressed_modifiers = set()

        self.hotkey_btn = ctk.CTkButton(
            container,
            text="Ctrl + Alt",
            font=(FONTS["family_mono"], FONTS["size_sm"]),
            text_color=COLORS["accent"],
            fg_color=COLORS["bg_tertiary"],
            hover_color=COLORS["bg_hover"],
            corner_radius=RADIUS["lg"],
            height=36,
            command=self._start_hotkey_capture
        )
        self.hotkey_btn.pack(fill="x")

    def _create_options(self):
        """Create checkboxes."""
        card = ctk.CTkFrame(
            self.left_panel,
            fg_color=COLORS["bg_secondary"],
            corner_radius=RADIUS["lg"],
            border_width=1,
            border_color=COLORS["border"]
        )
        card.pack(fill="x", pady=(0, 12))

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=14, pady=12)

        inner.columnconfigure(0, weight=1)
        inner.columnconfigure(1, weight=1)

        self.overlay_var = ctk.BooleanVar(value=True)
        overlay_check = ctk.CTkCheckBox(
            inner,
            text="Show floating pill",
            variable=self.overlay_var,
            font=(FONTS["family"], FONTS["size_xs"]),
            text_color=COLORS["text_secondary"],
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            border_color=COLORS["border"],
            checkmark_color=COLORS["text_primary"],
            corner_radius=RADIUS["sm"]
        )
        overlay_check.grid(row=0, column=0, sticky="w", padx=(0, 8))

        self.preprocessing_var = ctk.BooleanVar(value=True)
        preprocessing_check = ctk.CTkCheckBox(
            inner,
            text="Audio Preprocessing",
            variable=self.preprocessing_var,
            font=(FONTS["family"], FONTS["size_xs"]),
            text_color=COLORS["text_secondary"],
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            border_color=COLORS["border"],
            checkmark_color=COLORS["text_primary"],
            corner_radius=RADIUS["sm"]
        )
        preprocessing_check.grid(row=0, column=1, sticky="w", padx=(8, 0))

        # Row 1 - Variable Recognition
        self.variable_recognition_var = ctk.BooleanVar(value=True)
        variable_recognition_check = ctk.CTkCheckBox(
            inner,
            text="Variable Recognition",
            variable=self.variable_recognition_var,
            font=(FONTS["family"], FONTS["size_xs"]),
            text_color=COLORS["text_secondary"],
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            border_color=COLORS["border"],
            checkmark_color=COLORS["text_primary"],
            corner_radius=RADIUS["sm"]
        )
        variable_recognition_check.grid(row=1, column=0, sticky="w", padx=(0, 8), pady=(8, 0))

    def _create_footer(self):
        """Create footer with visible buttons."""
        footer = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        footer.pack(fill="x", side="bottom", pady=(12, 0))

        # Buttons
        btn_row = ctk.CTkFrame(footer, fg_color="transparent")
        btn_row.pack(fill="x", pady=(0, 6))

        self.save_btn = ctk.CTkButton(
            btn_row,
            text="Save Settings",
            font=(FONTS["family"], FONTS["size_md"]),
            fg_color=COLORS["bg_tertiary"],
            hover_color=COLORS["bg_hover"],
            border_color=COLORS["border"],
            border_width=1,
            corner_radius=RADIUS["lg"],
            height=44,
            text_color=COLORS["text_primary"],
            command=self._save_settings
        )
        self.save_btn.pack(side="left", expand=True, fill="x", padx=(0, 6))

        self.start_btn = ctk.CTkButton(
            btn_row,
            text="Start Service",
            font=(FONTS["family"], FONTS["size_md"], "bold"),
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            corner_radius=RADIUS["lg"],
            height=44,
            text_color=COLORS["text_primary"],
            command=self._toggle_service
        )
        self.start_btn.pack(side="right", expand=True, fill="x", padx=(6, 0))

        # Status (hidden - only used internally for app.py)
        self.status_dot = ctk.CTkLabel(footer, text="●", font=(FONTS["family"], 12))
        self.status_label = ctk.CTkLabel(footer, text="", font=(FONTS["family"], FONTS["size_xs"]))

    # Voice Notes methods
    def _save_note(self):
        """Save current note."""
        text = self.note_text.get("1.0", "end-1c").strip()
        if not text:
            return

        note = {
            "text": text,
            "timestamp": datetime.now().isoformat(),
            "id": len(self._notes)
        }
        self._notes.append(note)
        self._render_notes()
        self.note_text.delete("1.0", "end")
        self._save_notes_to_disk()

    def _render_notes(self):
        """Render notes list."""
        # Clear
        for widget in self.notes_list.winfo_children():
            widget.destroy()

        if not self._notes:
            empty = ctk.CTkLabel(
                self.notes_list,
                text="No notes yet",
                font=(FONTS["family"], FONTS["size_sm"]),
                text_color=COLORS["text_muted"]
            )
            empty.pack(pady=20)
            return

        # Render each note
        for note in reversed(self._notes):
            self._create_note_item(note)

    def _create_note_item(self, note):
        """Create note list item."""
        item = ctk.CTkFrame(
            self.notes_list,
            fg_color=COLORS["bg_tertiary"],
            corner_radius=RADIUS["lg"],
            cursor="hand2"
        )
        item.pack(fill="x", pady=(0, 8), padx=8)

        inner = ctk.CTkFrame(item, fg_color="transparent")
        inner.pack(fill="x", padx=10, pady=10)

        # Timestamp
        try:
            dt = datetime.fromisoformat(note["timestamp"])
            time_str = dt.strftime("%b %d, %H:%M")
        except:
            time_str = "Unknown"

        time_label = ctk.CTkLabel(
            inner,
            text=time_str,
            font=(FONTS["family"], FONTS["size_xs"]),
            text_color=COLORS["text_muted"],
            anchor="w",
            cursor="hand2"
        )
        time_label.pack(anchor="w", pady=(0, 4))

        # Text
        text_label = ctk.CTkLabel(
            inner,
            text=note["text"][:100] + ("..." if len(note["text"]) > 100 else ""),
            font=(FONTS["family"], FONTS["size_sm"]),
            text_color=COLORS["text_primary"],
            anchor="w",
            justify="left",
            cursor="hand2"
        )
        text_label.pack(anchor="w", fill="x")

        # Delete button
        del_btn = ctk.CTkButton(
            inner,
            text="Delete",
            width=60,
            height=24,
            font=(FONTS["family"], FONTS["size_xs"]),
            fg_color=COLORS["error"],
            hover_color="#dc2626",
            corner_radius=RADIUS["sm"],
            command=lambda: self._delete_note(note["id"])
        )
        del_btn.pack(anchor="e", pady=(4, 0))

        # Bind click to load note
        def load_note(e):
            # Don't load if clicking delete button
            if e.widget != del_btn:
                self.note_text.delete("1.0", "end")
                self.note_text.insert("1.0", note["text"])

        item.bind("<Button-1>", load_note)
        inner.bind("<Button-1>", load_note)
        time_label.bind("<Button-1>", load_note)
        text_label.bind("<Button-1>", load_note)

    def _delete_note(self, note_id):
        """Delete a note."""
        self._notes = [n for n in self._notes if n["id"] != note_id]
        self._render_notes()
        self._save_notes_to_disk()

    def _load_notes(self):
        """Load notes from disk."""
        try:
            notes_path = os.path.join(os.path.dirname(self._settings._settings_path), "voice_notes.json")
            if os.path.exists(notes_path):
                with open(notes_path, "r", encoding="utf-8") as f:
                    self._notes = json.load(f)
                self._render_notes()
        except Exception as e:
            logger.error(f"Failed to load notes: {e}")

    def _save_notes_to_disk(self):
        """Save notes to disk."""
        try:
            notes_path = os.path.join(os.path.dirname(self._settings._settings_path), "voice_notes.json")
            with open(notes_path, "w", encoding="utf-8") as f:
                json.dump(self._notes, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save notes: {e}")

    # Hotkey capture methods
    def _toggle_api(self):
        if self.api_entry.cget("show") == "*":
            self.api_entry.configure(show="")
            self.show_btn.configure(text="Hide")
        else:
            self.api_entry.configure(show="*")
            self.show_btn.configure(text="Show")

    def _start_hotkey_capture(self):
        if self._capturing_hotkey:
            return
        self._capturing_hotkey = True
        self._pressed_modifiers = set()
        self.hotkey_btn.configure(text="Press keys...", text_color=COLORS["text_primary"])
        self.bind("<KeyPress>", self._on_hotkey_press)
        self.bind("<KeyRelease>", self._on_hotkey_release)

    def _on_hotkey_press(self, event):
        if not self._capturing_hotkey:
            return
        key = event.keysym.lower()
        if key in ("control_l", "control_r"):
            self._pressed_modifiers.add("ctrl")
            return
        if key in ("shift_l", "shift_r"):
            self._pressed_modifiers.add("shift")
            return
        if key in ("alt_l", "alt_r"):
            self._pressed_modifiers.add("alt")
            return
        parts = []
        if "ctrl" in self._pressed_modifiers or event.state & 0x4:
            parts.append("ctrl")
        if "shift" in self._pressed_modifiers or event.state & 0x1:
            parts.append("shift")
        if "alt" in self._pressed_modifiers or event.state & 0x8:
            parts.append("alt")
        parts.append(key)
        self._finalize_hotkey(parts)

    def _on_hotkey_release(self, event):
        if not self._capturing_hotkey:
            return
        key = event.keysym.lower()
        if key not in ("control_l", "control_r", "shift_l", "shift_r", "alt_l", "alt_r"):
            return
        if self._pressed_modifiers:
            self.after(100, self._check_finalize_modifiers)

    def _check_finalize_modifiers(self):
        if not self._capturing_hotkey or not self._pressed_modifiers:
            return
        parts = list(self._pressed_modifiers)
        order = ["ctrl", "shift", "alt"]
        parts = [m for m in order if m in parts]
        if parts:
            self._finalize_hotkey(parts)

    def _finalize_hotkey(self, parts):
        if not parts:
            return
        hotkey_str = "+".join(parts)
        display_text = " + ".join(p.capitalize() for p in parts)
        self._hotkey_string = hotkey_str
        self.hotkey_btn.configure(text=display_text, text_color=COLORS["accent"])
        self._capturing_hotkey = False
        self._pressed_modifiers = set()
        self.unbind("<KeyPress>")
        self.unbind("<KeyRelease>")
        logger.info(f"Hotkey changed to: {hotkey_str}")

    def _load_mics(self):
        try:
            if self._audio:
                self._devices = self._audio.get_input_devices()
                names = [d.name for d in self._devices]
                self.mic_dropdown.configure(values=names)
                if self._devices:
                    saved_name = self._settings.get("audio.device_name", "")
                    found = False
                    for d in self._devices:
                        if d.name == saved_name:
                            self.mic_dropdown.set(d.name)
                            found = True
                            break
                    if not found:
                        default = next((d for d in self._devices if d.is_default), self._devices[0])
                        self.mic_dropdown.set(default.name)
        except Exception as e:
            logger.error(f"Failed to load mics: {e}")
            self._devices = []
            self.mic_dropdown.configure(values=["No microphone found"])

    def _save_settings(self):
        try:
            logger.info("Saving settings...")
            self._settings.set_api_key(self.api_entry.get())
            self._settings.set("ui.show_overlay", self.overlay_var.get())
            self._settings.set("audio.preprocessing_enabled", self.preprocessing_var.get())
            self._settings.set("variable_recognition.enabled", self.variable_recognition_var.get())

            model_choice = self.model_dropdown.get()
            model_map = {
                "None (fastest)": "",
                "gpt-3.5-turbo (fast)": "gpt-3.5-turbo",
                "gpt-4o-mini (balanced)": "gpt-4o-mini",
                "gpt-4o (best)": "gpt-4o"
            }
            model = model_map.get(model_choice, "gpt-4o-mini")
            self._settings.set("transcription.cleanup_model", model)
            self._settings.set("transcription.use_cleanup", bool(model))

            mic_name = self.mic_dropdown.get()
            if hasattr(self, '_devices'):
                for d in self._devices:
                    if d.name == mic_name:
                        self._settings.set("audio.device_id", d.id)
                        self._settings.set("audio.device_name", d.name)
                        break

            lang_name = self.lang_dropdown.get()
            for code, name in SUPPORTED_LANGUAGES.items():
                if name == lang_name:
                    self._settings.set_language(code)
                    break

            self._settings.set_hotkey_string(self._hotkey_string)
            self._settings.save()
            logger.info("Settings saved successfully")
            self.api_status.configure(text="✓ Saved", text_color=COLORS["success"])
            self.after(2000, lambda: self.api_status.configure(text=""))
        except Exception as e:
            logger.error(f"Save failed: {e}", exc_info=True)
            self.api_status.configure(text=f"Error: {e}", text_color=COLORS["error"])

    def _load_settings(self):
        try:
            self._settings.load()
            self.api_entry.insert(0, self._settings.get_api_key())

            lang_code = self._settings.get_language()
            lang_name = SUPPORTED_LANGUAGES.get(lang_code, "Auto-detect")
            self.lang_dropdown.set(lang_name)

            model = self._settings.get("transcription.cleanup_model", "gpt-4o-mini")
            model_display = {
                "": "None (fastest)",
                "gpt-3.5-turbo": "gpt-3.5-turbo (fast)",
                "gpt-4o-mini": "gpt-4o-mini (balanced)",
                "gpt-4o": "gpt-4o (best)"
            }
            self.model_dropdown.set(model_display.get(model, "gpt-4o-mini (balanced)"))

            self.overlay_var.set(self._settings.get("ui.show_overlay", True))
            self.preprocessing_var.set(self._settings.get("audio.preprocessing_enabled", True))
            self.variable_recognition_var.set(self._settings.get("variable_recognition.enabled", True))

            hotkey_str = self._settings.get_hotkey_string()
            if hotkey_str:
                self._hotkey_string = hotkey_str.lower().replace(" ", "")
                display_text = " + ".join(p.capitalize() for p in self._hotkey_string.split("+"))
                self.hotkey_btn.configure(text=display_text)
        except:
            pass

    def _toggle_service(self):
        if self._is_running:
            self._stop_service()
        else:
            self._start_service()

    def _start_service(self):
        api_key = self.api_entry.get()
        if not api_key or not api_key.startswith("sk-"):
            self.api_status.configure(text="⚠ Enter valid API key", text_color=COLORS["error"])
            return

        self._is_running = True
        self.start_btn.configure(
            text="Stop Service",
            fg_color=COLORS["error"],
            hover_color="#dc2626"
        )
        self.status_dot.configure(text_color=COLORS["success"])
        self.status_label.configure(text="Service running", text_color=COLORS["text_secondary"])

        if self._on_start:
            self._on_start()

    def _stop_service(self):
        self._is_running = False
        self.start_btn.configure(
            text="Start Service",
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"]
        )
        self.status_dot.configure(text_color=COLORS["text_muted"])
        self.status_label.configure(text="Ready to start", text_color=COLORS["text_muted"])

        if self._on_stop:
            self._on_stop()

    def _on_close(self):
        self.quit()
        self.destroy()

    # Public method to add transcribed text to current note
    def add_transcription_to_note(self, text: str):
        """Add transcribed text to current note."""
        current = self.note_text.get("1.0", "end-1c")
        if current:
            self.note_text.insert("end", "\n\n")
        self.note_text.insert("end", text)
