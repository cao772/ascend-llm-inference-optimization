"""V2 hardware lineage and responsive QA on Chromium + WebKit engines.

WebKit approximates Safari's rendering engine; this is not a native macOS
Safari certification. No live NPU or remote assets are required.
"""
import argparse
from pathlib import Path
from playwright.sync_api import sync_playwright


def exercise(browser, html, width, screenshots, errors):
    page=browser.new_page(viewport={"width":width,"height":850},device_scale_factor=1)
    page.on("pageerror",lambda exc: errors.append(str(exc)))
    page.goto(html.resolve().as_uri())
    assert page.locator("#product-grid .product-card").count()==10
    assert page.locator("#family-rail button").count()>=5
    # Form → family → concrete SKU → grounded processor level.
    page.locator("#product-tabs button",has_text="推理卡").click()
    assert page.locator("#product-grid .product-card").count()==2
    page.locator("#family-rail button",has_text="Atlas 推理系列产品").click()
    assert page.locator("#product-grid .product-card").count()==2
    page.locator("#product-grid .product-card",has_text="Atlas 300I Duo").click()
    assert "Ascend 310P" in page.locator("#product-detail").inner_text()
    page.locator('#product-crumb button[data-level="processor"]').click()
    assert page.locator("#drawer").is_visible()
    assert "310P" in page.locator("#drawer").inner_text()
    page.keyboard.press("Escape")
    assert page.locator("#drawer").is_hidden()
    # Product-specific topology should appear only for the official A3 scope.
    page.locator("#product-tabs button",has_text="超节点").click()
    page.locator("#product-grid .product-card",has_text="Atlas 900 A3").click()
    assert page.locator("#topology-evidence").is_visible()
    assert "HCCS-L2" in page.locator("#topology-evidence").inner_text()
    page.locator("#topology-source").click()
    assert "特定产品" in page.locator("#drawer").inner_text() or "A3" in page.locator("#drawer").inner_text()
    page.keyboard.press("Escape")
    page.locator("#product-tabs button",has_text="推理卡").click()
    assert page.locator("#topology-evidence").is_hidden()
    # Core modules remain functional while navigating a scoped product.
    page.locator("#path-vector").click()
    assert page.locator("#memory-path span").count()==5
    page.locator("#operator-tabs button",has_text="MoE").click()
    assert page.locator("#operator-steps button").count()==6
    page.locator("#operator-steps button").nth(5).click()
    assert "06 / 06" in page.locator("#op-number").inner_text()
    assert page.locator("#graph-stage .graph-node").count()>=2
    if width<=950:
        page.locator("#nav-toggle").click()
        assert page.locator("#nav").is_visible()
        page.keyboard.press("Escape")
        page.locator('#nav a[href="#operators"]').click()
        assert page.locator("#nav").is_hidden()
    overflow=page.evaluate("document.documentElement.scrollWidth-document.documentElement.clientWidth")
    assert overflow<=3, f"Horizontal overflow on {browser.browser_type.name} {width}: {overflow}px"
    if screenshots and width in {375,1440}:
        screenshots.mkdir(parents=True,exist_ok=True)
        page.screenshot(path=str(screenshots/f"ascend-v2-{browser.browser_type.name}-{width}.png"),full_page=True)
    page.close()


def run(html: Path, screenshots: Path | None):
    assert html.is_file()
    with sync_playwright() as playwright:
        errors=[]
        for engine in ("chromium","webkit"):
            browser=getattr(playwright,engine).launch(headless=True)
            for width in (375,768,1440):
                exercise(browser,html,width,screenshots,errors)
            browser.close()
        assert not errors, errors
    print("Cross-engine PASS: Chromium + WebKit, 375/768/1440, 4-level product taxonomy, official evidence and 7 operator storyboards")


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("html",type=Path)
    parser.add_argument("--screenshots",type=Path)
    args=parser.parse_args()
    run(args.html,args.screenshots)
