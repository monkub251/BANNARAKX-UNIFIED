"""Pro-only tweaks. Every value is snapshotted before it is touched and restored on Reset.
Nothing here changes game files or game mechanics, and nothing lowers system security."""
from __future__ import annotations

from dataclasses import dataclass, field

HKCU, HKLM = "HKCU", "HKLM"
SZ, DWORD = "SZ", "DWORD"


@dataclass(frozen=True)
class RegItem:
    hive: str
    path: str
    name: str
    type: str
    value: object

    @property
    def key(self) -> str:
        return f"{self.hive}\\{self.path}\\{self.name}"


@dataclass(frozen=True)
class Tweak:
    id: str
    title: str
    why: str
    features: tuple[str, ...]      # spec sections 4.1 .. 4.9
    level: str                     # "safe" or "max"
    items: tuple[RegItem, ...] = field(default_factory=tuple)
    power_plan: str | None = None  # GUID, handled via powercfg


_MOUSE = r"Control Panel\Mouse"
_KBD = r"Control Panel\Keyboard"
_ACC = r"Control Panel\Accessibility"
_MM = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile"

TWEAKS: tuple[Tweak, ...] = (
    Tweak("mouse_1to1", "Mouse 1:1 (no acceleration)",
          "Same hand movement = same turn distance, easier to aim, turn and dodge.",
          ("4.1", "4.3"), "safe", (
              RegItem(HKCU, _MOUSE, "MouseSpeed", SZ, "0"),
              RegItem(HKCU, _MOUSE, "MouseThreshold1", SZ, "0"),
              RegItem(HKCU, _MOUSE, "MouseThreshold2", SZ, "0"))),
    Tweak("kbd_fast", "Fastest key repeat",
          "Movement keys register and repeat without delay.",
          ("4.1", "4.5", "4.6"), "safe", (
              RegItem(HKCU, _KBD, "KeyboardDelay", SZ, "0"),
              RegItem(HKCU, _KBD, "KeyboardSpeed", SZ, "31"))),
    Tweak("no_popups", "No Sticky/Filter/Toggle Keys pop-ups",
          "Stops Windows from interrupting the game when a key is spammed.",
          ("4.5", "4.6", "4.8"), "safe", (
              RegItem(HKCU, _ACC + r"\StickyKeys", "Flags", SZ, "506"),
              RegItem(HKCU, _ACC + r"\Keyboard Response", "Flags", SZ, "122"),
              RegItem(HKCU, _ACC + r"\ToggleKeys", "Flags", SZ, "58"))),
    Tweak("game_mode", "Windows Game Mode on",
          "Keeps Windows background work away from the game.",
          ("4.2", "4.8"), "safe", (
              RegItem(HKCU, r"Software\Microsoft\GameBar", "AutoGameModeEnabled", DWORD, 1),
              RegItem(HKCU, r"Software\Microsoft\GameBar", "AllowAutoGameMode", DWORD, 1))),
    Tweak("no_capture", "Game DVR / background capture off",
          "Removes hidden recording overhead that causes frame-time spikes.",
          ("4.2", "4.7", "4.8"), "safe", (
              RegItem(HKCU, r"System\GameConfigStore", "GameDVR_Enabled", DWORD, 0),
              RegItem(HKCU, r"Software\Microsoft\Windows\CurrentVersion\GameDVR", "AppCaptureEnabled", DWORD, 0))),
    # ---- MAX level: Pro / knife only ------------------------------------------------
    Tweak("fg_priority", "Foreground priority boost",
          "Gives the game window more CPU time slices, steadier input under load.",
          ("4.1", "4.4", "4.5", "4.9"), "max", (
              RegItem(HKLM, r"SYSTEM\CurrentControlSet\Control\PriorityControl",
                      "Win32PrioritySeparation", DWORD, 38),)),
    Tweak("timer_res", "Precise system timer",
          "Lets the game keep its own timer resolution, smoother frame pacing.",
          ("4.2", "4.8"), "max", (
              RegItem(HKLM, r"SYSTEM\CurrentControlSet\Control\Session Manager\kernel",
                      "GlobalTimerResolutionRequests", DWORD, 1),)),
    Tweak("mmcss_games", "Games scheduling class (MMCSS)",
          "Higher GPU/CPU scheduling priority for the Games task class.",
          ("4.7", "4.8", "4.9"), "max", (
              RegItem(HKLM, _MM + r"\Tasks\Games", "GPU Priority", DWORD, 8),
              RegItem(HKLM, _MM + r"\Tasks\Games", "Priority", DWORD, 6),
              RegItem(HKLM, _MM + r"\Tasks\Games", "Scheduling Category", SZ, "High"),
              RegItem(HKLM, _MM + r"\Tasks\Games", "SFIO Priority", SZ, "High"))),
    Tweak("net_throttle", "Network throttling off",
          "Stops Windows from throttling network packets while a game runs.",
          ("4.8", "4.9"), "max", (
              RegItem(HKLM, _MM, "NetworkThrottlingIndex", DWORD, 0xFFFFFFFF),)),
    Tweak("power_high", "High Performance power plan",
          "No CPU down-clocking in the middle of a fight. Your old plan is restored on Reset.",
          ("4.8", "4.9"), "max", (), power_plan="8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"),
)

PRESETS = {"safe": ("safe",), "max": ("safe", "max")}


def select(preset: str) -> list[Tweak]:
    levels = PRESETS[preset]
    return [t for t in TWEAKS if t.level in levels]
