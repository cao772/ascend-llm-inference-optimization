"use strict";
(function(){
const D=JSON.parse(document.getElementById("app-data").textContent);
const $=id=>document.getElementById(id);
const esc=x=>String(x??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const safeLink=(url,label)=>/^https:\/\/[^\s"'<>]+$/i.test(String(url))?'<a class="source-link" href="'+esc(url)+'" target="_blank" rel="noopener noreferrer">'+esc(label)+'</a>':"";
const labelStatus=v=>v==null?"详见官方规格":String(v);
let previousFocus=null;
function drawer({title,category="RESEARCH EVIDENCE",body="",items=[],urls=[]}){
 previousFocus=document.activeElement;
 $("drawer-title").textContent=title;$("drawer-category").textContent=category;
 $("drawer-content").innerHTML="<p>"+esc(body)+"</p>"+(items.length?"<ul>"+items.map(x=>"<li>"+esc(x)+"</li>").join("")+"</ul>":"")+(urls.length?'<hr class="divider"><div class="source-links">'+urls.map((u,i)=>safeLink(u,"原始来源 "+(i+1))).join("")+"</div>":"");
 $("drawer").hidden=false;$("drawer-backdrop").hidden=false;document.body.style.overflow="hidden";$("drawer-close").focus();
}
function closeDrawer(){$("drawer").hidden=true;$("drawer-backdrop").hidden=true;document.body.style.overflow="";previousFocus?.focus?.()}
$("drawer-close").addEventListener("click",closeDrawer);$("drawer-backdrop").addEventListener("click",closeDrawer);
document.addEventListener("keydown",e=>{if(e.key==="Escape"&&!$("drawer").hidden)closeDrawer();if(e.key==="Tab"&&!$("drawer").hidden){const nodes=[...$("drawer").querySelectorAll("button,a,[tabindex]:not([tabindex='-1'])")].filter(n=>!n.disabled);if(!nodes.length)return;const first=nodes[0],last=nodes[nodes.length-1];if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus()}else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus()}}});
$("nav-toggle").addEventListener("click",()=>{const open=$("nav").classList.toggle("open");$("nav-toggle").setAttribute("aria-expanded",String(open))});
document.querySelectorAll("#nav a").forEach(a=>a.addEventListener("click",()=>{$("nav").classList.remove("open");$("nav-toggle").setAttribute("aria-expanded","false")}));
function tabs(node,values,active,onClick){node.innerHTML=values.map(({id,label})=>'<button type="button" class="tab" data-id="'+esc(id)+'" aria-pressed="'+(id===active?'true':'false')+'">'+esc(label)+'</button>').join("");node.querySelectorAll("button").forEach(b=>b.addEventListener("click",()=>onClick(b.dataset.id)))}
function blockButton(text,id,selected,klass="chip"){return '<button type="button" class="'+klass+'" data-id="'+esc(id)+'" aria-pressed="'+String(id===selected)+'">'+esc(text)+'</button>'}
const officialArch="https://www.hiascend.com/document/detail/en/CANNCommunityEdition/910/programug/Ascendcopdevg/docs/en/guide/programming_guide/advanced_programming/hardware_implementation/basic_architecture.md";
const officialProduct="https://www.hiascend.com/doc_center/source/zh/mind-sdk/600/description/productform/hardwaredesc_0001.html";
const frameworkDocs="https://docs.vllm.ai/projects/ascend/en/v0.30.0/user_guide/release_notes.html";
const kernelDocs="https://docs.vllm.ai/projects/ascend/en/v0.30.0/user_guide/feature_guide/graph_mode.html";
const sequences="https://docs.vllm.ai/projects/ascend/en/v0.30.0/user_guide/feature_guide/sequence_parallelism.html";
const heroStages=[
{id:"request",name:"请求/调度",eng:"Host · Scheduler",body:"请求到达后会先经历分词、排队、Batch 组装和引擎调度，不同并发与调度策略可能影响 TTFT 与 P95。",items:["检查队列时间与预处理是否计入指标","观察 Host gap、吞吐与 Batch 形状"],jump:"#lifecycle"},
{id:"prefill",name:"Prefill",eng:"Input tokens",body:"对输入 Token 做预填充计算，通常更需要关注长输入、Attention/GDN、数据搬运与多卡通信。",items:["ISL 与 TTFT 的关系","注意力/线性状态计算与通信路径"],jump:"#operators"},
{id:"cache",name:"KV / State",eng:"Memory & reuse",body:"Full Attention 常用 KV Cache，部分线性/混合注意力还涉及 recurrent state；二者不能完全等同。",items:["内存容量与缓存页表","状态正确性、Prefix 复用与空间开销"],jump:"#anatomy"},
{id:"decode",name:"Decode",eng:"Output tokens",body:"生成阶段反复更新 Token，关注 KV/State 访问、调度间隙、微小 Kernel 与 MTP 自然草稿接受率。",items:["TPOT、输出吞吐和尾延迟","只凭一条算子微基准不能推导端到端收益"],jump:"#lifecycle"}
];
let currentHero="prefill";function renderHero(){ $("hero-chain").innerHTML=heroStages.map(x=>'<button class="flow-node" aria-pressed="'+(x.id===currentHero)+'" data-id="'+x.id+'">'+esc(x.name)+'<small>'+esc(x.eng)+'</small></button>').join("");$("hero-chain").querySelectorAll("button").forEach(b=>b.addEventListener("click",()=>{currentHero=b.dataset.id;renderHero();const s=heroStages.find(x=>x.id===currentHero);drawer({title:s.name,category:"请求链路·解释",body:s.body,items:s.items,urls:[officialArch,frameworkDocs]})}))}
function initGenericEvidence(){document.querySelectorAll("[data-drawer-key]").forEach(b=>b.addEventListener("click",()=>{
 const key=b.dataset.drawerKey;
 if(key==="product")drawer({title:"官方产品、芯片与规格必须分开",body:"Atlas 产品形态不同于 310P/910B/910C 这样的芯片系列标识。按不同产品和配置展示官方规格，便于对照部署形态与计算资源。",items:["先核对正式产品名和形态","再核对产品具体规格文档与测试精度","最后核对对应 CANN/框架/模型/并行拓扑"],urls:[officialProduct]});
 else if(key==="architecture")drawer({title:"Ascend C 架构抽象与代际差异",body:"此处使用 Cube/Vector/Scalar/GM/UB/L1/L0/MTE 教学抽象，不指认任何一款芯片的物理单元数量、实际 Cache 大小或内部连线布局。",items:["Cube、Vector、Scalar 执行不同计算与控制任务","GM 与 Local Memory 关系要看具体架构","AIC/AIV 分离仅对应部分官方架构"],urls:[officialArch]});
 else drawer({title:"软件版本与功能兼容性",body:"vLLM-Ascend 在不同时期有不同版本的 Graph、Static/Super Kernel、Sequence Parallel 等能力。必须区分功能文档、设备支持、运行时命中与实际收益。",items:["确认目标芯片/版本/模型/精度/拓扑兼容","通过日志、Profiler 证明目标 Kernel 真实命中","单变量 A/B 并验收数值正确性"],urls:[frameworkDocs,kernelDocs,sequences]});
}))}
let form="all",familyId="all",productId=null,compareIds=[];
const lineage=D.productLineage;

const verifiedCatalog=D.verifiedSpecs;
function verifiedProduct(id){return verifiedCatalog.products.find(p=>p.id===id)}
function formatScopedValue(x){return (x.values?x.values.join(" / "):String(x.value))+" "+x.unit}
function verifiedFactsMarkup(rec){return rec?'<div class="section-header"><div><h3 class="panel-title">已核实的具体产品规格</h3><p class="section-intro">来源明确，且为整卡 / 整机或某种可选配置；不可将不同单位拼成同一“显卡算力”。</p></div><span class="badge">华为官方产品页</span></div><div class="spec-grid">'+rec.specs.map(x=>'<div class="spec-tile"><span class="data-label">'+esc(x.label)+'</span><strong>'+esc(formatScopedValue(x))+'</strong><small>'+esc(x.scope)+'</small></div>').join("")+'</div><div class="linkline"><button class="btn ghost" type="button" id="verified-source">查看规格来源与版本限制</button></div>':'<div class="verified-pending">产品信息以具体 SKU 和配置为索引；可从下方官方来源查阅型号说明与参数。</div>'}

const forms=[{id:"all",label:"全部产品"},{id:"module",label:"模块"},{id:"accelerator_card",label:"推理卡"},{id:"edge_system",label:"边缘整机"},{id:"inference_server",label:"推理服务器"},{id:"training_server",label:"训练服务器"},{id:"compute_pod",label:"超节点"}];
function familyFor(p){return lineage.productFamilyOverrides[p.id]||lineage.families.find(f=>f.name===p.family)?.id||"unclassified"}
function familyName(id){return lineage.families.find(f=>f.id===id)?.name||"尚未独立分类"}
function processorProof(p){return lineage.productProcessorMappings.find(m=>m.productId===p.id)}
function visibleProducts(){return D.hardware.products.filter(p=>(form==="all"||p.form===form)&&(familyId==="all"||familyFor(p)===familyId))}
function productSelection(){const items=visibleProducts();const p=items.find(p=>p.id===productId)||items[0]||null;productId=p?.id||null;return p}
function displayBreadcrumb(p){
 const items=[{title:"形态："+(form==="all"?"全部":D.hardware.formVocab[form]),level:"form"},{title:"产品族："+(familyId==="all"?"全部":familyName(familyId)),level:"family"},{title:"产品："+p.name,level:"product"},{title:"处理器："+(processorProof(p)?.processorFamily||"型号资料"),level:"processor"}];
 $("product-crumb").innerHTML=items.map((i,n)=>(n?'<span class="crumb-arrow" aria-hidden="true">›</span>':"")+'<button class="crumb-btn" type="button" data-level="'+i.level+'" aria-current="'+(n===3?"step":"false")+'">'+esc(i.title)+'</button>').join("");
 $("product-crumb").querySelectorAll("button").forEach(btn=>btn.addEventListener("click",()=>{
   const lv=btn.dataset.level;
   if(lv==="form"){form="all";familyId="all";productId=null;renderProducts()}
   else if(lv==="family"){form="all";familyId=familyFor(p);productId=null;renderProducts()}
   else if(lv==="product"){productId=p.id;renderProducts()}
   else{
     const m=processorProof(p);
     drawer({title:p.name+" · 处理器证据",category:"产品→处理器→版本",body:m?m.processorFamily+"：官方产品形态文档将该产品列在配置此处理器的产品族中。":"此产品当前没有固定到处理器型号的充分官方证据，不能用产品族名称臆测芯片。",items:m?[m.scope,"不是精确芯片规格或型号兼容结论"]:["请查具体 SKU 数据手册或服务/设备清单"],urls:m?[m.sourceUrl,p.sourceUrl]:[p.sourceUrl]});
   }
 }));
}
function renderProducts(){
 tabs($("product-tabs"),forms,form,x=>{form=x;familyId="all";productId=null;renderProducts()});
 const familyMatches=lineage.families.filter(f=>D.hardware.products.some(p=>(form==="all"||p.form===form)&&familyFor(p)===f.id));
 const familyOptions=[{id:"all",label:"全部产品族"},...familyMatches.map(x=>({id:x.id,label:x.name}))];
 if(familyId!=="all"&&!familyMatches.some(f=>f.id===familyId))familyId="all";
 $("family-rail").innerHTML=familyOptions.map(x=>'<button type="button" class="family-btn" aria-pressed="'+String(x.id===familyId)+'" data-id="'+esc(x.id)+'">'+esc(x.label)+'<small>'+(x.id==="all"?D.hardware.products.filter(p=>form==="all"||p.form===form).length:D.hardware.products.filter(p=>(form==="all"||p.form===form)&&familyFor(p)===x.id).length)+'</small></button>').join("");
 $("family-rail").querySelectorAll("button").forEach(btn=>btn.addEventListener("click",()=>{familyId=btn.dataset.id;productId=null;renderProducts()}));
 const subset=visibleProducts();if(!subset.some(p=>p.id===productId))productId=subset[0]?.id||null;
 $("product-grid").innerHTML=subset.map(p=>'<button class="product-card" type="button" data-id="'+esc(p.id)+'" aria-pressed="'+String(p.id===productId)+'"><span class="data-label">'+esc(D.hardware.formVocab[p.form])+'</span><h3>'+esc(p.name)+'</h3><p>'+esc(familyName(familyFor(p)))+'</p><span class="badge neutral" style="margin-top:10px">'+(verifiedProduct(p.id)?'官方规格':'产品资料')+'</span></button>').join("");
 $("product-grid").querySelectorAll("button").forEach(btn=>btn.addEventListener("click",()=>{productId=btn.dataset.id;renderProducts()}));
 let p=productSelection();
 if(!p){$("product-detail").innerHTML='<p class="muted">该筛选组合暂未收录产品。</p>';$("topology-evidence").hidden=true;return}
 displayBreadcrumb(p);
 const map=processorProof(p);
 const fields=[["所属产品族",familyName(familyFor(p))],["产品形态",D.hardware.formVocab[p.form]],["板载内存",p.quantitative.deviceMemoryGB],["内存带宽",p.quantitative.memoryBandwidthGBs],["峰值算力",p.quantitative.computeTOPS],["功耗",p.quantitative.powerW],["软件兼容",p.compatibilityStatus==="not_assessed"?"按版本匹配":"版本说明"]];
 $("product-detail").innerHTML='<div class="data-label">3 / PRODUCT SKU · 官方产品目录</div><h3>'+esc(p.name)+'</h3><p class="small muted">'+esc(p.remark)+'</p><div class="processor-proof"><span class="data-label">4 / PROCESSOR EVIDENCE</span><strong>'+esc(map?map.processorFamily:"按产品资料标识")+'</strong><p>'+esc(map?map.scope:"产品处理器信息请参考该整机或模块的官方规格。")+'</p><span class="proof-note">'+esc(map?"来源：官方产品形态分组；非 SKU 精确规格":"产品参数见该 SKU 对应的官方规格表")+'</span></div>'+fields.map(([k,v])=>'<div class="fact"><span>'+esc(k)+'</span><b class="'+(v==null?"no-data":"")+'">'+esc(labelStatus(v))+'</b></div>').join("")+'<div class="linkline"><button id="product-source" class="btn ghost" type="button">官方来源</button><button id="product-add" class="btn ghost" type="button">'+(compareIds.includes(p.id)?"从对比移除":"加入对比")+'</button></div>';
 $("product-source").addEventListener("click",()=>drawer({title:p.name,category:"产品形态、族谱与处理器来源",body:p.remark,items:[...p.limitations,...(map?[map.scope]:[])],urls:[p.sourceUrl,...(map?[map.sourceUrl]:[])]}));
 $("product-add").addEventListener("click",()=>{if(compareIds.includes(p.id))compareIds=compareIds.filter(z=>z!==p.id);else if(compareIds.length<3)compareIds.push(p.id);else {drawer({title:"最多比较三个产品",body:"删除一项已选产品后再加入新产品。未核实的精确参数不会参与数值排名。"});return}renderProducts()});
 $("processor-topics").innerHTML=D.hardware.processorResearchTopics.map(t=>'<p class="small">'+esc(t.name)+' <span class="badge warn">芯片研究标签 / 无SKU规格</span></p>').join("");
 $("compare-products").textContent="对比已选 "+compareIds.length+" 项";

 const spec=verifiedProduct(p.id);
 $("verified-spec-detail").innerHTML=verifiedFactsMarkup(spec);
 const btn=$("verified-source");
 if(btn&&spec)btn.addEventListener("click",()=>drawer({title:spec.productName,category:"供应商规格 / 强制保持单位与范围",body:"下述数值仅对具体产品和标注配置有效，不代表模型推理性能，不能把可选配置相加。",items:[...spec.specs.map(x=>x.label+"："+formatScopedValue(x)+"（"+x.scope+"）"),...spec.limitations],urls:[spec.sourceUrl]}));

 const topology=lineage.topologyCase;
 const show=p.id===topology.productId;
 $("topology-evidence").hidden=!show;
 if(show){
   $("topology-evidence").innerHTML='<div class="data-label">PRODUCT-SCOPED TOPOLOGY / OFFICIAL</div><h3>'+esc(topology.title)+'</h3><p>此处展示特定产品官方调度/拓扑说明中的层次，不作为所有昇腾芯片的统一架构图。</p><div class="topology-steps">'+topology.steps.map((t,i)=>'<div class="topology-step"><b>0'+(i+1)+'</b>'+esc(t)+'</div>').join("")+'</div><p class="no-data">'+esc(topology.warning)+'</p><button type="button" class="btn ghost" id="topology-source">查看对应官方拓扑文档</button>';
   $("topology-source").addEventListener("click",()=>drawer({title:topology.title,category:"产品级拓扑示例",body:topology.warning,items:topology.steps,urls:[topology.sourceUrl]}));
 }
}
$("compare-products").addEventListener("click",()=>{if(compareIds.length===0){drawer({title:"尚未选择产品",body:"先在产品详情中点击「加入对比」。产品对照不会生成未经来源证实的算力、带宽或功耗。"});return}const ps=compareIds.map(id=>D.hardware.products.find(p=>p.id===id)).filter(Boolean);const fields=[["产品名称",p=>p.name],["形态",p=>D.hardware.formVocab[p.form]],["已核实的产品级参数（不同范围不直接比较）",p=>verifiedProduct(p.id)?verifiedProduct(p.id).specs.slice(0,2).map(x=>x.label+": "+formatScopedValue(x)+"（"+x.scope+"）").join("；"):"官方产品资料"],["芯片或处理器",p=>p.processor||"未核验"],["板载内存",p=>labelStatus(p.quantitative.deviceMemoryGB)],["内存带宽",p=>labelStatus(p.quantitative.memoryBandwidthGBs)],["功耗",p=>labelStatus(p.quantitative.powerW)],["模型兼容",p=>"按版本匹配"]];$("compare-table").innerHTML='<table class="compare-table"><thead><tr><th>比较维度</th>'+ps.map(p=>'<th>'+esc(p.name)+'</th>').join("")+'</tr></thead><tbody>'+fields.map(([k,f])=>'<tr><th>'+esc(k)+'</th>'+ps.map(p=>'<td>'+esc(f(p))+'</td>').join("")+'</tr>').join("")+'</tbody></table>';$("comparison").hidden=false;$("comparison").scrollIntoView({behavior:matchMedia("(prefers-reduced-motion: reduce)").matches?"instant":"smooth",block:"nearest"})});
$("clear-compare").addEventListener("click",()=>{compareIds=[];$("comparison").hidden=true;renderProducts()});
const levels=[{id:"device",label:"① 产品层",title:"设备/加速卡/整机",desc:"Host CPU、NPU、系统内存与设备互联共同组成服务形态。这里不等同于某款单独芯片。"},
{id:"npu",label:"② NPU 层",title:"NPU 计算和通信资源",desc:"芯片内含计算、存储/数据搬运等资源；单卡与多卡还受硬件拓扑和软件运行时限制。"},
{id:"core",label:"③ AI Core 层",title:"AI Core 功能组件",desc:"进入 Cube/Vector/Scalar/Local Memory/Global Memory 等功能抽象，具体硬件实现因代际而异。"},
{id:"flow",label:"④ 数据通路",title:"GM / Local / Compute 典型数据流",desc:"切换矩阵与向量两类典型路径，逐步观察数据复用和写回的逻辑机制。"}];
const chip={
cube:{title:"Cube / 矩阵计算",hint:"Tile 分块、矩阵 GEMM、Expert GEMM 等候选计算主干。",measure:"Profiler：Cube 实际活跃率、矩阵形状、Tile 与数据搬运是否构成热点。"},
vector:{title:"Vector / 向量运算",hint:"用于部分归一化、激活、门控及逐元素处理。",measure:"Profiler：Vector 算子时间、Kernel 启动次数、数据回写/读取次数。"},
scalar:{title:"Scalar / 控制",hint:"控制、地址计算和调度；不应把所有 Host gap 归咎于这一单元。",measure:"检查主机调度和 NPU 队列空隙，不依赖示意布局推断控制开销。"},
gm:{title:"Global Memory",hint:"模型参数、激活与缓存可能依赖外部存储及带宽；具体产品采用何种内存需要单独核对。",measure:"内存峰值、读写吞吐、访存时间，分开看容量与带宽。"},
local:{title:"Local Memory：UB/L1/L0",hint:"片内分层数据暂存与复用。不同代际 L0/UB 组织和路径可能不同。",measure:"Tile 命中、重复读写 GM、布局与占用率；与准确硬件架构对应。"},
mte:{title:"MTE / DMA / 数据搬运",hint:"在 GM、片内存储与计算单元间移动张量。搬运不与计算重叠时可能产生等待。",measure:"搬运/计算重叠、待机、布局变换开销和实际调度 trace。"}};
let currentLevel="core",currentUnit="cube",pathType="gemm",pathIndex=0;
const paths=Object.fromEntries(D.architecturePaths.paths.map(p=>[p.id,p.steps.map(x=>x.name)]));

function renderCoreFlowSvg(){
 const chapter=D.architecturePaths.paths.find(x=>x.id===pathType);
 const steps=chapter.steps;const count=steps.length;
 const boxWidth=count===7?105:137,gap=count===7?22:38,start=22,midY=91;
 const positions=steps.map((_,i)=>start+i*(boxWidth+gap));
 const total=positions[positions.length-1]+boxWidth+22;
 const defs='<defs><marker id="flow-arr" markerWidth="7" markerHeight="7" refX="5" refY="3.5" orient="auto"><path d="M0,0 L7,3.5 L0,7 z" fill="#79bfcd"/></marker></defs>';
 const segments=steps.slice(1).map((st,i)=>{const a=positions[i]+boxWidth+3,b=positions[i+1]-6;return'<path class="flow-edge '+(pathIndex===i+1?'is-current':'')+'" d="M'+a+' '+midY+' L'+b+' '+midY+'" marker-end="url(#flow-arr)"/>'}).join("");
 const blocks=steps.map((st,i)=>{const x=positions[i],on=i===pathIndex;return'<g><rect class="flow-rect '+(on?'is-current':'')+'" x="'+x+'" y="50" rx="11" width="'+boxWidth+'" height="82"/><text x="'+(x+boxWidth/2)+'" y="83">'+esc(st.name)+'</text><text class="svg-sub" x="'+(x+boxWidth/2)+'" y="110">'+esc(pathType==='gemm'&&i===3?'矩阵计算':pathType==='vector'&&i===2?'向量计算':i===0?'输入/读取':i===count-1?'写回':'局部数据')+'</text></g>'}).join("");
 $("core-illustration").setAttribute("aria-label",chapter.label+"："+steps.map(x=>x.name).join(" → ")+"。正在讲解 "+steps[pathIndex].name);
 $("core-illustration").innerHTML='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 '+total+' 174" aria-hidden="true">'+defs+'<text x="20" y="19" style="text-anchor:start;fill:#94e7df;font-size:12px">'+esc(chapter.engine+' / 官方架构的典型教学通路')+'</text>'+segments+blocks+'<text x="'+(total/2)+'" y="155" class="svg-sub">节点和箭头仅表示先后关系，不对应实测时间或硬件物理距离</text></svg>';
 const st=steps[pathIndex];
 $("core-step-detail").textContent="第 "+(pathIndex+1)+"/"+count+" 步："+st.detail+" 可能瓶颈："+st.question+" 如何验证："+st.verify;
}

function renderAnatomy(){
 tabs($("anatomy-levels"),levels.map(x=>({id:x.id,label:x.label})),currentLevel,x=>{currentLevel=x;renderAnatomy()});
 const show=currentLevel==="core"||currentLevel==="flow";$("chip-shell").hidden=!show;$("anatomy-layer-display").hidden=show;$("memory-path").hidden=currentLevel!=="flow";$("path-next").disabled=currentLevel!=="flow";
 if(!show){const l=levels.find(x=>x.id===currentLevel);$("anatomy-layer-display").innerHTML='<div><span class="data-label">'+esc(l.label)+'</span><strong>'+esc(l.title)+'</strong><p class="small muted">'+esc(l.desc)+'</p></div>'}
 $("chip-units").innerHTML=Object.entries(chip).map(([id,o])=>'<button type="button" data-id="'+id+'" aria-pressed="'+String(id===currentUnit)+'"><b>'+esc(o.title.split("/")[0])+'</b><small>'+esc(o.hint.slice(0,26))+'…</small></button>').join("");
 $("chip-units").querySelectorAll("button").forEach(b=>b.addEventListener("click",()=>{currentUnit=b.dataset.id;currentLevel="core";renderAnatomy()}));
 const u=chip[currentUnit];$("chip-detail-title").textContent=u.title;$("chip-detail-text").textContent=u.hint;$("chip-detail-measure").textContent="怎么验证： "+u.measure;
 $("memory-path").innerHTML=paths[pathType].map((x,i)=>(i?'<i aria-hidden="true">→</i>':'')+'<span class="'+(i===pathIndex?"on":"")+'">'+esc(x)+'</span>').join("");
 $("path-gemm").className="btn "+(pathType==="gemm"?"":"ghost");$("path-vector").className="btn "+(pathType==="vector"?"":"ghost");
 renderCoreFlowSvg();
}
$("path-gemm").addEventListener("click",()=>{pathType="gemm";currentLevel="flow";pathIndex=0;renderAnatomy()});
$("path-vector").addEventListener("click",()=>{pathType="vector";currentLevel="flow";pathIndex=0;renderAnatomy()});
$("path-next").addEventListener("click",()=>{pathIndex=(pathIndex+1)%paths[pathType].length;renderAnatomy()});
const stack=[
["模型与服务","Model / Gateway","Tokenizer、请求参数、服务路由与应用负载。","确认输入/输出和网络/序列化/排队是否计入 TTFT。"],
["推理引擎","MindIE / vLLM-Ascend / SGLang-Ascend","负责请求调度、Batch、KV Cache、Prefill/Decode 与模型专用算子派发。","特性存在不等于选定模型、平台与版本支持。"],
["框架适配","torch_npu / MindSpore 等","适配上层框架的设备 Tensor、操作及异构执行路径；不同推理引擎不一定使用完全相同路径。","跟踪具体算子实际分派到何种实现。"],
["CANN 计算平台","Compile / Runtime / Operators","编译、运行时、算子接口及图执行支持，是很多 NPU 性能功能的基础。","核查 CANN 版本、Kernel 支持与图缓存限制。"],
["Driver / Firmware","Device Control","设备驱动、固件、资源与运行环境。","不兼容或报错时，优先确认官方支持矩阵。"],
["昇腾 NPU","Compute / Memory / Fabric","计算、片内/片外存储、搬运、多卡通信。","以真实 Profiler 证明 Cube、内存或 HCCL 等哪部分是瓶颈。"]
];let stackIndex=1;function renderStack(){
 $("stack-layers").innerHTML=stack.map((s,i)=>'<button class="stack-layer" type="button" data-i="'+i+'" aria-pressed="'+String(i===stackIndex)+'"><span class="index">0'+(i+1)+'</span><b>'+esc(s[0])+'</b><small>'+esc(s[1])+'</small></button>').join("");
 $("stack-layers").querySelectorAll("button").forEach(b=>b.addEventListener("click",()=>{stackIndex=Number(b.dataset.i);renderStack()}));
 let s=stack[stackIndex];$("stack-detail-title").textContent=s[0];$("stack-detail-text").textContent=s[2];$("stack-detail-gate").textContent="工程核验： "+s[3];
}

const compatibility=D.softwareCompat;
let compatFamilyId="A2";
function renderCompatibility(){
 tabs($("compat-family-tabs"),compatibility.hardwareFamilies.map(f=>({id:f.id,label:f.label})),compatFamilyId,x=>{compatFamilyId=x;renderCompatibility()});
 const family=compatibility.hardwareFamilies.find(f=>f.id===compatFamilyId);
 $("compat-view").innerHTML='<div class="data-label">'+esc(compatibility.release+' / 已验证的软件组合')+'</div><p class="small muted">已列举的设备：'+esc(family.examples.join("、"))+'。'+esc(family.note||"")+'</p><div class="compat-slice">'+compatibility.components.map(c=>{const supported=c.appliesTo.includes(compatFamilyId);return'<div class="compat-item"><b>'+esc(c.layer)+'</b><strong>'+esc(supported?c.version:"不适用此组件")+'</strong><small>'+esc(c.role)+'</small></div>'}).join("")+'</div><p class="tiny">版本属于同一官方验证组合，不能任意混搭。Triton Ascend 并非在 300I DUO / 200I Pro 上按该表使用。</p>';
 $("compat-models").innerHTML=compatibility.modelExamples.rows.map(m=>'<div class="compat-model"><span class="badge '+(compatFamilyId==="300I DUO"||compatFamilyId==="950DT"?"warn":"neutral")+'">官方支持表 · '+esc(m.documentedStatus)+'</span><strong>'+esc(m.model)+'</strong><small>文档列示硬件：'+esc(m.documentedHardware)+'</small><p>'+esc((compatFamilyId==="A2"||compatFamilyId==="A3")?m.interpretation:"此示例的文档硬件范围不包含所选系列；不可推定支持。")+'</p></div>').join("");
}
$("compat-source").addEventListener("click",()=>drawer({title:"vLLM-Ascend 0.30.0 软件与模型兼容快照",category:"OFFICIAL RELEASE-SCOPED MATRIX",body:"整套依赖版本按固定安装文档采集，模型支持按官方模型矩阵引用。这里只说明文档记载范围，不保证当前用户的具体型号部署已经成功。",items:compatibility.caveats,urls:[compatibility.sourceUrl,compatibility.modelExamples.sourceUrl]}));

const lengths=[32,512,1024,4096],outputs=[16,64,128,512],concurrencies=[1,4,8,32];
const lifecycle=[["排队 / 调度","Host Batch","业务负载、排队与 tokenization 可能影响首 Token 延迟。"],
["Prefill","Input tokens","长输入常增加预填充工作，可能涉及注意力/GDN、通信和内存搬运。"],
["KV / State","Cache memory","Full Attention KV Cache 与 GDN recurrent state 不能直接视作同一缓存机制。"],
["Decode","Output tokens","循环生成，重点观察 TPOT、Host gap、图形状、Cache 和 MTP 接受率。"],
["流式输出","Service Metrics","端到端还涉及网络、调度、流式传输等成本。"]];
let stageIndex=1;function renderLife(){
 const isl=lengths[+$("isl").value],osl=outputs[+$("osl").value],cc=concurrencies[+$("cc").value];
 $("isl-value").textContent=isl+" tokens";$("osl-value").textContent=osl+" tokens";$("cc-value").textContent=cc+" 路";
 $("timeline-stages").innerHTML=lifecycle.map((s,i)=>'<button type="button" class="stage" aria-pressed="'+String(i===stageIndex)+'" data-i="'+i+'"><span class="data-label">0'+(i+1)+'</span><b>'+s[0]+'</b><small>'+s[1]+'</small></button>').join("");
 $("timeline-stages").querySelectorAll("button").forEach(b=>b.addEventListener("click",()=>{stageIndex=Number(b.dataset.i);renderLife()}));
 const p=Math.round(20+Math.log2(isl)*3.2),d=100-p;const pre=Math.max(18,p);
 $("lifecycle-tracks").innerHTML='<span>HOST</span><div class="track"><span class="segment host" style="width:28%">调度 / Batch</span><span class="segment host" style="width:23%">发起</span><span class="segment host" style="width:49%">持续调度</span></div><span>NPU</span><div class="track"><span class="segment prefill" style="width:'+pre+'%">Prefill</span><span class="segment decode" style="width:'+(100-pre)+'%">Decode（示意）</span></div><span>存储</span><div class="track"><span class="segment cache" style="width:35%">Cache / State</span><span class="segment cache" style="width:65%">随 Token 维护与复用</span></div>';
 const s=lifecycle[stageIndex];$("lifecycle-detail").textContent=s[0]+"： "+s[2]+" 当前场景输入 "+isl+"、输出 "+osl+"、并发 "+cc+"；轨道尺寸只表达概念，不是计算出的真实时间。";
}
for(const id of ["isl","osl","cc"])$(id).addEventListener("input",renderLife);
const metrics=[["TTFT","首 token 到达时间","包括排队/网络与否须按测试协议明确"],["TPOT","后续 token 平均时间间隔","需说明统计分母与首 token 是否排除"],["P95","延迟的第 95 百分位","与请求窗口、并发及排队关系密切"],["TPS","输出 tokens/s 或 requests/s","两种吞吐单位不可互换"]];
function renderMetrics(){$("metric-definitions").innerHTML=metrics.map(m=>'<div class="metric-card"><b>'+m[0]+'</b><small>'+m[1]+'</small><p>'+m[2]+'</p></div>').join("")}
const factors=[
{key:"isl",name:"输入长度",chain:["ISL 变长","Prefill 工作量","Attention / GDN 与搬运","TTFT / Prefill"],desc:"输入序列长度通常直接改变 Prefill 计算和缓存建立。结构不同，成本变化也不同。",counter:"若排队/Tokenization 是首要成本，优化 Attention 不一定改善 TTFT。测分阶段 Prefill、队列、算子时间。"},
{key:"osl",name:"输出长度",chain:["OSL 变长","反复 Decode","KV / State / Host","TPOT 与总延迟"],desc:"输出越长，增量解码步骤通常越多，单步开销的累积就更值得关注。",counter:"吞吐与总延迟受请求分布和接受率影响；要分开量测 TPOT、token/s 和 P95。"},
{key:"concurrency",name:"并发与 Batch",chain:["C / Batch","调度与形状","资源争用/等待","TPS / P95"],desc:"批次和并发改变算子形状、显存占用和排队策略，因此 c1 的优化不一定能外推到 c32。",counter:"吞吐上升可能伴随 P95 变差；需记录到达率、Batch 构成和排队。"},
{key:"architecture",name:"Dense / MoE",chain:["模型结构","MLP / Router TopK","Grouped GEMM / Expert","算子利用率"],desc:"Dense 主要追踪矩阵与注意力结构；MoE 额外引入专家路由、负载偏斜与通信。",counter:"Dense 不适用 MoE Router 优化。要看真实路由直方图而非均匀假设。"},
{key:"attention",name:"Full / GDN",chain:["注意力结构","KV vs Recurrent","不同数据/状态路径","Prefill / Decode"],desc:"GDN 与 Full Attention 使用不同缓存/状态结构；Prefill 和 Decode 的专用 Kernel 不能视为同一个。",counter:"上游特定 MTP CUDA 分支的 8:1 Guard 不等于所有 GDN 不支持融合。"},
{key:"parallel",name:"TP / EP / 互联",chain:["并行策略","AllReduce / AllToAll","通信与计算重叠","多卡效率"],desc:"多卡拆分产生通信成本，拓扑、并行策略与实际网络可能决定等待时间。",counter:"融合可能造成死锁或精度一致性回归；要测每条 collective 与稳定性。"},
{key:"quant",name:"量化精度",chain:["dtype / bits","模型内存需求","带宽/Kernel 支持","吞吐与正确性"],desc:"低精度可能降低内存和带宽开销，但能否生效依赖具体 Kernel、硬件及模型布局。",counter:"量化带来反量化成本及数值差异；需要同负载精度和 E2E 验证。"},
{key:"graph",name:"Graph / Static",chain:["捕获/静态形状","减少重复 Launch","编译 / 缓存 / 回退","Host gap / TPOT"],desc:"静态执行可能减少 Launch 和部分调度开销，适用条件依赖版本、Shape、图命中。",counter:"动态形状、预编译成本和额外内存可能抵消收益；必须检查真实命中。"}
];
let factorId=factors[0].key;function renderFactors(){
 $("factor-tabs").innerHTML=factors.map(f=>blockButton(f.name,f.key,factorId)).join("");
 $("factor-tabs").querySelectorAll("button").forEach(b=>b.addEventListener("click",()=>{factorId=b.dataset.id;renderFactors()}));
 const f=factors.find(x=>x.key===factorId);
 $("factor-chain").innerHTML=f.chain.map((t,i)=>'<div class="causal-node">'+esc(t)+'<small>'+["输入条件","计算或调度","潜在热点","观测指标"][i]+'</small></div>').join("");
 $("factor-description").textContent=f.desc;$("factor-validate").textContent=f.counter;
}
let opId=D.operators.stories[0].id,opFrame=0;function selectedOp(){return D.operators.stories.find(x=>x.id===opId)||D.operators.stories[0]}
function renderOperator(){
 tabs($("operator-tabs"),D.operators.stories.map(x=>({id:x.id,label:x.title})),opId,id=>{opId=id;opFrame=0;renderOperator()});
 const story=selectedOp();$("operator-steps").innerHTML=story.frames.map((f,i)=>'<button type="button" class="stepbtn" data-i="'+i+'" aria-pressed="'+String(i===opFrame)+'">0'+(i+1)+' · '+esc(["输入/形状","执行步骤","访存与通信","潜在热点","优化逻辑","验证/回退"][i])+'</button>').join("");
 $("operator-steps").querySelectorAll("button").forEach(b=>b.addEventListener("click",()=>{opFrame=+b.dataset.i;renderOperator()}));
 $("gemm-lab-link").hidden=story.id!=="gemm";
 const f=story.frames[opFrame];$("op-number").textContent=String(opFrame+1).padStart(2,"0")+" / 06";$("op-stage").textContent=story.title+" · "+f.slug.toUpperCase();$("op-frame-title").textContent=f.label;$("op-frame-description").textContent=opFrame===5?"通过正确性检查、Profiler 和同条件性能对照，观察算子优化的实际效果。":"逐帧展示算子输入、计算、存储与通信机制。点击下方切换演示步骤。";
 const flows={
gemm:["GM","L1","Cube","Output"],rmsnorm:["Tensor","Reduce","Vector","Writeback"],"attention-gdn":["QKV / State","Prefill / Decode","Cache","Output"],"kv-cache":["Page mapping","KV store","Lookup","Reuse"],moe:["Router","TopK","Experts","Combine"],collectives:["TP ranks","AllReduce","Overlap","Sync"],"graph-mtp":["Host","Capture / Draft","Verify","Next token"]
 };
 $("op-visual-flow").innerHTML=(flows[story.id]||["Input","Compute","Memory","Output"]).map((x,i)=>(i?'<i>→</i>':'')+'<span class="'+(i===Math.min(opFrame,3)?"on":"")+'">'+esc(x)+'</span>').join("");
 $("op-limitation").textContent="关键条件："+story.limitations.join("；");$("op-prev").disabled=opFrame===0;$("op-next").disabled=opFrame===5;
}
$("op-prev").addEventListener("click",()=>{if(opFrame>0){opFrame--;renderOperator()}});$("op-next").addEventListener("click",()=>{if(opFrame<5){opFrame++;renderOperator()}});
$("op-sources").addEventListener("click",()=>{const x=selectedOp();drawer({title:x.title,category:"算子分镜 · 公开来源",body:"六帧交互展示算子执行机制；来源文档提供模型、形状、版本与硬件配置的具体参考。",items:x.limitations,urls:x.sourceUrls})});
const symptoms=[
{id:"oom",name:"模型加载失败 / OOM",roots:["权重和 Cache 容量不足","模型精度/分片配置与硬件不适配"],evidence:["容量/占用峰值、模型版本和数据类型","真实卡型/TP/EP/Cache 分配日志"],candidate:["先优化模型分片、量化或缓存规划","验证硬件与 Kernel 精度支持后做 A/B"],risk:"量化精度可能影响质量；不可只看模型能否加载。"},
{id:"ttft",name:"TTFT / 首 Token 很慢",roots:["排队/Tokenizer/Host 等待","长上下文 Prefill 和跨卡通信"],evidence:["拆分请求进入、入队、Prefill、首 Token 各阶段","对 ISL / 并发 / TP 做矩阵化对照"],candidate:["若 Prefill 是瓶颈，才研究 SP、Attention、GDN 和布局","若排队主导，改调度和并发策略"],risk:"仅优化 Prefill Kernel 不保证端到端 TTFT 改善。"},
{id:"tpot",name:"Decode / TPOT 很高",roots:["Host/Graph 间隙、Kernel 碎片","KV/GDN 状态或小 GEMM 访存成本"],evidence:["分阶段 Decode Trace、graph hit、kernel time","自然负载 MTP 接受率及质量比较"],candidate:["在兼容条件下评估图模式和状态访存","尝试 MTP / Kernel 复用，逐项消融"],risk:"MTP 开销或图 shape miss 可能使结果变差。"},
{id:"p95",name:"尾延迟 P95 波动",roots:["批次波动和排队","专家路由偏斜、图回退或资源争用"],evidence:["真实请求到达/并发/Batch 时间序列","Expert token 分布/状态切换/错误日志"],candidate:["先稳定调度、Batch 与负载分组","仅在具体瓶颈确认后调整 Router/EP"],risk:"P50 改善不意味着 P95 一定改善。"},
{id:"throughput",name:"高并发吞吐不足",roots:["内存/带宽瓶颈及 Cache 容量","Batch 与专家形状导致计算利用率低"],evidence:["tokens/s 与 requests/s 分开记录","每 batch Kernel 形状与 GM/计算时间"],candidate:["基于瓶颈调整 Batch、Cache 与分片策略","单项尝试 kernel 或通信优化"],risk:"吞吐和单请求延迟往往有权衡。"},
{id:"network",name:"多卡通信效率低",roots:["TP/EP 拆分不匹配互联拓扑","AllReduce/AllToAll 等待或同步"],evidence:["HCCL collective trace 与网络拓扑","通信/计算重叠和数值确定性"],candidate:["调整拓扑和 TP/EP/Sequence Parallel","确认兼容后尝试官方通信优化"],risk:"上游存在融合死锁和确定性回退案例，不能直接照搬。"},
{id:"kernel",name:"单个算子热点很高",roots:["Tile/布局与输入 shape 不匹配","融合前后引入反复 GM 写回或同步"],evidence:["实际 Dispatch 的 Kernel 与版本","逐个形状的微基准及端到端 A/B"],candidate:["先复用官方已有 Kernel 或图能力","再论证自定义 AscendC 实现价值"],risk:"算子微基准增益不等于服务 E2E 增益。"}
];
let symptomId="ttft";function renderDiagnosis(){
 $("symptoms").innerHTML=symptoms.map(x=>'<button aria-pressed="'+(x.id===symptomId)+'" data-id="'+x.id+'" type="button">'+esc(x.name)+'</button>').join("");
 $("symptoms").querySelectorAll("button").forEach(b=>b.addEventListener("click",()=>{symptomId=b.dataset.id;renderDiagnosis()}));
 let s=symptoms.find(x=>x.id===symptomId);
 const blocks=[["先分辨可能根因",s.roots],["测量什么才能区分",s.evidence],["条件性候选方案",s.candidate],["同条件 A/B + 回退",["保留数值/质量基线，检查 P50/P95 和稳定性","负收益/不兼容时退回上一步并保留证据"]]];
 $("diagnosis-path").innerHTML=blocks.map((b,i)=>'<div class="decision-step"><b>0'+(i+1)+' / '+esc(b[0])+'</b><p>'+b[1].map(x=>"• "+esc(x)).join("<br>")+'</p></div>').join("");
 $("diagnosis-warning").textContent="优化要点： "+s.risk;
}

let graphNodeId="case:QINF-001";
const kindLabels={case:"研究案例",model:"模型结构",upstream_pr:"上游 PR",failure_or_caveat:"失败或限制",mechanism:"优化机制",operator:"算子",architecture_feature:"模型结构特征"};
function graphNode(id){return D.atlas.nodes.find(n=>n.id===id)}
function renderGraph(){
 const nodes=D.atlas.nodes,edges=D.atlas.edges;
 const q=$("graph-search").value.toLowerCase().trim();
 const matches=nodes.filter(n=>(n.label+" "+n.id+" "+n.kind).toLowerCase().includes(q));
 if(!nodes.some(n=>n.id===graphNodeId))graphNodeId=nodes[0].id;
 const base=graphNode(graphNodeId);
 const direct=edges.filter(e=>e.source===graphNodeId||e.target===graphNodeId);
 const neighbors=[...new Set(direct.map(e=>e.source===graphNodeId?e.target:e.source))].sort();
 const maxNeighbors=window.innerWidth<700?5:8;
 const shown=neighbors.slice(0,maxNeighbors);
 const positions=shown.map((id,i)=>{const angle=-Math.PI/2+2*Math.PI*i/Math.max(1,shown.length);return{id,x:50+36*Math.cos(angle),y:50+33*Math.sin(angle)}});
 let lines='<svg class="graph-lines" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">'+positions.map(p=>'<line x1="50" y1="50" x2="'+p.x.toFixed(2)+'" y2="'+p.y.toFixed(2)+'" stroke="#4caab0" stroke-width=".5" opacity=".75" />').join("")+"</svg>";
 let html=lines+'<button type="button" class="graph-node primary" data-id="'+esc(base.id)+'" style="left:50%;top:50%" title="'+esc(base.label)+'">'+esc(base.label)+'</button>';
 html+=positions.map(p=>{const n=graphNode(p.id);return'<button type="button" class="graph-node" data-id="'+esc(n.id)+'" style="left:'+p.x.toFixed(2)+'%;top:'+p.y.toFixed(2)+'%" title="'+esc(n.label)+'">'+esc(n.label)+'</button>'}).join("");
 $("graph-stage").innerHTML=html;
 $("graph-stage").querySelectorAll("button").forEach(b=>b.addEventListener("click",()=>{graphNodeId=b.dataset.id;renderGraph()}));
 $("graph-counts").textContent=D.atlas.counts.nodes+" 个节点 / "+D.atlas.counts.edges+" 条来源关系";
 $("graph-matches").innerHTML=matches.slice(0,16).map(n=>blockButton(n.label,n.id,graphNodeId)).join("")+(matches.length>16?'<span class="tiny">另有 '+(matches.length-16)+' 条匹配，请缩小搜索条件</span>':"");
 $("graph-matches").querySelectorAll("button").forEach(b=>b.addEventListener("click",()=>{graphNodeId=b.dataset.id;renderGraph()}));
 $("graph-detail").innerHTML='<span class="data-label">'+esc(kindLabels[base.kind]||base.kind)+'</span><strong>'+esc(base.label)+'</strong><p class="small muted">一跳相关：'+direct.length+' 条关系；画布显示 '+shown.length+' 个邻居。标签相同不代表技术实现可直接移植。</p>'+direct.slice(0,9).map((e,i)=>{let other=graphNode(e.source===base.id?e.target:e.source);return'<div class="rel"><small>'+esc(e.relation)+' · '+esc(e.evidence_level)+'</small><b>'+esc(other?.label||"来源节点")+'</b><button class="btn ghost" data-edge="'+i+'" type="button">查看关系来源</button></div>'}).join("");
 $("graph-detail").querySelectorAll("button[data-edge]").forEach(b=>b.addEventListener("click",()=>{
 const e=direct[+b.dataset.edge],other=graphNode(e.source===graphNodeId?e.target:e.source);
 drawer({title:base.label+" → "+(other?.label||"相关节点"),category:"GRAPH RELATION / PROVENANCE",body:"关系类型："+e.relation+"。引用等级："+e.evidence_level+"；可沿来源链接追踪关联的技术记录。",items:["来源对应此研究图谱记录","项目无本地 NPU 性能实测"],urls:e.provenance_urls||[]});
 }));
}
$("graph-search").addEventListener("input",renderGraph);
window.addEventListener("resize",()=>{if(Math.abs(window.innerWidth-(window.__lastGraphWidth||0))>160){window.__lastGraphWidth=window.innerWidth;renderGraph()}});

let evidenceFilter="all";
function casePlatform(c){const h=(c.hardware||"").toLowerCase();return /ascend|910c|910b|昇腾/.test(h)?"ascend":/tpu|ironwood/.test(h)?"tpu":/nvidia|b200|h100|h200|cuda|mi300x|metal|apple|m4/.test(h)?"other":"other"}
function renderEvidence(){
 const corpus=D.cases.cases;const query=$("case-query").value.toLowerCase().trim();
 const filtered=corpus.filter(c=>(evidenceFilter==="all"||casePlatform(c)===evidenceFilter)&&JSON.stringify([c.name,c.model,c.hardware,c.mechanisms,c.operators,c.team,c.id]).toLowerCase().includes(query));
 $("case-grid").innerHTML=filtered.length?filtered.map(c=>'<article class="case-card"><div class="data-label">'+esc(c.id)+' / '+esc(c.team)+'</div><strong>'+esc(c.name)+'</strong><p>'+esc(c.model||"")+' · '+esc(c.stage||"")+'</p><div class="chips">'+(c.mechanisms||[]).slice(0,4).map(x=>'<span class="badge neutral">'+esc(x)+'</span>').join("")+'</div><p class="tiny">'+esc(c.evidence_status)+'</p><button class="btn ghost" type="button" data-id="'+esc(c.id)+'">详情与来源</button></article>').join(""):'<div class="empty">没有匹配的案例。当前研究库重点是 Qwen，不代表其他模型无相关技术。</div>';
 $("case-grid").querySelectorAll("button[data-id]").forEach(b=>b.addEventListener("click",()=>{const c=corpus.find(c=>c.id===b.dataset.id);drawer({title:c.name,category:"开源案例 · 技术来源",body:(c.outcome||"该条记录不包含实测性能数字")+"。硬件："+c.hardware+"。推理引擎："+(c.engine||"未指定"),items:[c.workload||"",c.notes||"", "验证状态："+c.evidence_status,"技术分析基于原始案例的设备与执行配置"],urls:[...(c.source_urls||[]),...(c.code_url?[c.code_url]:[])]})}));
}
function researchSummary(){
 const atlas=D.atlas;const cases=D.cases,pr=D.prs,fail=D.failures;
 const stats=[["案例",cases.cases.length],["上游 PR",pr.entries.length],["失败与限制",fail.failures.length],["图谱节点",atlas.counts.nodes]];
 $("research-stats").innerHTML=stats.map(([k,v])=>'<div class="metric-card"><b style="font-size:25px;color:var(--mint)">'+v+'</b><small>'+k+' · 历史研究快照</small></div>').join("");
 const variants=[{id:"all",label:"全部案例"},{id:"ascend",label:"昇腾案例"},{id:"other",label:"其他 GPU/Metal"},{id:"tpu",label:"TPU 机制类比"}];
 tabs($("evidence-tabs"),variants,evidenceFilter,x=>{evidenceFilter=x;researchSummary();renderEvidence()});
 $("count-products").textContent=D.hardware.products.length;$("count-operators").textContent=D.operators.stories.length*D.operators.frameContract.length;$("count-evidence").textContent=atlas.counts.nodes;
}
$("case-query").addEventListener("input",renderEvidence);

/* Detailed matrix tiling lab. These arithmetic values are conceptual memory-load
   counts for simple loop orders, NOT actual GM/HBM traffic, timings, or speedups. */
const tilingContent=D.tilingLab;
const TMath=globalThis.AscendTilingMath;
let tilingStep=0,tilingMethod="none";
const tileDimensionOptions=[32,64,80,96,112,128,144,256,512];
const tileSizeOptions=[16,32,64,128];
const tileInputs={M:"tile-M",N:"tile-N",K:"tile-K",tm:"tile-tm",tn:"tile-tn",tk:"tile-tk"};
function fillTileInputs(){
 for(const [key,id] of Object.entries(tileInputs)){
  const options=key.length===1?tileDimensionOptions:tileSizeOptions;
  $(id).innerHTML=options.map(v=>'<option value="'+v+'">'+v+'</option>').join("");
  $(id).addEventListener("change",()=>{tilingStep=0;renderTiling()});
 }
}
function setTilePreset(p){
 for(const key of Object.keys(tileInputs))$(tileInputs[key]).value=String(p[key]);
 tilingStep=0;renderTiling();
}
function matrixTiles(name,rows,cols,activeRow,activeCol){
 const maxRows=Math.min(rows,9),maxCols=Math.min(cols,9);
 let cells="";
 for(let r=0;r<maxRows;r++)for(let c=0;c<maxCols;c++){
  const active=r===activeRow&&c===activeCol;
  cells+='<span class="tile-cell'+(active?' selected':'')+'" aria-label="'+esc(name)+' Tile '+(r+1)+'-'+(c+1)+(active?' 选中':'')+'"></span>';
 }
 return '<div class="matrix-mini"><div class="matrix-top"><b>'+esc(name)+'</b><small>'+rows+' × '+cols+' 分块网格</small></div><div class="tile-grid" style="grid-template-columns:repeat('+maxCols+',minmax(0,1fr))">'+cells+'</div>'+(rows>9||cols>9?'<p class="tiny">仅展示前 9×9 块，其余未绘制</p>':'')+'</div>';
}
function bytesDisplay(x){return x.toLocaleString("zh-CN")+" B"}
function renderTiling(){
 const params=Object.fromEntries(Object.entries(tileInputs).map(([k,id])=>[k,Number($(id).value)]));
 const d=TMath.derive(params);
 if(tilingStep>=d.tileIterations)tilingStep=0;
 const t=TMath.tileAt(d,tilingStep);
 tabs($("tiling-presets"),tilingContent.presets.map(p=>({id:p.id,label:p.label})),"",id=>setTilePreset(tilingContent.presets.find(p=>p.id===id)));
 const activePreset=tilingContent.presets.find(p=>Object.keys(tileInputs).every(key=>p[key]===params[key]));
 $("tiling-presets").querySelectorAll("button").forEach(b=>b.setAttribute("aria-pressed",String(b.dataset.id===activePreset?.id)));
 tabs($("tiling-methods"),tilingContent.methods.map(m=>({id:m.id,label:m.label})),tilingMethod,id=>{tilingMethod=id;renderTiling()});
 const lenFmt=x=>x.toLocaleString("zh-CN");
 $("tiling-summary").innerHTML=[
  ["矩阵乘法",d.M+"×"+d.K+" · "+d.K+"×"+d.N],
  ["输出 Tile",d.mTiles+"×"+d.nTiles+" = "+d.outputTileCount],
  ["K 分块",String(d.kTiles)],
  ["逻辑计算任务",lenFmt(d.tileIterations)],
  ["估算片内工作集",bytesDisplay(d.localFootprintBytes)],
  ["数学 FLOPs",lenFmt(d.flopsConvention)]
 ].map(([label,v])=>'<div class="tile-stat"><small>'+label+'</small><strong>'+esc(v)+'</strong></div>').join("");
 $("tiling-matrices").innerHTML=matrixTiles("A[M,K]",d.mTiles,d.kTiles,t.mIndex,t.kIndex)+
  '<div class="matrix-op" aria-hidden="true">×</div>'+matrixTiles("B[K,N]",d.kTiles,d.nTiles,t.kIndex,t.nIndex)+
  '<div class="matrix-op" aria-hidden="true">→</div>'+matrixTiles("C[M,N]",d.mTiles,d.nTiles,t.mIndex,t.nIndex);
 const start=(m,n)=>"["+m+", "+n+")";
 $("tiling-step").innerHTML='<strong>计算步骤 '+(tilingStep+1)+' / '+d.tileIterations+'</strong><p>取 A 行段 '+start(t.mStart,t.mEnd)+'、K 段 '+start(t.kStart,t.kEnd)+'；取 B 的 K 段 '+start(t.kStart,t.kEnd)+'、列段 '+start(t.nStart,t.nEnd)+'，累加至 C('+t.mIndex+', '+t.nIndex+')。</p><p class="tiny">本次有效分块：'+t.mExtent+'×'+t.kExtent+' 和 '+t.kExtent+'×'+t.nExtent+'。'+(t.mExtent<d.tm||t.nExtent<d.tn||t.kExtent<d.tk?'当前为边界块，存在不足完整 Tile 的部分。':'当前为完整 Tile。')+'</p>';
 $("tiling-prev").disabled=tilingStep===0;
 $("tiling-next").disabled=tilingStep===d.tileIterations-1;
 const baseline=d.options.none.readBytes,selected=d.options[tilingMethod].readBytes;
 const selectedMethod=tilingContent.methods.find(x=>x.id===tilingMethod);
 const ratio=(selected/baseline*100).toFixed(1);
 $("tiling-traffic").innerHTML='<div class="tile-bars"><div><span>无复用（对照）</span><div class="tile-bar"><i style="width:100%"></i></div><b>'+bytesDisplay(baseline)+'</b></div><div><span>'+esc(selectedMethod.label)+'</span><div class="tile-bar"><i style="width:'+ratio+'%"></i></div><b>'+bytesDisplay(selected)+'</b></div></div><p class="small muted">在这一套<b>理想循环读取模型</b>里，读取元素量占无复用方案的 '+ratio+'%。这不是实测 GM 读取量，也不是性能提升百分比。</p>';
 $("tiling-caveat").textContent=selectedMethod.assumption+"。片内工作集按 A/B 输入块与 FP32 累加块计算；真实 Tiling 需结合 L1/L0/UB 容量与设备参数。";
}
fillTileInputs();setTilePreset(tilingContent.presets[1]);
$("tiling-prev").addEventListener("click",()=>{if(tilingStep>0){tilingStep--;renderTiling()}});
$("tiling-next").addEventListener("click",()=>{const d=TMath.derive(Object.fromEntries(Object.entries(tileInputs).map(([k,id])=>[k,+$(id).value])));if(tilingStep<d.tileIterations-1){tilingStep++;renderTiling()}});
$("tiling-reset").addEventListener("click",()=>{tilingStep=0;renderTiling()});
$("tiling-sources").addEventListener("click",()=>drawer({title:"GEMM Tiling：数学模型与昇腾官方实现的区别",category:"TEACHING ONLY · NOT NPU TRACE",body:tilingContent.evidenceScope,items:[...TMath.derive({M:64,N:64,K:64,tm:32,tn:32,tk:32}).disclaimers,...tilingContent.neverAssert.map(x=>"不提供："+x)],urls:[tilingContent.source.url,tilingContent.source.sourceSecond]}));


/* Externally published NPU result, strictly distinct from the educational
   GEMM loop model and this project's zero local hardware measurements. */
const published=D.publicMatmulEvidence;
function renderPublishedMatmul(){
 const c=published.case,kindNames={
  operator_execution_duration_us:"完整算子执行耗时",
  MTE2_pipeline_duration_us:"仅 MTE2 搬运流水耗时"
 };
 const stages=[c.first_experiment,c.second_experiment,c.third_experiment];
 $("evidence-workload").textContent="原文环境："+c.hardware+"；M="+c.matrix.M+" / N="+c.matrix.N+" / K="+c.matrix.K+
  "；"+c.matrix.inputs+" 输入，"+c.matrix.output+" 输出。硬件平台：Atlas A2 系列。";
 $("reported-evidence-grid").innerHTML=stages.map((x,i)=>{
   const scale=(x.after/x.before*100).toFixed(1);
   const factor=(x.before/x.after).toFixed(2);
   const name=["① 增加参与计算的核数","② 调整基础 Tile 与对齐","③ 启用大包搬运"][i];
   const context=[c.first_experiment.launcher_cube_cores_before+" → "+c.first_experiment.launcher_cube_cores_after+" 个计算核",
    "["+Object.values(c.second_experiment.tile_before).join(", ")+"] → ["+Object.values(c.second_experiment.tile_after).join(", ")+"]",
    "Matmul 模板配置 CFG_MDL"][i];
   return'<div class="reported-row"><div class="reported-row-head"><b>'+esc(name)+'</b><span class="badge neutral">'+esc(kindNames[x.measured_metric])+'</span></div><p class="tiny">'+esc(context)+'</p>'+
    '<div class="reported-bar-row"><span>修改前</span><div class="reported-track"><i style="width:100%"></i></div><strong>'+x.before.toLocaleString("zh-CN")+' μs</strong></div>'+
    '<div class="reported-bar-row"><span>修改后</span><div class="reported-track"><i style="width:'+scale+'%"></i></div><strong>'+x.after.toLocaleString("zh-CN")+' μs</strong></div>'+
    '<p class="tiny">公开案例中的同一指标耗时对照：约 '+factor+'×。</p></div>';
 }).join("");
 $("reported-evidence-caveat").textContent="数据来自 Ascend C Matmul 公开案例：① 为完整算子执行耗时；②③ 为 MTE2 搬运流水耗时，分组呈现不同优化环节。";
}
renderPublishedMatmul();
$("reported-evidence-source").addEventListener("click",()=>{
 const c=published.case;
 drawer({title:"Atlas A2 Matmul 优化：公开实测和可检验的代码证据",
  category:"ASCEND C · PUBLISHED PROFILER CASE",
  body:"Atlas A2 系列指定 Matmul 工作负载，分核、Tiling 和大包搬运三个实验分别记录算子执行时长与 MTE2 流水时长。",
  items:[
   "任务：FP16 输入、FP32 输出，M=4096/N=5120/K=4096",
   "算子总耗时：12,045 → 2,532 μs，示例 4→20 Cube 核",
   "MTE2 流水：2,452 → 808 μs，基础块 [64,64,256] → [128,256,64]",
   "MTE2 流水：808 → 591 μs，模板启用 CFG_MDL",
   "实验记录包含计算核数、基础 Tile 与 MTE2 流水时间。",
   "相关 CANN API：GetTiling / SetFixSplit / GetCoreMemSize。"
  ],
  urls:published.sources.map(x=>x.url)
 });
});


/* V2.5: sourced empirical evidence. Never claim external results as
   project-generated, or compare unlike metric scopes as one speedup. */
const expData=D.experimentEvidence;
const crossData=D.crossOperatorEvidence;
let experimentCategory="all";
let experimentId=expData.case_records[0]?.id||null;
const experimentTypes={all:"全部有来源案例",operator:"算子 Profile",service:"服务与故障",attention:"Attention",moe:"MoE",gdn:"GDN",communication:"多卡通信"};
function expFmt(v){if(v==null)return "未提供";return Number(v).toLocaleString("zh-CN",{maximumFractionDigits:3})}
function expKind(r){return r.kind||(r.id.startsWith("ASC-OP")?"operator":"service")}
function expTier(r){return ({"vendor_developer_preview":"厂商开发预览·作者报告","github_issue_report":"GitHub Issue·提交者报告","github_pr_author_report":"GitHub PR·尚未合并","github_issue_probe":"GitHub Issue·单项探针","official_feature_guide_measured":"上游官方特性指南·作者实测","github_issue_regression":"GitHub Issue·版本回退调查","github_rfc_report":"GitHub RFC·研究中"})[r.source_kind]||"来源型案例"}
function experimentMatches(r,q){
  return !q||JSON.stringify([r.title,r.family,r.area,r.hardware,r.model,r.workload,r.change,r.constraints,r.metrics.map(m=>m.label),r.reported_only]).toLowerCase().includes(q);
}
function renderExperimentHub(){
  const recs=[...expData.case_records,...crossData.case_records],q=$("experiment-query").value.trim().toLowerCase();
  const cases=recs.filter(r=>(experimentCategory==="all"||expKind(r)===experimentCategory||r.area===experimentCategory)&&experimentMatches(r,q));
  const op=recs.filter(r=>expKind(r)==="operator").length,svc=recs.length-op;
  const nmetrics=recs.reduce((sum,r)=>sum+r.metrics.filter(m=>m.before!==null&&m.after!==null).length,0);
  $("exp-summary").innerHTML=[
    [String(recs.length),"公开优化案例","覆盖 MatMul、Attention、MoE、GDN、通信等专题"],
    [String(op)+" / "+String(svc),"算子 / 服务","算子级 Profiler 与推理服务数据分层呈现"],
    [String(nmetrics),"性能对照指标","执行耗时、流水时间、TTFT、TPOT 与吞吐"],
    [String(recs.reduce((n,r)=>n+(r.reported_only||[]).length,0)),"补充观测数值","显存节省、缓存用量、单点耗时与性能变化"],
  ].map(x=>'<div class="exp-summary-tile"><strong>'+esc(x[0])+'</strong><span>'+esc(x[1])+'</span><small>'+esc(x[2])+'</small></div>').join("");
  tabs($("experiment-tabs"),Object.entries(experimentTypes).map(([id,label])=>({id,label})),experimentCategory,id=>{
    experimentCategory=id;experimentId=null;renderExperimentHub();
  });
  if(!cases.some(r=>r.id===experimentId))experimentId=cases[0]?.id||null;
  $("experiment-cards").innerHTML=cases.length?cases.map(r=>{
    const tag=r.area?({"attention":"Attention","moe":"MoE","gdn":"GDN","communication":"通信"}[r.area]||"专题"):(expKind(r)==="operator"?"算子":"服务");
    return '<button type="button" class="experiment-card" aria-pressed="'+String(r.id===experimentId)+'" data-id="'+esc(r.id)+'">'+
      '<div class="exp-card-top"><span class="badge neutral">'+tag+'</span><small>'+esc(r.id)+'</small></div>'+
      '<strong>'+esc(r.title)+'</strong><small>'+esc(r.hardware)+'</small><span class="exp-case-metrics">'+(r.metrics.length+(r.reported_only||[]).length)+' 项可追溯指标</span>'+
      '</button>';
  }).join(""):'<p class="empty">无匹配案例。请更改搜索词或来源分类。</p>';
  $("experiment-cards").querySelectorAll("button[data-id]").forEach(button=>button.addEventListener("click",()=>{
    experimentId=button.dataset.id;renderExperimentHub();
  }));
  const selected=recs.find(r=>r.id===experimentId);
  if(!selected){$("experiment-detail").innerHTML='<p class="empty">没有对应记录。</p>';return;}
  const w=selected.workload;
  const shape=[w.M!=null?"M="+w.M:null,w.N!=null?"N="+w.N:null,w.K!=null?"K="+w.K:null].filter(Boolean).join(" · ");
  const workload=[
    shape,w.dtype||null,w.format||null,w.shapes?.join(" / ")||null,
    w.requests!=null?"每轮 "+w.requests+" 请求 × "+w.repeat_rounds+" 轮":null,
    w.total_input_tokens_each_round!=null?"每轮输入 "+expFmt(w.total_input_tokens_each_round)+" tokens":null,
    w.input_tokens_range?"单请求输入 "+w.input_tokens_range.join("～")+" tokens":null,
    w.concurrency!=null?"并发 "+w.concurrency:null,
    w.output_cap!=null?"输出上限 "+w.output_cap+" tokens":null
  ].filter(Boolean);
  const metricHtml=selected.metrics.map(metric=>{
    const comparable=metric.comparable===true&&metric.before!=null&&metric.after!=null;
    const ratio=metric.before>0&&metric.after!=null?metric.after/metric.before:null;
    const trend=ratio!=null?(metric.direction==="higher"?(ratio>=1?"增加":"降低"):(ratio<=1?"降低":"增加")):"—";
    const difference=ratio!=null?Math.abs((ratio-1)*100).toFixed(1)+"%":"—";
    const maxVal=Math.max(metric.before||0,metric.after||0,1e-9);
    const barBefore=100*(metric.before||0)/maxVal;
    const barAfter=100*(metric.after||0)/maxVal;
    const staticTag=comparable?"同口径性能对照":"不同配置/轮次对照";
    const role=metric.scope.replaceAll("_"," ");
    return '<div class="exp-metric"><div class="exp-metric-heading"><strong>'+esc(metric.label)+'</strong><span class="badge '+(comparable?"neutral":"warn")+'">'+staticTag+'</span></div>'+
      '<small>原始指标口径：'+esc(role)+'</small>'+
      '<div class="exp-paired"><div><span>前 / 第 1 轮</span><strong>'+esc(expFmt(metric.before))+' '+esc(metric.unit)+'</strong></div><div><span>后 / 第 2 轮</span><strong>'+esc(expFmt(metric.after))+' '+esc(metric.unit)+'</strong></div></div>'+
      '<div class="exp-bars" aria-label="同一指标两个来源值的相对示意"><span class="exp-bar-base" style="width:'+barBefore.toFixed(1)+'%"></span><span class="exp-bar-result" style="width:'+barAfter.toFixed(1)+'%"></span></div>'+
      '<p class="tiny">'+(comparable?'同一指标数值'+trend+' '+difference+'（按公开报告两端点计算）':'按原文展示不同配置/轮次的指标变化，测试环境见上方记录。')+'</p></div>';
  }).join("");
  const observed=(selected.reported_only||[]).map(o=>'<li>'+esc(o.metric)+'：'+esc(o.value!=null?expFmt(o.value):(expFmt(o.before)+" → "+expFmt(o.after)))+' '+esc(o.unit)+'；'+esc(o.statement)+'</li>').join("");
  const caution=selected.constraints.map(t=>'<li>'+esc(t)+'</li>').join("");
  $("experiment-detail").innerHTML='<div class="exp-detail-top"><div class="data-label">'+esc(expTier(selected))+' · '+esc(selected.id)+'</div><h4>'+esc(selected.title)+'</h4><p class="muted small">'+esc(selected.interpretation)+'</p>'+
   '<div class="exp-workload">'+workload.map(t=>'<span>'+esc(t)+'</span>').join("")+'</div>'+
   '<p class="small"><b>本轮改变：</b>'+esc(selected.change)+'</p>'+
   (selected.model?'<p class="small"><b>模型：</b>'+esc(selected.model)+'</p>':'<p class="tiny">测量对象：独立算子工作负载。</p>')+
   (selected.source_status?'<p class="tiny"><b>原始记录状态：</b>'+esc(selected.source_status)+'</p>':'')+
   '<p class="small"><b>硬件：</b>'+esc(selected.hardware)+'</p></div>'+
   '<div class="exp-metric-list">'+metricHtml+'</div>'+
   (observed?'<h5>补充性能与资源指标</h5><ul class="exp-warnings">'+observed+'</ul>':'')+
   '<h5>实验条件与技术要点</h5><ul class="exp-warnings">'+caution+'</ul>'+
   '<div class="exp-provenance"><strong>技术原始资料</strong><p class="tiny">'+esc(expTier(selected))+'；点击进入原文查看测试环境、指标与实现过程。</p>'+
   safeLink(selected.source_url,"打开原始证据")+'</div>';
}
$("experiment-query").addEventListener("input",()=>{experimentId=null;renderExperimentHub()});
$("experiment-example").addEventListener("click",()=>{
 const ex=expData.documentation_examples[0];
 drawer({title:"vLLM-Ascend Benchmark 指标示例",category:"OFFICIAL BENCHMARK DOCUMENTATION",body:ex.interpretation,
  items:[ex.title,ex.change,ex.metrics.map(m=>m.label+"："+expFmt(m.after)+" "+m.unit).join("；"),...ex.constraints,
  "官方文档提供完整的 Benchmark 运行方式、输出字段与结果展示示例。"],urls:[ex.source_url]});
});
renderExperimentHub();

renderHero();initGenericEvidence();renderProducts();renderAnatomy();renderStack();renderMetrics();renderLife();renderFactors();renderOperator();renderDiagnosis();researchSummary();renderEvidence();renderGraph();renderCompatibility();
})();
