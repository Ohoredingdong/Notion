import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
const html=fs.readFileSync(new URL('../index.html',import.meta.url),'utf8');
assert.ok(html.startsWith('<!doctype html>'));
const source=html.match(/<script>([\s\S]*?)<\/script>/)?.[1];
assert.ok(source,'script exists');
new vm.Script(source,{filename:'study-training.js'});
const at=source.lastIndexOf("$('#brand-home').onclick");
assert.ok(at>0,'test runtime boundary');
const core=source.slice(0,at)+"\nglobalThis.__qa={games,makeQ,passages,data,lifetimeXP,levelFromXP,xpForAnswer,balancedTestGames,getAdaptiveDifficulty,sudokuSolutionCount,renderCompositeBreakdown,icons:GAME_ICON_PATHS};\n})();";
const state={console,localStorage:{getItem:()=>null,setItem:()=>{}},setInterval:()=>0,clearInterval:()=>{},setTimeout:()=>0,clearTimeout:()=>{}};
vm.createContext(state);
new vm.Script(core).runInContext(state,{timeout:30000});
const {games,makeQ,passages,data,lifetimeXP,levelFromXP,xpForAnswer,balancedTestGames,getAdaptiveDifficulty,sudokuSolutionCount,renderCompositeBreakdown,icons}=state.__qa;
assert.equal(games.length,49,'49 game definitions');
assert.equal(Object.keys(icons).length,49,'49 game icons');
assert.ok(passages.length>=18,'reading bank has 18 passages');
assert.equal(levelFromXP(),1,'new profile starts at level 1');
assert.equal(lifetimeXP(),0,'new profile starts with zero XP');
assert.equal(xpForAnswer(true,1),10);
assert.equal(xpForAnswer(true,2),13);
assert.equal(xpForAnswer(true,3),16);
for(const count of [5,8,12,20,100]){
 const selected=balancedTestGames(count);
 assert.equal(selected.length,count);
 const groups={math:0,brain:0,read:0};
 for(const g of selected)groups[g.group==='math'?'math':g.group==='read'?'read':'brain']++;
 assert.ok(Math.max(...Object.values(groups))-Math.min(...Object.values(groups))<=1,'balanced composite test');
}
const seenIndex=new Set();let checked=0;
for(const game of games){
 for(const diff of [1,2,3]){
  for(let i=0;i<45;i++){
   const q=makeQ(game.id,diff);
   assert.ok(q?.type&&q.prompt,game.id+' prompt/type');
   if(q.type==='choice'){
    assert.ok(q.options.length>=2,game.id+' choice options');
    assert.equal(new Set(q.options.map(String)).size,q.options.length,game.id+' unique options');
    assert.ok(q.options.some(x=>String(x)===String(q.answer)),game.id+' answer among options');
   }
   if(q.type==='sequence')assert.ok(q.keys.length&&q.answer,game.id+' sequence');
   if(q.type==='pairs')assert.equal(q.deck.length,q.answer*2);
   if(q.type==='sudoku'){assert.equal(q.grid?.length,4);assert.equal(sudokuSolutionCount(q.grid,q.fixed),1,'one Sudoku solution');const given=q.fixed.flat().filter(Boolean).length;assert.ok(given>=6&&given<=12,'sudoku clues bounded')}
   if(q.type==='grid')assert.ok(q.selected?.length>=2);
   if(game.id==='shuffle'){
    assert.equal(q.type,'choice','shell tracking uses answer selection');
    assert.ok(q.shellGame,'shell game marker exists');
    assert.ok(!q.visual,'no symbolic swap notation shown');
    assert.equal(q.moves.length,diff+2,'shell swap count scales with difficulty');
    let position=1;
    for(const [a,b] of q.moves){
      assert.ok(a>=1&&a<=3&&b>=1&&b<=3&&a!==b,'valid distinct slot swap');
      position=position===a?b:position===b?a:position;
    }
    assert.equal(Number(q.answer),position,'correct tracked ball location');
    assert.deepEqual([...q.options].sort(),['1','2','3'],'three visual answer positions');
   }
   if(game.id==='verbal'){
    assert.ok(q.previewHeading&&!q.previewHeading.includes('번째'),'no memory target leak');
    const m=q.prompt.match(/(\d+)번째/);assert.ok(m);seenIndex.add(Number(m[1]));
   }
   if(game.group==='read'&&!['verbal','chunks'].includes(game.id))assert.ok(q.explanation,game.id+' explanation');
   checked++;
  }
 }
}
assert.ok(seenIndex.size>=4,'verbal target index randomized');
data.progress.xp=501;assert.equal(levelFromXP(),2);
data.progress.xp=5001;
data.sessions=Array.from({length:1600},()=>({date:'2026-11-23',answers:[]}));
assert.equal(lifetimeXP(),5001,'XP survives 1500-session display cap');
assert.equal(levelFromXP(),11,'level derives from lifetime XP, not archived session count');
data.sessions=[{answers:Array.from({length:12},()=>({id:'flash',correct:true,seconds:9}))}];
assert.equal(getAdaptiveDifficulty('flash'),3,'adaptive difficulty increases for accurate fast answers');
data.sessions=[{answers:Array.from({length:12},()=>({id:'flash',correct:false,seconds:9}))}];
assert.equal(getAdaptiveDifficulty('flash'),1,'adaptive difficulty decreases for low accuracy');
const breakdown=renderCompositeBreakdown({items:[{group:'math'},{group:'memory'},{group:'read'}],answers:[{id:'twosum',correct:true},{id:'flash',correct:false},{id:'gist',correct:true}]});
for(const name of ['계산','두뇌','국어'])assert.ok(breakdown.includes(name),'mixed-test result includes '+name);
assert.match(html,/bestByGame:\(next\.progress\.bestByGame/,'import preserves personal bests');
assert.match(html,/record\.mode\|\|/,'retry keeps test mode');
assert.match(html,/id==='calc25'\?\[25\]:id==='calc100'\?\[100\]/,'fixed-length calculation games');
const legacy=fs.readFileSync(new URL('../../brain-training/index.html',import.meta.url),'utf8');
assert.match(legacy,/\.\.\/study-training\//,'legacy URL redirects to canonical training page');
console.log(JSON.stringify({ok:true,gameTypes:games.length,passages:passages.length,questionsChecked:checked,randomizedMemoryPositions:[...seenIndex].sort(),compositeMix:true},null,2));