"""Slide builder modules — each exports a ``build(prs, data)`` function."""

from pptx.dml.color import RGBColor

# Shared branding constants
PRIMARY_BLUE = RGBColor(0x10, 0x62, 0x80)
DARK_GRAY = RGBColor(0x39, 0x48, 0x49)
NAVY = RGBColor(0x0F, 0x2E, 0x55)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT_BLUE = RGBColor(0x4E, 0xA8, 0xC8)
LIGHT_GRAY = RGBColor(0xF2, 0xF2, 0xF2)
ACCENT_RED = RGBColor(0xD9, 0x53, 0x4F)
FONT_NAME = "Calibri"
