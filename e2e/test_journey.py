"""End-to-end: the full Lakshmi journey in Tamil, text mode, on a 360 x 800 phone viewport.

Run against a running app (backend serving the exported frontend):
    BASE_URL=http://localhost:8000 pytest e2e -q
Screenshots land in docs/screenshots/.
"""

import os
import re
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect, sync_playwright

BASE = os.environ.get("BASE_URL", "http://localhost:8000")
SHOTS = Path(__file__).resolve().parents[1] / "docs" / "screenshots"


@pytest.fixture(scope="module")
def page():
    SHOTS.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={"width": 360, "height": 800}, device_scale_factor=2, is_mobile=True, has_touch=True, locale="ta-IN")
        pg = ctx.new_page()
        yield pg
        b.close()


def shot(page: Page, name: str, full: bool = False):
    page.wait_for_timeout(250)
    page.screenshot(path=str(SHOTS / f"{name}.png"), full_page=full)


def chip(page: Page, label: str):
    page.get_by_role("button", name=label).first.click()


def test_lakshmi_journey(page: Page):
    page.goto(BASE + "/")
    expect(page.get_by_role("button", name=re.compile("தமிழ்"))).to_be_visible()
    shot(page, "01-language")
    page.get_by_role("button", name=re.compile("தமிழ்")).click()

    expect(page.get_by_text("தொடங்கும் முன்")).to_be_visible()
    shot(page, "02-consent")
    page.get_by_role("button", name="ஒப்புக்கொள்கிறேன், தொடங்குவோம்").click()

    expect(page.get_by_text("வணக்கம்")).to_be_visible()
    shot(page, "03-mic")
    page.get_by_role("button", name="தட்டச்சு செய்ய").click()
    box = page.get_by_label("உங்கள் பதிலைத் தட்டச்சு செய்யவும்")
    box.fill("என் கணவர் இறந்துவிட்டார். எனக்கு 62 வயது. நான் மதுரையில் இருக்கிறேன்.")
    page.get_by_role("button", name="அனுப்பு").click()

    # "Which of these do you have?" — multi-select chips
    expect(page.get_by_text("இவற்றில் உங்களிடம் எவை உள்ளன?")).to_be_visible()
    chip(page, "வங்கி / அஞ்சலகக் கணக்கு")
    chip(page, "PHH / AAY")
    chip(page, "வீட்டில் எரிவாயு இணைப்பு")
    shot(page, "04-chips")
    page.get_by_role("button", name="முடிந்தது", exact=True).click()

    answers = {
        "குடும்பத்தின் மொத்த ஆண்டு வருமானம்": "₹1.2 லட்சத்திற்கு கீழ்",
        "என்ன வேலை": "இல்லத்தரசி",
        "விவசாய நிலம்": "நிலம் இல்லை",
        "மாற்றுத்திறனாளி சான்றிதழ்": "இல்லை",
        "10 வயதுக்குட்பட்ட": "இல்லை",
        "சாதிச் சான்றிதழில்": "MBC",
    }
    for _ in range(12):
        page.wait_for_timeout(400)
        prompt = page.locator("section[aria-live]").inner_text()
        if "தகுதி பெறலாம்" in prompt:
            break
        if "குடும்பத்திற்கோ பொருந்துமா" in prompt:
            page.get_by_role("button", name="இவை எதுவும் இல்லை").click()
            continue
        for q, a in answers.items():
            if q in prompt:
                chip(page, a)
                break
        else:
            raise AssertionError(f"unexpected question: {prompt}")
    expect(page.get_by_role("link", name="என் திட்டங்கள்")).to_be_visible()
    shot(page, "05-done")

    page.get_by_role("link", name="என் திட்டங்கள்").click()
    expect(page.get_by_text("உங்களுக்குக் கிடைக்கக்கூடிய திட்டங்கள்")).to_be_visible()
    expect(page.get_by_text("இந்திரா காந்தி தேசிய விதவை ஓய்வூதியத் திட்டம்")).to_be_visible()
    expect(page.get_by_text("கலைஞர் மகளிர் உரிமைத் தொகை")).to_be_visible()
    expect(page.locator(".slip").filter(has_text="தகுதி உண்டு")).to_have_count(5)
    shot(page, "06-results")
    shot(page, "06-results-full", full=True)

    page.get_by_text("இந்திரா காந்தி தேசிய விதவை ஓய்வூதியத் திட்டம்").click()
    expect(page.get_by_text("எடுத்துச் செல்ல வேண்டிய ஆவணங்கள்")).to_be_visible()
    expect(page.get_by_role("link", name=re.compile("NSAP Guidelines"))).to_have_count(3)
    shot(page, "07-scheme", full=True)

    # Ask a question, answered from the scheme's own text with a citation
    page.get_by_label("இந்தத் திட்டம் பற்றிக் கேளுங்கள்").fill("எங்கே விண்ணப்பிப்பது?")
    page.get_by_role("button", name="கேள்", exact=True).click()
    expect(page.get_by_text("வட்டாட்சியர் அலுவலகம்").last).to_be_visible()

    # Packet PDF (signed link, valid 10 minutes)
    with page.expect_response(re.compile(r"/packets/.+\.pdf")) as resp:
        page.get_by_role("button", name="அலுவலகத்திற்கான PDF பதிவிறக்கு").click()
    r = resp.value
    assert r.ok and r.headers["content-type"] == "application/pdf"
    page.goto(BASE + "/scheme/?id=ignwps")  # the PDF download leaves the tab mid-navigation; reload rather than go_back
    expect(page.get_by_text("எடுத்துச் செல்ல வேண்டிய ஆவணங்கள்")).to_be_visible()

    # Delete my data from the menu
    page.get_by_role("button", name="பட்டியல்").click()
    page.get_by_role("button", name="என் தரவு அனைத்தையும் நீக்கு").click()
    page.get_by_role("button", name="ஆம், அனைத்தையும் நீக்கு").click()
    expect(page.get_by_text("உங்கள் தரவு நீக்கப்பட்டது.")).to_be_visible()
