"""DisplayAdapter: auto-refresh suspension and element recreate."""
from __future__ import annotations

from pycadwork.cadwork_adapter.types import ElementId


class DisplayAdapter:
    """Suspend / resume the cadwork viewport refresh and recreate elements."""

    def disable_auto_display_refresh(self) -> None:
        import utility_controller
        utility_controller.disable_auto_display_refresh()

    def enable_auto_display_refresh(self) -> None:
        import utility_controller
        utility_controller.enable_auto_display_refresh()

    def recreate_elements(self, eids: list[ElementId]) -> None:
        import element_controller
        element_controller.recreate_elements(list(eids))
