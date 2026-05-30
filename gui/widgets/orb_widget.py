"""
gui/widgets/orb_widget.py — Central animated orb using QPainter.

States and their visual behaviour:
  LOCKED   → dim red slow pulse
  IDLE     → slow blue breathing pulse (2 s period)
  LISTENING → fast cyan expanding rings
  THINKING → spinning arc segments (purple)
  EXECUTING → rapid amber flash
  SPEAKING  → sine-wave ripple (green)
  ERROR    → red strobe
"""

from __future__ import annotations
import math

from PySide6.QtCore import Qt, QTimer, QPointF, QRectF
from PySide6.QtGui import (
    QPainter, QPainterPath, QColor, QRadialGradient,
    QPen, QConicalGradient,
)
from PySide6.QtWidgets import QWidget

from core.state_machine import State

# Palette
_COLORS = {
    State.LOCKED:    ("#FF3355", "#880022"),
    State.IDLE:      ("#0066CC", "#003366"),
    State.LISTENING: ("#00D4FF", "#006688"),
    State.THINKING:  ("#7B5FFF", "#3A1F88"),
    State.EXECUTING: ("#FF9900", "#884400"),
    State.SPEAKING:  ("#00FF88", "#004422"),
    State.ERROR:     ("#FF3355", "#880022"),
}


class OrbWidget(QWidget):
    """Fully custom-painted animated orb."""

    ORB_RADIUS = 110

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(300, 300)
        self._state = State.IDLE

        self._tick = 0           # animation frame counter
        self._ring_phase = 0.0   # for expanding rings
        self._spin_angle = 0.0   # for thinking arc rotation
        self._wave_phase = 0.0   # for speaking wave

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._advance)
        self._timer.start(16)    # ~60 fps

    def set_state(self, state: State) -> None:
        if self._state != state:
            self._state = state
            self._tick = 0
            self.update()

    # ── Animation tick ───────────────────────────────────────────────────────

    def _advance(self) -> None:
        self._tick += 1
        self._ring_phase = (self._ring_phase + 0.04) % (2 * math.pi)
        self._spin_angle = (self._spin_angle + 3.0) % 360.0
        self._wave_phase = (self._wave_phase + 0.12) % (2 * math.pi)
        self.update()

    # ── Paint ────────────────────────────────────────────────────────────────

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        cx = self.width() / 2
        cy = self.height() / 2
        r = self.ORB_RADIUS

        primary, secondary = _COLORS.get(self._state, ("#0066CC", "#003366"))
        p_color = QColor(primary)
        s_color = QColor(secondary)

        state = self._state

        # 1. Outer glow rings
        if state == State.LISTENING:
            self._draw_listening_rings(painter, cx, cy, r, p_color)
        elif state == State.THINKING:
            self._draw_spinning_arcs(painter, cx, cy, r, p_color)
        elif state == State.SPEAKING:
            self._draw_speaking_waves(painter, cx, cy, r, p_color)
        else:
            self._draw_pulse_ring(painter, cx, cy, r, p_color, state)

        # 2. Core orb gradient
        self._draw_core(painter, cx, cy, r, p_color, s_color)

        # 3. Inner highlight
        self._draw_highlight(painter, cx, cy, r)

        painter.end()

    # ── Draw helpers ─────────────────────────────────────────────────────────

    def _draw_core(self, p: QPainter, cx, cy, r, primary: QColor, secondary: QColor):
        grad = QRadialGradient(QPointF(cx, cy - r * 0.2), r * 1.1)
        core = QColor(primary)
        core.setAlpha(220)
        mid = QColor(secondary)
        mid.setAlpha(200)
        edge = QColor(secondary)
        edge.setAlpha(80)
        grad.setColorAt(0.0, core)
        grad.setColorAt(0.55, mid)
        grad.setColorAt(1.0, edge)

        p.setBrush(grad)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(cx, cy), r, r)

    def _draw_highlight(self, p: QPainter, cx, cy, r):
        grad = QRadialGradient(QPointF(cx - r * 0.3, cy - r * 0.35), r * 0.55)
        grad.setColorAt(0.0, QColor(255, 255, 255, 60))
        grad.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.setBrush(grad)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(cx - r * 0.3, cy - r * 0.35), r * 0.55, r * 0.55)

    def _draw_pulse_ring(self, p: QPainter, cx, cy, r, color: QColor, state: State):
        # Slow breathing pulse
        if state == State.IDLE:
            t = (math.sin(self._ring_phase * 0.5) + 1) / 2     # 0→1 slow
        elif state in (State.LOCKED, State.ERROR):
            t = (math.sin(self._tick * 0.05) + 1) / 2
        elif state == State.EXECUTING:
            t = (math.sin(self._tick * 0.25) + 1) / 2
        else:
            t = 0.5

        ring_r = r + 12 + t * 20
        alpha = int(30 + t * 60)
        pen_color = QColor(color)
        pen_color.setAlpha(alpha)
        p.setPen(QPen(pen_color, 2.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(cx, cy), ring_r, ring_r)

    def _draw_listening_rings(self, p: QPainter, cx, cy, r, color: QColor):
        for i in range(3):
            phase = (self._ring_phase + i * (2 * math.pi / 3)) % (2 * math.pi)
            expand = (phase / (2 * math.pi))      # 0→1
            ring_r = r + 10 + expand * 55
            alpha = int(100 * (1 - expand))
            c = QColor(color)
            c.setAlpha(max(0, alpha))
            p.setPen(QPen(c, 2.0))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QPointF(cx, cy), ring_r, ring_r)

    def _draw_spinning_arcs(self, p: QPainter, cx, cy, r, color: QColor):
        pen = QPen(color, 3.5)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        rect = QRectF(cx - r - 18, cy - r - 18, (r + 18) * 2, (r + 18) * 2)
        for i in range(3):
            start_angle = int((self._spin_angle + i * 120) * 16)
            span = int(80 * 16)
            c = QColor(color)
            c.setAlpha(180 - i * 50)
            pen.setColor(c)
            p.setPen(pen)
            p.drawArc(rect, start_angle, span)

    def _draw_speaking_waves(self, p: QPainter, cx, cy, r, color: QColor):
        # Draw 3 ripple rings that expand and fade
        for i in range(3):
            phase = (self._wave_phase + i * 1.0) % (2 * math.pi)
            amp = math.sin(phase)
            ring_r = r + 8 + amp * 28
            alpha = int(max(0, 80 * ((amp + 1) / 2)))
            c = QColor(color)
            c.setAlpha(alpha)
            p.setPen(QPen(c, 2.0))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QPointF(cx, cy), ring_r, ring_r)
