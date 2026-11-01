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
    assert "140 TFLOPS" in page.locator("#verified-spec-detail").inner_text()
    assert "48 / 96 GB" in page.locator("#verified-spec-detail").inner_text()
    page.locator("#verified-source").click()
    assert "整卡" in page.locator("#drawer").inner_text()
    page.keyboard.press("Escape")

    page.locator('#product-crumb button[data-level="processor"]').click()
    assert page.locator("#drawer").is_visible()
    assert "310P" in page.locator("#drawer").inner_text()
    page.keyboard.press("Escape")
    assert page.locator("#drawer").is_hidden()
    # Product-specific topology should appear only for the official A3 scope.

    page.locator("#product-tabs button",has_text="推理服务器").click()
    page.locator("#product-grid .product-card",has_text="Atlas 800I A2").click()
    assert "392 GB/s" in page.locator("#verified-spec-detail").inner_text()
    assert "可选" in page.locator("#verified-spec-detail").inner_text()
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

    page.locator("#path-gemm").click()
    assert page.locator("#core-illustration svg").count()==1
    assert "FixPipe" in page.locator("#core-illustration").text_content()
    assert "第 1/7 步" in page.locator("#core-step-detail").inner_text()
    page.locator("#path-next").click()
    assert "第 2/7 步" in page.locator("#core-step-detail").inner_text()
    page.locator("#path-vector").click()
    assert "Vector" in page.locator("#core-illustration").text_content()
    assert "第 1/5 步" in page.locator("#core-step-detail").inner_text()
    # V2.4 external published measurements: separate total operator vs MTE2 evidence.
    assert page.locator("#reported-evidence-grid .reported-row").count()==3
    text=page.locator("#reported-evidence-grid").inner_text()
    assert "12,045 μs" in text and "2,532 μs" in text
    assert "2,452 μs" in text and "808 μs" in text and "591 μs" in text
    assert "完整算子执行耗时" in text and "MTE2 搬运流水耗时" in text
    assert "Ascend C 公开测试数据" in page.locator("#matmul-reported-evidence").inner_text()
    page.locator("#reported-evidence-source").click()
    assert page.locator("#drawer").is_visible()
    assert "原始" in page.locator("#drawer").inner_text() or "MTE2" in page.locator("#drawer").inner_text()
    page.keyboard.press("Escape")
    # V2.3 interactive GEMM: real arithmetic, ragged boundaries, idealized reads.
    assert page.locator("#tiling-summary .tile-stat").count()==6
    page.locator("#tiling-presets button",has_text="非整除").click()
    assert "18" in page.locator("#tiling-summary").inner_text()
    assert page.locator("#tiling-matrices .matrix-mini").count()==3
    page.locator("#tiling-next").click()
    assert "2 / 18" in page.locator("#tiling-step").inner_text()
    page.locator("#tiling-methods button",has_text="理想复用 B").click()
    assert "不是实测 GM" in page.locator("#tiling-traffic").inner_text()
    page.locator("#tiling-sources").click()
    assert "NPU" in page.locator("#drawer").inner_text()
    page.keyboard.press("Escape")
    assert page.locator("#drawer").is_hidden()
    page.locator("#compat-family-tabs button",has_text="Atlas 推理系列").click()
    assert "不适用此组件" in page.locator("#compat-view").inner_text()
    page.locator("#compat-family-tabs button",has_text="Atlas A3").click()
    assert "CANN Toolkit" in page.locator("#compat-view").inner_text()
    assert "GLM" in page.locator("#compat-models").inner_text()

    assert page.locator("#memory-path span").count()==5
    page.locator("#operator-tabs button",has_text="MatMul").click()
    assert page.locator("#gemm-lab-link").is_visible()
    page.locator("#operator-tabs button",has_text="MoE").click()
    assert page.locator("#gemm-lab-link").is_hidden()
    assert page.locator("#operator-steps button").count()==6
    page.locator("#operator-steps button").nth(5).click()
    assert "06 / 06" in page.locator("#op-number").inner_text()
    # V2.5 empirical archive: filter, inspect published profiler, examine cache two rounds.
    assert page.locator("#exp-summary .exp-summary-tile").count()==4
    assert "31" in page.locator("#exp-summary").inner_text()
    assert page.locator("#experiment-cards .experiment-card").count()==15
    page.locator("#experiment-tabs button",has_text="算子 Profile").click()
    assert page.locator("#experiment-cards .experiment-card").count()==8
    page.locator("#experiment-query").fill("Scalar")
    assert page.locator("#experiment-cards .experiment-card").count()>=1
    assert "10.62" in page.locator("#experiment-detail").inner_text()
    assert "7.87" in page.locator("#experiment-detail").inner_text()
    page.locator("#experiment-query").fill("")
    page.locator("#experiment-tabs button",has_text="服务与故障").click()
    assert page.locator("#experiment-cards .experiment-card").count()==7
    assert "不同配置/轮次对照" in page.locator("#experiment-detail").inner_text()
    assert "3990.14" in page.locator("#experiment-detail").inner_text() or "3,990.14" in page.locator("#experiment-detail").inner_text()
    page.locator("#experiment-example").click()
    assert "Benchmark" in page.locator("#drawer").inner_text()
    page.keyboard.press("Escape")
    assert page.locator("#drawer").is_hidden()

    page.locator("#experiment-tabs button",has_text="Attention").click()
    assert page.locator("#experiment-cards .experiment-card").count()==1
    assert page.locator("#experiment-detail .exp-metric").count()==0  # unpaired percentages cannot create fake before/after values
    assert "6.2" in page.locator("#experiment-detail").inner_text()
    assert "open PR" in page.locator("#experiment-detail").inner_text()
    page.locator("#experiment-tabs button",has_text="MoE").click()
    assert page.locator("#experiment-cards .experiment-card").count()==2
    page.locator("#experiment-cards .experiment-card",has_text="DeepSeek-R1").click()
    assert "9.72" in page.locator("#experiment-detail").inner_text()
    assert "退化" in page.locator("#experiment-detail").inner_text()
    page.locator("#experiment-tabs button",has_text="GDN").click()
    assert page.locator("#experiment-cards .experiment-card").count()==2
    assert "39" in page.locator("#experiment-detail").inner_text()
    page.locator("#experiment-tabs button",has_text="多卡通信").click()
    assert page.locator("#experiment-cards .experiment-card").count()==2
    assert "1,719.37" in page.locator("#experiment-detail").inner_text()
    assert "不同配置/轮次对照" in page.locator("#experiment-detail").inner_text()
    page.locator("#experiment-query").fill("")
    page.locator("#experiment-tabs button",has_text="全部有来源案例").click()
    assert page.locator("#graph-stage .graph-node").count()>=2
    if width<=950:
        page.locator("#nav-toggle").click()
        assert page.locator("#nav").is_visible()
        page.keyboard.press("Escape")
        page.locator('#nav a[href="#operators"]').click()
        assert page.locator("#nav").is_hidden()
    overflow=page.evaluate("document.documentElement.scrollWidth-document.documentElement.clientWidth")
    if overflow>3:
        offenders=page.evaluate("""Array.from(document.querySelectorAll("*")).map(e=>({tag:e.tagName,id:e.id,cls:String(e.className).slice(0,80),left:Math.round(e.getBoundingClientRect().left),right:Math.round(e.getBoundingClientRect().right)})).filter(x=>x.right>document.documentElement.clientWidth+3||x.left < -3).slice(0,18)""")
        raise AssertionError(f"Horizontal overflow on {browser.browser_type.name} {width}: {overflow}px; offenders={offenders}")
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
