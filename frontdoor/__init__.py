"""Portable front door: every prompt -> m1frame routing on any backend."""
from frontdoor.agent import FrontDoor, FrontDoorResult
from frontdoor.protocol import parse_tool_call

__all__ = ["FrontDoor", "FrontDoorResult", "parse_tool_call"]
