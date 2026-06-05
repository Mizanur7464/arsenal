"""Detect queue, captcha, sold out, and other page conditions."""

from dataclasses import dataclass

from playwright.sync_api import Page


@dataclass
class PageState:
    label: str
    details: str
    url: str

    def line(self) -> str:
        return f"{self.label}: {self.details}"


def is_queue_page(page: Page) -> bool:
    url = page.url.lower()
    if any(x in url for x in ("hd-queue", "queue-it", "softblock")):
        return True
    try:
        title = (page.title() or "").lower()
        if "queue" in title and "event/index" not in url:
            return True
    except Exception:
        pass
    return False


def is_real_event_ticket_page(page: Page, event_id: int) -> bool:
    """True only on Arsenal ticket listing — not Queue-it waiting screen."""
    if is_queue_page(page):
        return False
    url = page.url.lower()
    if "restricted" in url:
        return False
    try:
        if "restricted" in (page.title() or "").lower():
            return False
    except Exception:
        pass
    return (
        "eticketing.co.uk" in url
        and f"event/index/{event_id}" in url.replace("\\", "/")
    )


def detect_page_state(page: Page) -> PageState:
    url = page.url.lower()
    try:
        body = page.locator("body").inner_text(timeout=5000).lower()
    except Exception:
        body = ""

    if "captcha" in body or "recaptcha" in body or "hcaptcha" in body:
        return PageState("CAPTCHA", "Captcha detected — manual step may be needed", page.url)

    if (
        is_queue_page(page)
        or "waiting room" in body
        or "your place in line" in body
        or "why is there a queue" in body
    ):
        return PageState("QUEUE", "Queue / waiting room active", page.url)

    if f"event/index" in url:
        if any(
            x in body
            for x in (
                "sold out",
                "no tickets available",
                "there are no tickets",
            )
        ):
            return PageState("SOLD_OUT", "No tickets available on page", page.url)
        return PageState("EVENT", "On event ticket page (seat map or listings)", page.url)

    if any(
        x in body
        for x in (
            "sold out",
            "no tickets available",
            "there are no tickets",
        )
    ):
        return PageState("SOLD_OUT", "No tickets available on page", page.url)

    if "eticketing.co.uk/arsenal" in url:
        return PageState("SITE", "On Arsenal eTicketing (home or listing)", page.url)

    if "login" in url or "signin" in url:
        return PageState("LOGIN", "Login page", page.url)

    return PageState("UNKNOWN", "Page loaded — state unclear", page.url)
