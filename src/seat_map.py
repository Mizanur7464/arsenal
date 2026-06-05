"""Arsenal EDP seat-map: wait for SPA, scan main page + iframes/canvas, pick seats."""

import re
from typing import Any

from playwright.sync_api import Frame, Page

from .auth import dismiss_cookie_and_overlays
from .logger_setup import sub, sub_ok, sub_warn

PRICE_RE = re.compile(r"£\s*(\d+(?:\.\d{2})?)")
MAP_READY_HINTS = (
    "filter your search",
    "event information",
    "choose by",
    "quantity",
    "seat map",
    "available",
)
SKIP_TEXT = re.compile(
    r"being purchased|sold out|not available|unavailable|reserved|restricted",
    re.I,
)
ADD_BASKET_SELECTORS = [
    'button:has-text("Add to Basket")',
    'button:has-text("Add to basket")',
    'button:has-text("Add To Basket")',
    'button:has-text("Continue")',
    'button:has-text("Confirm")',
    'button:has-text("Add")',
]
FIND_CLICKABLES_JS = """
() => {
  const out = [];
  const skip = /being purchased|sold out|not available|unavailable|reserved|disabled/i;
  const nodes = document.querySelectorAll(
    'button, a, [role="button"], li, div, span, g, path, circle, rect, polygon'
  );
  for (const el of nodes) {
    const text = (el.innerText || el.getAttribute('aria-label') || '').trim();
    if (text && skip.test(text)) continue;
    const st = window.getComputedStyle(el);
    if (st.display === 'none' || st.visibility === 'hidden' || parseFloat(st.opacity) < 0.25) continue;
    const r = el.getBoundingClientRect();
    if (r.width < 6 || r.height < 6 || r.bottom < 0 || r.right < 0) continue;
    const tag = el.tagName.toLowerCase();
    if (text.includes('£') && text.length < 150) {
      out.push({ kind: 'price', x: r.x + r.width / 2, y: r.y + r.height / 2, label: text.slice(0, 80) });
      continue;
    }
    if (tag === 'path' || tag === 'circle' || tag === 'rect' || tag === 'polygon' || tag === 'g') {
      const fill = (el.getAttribute('fill') || '').toLowerCase();
      const cls = (el.className?.baseVal || el.className || '').toString().toLowerCase();
      if (cls.includes('unavail') || cls.includes('sold') || cls.includes('disabled')) continue;
      if (fill && /gray|grey|#ccc|#ddd|#eee|#f5|#fff|silver/i.test(fill)) continue;
      if (fill || cls.includes('avail') || cls.includes('select') || cls.includes('active')) {
        out.push({ kind: 'svg', x: r.x + r.width / 2, y: r.y + r.height / 2, label: cls.slice(0, 40) || fill });
      }
    }
  }
  const canvas = document.querySelector('canvas');
  if (canvas) {
    const r = canvas.getBoundingClientRect();
    if (r.width > 40 && r.height > 40) {
      out.push({ kind: 'canvas', x: r.x + r.width / 2, y: r.y + r.height / 2, label: 'canvas', w: r.width, h: r.height });
    }
  }
  return out.slice(0, 50);
}
"""
CANVAS_SEAT_JS = """
(el) => {
  const canvas = el;
  const ctx = canvas.getContext('2d');
  if (!ctx) return [];
  const w = canvas.width, h = canvas.height;
  if (w < 10 || h < 10) return [];
  let img;
  try { img = ctx.getImageData(0, 0, w, h); } catch (e) { return []; }
  const pts = [];
  const step = Math.max(8, Math.floor(Math.min(w, h) / 80));
  for (let y = step; y < h - step; y += step) {
    for (let x = step; x < w - step; x += step) {
      const i = (y * w + x) * 4;
      const r = img.data[i], g = img.data[i + 1], b = img.data[i + 2], a = img.data[i + 3];
      if (a < 128) continue;
      const grey = Math.abs(r - g) < 25 && Math.abs(g - b) < 25;
      if (grey && r > 120) continue;
      if (r > 240 && g > 240 && b > 240) continue;
      if (b > 70 && b >= r && !(grey && r > 100)) {
        pts.push({ x, y });
        if (pts.length >= 8) return pts;
      }
    }
  }
  return pts;
}
"""


def map_ready_seconds(config: dict) -> float:
    return float(config.get("retry", {}).get("map_ready_seconds", 6))


