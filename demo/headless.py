#!/usr/bin/env python3
"""
Headless Display — Universal headless rendering with visual output.
====================================================================

Auto-detects the runtime environment and provides the appropriate
virtual framebuffer + visual output channel:

  * **Colab**:    pyvirtualdisplay + Xvfb, frames shown inline via
                  ``IPython.display.Image``
  * **Cloud/K8s**: Xvfb (or SDL dummy), frames saved as GIF/video
  * **Local**:    SDL_VIDEODRIVER=dummy, frames captured to numpy

Usage::

    from headless import HeadlessDisplay

    hd = HeadlessDisplay()         # auto-detects environment
    hd.start()                     # sets up virtual framebuffer

    # Inside game loop:
    hd.capture(game_surface)       # grabs current frame
    hd.show()                      # displays inline (Colab) or no-op

    hd.save_gif("session.gif")     # export recorded frames as GIF
    hd.stop()                      # tears down virtual display

Install (Colab)::

    !apt-get -qq install -y xvfb
    !pip install -q pyvirtualdisplay Pillow

Install (Cloud/K8s)::

    apt-get install -y xvfb
    pip install pyvirtualdisplay Pillow
"""

from __future__ import annotations

import io
import os
import sys
import time
from enum import Enum, auto
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# ---------------------------------------------------------------------------
# Lazy / guarded imports
# ---------------------------------------------------------------------------
try:
    import pygame
    HAS_PYGAME = True
except ImportError:
    HAS_PYGAME = False

try:
    from PIL import Image as PILImage
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


# ---------------------------------------------------------------------------
# Environment detection
# ---------------------------------------------------------------------------
class RuntimeEnv(Enum):
    COLAB = auto()
    CLOUD = auto()     # K8s, GCP VM, EC2, etc.
    LOCAL = auto()


def detect_environment() -> RuntimeEnv:
    """Auto-detect the runtime environment."""
    # Google Colab
    if "google.colab" in sys.modules or "COLAB_RELEASE_TAG" in os.environ:
        return RuntimeEnv.COLAB
    try:
        # noinspection PyUnresolvedReferences
        import google.colab  # noqa: F401
        return RuntimeEnv.COLAB
    except ImportError:
        pass

    # Kubernetes / cloud indicators
    cloud_indicators = [
        "KUBERNETES_SERVICE_HOST",   # K8s pod
        "K_SERVICE",                 # Cloud Run
        "AWS_EXECUTION_ENV",         # Lambda / ECS
        "GOOGLE_CLOUD_PROJECT",      # GCP VM
        "ECS_CONTAINER_METADATA_URI", # ECS
        "CLOUD_RUN_JOB",            # Cloud Run Jobs
    ]
    if any(k in os.environ for k in cloud_indicators):
        return RuntimeEnv.CLOUD

    # No DISPLAY on Linux = headless server
    if sys.platform == "linux" and not os.environ.get("DISPLAY"):
        return RuntimeEnv.CLOUD

    return RuntimeEnv.LOCAL


