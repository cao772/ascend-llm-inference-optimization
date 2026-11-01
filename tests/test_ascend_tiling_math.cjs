"use strict";
const {test}=require("node:test");
const assert=require("node:assert/strict");
const {derive,tileAt}=require("../design/ascend-explorer-v2/site/tiling_math.js");

test("basic tile dimensions and K reductions are deterministic",()=>{
 const d=derive({M:64,N:64,K:64,tm:32,tn:32,tk:32});
 assert.deepEqual([d.mTiles,d.nTiles,d.kTiles,d.outputTileCount,d.tileIterations],[2,2,2,4,8]);
 assert.equal(d.flopsConvention,2*64*64*64);
 assert.equal(d.options.none.readBytes,32768);
 assert.equal(d.options.reuseA.readBytes,24576);
 assert.equal(d.options.reuseB.readBytes,24576);
 assert.equal(d.options.both.readBytes,16384);
});
test("boundary tile uses real extents not full assumed shape",()=>{
 const d=derive({M:144,N:112,K:80,tm:64,tn:64,tk:32});
 assert.equal(d.tileIterations,18);
 const final=tileAt(d,17);
 assert.deepEqual([final.mIndex,final.nIndex,final.kIndex],[2,1,2]);
 assert.deepEqual([final.mExtent,final.nExtent,final.kExtent],[16,48,16]);
 assert.deepEqual([final.mStart,final.nStart,final.kStart],[128,64,64]);
});
test("logical reuse algebra keeps realistic inequality and no fake speedup",()=>{
 const d=derive({M:64,N:96,K:80,tm:32,tn:64,tk:32});
 assert.deepEqual([d.mTiles,d.nTiles,d.kTiles],[2,2,3]);
 assert.equal(d.options.none.readBytes,(64*80*2+80*96*2)*2);
 assert.equal(d.options.reuseB.readBytes,(64*80*2+80*96)*2);
 assert.ok(d.options.both.readBytes<=d.options.reuseB.readBytes);
 assert.ok(d.options.reuseB.readBytes<=d.options.none.readBytes);
 assert.ok(d.disclaimers.some(x=>x.includes("不是硬件")));
});
test("single output tile has no imaginary cross-tile savings",()=>{
 const d=derive({M:32,N:32,K:32,tm:64,tn:64,tk:16});
 assert.equal(d.outputTileCount,1);
 assert.equal(d.options.none.readBytes,d.options.both.readBytes);
});
test("rejects invalid sizes and invalid step index",()=>{
 assert.throws(()=>derive({M:0,N:64,K:64,tm:32,tn:32,tk:32}),RangeError);
 assert.throws(()=>derive({M:64,N:64,K:64,tm:0,tn:32,tk:32}),RangeError);
 assert.throws(()=>derive({M:64,N:64,K:64,tm:512,tn:32,tk:32}),RangeError);
 const d=derive({M:64,N:64,K:64,tm:32,tn:32,tk:32});
 assert.throws(()=>tileAt(d,-1),RangeError);
 assert.throws(()=>tileAt(d,8),RangeError);
});
test("footprint is explicitly a local arithmetic estimate",()=>{
 const d=derive({M:128,N:128,K:128,tm:32,tn:64,tk:32});
 assert.equal(d.localFootprintBytes,(32*32+32*64)*2+32*64*4);
 assert.equal(d.lowerBoundInputBytes,(128*128+128*128)*2);
 assert.ok(d.disclaimers.some(x=>x.includes("片")||x.includes("缓存")||x.includes("复用")));
});
