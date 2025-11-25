"""
VoiceType Modern Theme - Inspired by Cursor, Notion, Obsidian

Clean, minimal, dark design with subtle accents.
"""

from dataclasses import dataclass

# Modern Dark Color Palette (Cursor/Obsidian style)
COLORS = {
    # Backgrounds - True blacks and grays
    "bg_primary": "#0a0a0a",      # Main background (near black)
    "bg_secondary": "#111111",     # Cards, elevated surfaces
    "bg_tertiary": "#1a1a1a",      # Hover states, inputs
    "bg_hover": "#222222",         # Hover on secondary
    "bg_active": "#2a2a2a",        # Active/pressed states

    # Accent - Violet/Purple (like the React design)
    "accent": "#8b5cf6",           # Primary accent (violet)
    "accent_hover": "#a78bfa",     # Accent hover (lighter violet)
    "accent_muted": "#5b21b6",     # Muted accent for backgrounds (darker violet)
    "accent_subtle": "rgba(139, 92, 246, 0.1)",  # Very subtle accent bg

    # Text
    "text_primary": "#fafafa",     # Primary text (almost white)
    "text_secondary": "#a1a1aa",   # Secondary text
    "text_muted": "#71717a",       # Muted/placeholder text
    "text_disabled": "#52525b",    # Disabled text

    # Borders
    "border": "#27272a",           # Default border
    "border_subtle": "#1f1f23",    # Subtle border
    "border_focus": "#0ea5e9",     # Focus border (accent)

    # Status
    "success": "#22c55e",          # Green
    "error": "#ef4444",            # Red
    "warning": "#f59e0b",          # Orange
    "recording": "#ef4444",        # Recording indicator

    # Special
    "overlay": "rgba(0, 0, 0, 0.8)",
    "glass": "rgba(17, 17, 17, 0.9)",
}

# Font configuration
FONTS = {
    "family": "Segoe UI",
    "family_mono": "Cascadia Code",
    "size_xs": 11,
    "size_sm": 12,
    "size_md": 13,
    "size_lg": 15,
    "size_xl": 18,
    "size_2xl": 24,
    "size_3xl": 32,
}

# Spacing
SPACING = {
    "xs": 4,
    "sm": 8,
    "md": 12,
    "lg": 16,
    "xl": 24,
    "2xl": 32,
    "3xl": 48,
}

# Border radius
RADIUS = {
    "sm": 4,
    "md": 6,
    "lg": 8,
    "xl": 12,
    "2xl": 16,
    "full": 9999,
}

# Gradient sequences for animations
GRADIENT_BORDER = [
    "#0ea5e9",  # Sky blue
    "#06b6d4",  # Cyan
    "#8b5cf6",  # Purple
    "#d946ef",  # Fuchsia
    "#f43f5e",  # Rose
    "#f97316",  # Orange
    "#eab308",  # Yellow
    "#84cc16",  # Lime
    "#22c55e",  # Green
    "#10b981",  # Emerald
    "#14b8a6",  # Teal
    "#0ea5e9",  # Back to start
]

# Shining text gradient (dark -> bright -> dark)
GRADIENT_TEXT = [
    "#404040",  # Dark gray
    "#525252",
    "#737373",
    "#a3a3a3",
    "#d4d4d4",
    "#fafafa",  # Bright white
    "#d4d4d4",
    "#a3a3a3",
    "#737373",
    "#525252",
    "#404040",  # Back to dark
]


@dataclass
class ModernTheme:
    """Modern theme configuration."""

    @classmethod
    def apply(cls):
        """Apply theme to CustomTkinter."""
        import customtkinter as ctk
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        return cls()

    @staticmethod
    def get_font(size: str = "md", weight: str = "normal", mono: bool = False):
        """Get font tuple."""
        family = FONTS["family_mono"] if mono else FONTS["family"]
        size_val = FONTS.get(f"size_{size}", FONTS["size_md"])

        if weight == "bold":
            return (family, size_val, "bold")
        return (family, size_val)


def apply_theme():
    """Apply modern theme globally."""
    return ModernTheme.apply()