# ---------------------------------------------------------------------------
# HeadlessDisplay
# ---------------------------------------------------------------------------
class HeadlessDisplay:
    """Universal headless rendering with visual output.

    Parameters
    ----------
    env : RuntimeEnv, optional
        Force a specific environment.  ``None`` = auto-detect.
    width, height : int
        Virtual framebuffer resolution.
    max_frames : int
        Max frames to keep in the ring buffer (0 = unlimited).
    capture_every : int
        Only store every Nth captured frame (saves memory for GIF).
    """

    def __init__(
        self,
        env: Optional[RuntimeEnv] = None,
        width: int = 640,
        height: int = 480,
        max_frames: int = 600,
        capture_every: int = 2,
    ) -> None:
        self.env = env or detect_environment()
        self.width = width
        self.height = height
        self.max_frames = max_frames
        self.capture_every = max(1, capture_every)

        self._vdisplay: Any = None       # pyvirtualdisplay.Display
        self._frames: List[bytes] = []   # PNG bytes ring-buffer
        self._frame_count: int = 0
        self._started: bool = False
        self._ipython_display: Any = None
        self._ipython_clear: Any = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> "HeadlessDisplay":
        """Set up virtual framebuffer according to detected environment."""
        if self._started:
            return self

        if self.env in (RuntimeEnv.COLAB, RuntimeEnv.CLOUD):
            self._start_xvfb()
        else:
            # Local headless — SDL dummy driver
            os.environ["SDL_VIDEODRIVER"] = "dummy"

        # Pre-import IPython display helpers for Colab
        if self.env == RuntimeEnv.COLAB:
            try:
                from IPython.display import display, clear_output, Image  # noqa: F401
                self._ipython_display = display
                self._ipython_clear = clear_output
            except ImportError:
                pass

        self._started = True
        return self

    def stop(self) -> None:
        """Tear down virtual display."""
        if self._vdisplay is not None:
            try:
                self._vdisplay.stop()
            except Exception:
                pass
            self._vdisplay = None
        self._started = False

    # ------------------------------------------------------------------
    # Frame capture
    # ------------------------------------------------------------------

    def capture(self, surface: "pygame.Surface") -> Optional[np.ndarray]:
        """Capture a frame from a pygame Surface.

        Returns the frame as an (H, W, 3) uint8 numpy array, or None
        if pygame/surfarray is unavailable.
        """
        self._frame_count += 1

        if not HAS_PYGAME:
            return None

        # Convert surface to numpy
        arr: np.ndarray = pygame.surfarray.array3d(surface)  # (W, H, 3)
        arr = arr.transpose((1, 0, 2))  # (H, W, 3)

        # Store PNG bytes in ring buffer (only every Nth frame)
        if self._frame_count % self.capture_every == 0 and HAS_PIL:
            png_bytes = self._array_to_png(arr)
            self._frames.append(png_bytes)
            if self.max_frames > 0 and len(self._frames) > self.max_frames:
                self._frames.pop(0)

        return arr.astype(np.uint8)

    def get_last_frame_png(self) -> Optional[bytes]:
        """Return the last captured frame as PNG bytes."""
        return self._frames[-1] if self._frames else None

    def get_last_frame_array(self, surface: "pygame.Surface") -> np.ndarray:
        """Quick capture → numpy without storing to ring buffer."""
        if not HAS_PYGAME:
            return np.zeros((self.height, self.width, 3), dtype=np.uint8)
        arr = pygame.surfarray.array3d(surface)
        return arr.transpose((1, 0, 2)).astype(np.uint8)

    @property
    def frame_count(self) -> int:
        return self._frame_count

    @property
    def stored_frames(self) -> int:
        return len(self._frames)

    # ------------------------------------------------------------------
    # Visual output
    # ------------------------------------------------------------------

    def show(self, surface: Optional["pygame.Surface"] = None) -> None:
        """Display the latest frame inline (Colab) or no-op elsewhere.

        If *surface* is given, captures it first.
        """
        if surface is not None:
            self.capture(surface)

        if self.env == RuntimeEnv.COLAB and self._ipython_display:
            png = self.get_last_frame_png()
            if png:
                from IPython.display import Image
                if self._ipython_clear:
                    self._ipython_clear(wait=True)
                self._ipython_display(Image(data=png))

    def show_array(self, arr: np.ndarray) -> None:
        """Display a numpy (H,W,3) array inline (Colab only)."""
        if not HAS_PIL:
            return
        png = self._array_to_png(arr)
        if self.env == RuntimeEnv.COLAB and self._ipython_display:
            from IPython.display import Image
            if self._ipython_clear:
                self._ipython_clear(wait=True)
            self._ipython_display(Image(data=png))

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def save_gif(
        self,
        path: str = "session.gif",
        fps: int = 15,
        scale: float = 1.0,
    ) -> Optional[str]:
        """Save captured frames as an animated GIF.

        Returns the output path on success, None on failure.
        """
        if not HAS_PIL or not self._frames:
            return None

        images: List[PILImage.Image] = []
        for png_bytes in self._frames:
            img = PILImage.open(io.BytesIO(png_bytes)).convert("RGB")
            if scale != 1.0:
                new_w = int(img.width * scale)
                new_h = int(img.height * scale)
                img = img.resize((new_w, new_h), PILImage.LANCZOS)
            images.append(img)

        if not images:
            return None

        duration_ms = int(1000 / fps)
        images[0].save(
            path,
            save_all=True,
            append_images=images[1:],
            duration=duration_ms,
            loop=0,
            optimize=True,
        )
        return path

    def save_video(
        self,
        path: str = "session.mp4",
        fps: int = 30,
    ) -> Optional[str]:
        """Save captured frames as MP4 video (requires opencv-python).

        Returns the output path on success, None on failure.
        """
        if not self._frames or not HAS_PIL:
            return None

        try:
            import cv2
        except ImportError:
            print("[headless] opencv-python not available, falling back to GIF")
            gif_path = path.replace(".mp4", ".gif")
            return self.save_gif(gif_path, fps=fps)

        # Determine frame size from the first image
        first = PILImage.open(io.BytesIO(self._frames[0])).convert("RGB")
        w, h = first.size

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(path, fourcc, fps, (w, h))

        for png_bytes in self._frames:
            img = PILImage.open(io.BytesIO(png_bytes)).convert("RGB")
            frame = np.array(img)
            frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            writer.write(frame_bgr)

        writer.release()
        return path

    def save_screenshot(self, path: str = "screenshot.png") -> Optional[str]:
        """Save the most recent frame as a PNG file."""
        png = self.get_last_frame_png()
        if png is None:
            return None
        Path(path).write_bytes(png)
        return path

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def status(self) -> Dict[str, Any]:
        """Return current headless display status."""
        return {
            "env": self.env.name,
            "started": self._started,
            "resolution": f"{self.width}x{self.height}",
            "frames_captured": self._frame_count,
            "frames_stored": len(self._frames),
            "xvfb_active": self._vdisplay is not None,
            "ipython_available": self._ipython_display is not None,
            "pil_available": HAS_PIL,
            "pygame_available": HAS_PYGAME,
        }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _start_xvfb(self) -> None:
        """Start Xvfb virtual framebuffer via pyvirtualdisplay."""
        try:
            from pyvirtualdisplay import Display
            self._vdisplay = Display(
                visible=False,
                size=(self.width, self.height),
            )
            self._vdisplay.start()
            # Point SDL at the virtual display
            os.environ["DISPLAY"] = self._vdisplay.env()["DISPLAY"]
        except ImportError:
            # Fallback: try bare SDL dummy driver
            print(
                "[headless] pyvirtualdisplay not found, using SDL dummy driver.\n"
                "  Install: pip install pyvirtualdisplay && apt-get install xvfb"
            )
            os.environ["SDL_VIDEODRIVER"] = "dummy"
        except Exception as exc:
            print(f"[headless] Xvfb failed ({exc}), falling back to SDL dummy")
            os.environ["SDL_VIDEODRIVER"] = "dummy"

    @staticmethod
    def _array_to_png(arr: np.ndarray) -> bytes:
        """Convert (H, W, 3) uint8 array to PNG bytes."""
        img = PILImage.fromarray(arr.astype(np.uint8))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()


