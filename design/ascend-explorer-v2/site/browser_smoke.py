"""Real Chromium interactions for the standalone Ascend V2 site.

Requires: pip install playwright && python -m playwright install chromium
Runs ONLY on a built offline HTML artifact, no NPU runtime or web calls.
"""
import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright


def run(html_path: Path, screenshots: Path | None = None):
    assert html_path.is_file(), str(html_path)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        errors = []
        page = browser.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=1)
        page.on("pageerror", lambda exc: errors.append(str(exc)))
        page.goto(html_path.resolve().as_uri())
        assert page.locator("#product-grid .product-card").count() > 0
        assert page.locator("#hero-chain button").count() == 4
        assert page.locator("#research-stats .metric-card").count() == 4
        assert "75" in page.locator("#count-evidence").inner_text()
        # D1: product filtering, detail, comparison, official evidence.
        page.locator("#product-tabs button", has_text="推理卡").click()
        assert page.locator("#product-grid .product-card").count() == 2
        page.locator("#product-grid .product-card").first.click()
        page.locator("#product-add").click()
        page.locator("#compare-products").click()
        assert page.locator("#comparison").is_visible()
        page.locator("#clear-compare").click()
        page.locator("#product-source").click()
        assert page.locator("#drawer").is_visible()
        page.keyboard.press("Escape")
        assert page.locator("#drawer").is_hidden()
        # D2: chip component, memory path and software layer.
        page.locator("#chip-units button", has_text="Cube").click()
        assert "Cube" in page.locator("#chip-detail-title").inner_text()
        page.locator("#path-vector").click()
        assert page.locator("#memory-path span").count() == 5
        page.locator("#path-next").click()
        page.locator("#stack-layers .stack-layer").nth(3).click()
        assert "CANN" in page.locator("#stack-detail-title").inner_text()
        # D3: token timeline and evidence-only metrics.
        page.locator("#isl").fill("3")
        page.locator("#osl").fill("3")
        assert "4096" in page.locator("#isl-value").inner_text()
        page.locator("#timeline-stages .stage").nth(3).click()
        assert "Decode" in page.locator("#lifecycle-detail").inner_text()
        # D4: factor and operator storyboard.
        page.locator("#factor-tabs button", has_text="Graph").click()
        assert "Graph" in page.locator("#factor-chain").inner_text()
        page.locator("#operator-tabs button", has_text="MoE").click()
        assert page.locator("#operator-steps button").count() == 6
        page.locator("#operator-steps button").nth(5).click()
        assert "06 / 06" in page.locator("#op-number").inner_text()
        page.locator("#op-sources").click()
        assert page.locator("#drawer").is_visible()
        page.locator("#drawer-close").click()
        # D5: diagnosis, cases and evidence drawer.
        page.locator("#symptoms button", has_text="TTFT").click()
        assert page.locator("#diagnosis-path .decision-step").count() == 4
        page.locator("#evidence-tabs button", has_text="全部案例").click()
        assert page.locator("#case-grid .case-card").count() == 15
        page.locator("#case-query").fill("GDN")
        assert page.locator("#case-grid .case-card").count() > 0
        page.locator("#case-grid .case-card button").first.click()
        assert page.locator("#drawer").is_visible()
        page.keyboard.press("Escape")
        # Desktop screenshot for documentation (not screenshot-based implementation).
        if screenshots:
            screenshots.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(screenshots / "ascend-v2-desktop.png"), full_page=True)
        # Mobile, navigation, overflow check.
        mobile = browser.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=1, is_mobile=True)
        mobile.on("pageerror", lambda exc: errors.append(str(exc)))
        mobile.goto(html_path.resolve().as_uri())
        mobile.locator("#nav-toggle").click()
        assert mobile.locator("#nav").is_visible()
        mobile.locator('#nav a[href="#hardware"]').click()
        assert mobile.locator("#nav").is_hidden()
        width = mobile.evaluate("document.documentElement.scrollWidth - window.innerWidth")
        assert width <= 3, f"Mobile horizontal overflow by {width}px"
        if screenshots:
            mobile.screenshot(path=str(screenshots / "ascend-v2-mobile.png"), full_page=True)
        assert not errors, errors
        browser.close()
        print("Chromium PASS: 9 sections, hardware, anatomy, stack, lifecycle, 7 ops, diagnosis, case search, drawer and mobile.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("html", type=Path)
    parser.add_argument("--screenshots", type=Path)
    args = parser.parse_args()
    run(args.html, args.screenshots)
