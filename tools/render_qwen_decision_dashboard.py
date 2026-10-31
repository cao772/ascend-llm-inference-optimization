#!/usr/bin/env python3
"""Render a portable, fully offline Qwen inference research/decision dashboard.

The HTML contains only curated evidence, explicit hypotheses and NOT MEASURED
placeholders. No CDN, trackers, network calls, JS libraries or benchmarks.
"""
import argparse
import json
from pathlib import Path

from build_qwen_decision_pipeline import (
    CASES_PATH, FAILURES_PATH, MATRIX, PRS_PATH, RULES, _load, decide
)

HTML = r'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="dark">
<title>Qwen 推理优化 · 证据到决策全链路</title>
<style>
:root{--navy:#091224;--navy2:#0e1b33;--panel:#12213a;--line:#283d57;
--txt:#e9f1ff;--dim:#a7bbd2;--teal:#70e0d8;--blue:#8fbaff;--amber:#f5cb80;
--red:#ffaaa8;--success:#a1e8b8}*{box-sizing:border-box}
html{scroll-behavior:smooth}body{margin:0;background:radial-gradient(circle at 80% 0,#142d4c 0,transparent 32rem),var(--navy);color:var(--txt);font-family:system-ui,-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;line-height:1.58}
a{color:var(--blue);text-underline-offset:3px}a:hover{color:white}
.wrap{max-width:1280px;margin:auto;padding:0 28px}.top{border-bottom:1px solid var(--line);background:#0a1529ec;position:sticky;top:0;z-index:4;backdrop-filter:blur(12px)}
.top .wrap{display:flex;align-items:center;justify-content:space-between;min-height:66px;gap:20px}
.brand{font-size:15px;font-weight:750;letter-spacing:.08em}.brand b{color:var(--teal)}
.top small,.muted{color:var(--dim)}.nav{display:flex;gap:18px;font-size:13px}.nav a{text-decoration:none}
.hero{padding:42px 0 25px}.eyebrow{font-size:12px;text-transform:uppercase;letter-spacing:.17em;color:var(--teal);font-weight:700}
h1{font-size:clamp(29px,4.2vw,49px);line-height:1.16;letter-spacing:-.04em;margin:14px 0 16px;font-weight:750}
.hero p{font-size:15px;max-width:780px;color:var(--dim)}
.note{border:1px solid #74573c;border-radius:12px;background:#3f302342;padding:12px 15px;color:#f8deaf;font-size:13px;margin:24px 0}
.metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:22px 0 30px}
.metric{background:var(--navy2);border:1px solid var(--line);border-radius:13px;padding:18px 20px}
.metric .number{font-size:29px;font-weight:750;letter-spacing:-.04em}.metric .label{color:var(--dim);font-size:12px}
section{padding:28px 0}h2{font-size:23px;line-height:1.4;margin:3px 0 17px}h3{font-size:16px;margin:0 0 10px}
.sub{color:var(--dim);font-size:13px;margin:-5px 0 20px}
.pipeline{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:8px}
.step{position:relative;min-height:165px;padding:16px 13px;border:1px solid var(--line);border-radius:13px;background:linear-gradient(180deg,#172b46,#0e2037)}
.step:after{content:"→";position:absolute;right:-11px;top:55px;font-size:18px;z-index:2;color:var(--teal)}
.step:last-child:after{content:none}.stepnum{font-size:12px;color:var(--teal);font-weight:700}
.step h3{margin:9px 0 5px;font-size:15px}.step .desc{color:var(--dim);font-size:12px}.step small{display:block;color:#dce6f5;font-size:11px;margin-top:8px}
.controlbar{display:flex;justify-content:space-between;align-items:end;gap:16px;flex-wrap:wrap;margin:10px 0 15px}
label{font-weight:650;font-size:12px;color:var(--dim);display:block;margin-bottom:6px}select{width:min(100%,560px);border:1px solid #506b88;border-radius:9px;background:#172840;color:var(--txt);padding:12px 13px;font-size:14px}
button{cursor:pointer;background:#152a43;color:var(--txt);border:1px solid var(--line);padding:8px 14px;border-radius:8px;font-size:13px}
button:hover{border-color:var(--blue)}button.active{background:#24465b;border-color:#5bafb6;color:white}
.action{background:#173e4c;border:1px solid #277683;color:#ddffff;padding:10px 13px}
.hero-grid{display:grid;grid-template-columns:1.4fr 1fr;gap:14px;margin-top:18px}
.panel{background:var(--navy2);border:1px solid var(--line);border-radius:15px;padding:18px 20px}
.pill{display:inline-flex;align-items:center;border-radius:100px;border:1px solid #546176;background:#27354a;color:#d6e4f9;padding:2px 10px;font-size:11px;font-weight:700}
.pill.p0{color:var(--teal);border-color:#356e74;background:#153a46}
.pill.p1{color:var(--blue);border-color:#395980}.pill.p2{color:#dabcfb;border-color:#66517d}
.pill.block{color:var(--red);border-color:#96544f;background:#462c32}
.pill.pending{color:var(--amber);border-color:#8b7050;background:#3d3127}
.factline{display:flex;gap:8px;flex-wrap:wrap;margin:14px 0}
.fact{background:#192e48;border:1px solid #2e4966;border-radius:9px;padding:8px 10px;font-size:12px}
.dataflag{font-weight:650;color:var(--teal)}
.dimtext{color:var(--dim);font-size:13px}.smalltext{font-size:12px;color:var(--dim)}
.rule{height:1px;background:var(--line);margin:14px 0}
.results{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:10px;margin:16px 0}
.result{border:1px solid var(--line);background:#0b1b31;padding:15px;border-radius:11px}
.result strong{display:block;font-size:20px;color:var(--amber);margin-top:7px}
.filters{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:15px}
.cards{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.hcard{background:var(--navy2);border:1px solid var(--line);border-radius:14px;padding:18px 18px 15px}
.hcard h3{margin:13px 0 8px;font-size:17px}.hcard p{margin:8px 0;font-size:13px}
.headrow{display:flex;gap:7px;align-items:center;flex-wrap:wrap}
.hcard .why{color:#d7e4f5}.prediction{background:#102d3d;border-left:3px solid #4eadae;padding:9px 11px;margin:12px 0;color:#c4ede9;font-size:12px}
details{border-top:1px solid var(--line);margin-top:13px;padding-top:9px}
summary{cursor:pointer;color:var(--blue);font-size:12px;font-weight:650}dt{color:var(--teal);font-size:12px;font-weight:700;margin-top:13px}
dd{margin:3px 0;color:#d7e4f5;font-size:12px}.links{display:flex;gap:10px;flex-wrap:wrap;margin:9px 0}
.links a{display:inline-block;font-size:11px;border:1px solid #355472;border-radius:5px;padding:3px 7px;text-decoration:none}
.risk{color:#ffcaa5;font-size:12px}.placeholder{color:var(--dim);font-style:italic}
.sr{border-top:1px solid var(--line);padding-top:10px;margin-top:10px}
.foot{border-top:1px solid var(--line);margin:42px 0 0;padding:28px 0 45px;color:var(--dim);font-size:12px}
.no-results{padding:25px;border:1px dashed var(--line);color:var(--dim);border-radius:10px}
.two{display:grid;grid-template-columns:1fr 1fr;gap:14px}.list{font-size:13px;color:#d6e3f2;padding-left:18px}
.list li{margin:6px 0}.statusrows{display:grid;gap:8px}
.statusrow{display:flex;justify-content:space-between;gap:18px;border-bottom:1px solid #223852;padding-bottom:8px;font-size:12px}
.statusrow span:last-child{color:var(--amber);font-weight:700}
@media(max-width:1080px){.pipeline{grid-template-columns:repeat(3,1fr)}.step:nth-child(3):after{content:none}.metrics{grid-template-columns:repeat(2,1fr)}}
@media(max-width:720px){.wrap{padding:0 16px}.nav{display:none}.pipeline{grid-template-columns:repeat(2,1fr)}.step:after{content:none}.hero-grid,.two,.cards{grid-template-columns:1fr}.results{grid-template-columns:repeat(2,1fr)}.controlbar{align-items:stretch}.top .wrap{min-height:58px}}
@media print{.top,button,.filters{display:none!important}body{background:white;color:#111}.panel,.hcard,.metric,.step{background:#fff;color:#111;break-inside:avoid}.muted,.dimtext{color:#555}}
</style></head>
<body>
<div class="top"><div class="wrap"><div class="brand"><b>QWEN</b> · INFERENCE INTELLIGENCE <small>/ 研究工作台</small></div><div class="nav"><a href="#pipeline">技术闭环</a><a href="#scenarios">情景推演</a><a href="#decisions">候选决策</a><a href="#acceptance">验收合同</a></div></div></div>
<main class="wrap">
<header class="hero"><div class="eyebrow">Evidence → Hypothesis → Experiment → Decision</div>
<h1>Qwen 推理优化<br>完整链路与条件性结果推演</h1>
<p>用公开案例、模型结构和上游源码驱动的<strong>可证伪假设</strong>，逐步确定优化方向、排除错误路径，再为未来实机验证准备可执行的实验合同。</p>
<div class="note"><b>研究状态 · 无落地环境</b>　此页不包含我方 NPU/GPU 性能数据。展示的优先级是研究顺序，不是实际瓶颈排名；所有收益均为条件性推测，TTFT / TPOT / TPS 仍须实测。</div>
<div class="metrics" id="counts"></div>
</header>
<section id="pipeline"><div class="eyebrow">SYSTEM WORKFLOW</div><h2>六阶段证据到结论闭环</h2><p class="sub">每一步都有输入、输出和通行门槛。缺乏真实 Profiling 时，不会从模型结构直接跳到“优化有效”。</p><div class="pipeline" id="steps"></div></section>
<section id="scenarios"><div class="eyebrow">SCENARIO LAB</div><h2>模型 × 硬件 × 负载情景推演</h2><p class="sub">以下都是未来实验设定，不代表用户已有芯片或部署条件。</p>
<div class="controlbar"><div style="flex:1;min-width:240px"><label for="scenario">选择研究情景</label><select id="scenario"></select></div><button id="download" class="action" type="button">导出全链路分析 JSON</button></div>
<div class="hero-grid"><div class="panel"><div class="eyebrow">MODEL / WORKLOAD</div><h2 id="sc-title" style="margin-top:11px"></h2><p class="dimtext" id="sc-desc"></p><div class="factline" id="sc-facts"></div><div class="rule"></div><h3>当前有依据的静态模型事实</h3><p class="dimtext" id="static-facts"></p><p class="risk" id="sc-uncertainties"></p></div>
<div class="panel"><div class="eyebrow">VERIFICATION GATES</div><h3 style="margin-top:12px">离实际性能结论还有哪些证据门槛</h3><div class="statusrows" id="gates"></div><p class="smalltext" style="margin-top:12px">这些门槛是当前缺失证据，不是项目开发失败。</p></div></div>
<h3 style="margin-top:24px">该情景的结果面板</h3><p class="sub">所有性能指标保持空值，防止静态推演被误认为跑分。</p><div class="results" id="results"></div>
</section>
<section id="decisions"><div class="eyebrow">HYPOTHESIS & DECISION</div><h2>候选优化、明确排除和验证条件</h2><p class="sub">每条研究路径提供触发条件、来源链接、测量方法、可证伪验收标准与回退方案。</p><div class="filters" id="filters"></div><div class="cards" id="cards"></div></section>
<section id="acceptance"><div class="eyebrow">ACCEPTANCE CONTRACT</div><h2>未来实机阶段应当怎么得出结论</h2><div class="two"><div class="panel"><h3>统一 A/B 实验合同</h3><ul class="list"><li>固定模型权重 revision、软件 SHA、CANN/驱动、TP/EP 和量化精度</li><li>同输入模板、相同采样设置、足够重复次数和稳定预热</li><li>区分 Prefill / Decode、算子 / 服务指标，报告 P50 与 P95</li><li>在相同业务语料下分别记录自然 MTP 接受率与受控接受率</li><li>检验数值正确性、确定性、超时、死锁、资源与回退能力</li><li>仅当性能超过统计噪声且正确性稳定，才升级为已验证优化</li></ul></div>
<div class="panel"><h3>证据级别不能越级</h3><div class="statusrows"><div class="statusrow"><span>官方源码与模型结构</span><span>已整理</span></div><div class="statusrow"><span>与当前版本/硬件兼容</span><span>待核验</span></div><div class="statusrow"><span>真实 Profile 定位瓶颈</span><span>待实测</span></div><div class="statusrow"><span>算子运行时实际命中</span><span>待实测</span></div><div class="statusrow"><span>同条件 A/B 的性能改善</span><span>待实测</span></div><div class="statusrow"><span>正确性及回退通过</span><span>待实测</span></div></div><p class="smalltext">本页属于「源码事实 + 可证伪假设 + 预设计验证链路」，不是部署验收报告。</p></div></div></section>
</main>
<footer class="foot"><div class="wrap">Research-only · Data as of 2026-10-31 · No weights, no GPU/NPU profiling, no invented benchmarks. 来源在每条研究卡片中；支持离线打开，所有交互不需要服务器。</div></footer>
<script id="research-data" type="application/json">__PAYLOAD__</script>
<script>
"use strict";
const DATA=JSON.parse(document.getElementById("research-data").textContent);
const $=id=>document.getElementById(id);
const state={scenario:DATA.scenarios[0].id,filter:"ALL"};
const esc=x=>String(x??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const safeLink=(url,label)=> /^https:\/\/[^\s"'<>]+$/.test(String(url)) ? '<a href="'+esc(url)+'" target="_blank" rel="noopener noreferrer">'+esc(label)+'</a>' : "";
const statusLabels={"P0":"先行验证","P1":"优先候选","P2":"后续候选","BLOCK":"排除特定路径"};
const statusClass={"P0":"p0","P1":"p1","P2":"p2","BLOCK":"block"};
function renderStatic(){
 let c=DATA.source_counts;
 $("counts").innerHTML=[["案例",c.external_case_records],["Qwen结构",c.official_model_structures],["上游 PR",c.upstream_pr_records],["失败/限制",c.failure_or_limit_records]].map(([a,b])=>'<div class="metric"><div class="number">'+esc(b)+'</div><div class="label">'+esc(a)+'</div></div>').join("");
 $("steps").innerHTML=DATA.pipeline.map((s,i)=>'<div class="step"><span class="stepnum">'+String(i+1).padStart(2,"0")+'</span><h3>'+esc(s.name)+'</h3><div class="desc">'+esc(s.output)+'</div><small>门槛：'+esc(s.gate)+'</small></div>').join("");
 $("scenario").innerHTML=DATA.scenarios.map(s=>'<option value="'+esc(s.id)+'">'+esc(s.title)+'</option>').join("");
 $("filters").innerHTML=["ALL","P0","P1","P2","BLOCK"].map(k=>'<button type="button" data-filter="'+k+'" aria-pressed="false">'+(k==="ALL"?"全部":statusLabels[k])+'</button>').join("");
 $("filters").addEventListener("click",e=>{const b=e.target.closest("[data-filter]");if(!b)return;state.filter=b.dataset.filter;renderDecisions()});
 $("scenario").addEventListener("change",e=>{state.scenario=e.target.value;renderScenario()});
 $("download").addEventListener("click",()=>{
 const blob=new Blob([JSON.stringify(DATA,null,2)],{type:"application/json;charset=utf-8"});
 const url=URL.createObjectURL(blob);const a=document.createElement("a");a.href=url;a.download="qwen-fullchain-decision-v1.json";document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
 });
}
function sNow(){return DATA.scenarios.find(s=>s.id===state.scenario)||DATA.scenarios[0]}
function renderScenario(){
 let s=sNow(),m=s.static_model_facts;
 $("sc-title").textContent=s.title;$("sc-desc").textContent=s.description;
 let facts=[s.framework_target,s.stage.toUpperCase()+" / C="+s.concurrency,"TP="+s.tp,"ISL/OSL "+s.input_tokens+"/"+s.output_tokens];
 $("sc-facts").innerHTML=facts.map(t=>'<span class="fact">'+esc(t)+'</span>').join("");
 $("static-facts").innerHTML='<span class="dataflag">'+(m.moe?'MoE':'Dense')+'</span>　GDN V/K：'+esc(m.gdn_head_ratio)+':1　·　'+(m.linear_attention_layers_explicit===null?'GDN层数未明示':esc(m.linear_attention_layers_explicit)+'层 GDN/Linear')+'　·　'+(m.moe?'专家 '+esc(m.num_experts)+' / TopK '+esc(m.num_experts_per_tok):'无 MoE 路由');
 $("sc-uncertainties").textContent="待核实：" + s.uncertainties.join("；");
 const gateMap={model_structure:"模型结构",chip_compatibility:"芯片/软件支持",runtime_baseline:"运行基线",profiling:"Profiler",correctness:"正确性",optimization_ab:"性能 A/B",production_rollout:"部署准入"};
 $("gates").innerHTML=Object.entries(s.entry_gates).map(([k,v])=>'<div class="statusrow"><span>'+esc(gateMap[k]||k)+'</span><span>'+esc(v==="reviewed_static_config_not_runtime_verified"?"静态整理":"未具备")+'</span></div>').join("");
 const names=[["TTFT P50","TTFT_p50_ms","ms"],["TPOT P50","TPOT_p50_ms","ms"],["E2E P95","E2E_p95_ms","ms"],["输出吞吐","output_tokens_s","tok/s"],["请求吞吐","requests_s","req/s"]];
 $("results").innerHTML=names.map(([n,k,u])=>'<div class="result"><div class="smalltext">'+esc(n)+'</div><strong>'+(s.observed_results[k]===null?"待实测":esc(s.observed_results[k])+" "+esc(u))+'</strong><span class="smalltext">本项目观测值：'+(s.observed_results[k]===null?"无":"有")+'</span></div>').join("");
 renderDecisions();
}
function renderDecisions(){
 let s=sNow();
 [...$("filters").querySelectorAll("button")].forEach(b=>{let active=b.dataset.filter===state.filter;b.classList.toggle("active",active);b.setAttribute("aria-pressed",String(active))});
 let rows=s.priority_actions.filter(h=>state.filter==="ALL"||h.priority===state.filter);
 $("cards").innerHTML=rows.length?rows.map(h=>{
  const refs=[...h.evidence.map((x,i)=>safeLink(x,"来源 "+(i+1))),...h.related_pr_urls.map((x,i)=>safeLink(x,h.related_pr_ids[i])),
   ...h.related_failure_sources.flatMap(item=>item.sources.map((x,i)=>safeLink(x,item.id+" / "+(i+1))))].filter(Boolean);
  return '<article class="hcard"><div class="headrow"><span class="pill '+statusClass[h.priority]+'">'+esc(statusLabels[h.priority])+'</span><span class="smalltext">'+esc(h.id)+' · '+esc(h.stage)+'</span><span class="pill pending">未实测</span></div><h3>'+esc(h.name)+'</h3><p class="why">'+esc(h.reason)+'</p><div class="prediction"><b>条件性推测：</b>'+esc(h.conditional_prediction)+'</div><details><summary>展开证据、测量方法、判定与回退</summary><dl><dt>证据和源码</dt><dd class="links">'+refs.join("")+'</dd><dt>需要采集</dt><dd>'+esc(h.measure)+'</dd><dt>验收/证伪标准</dt><dd>'+esc(h.acceptance)+'</dd><dt>不成立时如何回退</dt><dd>'+esc(h.rollback)+'</dd><dt>证据类型</dt><dd>'+esc(h.assessment_type)+'</dd><dt>特别限制</dt><dd>'+esc(h.flags.join(" / "))+'</dd></dl></details></article>';
 }).join(""):'<div class="no-results">当前情景没有这个类别的候选。请切换筛选项或研究情景。</div>';
}
renderStatic();renderScenario();
</script></body></html>'''


def render(report):
    if report["real_hardware_measurements"] != 0 or report["deployment_available"]:
        raise ValueError("This renderer only supports research-only, no-hardware outputs")
    for sc in report["scenarios"]:
        if sc["measurement_status"] != "not_measured" or any(v is not None for v in sc["observed_results"].values()):
            raise ValueError("Refuse to render unverified measurements as if sourced")
    payload = json.dumps(report, ensure_ascii=False, separators=(",", ":"))
    payload = payload.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    return HTML.replace("__PAYLOAD__", payload)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    try:
        report = decide(_load(RULES), _load(MATRIX), _load(CASES_PATH),
                        _load(PRS_PATH), _load(FAILURES_PATH))
        content = render(report)
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(content, encoding="utf-8")
    except (ValueError, OSError, KeyError) as err:
        p.error(str(err))
    print(f"Rendered {len(report['scenarios'])} research scenarios to {a.output}")


if __name__ == "__main__":
    main()