# ---------------------------------------------------------------------------
# Convenience: run a game headless and capture frames
# ---------------------------------------------------------------------------
def run_headless(
    num_steps: int = 300,
    ai_pilot: bool = True,
    save_gif_path: Optional[str] = "headless_session.gif",
    show_every: int = 30,
    capture_every: int = 2,
    max_frames: int = 600,
    gif_fps: int = 15,
    gif_scale: float = 0.5,
) -> HeadlessDisplay:
    """Run the Aethermoor game headless for *num_steps* frames.

    Returns the HeadlessDisplay with all captured frames.

    Parameters
    ----------
    num_steps : int
        Number of game ticks to run.
    ai_pilot : bool
        Enable AI autopilot for autonomous play.
    save_gif_path : str or None
        If set, saves a GIF at the end.
    show_every : int
        In Colab, show a frame inline every N steps.
    capture_every : int
        Keep one stored frame every N ticks.
    max_frames : int
        Maximum number of stored frames in ring buffer.
    gif_fps : int
        Output GIF frame rate.
    gif_scale : float
        Output GIF scale factor.
    """
    hd = HeadlessDisplay(
        max_frames=max_frames,
        capture_every=capture_every,
    )
    hd.start()

    # Must import AFTER headless display is set up
    # so pygame sees the virtual framebuffer / dummy driver
    import pygame
    sys.path.insert(0, str(Path(__file__).parent))
    from aethermoor_game import AethermoorGame, AIPilot

    game = AethermoorGame()
    pilot = AIPilot(game)
    if ai_pilot:
        pilot.enabled = True

    # Patch update with pilot
    _orig_update = game._update
    def _patched_update(dt: float) -> None:
        pilot.tick(dt)
        _orig_update(dt)
    game._update = _patched_update

    dt = 1.0 / 30.0
    print(f"[headless] Running {num_steps} steps ({hd.env.name} mode)...")

    for step in range(num_steps):
        game._handle_events()
        game._update(dt)
        game._draw()

        # Capture the game surface
        hd.capture(game.game_surface)

        # Show inline on Colab periodically
        if hd.env == RuntimeEnv.COLAB and step % show_every == 0:
            hd.show()

        if not game.running:
            print(f"[headless] Game exited at step {step}")
            break

    # Export
    if save_gif_path and hd.stored_frames > 0:
        result = hd.save_gif(save_gif_path, fps=gif_fps, scale=gif_scale)
        if result:
            print(f"[headless] GIF saved: {result} ({hd.stored_frames} frames)")
            # Show GIF inline on Colab
            if hd.env == RuntimeEnv.COLAB and hd._ipython_display:
                from IPython.display import Image
                hd._ipython_display(Image(filename=result))

    # Cleanup
    try:
        game.hf_trainer.stop()
    except Exception:
        pass
    pygame.quit()
    hd.stop()

    print(f"[headless] Done. Captured {hd.frame_count} frames, "
          f"stored {hd.stored_frames} for export.")

    return hd


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run Aethermoor headless")
    parser.add_argument("--steps", type=int, default=300, help="Number of ticks")
    parser.add_argument("--gif", type=str, default="headless_session.gif", help="GIF output path")
    parser.add_argument("--no-ai", action="store_true", help="Disable AI autopilot")
    parser.add_argument("--show-every", type=int, default=30, help="Inline display interval (Colab)")
    parser.add_argument("--capture-every", type=int, default=2, help="Store one frame every N ticks")
    parser.add_argument("--max-frames", type=int, default=600, help="Max stored frames in memory")
    parser.add_argument("--fps", type=int, default=15, help="Output GIF fps")
    parser.add_argument("--scale", type=float, default=0.5, help="Output GIF scale (0-1)")
    args = parser.parse_args()

    hd = run_headless(
        num_steps=args.steps,
        ai_pilot=not args.no_ai,
        save_gif_path=args.gif,
        show_every=args.show_every,
        capture_every=args.capture_every,
        max_frames=args.max_frames,
        gif_fps=args.fps,
        gif_scale=args.scale,
    )
    print(f"\nStatus: {hd.status()}")
