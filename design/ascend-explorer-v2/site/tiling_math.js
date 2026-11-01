/* Ascend GEMM tiling educational mathematics: platform-independent, not a kernel simulator. */
(function(root,factory){
  "use strict";
  const lib=factory();
  if(typeof module==="object"&&module.exports)module.exports=lib;
  if(root)root.AscendTilingMath=lib;
})(typeof globalThis!=="undefined"?globalThis:null,function(){
  "use strict";
  function check(x,name,upper=4096){
    if(!Number.isSafeInteger(x)||x<=0||x>upper)throw new RangeError(name+" must be a positive integer <= "+upper);
  }
  function derive({M,N,K,tm,tn,tk,bytesPerInput=2,bytesPerAccumulator=4}){
    for(const [name,value] of Object.entries({M,N,K}))check(value,name);
    for(const [name,value] of Object.entries({tm,tn,tk}))check(value,name,256);
    check(bytesPerInput,"bytesPerInput",16);check(bytesPerAccumulator,"bytesPerAccumulator",16);
    const mTiles=Math.ceil(M/tm),nTiles=Math.ceil(N/tn),kTiles=Math.ceil(K/tk);
    const baselineA=M*K*nTiles,baselineB=K*N*mTiles;
    const minA=M*K,minB=K*N;
    const loads={
      none:{a:baselineA,b:baselineB},
      reuseA:{a:minA,b:baselineB},
      reuseB:{a:baselineA,b:minB},
      both:{a:minA,b:minB},
    };
    const options=Object.fromEntries(Object.entries(loads).map(([key,v])=>[key,{
      elementsA:v.a,elementsB:v.b,readBytes:(v.a+v.b)*bytesPerInput,
      fractionOfBaseline:(v.a+v.b)/(baselineA+baselineB),
    }]));
    return {
      M,N,K,tm,tn,tk,bytesPerInput,bytesPerAccumulator,
      mTiles,nTiles,kTiles,outputTileCount:mTiles*nTiles,
      tileIterations:mTiles*nTiles*kTiles,
      flopsConvention:2*M*N*K,
      localFootprintBytes:(tm*tk+tk*tn)*bytesPerInput+tm*tn*bytesPerAccumulator,
      lowerBoundInputBytes:(M*K+K*N)*bytesPerInput,
      options,
      disclaimers:[
        "此处按理想化循环访问次数计算逻辑 A/B 加载元素量，不是硬件 GM/HBM 实际传输字节数。",
        "复用策略未证明 L1/UB/L0 容量、布局或缓存驻留可实现；both 是理论下界。",
        "未计输出写回、布局变换、padding、边界、同步、DMA/Cache、并行核分配与其他硬件开销。",
        "FLOPs 采用乘加记 2 次运算的数学约定，不代表实际吞吐或加速倍数。"
      ]
    };
  }
  function tileAt(d,index){
    check(index+1,"step",d.tileIterations);
    const perM=d.nTiles*d.kTiles,mIndex=Math.floor(index/perM);
    const rest=index%perM,nIndex=Math.floor(rest/d.kTiles),kIndex=rest%d.kTiles;
    const mStart=mIndex*d.tm,nStart=nIndex*d.tn,kStart=kIndex*d.tk;
    return {
      index,mIndex,nIndex,kIndex,mStart,nStart,kStart,
      mEnd:Math.min(d.M,mStart+d.tm),nEnd:Math.min(d.N,nStart+d.tn),
      kEnd:Math.min(d.K,kStart+d.tk),
      mExtent:Math.min(d.tm,d.M-mStart),nExtent:Math.min(d.tn,d.N-nStart),
      kExtent:Math.min(d.tk,d.K-kStart),
    };
  }
  return Object.freeze({derive,tileAt});
});