def wait_for_ticket_ui(page: Page, config: dict) -> bool:
    """Wait until seat-map / filter UI is rendered (SPA)."""
    ms = int(map_ready_seconds(config) * 1000)
    sub(f"Waiting up to {ms // 1000}s for ticket UI to render...")
    deadline = ms
    step = 800
    elapsed = 0
    while elapsed < deadline:
        dismiss_cookie_and_overlays(page)
        try:
            body = page.locator("body").inner_text(timeout=2000).lower()
        except Exception:
            body = ""
        if any(h in body for h in MAP_READY_HINTS):
            sub_ok("Ticket UI text detected")
            page.wait_for_timeout(1000)
            return True
        if page.locator("canvas").first.is_visible(timeout=500):
            sub_ok("Seat map canvas visible")
            page.wait_for_timeout(1000)
            return True
        for frame in page.frames:
            try:
                if frame.locator("canvas").first.is_visible(timeout=400):
                    sub_ok("Canvas found in iframe")
                    page.wait_for_timeout(1000)
                    return True
            except Exception:
                continue
        page.wait_for_timeout(step)
        elapsed += step
    sub_warn("Ticket UI slow to load — scanning anyway")
    return False


def soft_refresh_event_page(page: Page, event_url: str, timeout_ms: int, config: dict) -> None:
    """Reload event page then wait for map (monitor cycles)."""
    reload = config.get("retry", {}).get("monitor_reload", True)
    if reload and event_url:
        from .browser import goto

        goto(page, event_url, timeout_ms, label="event-refresh")
    else:
        try:
            page.reload(wait_until="domcontentloaded", timeout=timeout_ms)
        except Exception:
            pass
    wait_for_ticket_ui(page, config)


def prepare_event_page(page: Page, config: dict, *, quiet: bool = False) -> None:
    dismiss_cookie_and_overlays(page)
    wait_for_ticket_ui(page, config)
    qty = max(1, int(config.get("filters", {}).get("quantity", 1)))
    _set_quantity_stepper(page, qty, quiet=quiet)
    if not config.get("filters", {}).get("seats_together", True):
        _ensure_seats_together_off(page)
    _open_choose_by_area(page)


def _open_choose_by_area(page: Page) -> None:
    for text in ("Choose by Area", "Choose By Area", "By Area", "Areas"):
        try:
            tab = page.get_by_role("tab", name=text).first
            if tab.is_visible(timeout=800):
                tab.click()
                page.wait_for_timeout(800)
                return
        except Exception:
            pass
        try:
            loc = page.get_by_text(text, exact=False).first
            if loc.is_visible(timeout=800):
                loc.click()
                page.wait_for_timeout(800)
                return
        except Exception:
            continue


def _set_quantity_stepper(page: Page, target: int, *, quiet: bool = False) -> bool:
    if not quiet:
        sub(f"Setting quantity to {target} via +/- controls...")
    current = _read_quantity_value(page)
    if current is None:
        current = 1
    if current == target:
        if not quiet:
            sub_ok(f"Quantity is {target}")
        return True

    plus = [
        'button[aria-label*="increase" i]',
        '[class*="increment" i] button',
        '[class*="increment" i]',
        'button:has-text("+")',
    ]
    minus = [
        'button[aria-label*="decrease" i]',
        '[class*="decrement" i] button',
        '[class*="decrement" i]',
        'button:has-text("-")',
    ]
    for _ in range(12):
        if current == target:
            if not quiet:
                sub_ok(f"Quantity is {target}")
            return True
        if current < target:
            if not _click_stepper(page, plus):
                break
        elif not _click_stepper(page, minus):
            break
        page.wait_for_timeout(350)
        current = _read_quantity_value(page) or current
    return current == target


def _read_quantity_value(page: Page) -> int | None:
    try:
        for sel in ('[class*="quantity" i] input', 'input[type="number"]'):
            loc = page.locator(sel).first
            if loc.is_visible(timeout=800):
                val = loc.input_value() or loc.inner_text()
                if val and str(val).strip().isdigit():
                    return int(str(val).strip())
    except Exception:
        pass
    return None


def _click_stepper(page: Page, selectors: list[str]) -> bool:
    for sel in selectors:
        try:
            btn = page.locator(sel).first
            if btn.is_visible(timeout=1000):
                btn.click(force=True)
                return True
        except Exception:
            continue
    return False


def _ensure_seats_together_off(page: Page) -> None:
    try:
        loc = page.locator('text=Only show me seats together').first
        if not loc.is_visible(timeout=1500):
            return
        inp = page.locator('text=Only show me seats together').locator("xpath=..//input[@type='checkbox']").first
        if inp.is_visible(timeout=800) and inp.is_checked():
            inp.click(force=True)
            sub_ok("Seats-together toggle OFF")
    except Exception:
        pass


def _iter_scan_roots(page: Page) -> list[Page | Frame]:
    roots: list[Page | Frame] = [page]
    for frame in page.frames:
        if frame == page.main_frame:
            continue
        try:
            if frame.is_detached():
                continue
        except Exception:
            continue
        roots.append(frame)
    return roots


