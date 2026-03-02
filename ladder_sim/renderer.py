import tkinter as tk
from elements import Contact, Coil, TON, TOF, CTU, CTD

# Layout constants
CELL_W = 90       # pixels per element cell
CELL_H = 80       # pixels per rung (base height)
BRANCH_H = 50     # extra height per parallel branch
RAIL_X = 30       # left power rail x
RIGHT_MARGIN = 40 # gap between last element and right rail
RUNG_TOP = 20     # y offset for first rung
COMMENT_H = 18    # height reserved for rung comment

COLOR_ENERGIZED = "#00aa44"
COLOR_DE = "#888888"
COLOR_RAIL = "#222222"
COLOR_TEXT = "#000000"
COLOR_BG = "#ffffff"
COLOR_COIL_ON = "#0055cc"
COLOR_BLOCK_BG = "#eef4ff"


class LadderRenderer:
    def __init__(self, canvas: tk.Canvas, engine):
        self.canvas = canvas
        self.engine = engine
        self.clickables: list[tuple[str, int, int, int, int]] = []

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def draw(self):
        c = self.canvas
        c.delete("all")
        self.clickables = []

        rungs = self.engine.rungs
        canvas_width = int(c["width"]) if c["width"] != "" else 900

        y = RUNG_TOP
        for rung in rungs:
            rung_height = self._rung_height(rung["series"])
            mid_y = y + COMMENT_H + rung_height // 2

            # Comment
            if rung["comment"]:
                c.create_text(RAIL_X + 10, y + 4, anchor="nw",
                              text=rung["comment"], font=("Helvetica", 9, "italic"),
                              fill="#555555")

            # Left rail
            c.create_line(RAIL_X, y + COMMENT_H,
                          RAIL_X, y + COMMENT_H + rung_height,
                          width=3, fill=COLOR_RAIL)

            # Draw series elements; returns x_end
            x_end = self._draw_series(rung["series"], RAIL_X, mid_y,
                                       y + COMMENT_H, rung_height)

            # Right rail
            right_x = x_end + RIGHT_MARGIN
            c.create_line(right_x, y + COMMENT_H,
                          right_x, y + COMMENT_H + rung_height,
                          width=3, fill=COLOR_RAIL)

            # Wire from last element to right rail
            c.create_line(x_end, mid_y, right_x, mid_y,
                          width=2, fill=COLOR_RAIL)

            y += COMMENT_H + rung_height + 10

    def hit_test(self, px: int, py: int) -> str | None:
        for (bit, x1, y1, x2, y2) in self.clickables:
            if x1 <= px <= x2 and y1 <= py <= y2:
                return bit
        return None

    # ------------------------------------------------------------------
    # Height calculation (needed before drawing)
    # ------------------------------------------------------------------

    def _rung_height(self, series) -> int:
        max_branches = 1
        for elem in series:
            if isinstance(elem, dict) and "parallel" in elem:
                max_branches = max(max_branches, len(elem["parallel"]))
        return CELL_H + (max_branches - 1) * BRANCH_H

    # ------------------------------------------------------------------
    # Series / element drawing
    # ------------------------------------------------------------------

    def _draw_series(self, series, x_start: int, mid_y: int,
                     top_y: int, height: int) -> int:
        """Draw a series list of elements starting at x_start on mid_y.
        Returns x position after the last element."""
        x = x_start
        # Leading wire from rail to first element
        first_x = x + 10
        c = self.canvas

        power = True  # track energisation for colouring
        prev_power = True

        # We need two passes: compute energisation, then draw.
        # But energisation is in the engine already, so we read from engine.bits.
        # We track it separately here for wire colouring.
        x = x_start

        for i, elem in enumerate(series):
            if isinstance(elem, dict) and "parallel" in elem:
                color = COLOR_ENERGIZED if prev_power else COLOR_DE
                x_end = self._draw_parallel(elem["parallel"], x, mid_y, top_y, height, prev_power)
                # Determine if any branch is energized
                branch_power = any(
                    self._series_energized(branch) for branch in elem["parallel"]
                )
                prev_power = prev_power and branch_power
                x = x_end
            elif isinstance(elem, Contact):
                color = COLOR_ENERGIZED if prev_power else COLOR_DE
                x_end = self._draw_contact(x, mid_y, elem, color)
                bit_val = self.engine.bits.get(elem.bit, False)
                contact_pass = (not bit_val) if elem.type == "NC" else bit_val
                prev_power = prev_power and contact_pass
                x = x_end
            elif isinstance(elem, Coil):
                color = COLOR_COIL_ON if prev_power else COLOR_DE
                x_end = self._draw_coil(x, mid_y, elem, color)
                x = x_end
            elif isinstance(elem, (TON, TOF)):
                color = COLOR_ENERGIZED if prev_power else COLOR_DE
                x_end = self._draw_timer_block(x, mid_y, elem, color)
                x = x_end
            elif isinstance(elem, (CTU, CTD)):
                color = COLOR_ENERGIZED if prev_power else COLOR_DE
                x_end = self._draw_counter_block(x, mid_y, elem, color)
                x = x_end

        return x

    def _series_energized(self, series) -> bool:
        """Return True if the series evaluates to True based on current bit states."""
        power = True
        for elem in series:
            if isinstance(elem, dict) and "parallel" in elem:
                power = power and any(self._series_energized(b) for b in elem["parallel"])
            elif isinstance(elem, Contact):
                bit_val = self.engine.bits.get(elem.bit, False)
                if elem.type == "NC":
                    bit_val = not bit_val
                power = power and bit_val
            # Coils/timers/counters don't block power in series evaluation for display
        return power

    # ------------------------------------------------------------------
    # Contact  --[ ]--  or  --[/]--
    # ------------------------------------------------------------------

    def _draw_contact(self, x: int, y: int, elem: Contact, wire_color: str) -> int:
        c = self.canvas
        x1 = x + 8
        x2 = x1 + CELL_W - 16
        bar_left = x1 + 10
        bar_right = x2 - 10

        bit_val = self.engine.bits.get(elem.bit, False)
        if elem.type == "NC":
            contact_on = not bit_val
        else:
            contact_on = bit_val
        contact_color = COLOR_ENERGIZED if contact_on else COLOR_DE

        # Wire in
        c.create_line(x, y, x1, y, width=2, fill=wire_color)
        # Left bar
        c.create_line(bar_left, y - 10, bar_left, y + 10, width=2, fill=contact_color)
        # Wire between bars
        c.create_line(bar_left, y, bar_right, y, width=2, fill=contact_color)
        # Right bar
        c.create_line(bar_right, y - 10, bar_right, y + 10, width=2, fill=contact_color)
        # Wire out
        c.create_line(bar_right, y, x2, y, width=2, fill=contact_color)

        # NC slash
        if elem.type == "NC":
            c.create_line(bar_left + 3, y + 10, bar_right - 3, y - 10,
                          width=2, fill=contact_color)

        # Label (bit name / label)
        label = self._bit_label(elem.bit)
        c.create_text((bar_left + bar_right) // 2, y - 16,
                      text=elem.bit, font=("Courier", 8), fill="#333333")
        c.create_text((bar_left + bar_right) // 2, y + 18,
                      text=label, font=("Helvetica", 8), fill="#333333")

        # Register clickable if input
        meta = self.engine.bit_meta.get(elem.bit, {})
        if meta.get("type") == "input":
            self.clickables.append((elem.bit, bar_left - 5, y - 14, bar_right + 5, y + 14))

        return x2

    # ------------------------------------------------------------------
    # Coil  --( )--
    # ------------------------------------------------------------------

    def _draw_coil(self, x: int, y: int, elem: Coil, wire_color: str) -> int:
        c = self.canvas
        x1 = x + 8
        x2 = x1 + CELL_W - 16
        cx = (x1 + x2) // 2
        r = 12

        if elem.type == "reset_all":
            coil_color = wire_color
        else:
            bit_val = self.engine.bits.get(elem.bit, False)
            coil_color = COLOR_COIL_ON if bit_val else COLOR_DE

        # Wire in
        c.create_line(x, y, x1, y, width=2, fill=wire_color)
        # Circle
        c.create_oval(cx - r, y - r, cx + r, y + r,
                      outline=coil_color, width=2, fill=COLOR_BG)
        # Wire out (short, to rail)
        c.create_line(cx + r, y, x2, y, width=2, fill=coil_color)

        # Type letter inside circle
        symbol = {"coil": "", "set": "S", "reset": "R", "reset_all": "RST"}.get(elem.type, "")
        if symbol:
            font_size = 7 if elem.type == "reset_all" else 9
            c.create_text(cx, y, text=symbol, font=("Helvetica", font_size, "bold"),
                          fill=coil_color)

        # Labels
        if elem.type != "reset_all":
            label = self._bit_label(elem.bit)
            c.create_text(cx, y - 20, text=elem.bit, font=("Courier", 8), fill="#333333")
            c.create_text(cx, y + 20, text=label, font=("Helvetica", 8), fill="#333333")

        return x2

    # ------------------------------------------------------------------
    # Timer block
    # ------------------------------------------------------------------

    def _draw_timer_block(self, x: int, y: int, elem, wire_color: str) -> int:
        c = self.canvas
        bw, bh = 110, 36
        x1 = x + 8
        x2 = x1 + bw
        top = y - bh // 2
        bot = y + bh // 2

        ts = self.engine.timers.get(elem.bit)
        acc = int(ts.accumulated_ms) if ts else 0

        c.create_line(x, y, x1, y, width=2, fill=wire_color)
        c.create_rectangle(x1, top, x2, bot, outline=wire_color, fill=COLOR_BLOCK_BG, width=2)

        kind = "TON" if isinstance(elem, TON) else "TOF"
        c.create_text(x1 + 5, top + 4, anchor="nw",
                      text=f"{kind}  {elem.bit}", font=("Courier", 8, "bold"), fill="#000")
        c.create_text(x1 + 5, top + 18, anchor="nw",
                      text=f"ACC: {acc} ms", font=("Courier", 8), fill="#333")

        c.create_line(x2, y, x2 + 8, y, width=2, fill=wire_color)
        return x2 + 8

    # ------------------------------------------------------------------
    # Counter block
    # ------------------------------------------------------------------

    def _draw_counter_block(self, x: int, y: int, elem, wire_color: str) -> int:
        c = self.canvas
        bw, bh = 110, 36
        x1 = x + 8
        x2 = x1 + bw
        top = y - bh // 2
        bot = y + bh // 2

        cs = self.engine.counters.get(elem.bit)
        count = cs.count if cs else 0

        c.create_line(x, y, x1, y, width=2, fill=wire_color)
        c.create_rectangle(x1, top, x2, bot, outline=wire_color, fill=COLOR_BLOCK_BG, width=2)

        kind = "CTU" if isinstance(elem, CTU) else "CTD"
        c.create_text(x1 + 5, top + 4, anchor="nw",
                      text=f"{kind}  {elem.bit}", font=("Courier", 8, "bold"), fill="#000")
        c.create_text(x1 + 5, top + 18, anchor="nw",
                      text=f"CNT: {count}", font=("Courier", 8), fill="#333")

        c.create_line(x2, y, x2 + 8, y, width=2, fill=wire_color)
        return x2 + 8

    # ------------------------------------------------------------------
    # Parallel block
    # ------------------------------------------------------------------

    def _draw_parallel(self, branches: list, x: int, mid_y: int,
                        top_y: int, height: int, incoming_power: bool) -> int:
        c = self.canvas
        n = len(branches)

        # Vertical spread: place branches evenly
        branch_ys = []
        if n == 1:
            branch_ys = [mid_y]
        else:
            spacing = BRANCH_H
            total_span = (n - 1) * spacing
            start_y = mid_y - total_span // 2
            branch_ys = [start_y + i * spacing for i in range(n)]

        # Determine max width of all branches (draw to find x_end)
        # We draw each branch and remember x_end
        x_in = x + 10
        branch_ends = []

        for i, (branch, by) in enumerate(zip(branches, branch_ys)):
            branch_energized = incoming_power and self._series_energized(branch)
            branch_color = COLOR_ENERGIZED if branch_energized else COLOR_DE

            # Horizontal wire from left junction to first element
            c.create_line(x_in, by, x_in + 6, by, width=2, fill=branch_color)

            x_end = self._draw_series(branch, x_in, by,
                                       top_y, height)
            branch_ends.append(x_end)

        max_end = max(branch_ends)

        # Left vertical bar connecting all branches
        c.create_line(x_in, branch_ys[0], x_in, branch_ys[-1], width=2, fill=COLOR_RAIL)
        # Right vertical bar
        c.create_line(max_end, branch_ys[0], max_end, branch_ys[-1], width=2, fill=COLOR_RAIL)

        # Extend short branches to max_end with wires
        for i, (x_end, by) in enumerate(zip(branch_ends, branch_ys)):
            if x_end < max_end:
                branch_energized = incoming_power and self._series_energized(branches[i])
                fill = COLOR_ENERGIZED if branch_energized else COLOR_DE
                c.create_line(x_end, by, max_end, by, width=2, fill=fill)

        # Wire from x to left bar at mid_y
        overall_energized = incoming_power and any(
            self._series_energized(b) for b in branches
        )
        wire_color = COLOR_ENERGIZED if incoming_power else COLOR_DE
        c.create_line(x, mid_y, x_in, mid_y, width=2, fill=wire_color)
        c.create_line(x_in, mid_y, x_in, branch_ys[0], width=2, fill=COLOR_RAIL)
        c.create_line(x_in, mid_y, x_in, branch_ys[-1], width=2, fill=COLOR_RAIL)

        # Wire from right bar to continuation at mid_y
        out_color = COLOR_ENERGIZED if overall_energized else COLOR_DE
        c.create_line(max_end, mid_y, max_end + 10, mid_y, width=2, fill=out_color)

        return max_end + 10

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _bit_label(self, bit: str) -> str:
        meta = self.engine.bit_meta.get(bit, {})
        return meta.get("label", "")