def _find_click_targets(root: Page | Frame) -> list[dict[str, Any]]:
    try:
        raw = root.evaluate(FIND_CLICKABLES_JS)
        return raw if isinstance(raw, list) else []
    except Exception:
        return []


def _click_at(root: Page | Frame, x: float, y: float, dry_run: bool) -> bool:
    if dry_run:
        return True
    try:
        if isinstance(root, Page):
            root.mouse.click(x, y)
        else:
            root.page.mouse.click(x, y)
        return True
    except Exception:
        return False


def _click_canvas_seats(page: Page, dry_run: bool) -> bool:
    for root in _iter_scan_roots(page):
        try:
            canvas = root.locator("canvas").first
            if not canvas.is_visible(timeout=1500):
                continue
            box = canvas.bounding_box()
            if not box:
                continue
            pts = canvas.evaluate(CANVAS_SEAT_JS)
            if not pts:
                continue
            dims = canvas.evaluate("c => ({ w: c.width, h: c.height })")
            cw = max(float(dims.get("w") or 1), 1)
            ch = max(float(dims.get("h") or 1), 1)
            sub(f"Canvas: trying {len(pts)} coloured seat point(s)...")
            for pt in pts[:6]:
                cx = box["x"] + (pt["x"] / cw) * box["width"]
                cy = box["y"] + (pt["y"] / ch) * box["height"]
                if dry_run:
                    sub_ok("DRY_RUN: would click canvas seat")
                    return True
                page.mouse.click(cx, cy)
                page.wait_for_timeout(1200)
                if _click_add_to_basket(page, dry_run):
                    return True
        except Exception:
            continue
    return False


def _click_js_targets(page: Page, targets: list[dict[str, Any]], dry_run: bool) -> bool:
    order = sorted(
        targets,
        key=lambda t: (0 if t.get("kind") == "price" else 1 if t.get("kind") == "svg" else 2),
    )
    for t in order[:12]:
        kind = t.get("kind", "")
        label = (t.get("label") or "")[:50]
        if SKIP_TEXT.search(label):
            continue
        if dry_run:
            sub_ok(f"DRY_RUN: would click {kind} @ {label}")
            return True
        for root in _iter_scan_roots(page):
            try:
                if kind == "price" and label:
                    loc = root.get_by_text(label[:25], exact=False).first
                    if loc.is_visible(timeout=1200):
                        loc.click()
                        page.wait_for_timeout(1500)
                        sub_ok(f"Clicked price row: {label[:40]}")
                        return True
                x, y = t.get("x"), t.get("y")
                if x is not None and y is not None:
                    _click_at(root, float(x), float(y), dry_run=False)
                    page.wait_for_timeout(1500)
                    sub_ok(f"Clicked {kind} on map")
                    return True
            except Exception:
                continue
    return False


def _click_add_to_basket(page: Page, dry_run: bool) -> bool:
    for sel in ADD_BASKET_SELECTORS:
        try:
            btn = page.locator(sel).first
            if btn.is_visible(timeout=2000):
                if dry_run:
                    return True
                btn.click()
                page.wait_for_timeout(2000)
                sub_ok(f"Clicked [{sel}]")
                return True
        except Exception:
            continue
    return False


def count_map_targets(page: Page) -> int:
    total = 0
    for root in _iter_scan_roots(page):
        total += len(_find_click_targets(root))
    return total


def try_pick_seat_and_basket(page: Page, config: dict, dry_run: bool) -> bool:
    """Pick first available seat/section via DOM + canvas, then add to basket."""
    prepare_event_page(page, config, quiet=True)

    targets: list[dict[str, Any]] = []
    for root in _iter_scan_roots(page):
        targets.extend(_find_click_targets(root))

    n_price = sum(1 for t in targets if t.get("kind") == "price")
    n_svg = sum(1 for t in targets if t.get("kind") == "svg")
    n_canvas = sum(1 for t in targets if t.get("kind") == "canvas")
    sub(f"Map scan: {len(targets)} targets (price={n_price}, svg={n_svg}, canvas={n_canvas})")

    clicked = False
    if targets:
        clicked = _click_js_targets(page, targets, dry_run)
    if not clicked:
        clicked = _click_canvas_seats(page, dry_run)
    if not clicked:
        sub_warn("No available seat/section to click on map")
        return False

    page.wait_for_timeout(1000)
    if _click_add_to_basket(page, dry_run):
        return True

    from .tickets import confirm_in_basket

    if dry_run or confirm_in_basket(page):
        return True

    sub_warn("Seat clicked but basket not confirmed")
    return False
