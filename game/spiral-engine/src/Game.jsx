import { useState, useEffect, useRef } from "react";
import { compilePair } from "./tongueRoles.js";

const PI=Math.PI,{sin,cos,sqrt,min,max,abs,floor,pow,random,round,ceil,atan2}=Math;
const W=620,H=620,CX=W/2,CY=H/2,RAD=260;

// ─── SIX SACRED TONGUES (the programming language) ───
const TONGUES=[
  {id:"KO",name:"Kor'aelin",glyph:"ᚲ",color:"#ef4444",desc:"Control Flow",keyword:"loop"},
  {id:"AV",name:"Avali",glyph:"ᚨ",color:"#22d3ee",desc:"Input/Output",keyword:"sense"},
  {id:"RU",name:"Runethic",glyph:"ᚱ",color:"#34d399",desc:"Scope/Context",keyword:"area"},
  {id:"CA",name:"Cassisivadan",glyph:"ᚳ",color:"#fbbf24",desc:"Math/Logic",keyword:"calc"},
  {id:"UM",name:"Umbroth",glyph:"ᚢ",color:"#a78bfa",desc:"Security",keyword:"ward"},
  {id:"DR",name:"Draumric",glyph:"ᛞ",color:"#f472b6",desc:"Transforms",keyword:"morph"},
];

// ─── SPELLS = 2-TONGUE PROGRAMS ───
function getSpell(t1,t2){
  const k=t1+"+"+t2;
  const SPELLS={
    "CA+CA":{name:"Power Surge",icon:"⚡",desc:"calc(calc()) — Pure damage",color:"#fbbf24",dmg:5,rate:50,range:110,splash:0,slow:0,effect:"bolt",tier:2},
    "CA+KO":{name:"Loop Bolt",icon:"↻",desc:"loop(calc()) — Rapid fire",color:"#f59e0b",dmg:1.5,rate:12,range:100,splash:0,slow:0,effect:"rapid",tier:1},
    "KO+CA":{name:"Loop Bolt",icon:"↻",desc:"loop(calc()) — Rapid fire",color:"#f59e0b",dmg:1.5,rate:12,range:100,splash:0,slow:0,effect:"rapid",tier:1},
    "CA+DR":{name:"Transmute Ray",icon:"✧",desc:"calc(morph()) — Convert damage",color:"#e879f9",dmg:3,rate:35,range:120,splash:0,slow:0,effect:"ray",tier:2},
    "DR+CA":{name:"Transmute Ray",icon:"✧",desc:"calc(morph()) — Convert damage",color:"#e879f9",dmg:3,rate:35,range:120,splash:0,slow:0,effect:"ray",tier:2},
    "RU+CA":{name:"Blast Zone",icon:"💥",desc:"area(calc()) — Splash damage",color:"#34d399",dmg:2.5,rate:45,range:90,splash:45,slow:0,effect:"blast",tier:2},
    "CA+RU":{name:"Blast Zone",icon:"💥",desc:"area(calc()) — Splash damage",color:"#34d399",dmg:2.5,rate:45,range:90,splash:45,slow:0,effect:"blast",tier:2},
    "RU+RU":{name:"Wide Field",icon:"◎",desc:"area(area()) — Huge range",color:"#34d399",dmg:1,rate:30,range:160,splash:30,slow:0,effect:"field",tier:1},
    "RU+KO":{name:"Pulse Ring",icon:"◉",desc:"area(loop()) — Repeating pulse",color:"#86efac",dmg:1.5,rate:20,range:80,splash:50,slow:0,effect:"pulse",tier:2},
    "KO+RU":{name:"Pulse Ring",icon:"◉",desc:"area(loop()) — Repeating pulse",color:"#86efac",dmg:1.5,rate:20,range:80,splash:50,slow:0,effect:"pulse",tier:2},
    "UM+UM":{name:"Double Ward",icon:"🛡",desc:"ward(ward()) — Heavy shield",color:"#a78bfa",dmg:0,rate:0,range:60,splash:0,slow:0,effect:"shield",tier:2,shield:true,shieldAmt:8},
    "UM+RU":{name:"Barrier Field",icon:"⬡",desc:"ward(area()) — Zone shield",color:"#818cf8",dmg:0.5,rate:30,range:70,splash:35,slow:0.3,effect:"barrier",tier:2},
    "RU+UM":{name:"Barrier Field",icon:"⬡",desc:"ward(area()) — Zone shield",color:"#818cf8",dmg:0.5,rate:30,range:70,splash:35,slow:0.3,effect:"barrier",tier:2},
    "UM+CA":{name:"Thorn Ward",icon:"⚔",desc:"ward(calc()) — Damages attackers",color:"#c084fc",dmg:2,rate:25,range:50,splash:0,slow:0,effect:"thorns",tier:2},
    "CA+UM":{name:"Thorn Ward",icon:"⚔",desc:"ward(calc()) — Damages attackers",color:"#c084fc",dmg:2,rate:25,range:50,splash:0,slow:0,effect:"thorns",tier:2},
    "KO+KO":{name:"Stun Lock",icon:"⏸",desc:"loop(loop()) — Stun enemies",color:"#ef4444",dmg:0.5,rate:40,range:80,splash:0,slow:0,effect:"stun",tier:2,stun:40},
    "KO+DR":{name:"Redirect",icon:"↪",desc:"loop(morph()) — Push enemies back",color:"#fb923c",dmg:0.8,rate:35,range:90,splash:0,slow:0,effect:"push",tier:2,push:true},
    "DR+KO":{name:"Redirect",icon:"↪",desc:"loop(morph()) — Push enemies back",color:"#fb923c",dmg:0.8,rate:35,range:90,splash:0,slow:0,effect:"push",tier:2,push:true},
    "AV+CA":{name:"Sniper Sense",icon:"◎",desc:"sense(calc()) — Long range + crit",color:"#22d3ee",dmg:6,rate:70,range:180,splash:0,slow:0,effect:"snipe",tier:2},
    "CA+AV":{name:"Sniper Sense",icon:"◎",desc:"sense(calc()) — Long range + crit",color:"#22d3ee",dmg:6,rate:70,range:180,splash:0,slow:0,effect:"snipe",tier:2},
    "AV+AV":{name:"True Sight",icon:"👁",desc:"sense(sense()) — Reveals + marks",color:"#67e8f9",dmg:1,rate:15,range:140,splash:0,slow:0,effect:"mark",tier:1,mark:true},
    "AV+RU":{name:"Scan Pulse",icon:"📡",desc:"sense(area()) — Detect all in zone",color:"#06b6d4",dmg:0.8,rate:18,range:100,splash:60,slow:0,effect:"scan",tier:1},
    "RU+AV":{name:"Scan Pulse",icon:"📡",desc:"sense(area()) — Detect all in zone",color:"#06b6d4",dmg:0.8,rate:18,range:100,splash:60,slow:0,effect:"scan",tier:1},
    "AV+UM":{name:"Frost Sense",icon:"❄",desc:"sense(ward()) — Slows detected",color:"#93c5fd",dmg:0.5,rate:20,range:100,splash:0,slow:0.5,effect:"frost",tier:1},
    "UM+AV":{name:"Frost Sense",icon:"❄",desc:"sense(ward()) — Slows detected",color:"#93c5fd",dmg:0.5,rate:20,range:100,splash:0,slow:0.5,effect:"frost",tier:1},
    "DR+DR":{name:"Chaos Warp",icon:"🌀",desc:"morph(morph()) — Random strong effect",color:"#f472b6",dmg:4,rate:55,range:100,splash:30,slow:0.3,effect:"chaos",tier:3},
    "DR+RU":{name:"Morph Field",icon:"◈",desc:"morph(area()) — Transform zone",color:"#f9a8d4",dmg:1.5,rate:25,range:80,splash:40,slow:0.4,effect:"morphfield",tier:2},
    "RU+DR":{name:"Morph Field",icon:"◈",desc:"morph(area()) — Transform zone",color:"#f9a8d4",dmg:1.5,rate:25,range:80,splash:40,slow:0.4,effect:"morphfield",tier:2},
    "AV+DR":{name:"Phase Shift",icon:"⟐",desc:"sense(morph()) — Phasing shots",color:"#5eead4",dmg:2,rate:30,range:110,splash:0,slow:0,effect:"phase",tier:2},
    "DR+AV":{name:"Phase Shift",icon:"⟐",desc:"sense(morph()) — Phasing shots",color:"#5eead4",dmg:2,rate:30,range:110,splash:0,slow:0,effect:"phase",tier:2},
    "AV+KO":{name:"Auto Target",icon:"⊕",desc:"sense(loop()) — Lock-on stream",color:"#2dd4bf",dmg:1,rate:8,range:90,splash:0,slow:0,effect:"lockon",tier:1},
    "KO+AV":{name:"Auto Target",icon:"⊕",desc:"sense(loop()) — Lock-on stream",color:"#2dd4bf",dmg:1,rate:8,range:90,splash:0,slow:0,effect:"lockon",tier:1},
    "UM+KO":{name:"Trap Loop",icon:"⊘",desc:"ward(loop()) — Repeated trap",color:"#c4b5fd",dmg:1.5,rate:30,range:60,splash:25,slow:0.3,effect:"trap",tier:2},
    "KO+UM":{name:"Trap Loop",icon:"⊘",desc:"ward(loop()) — Repeated trap",color:"#c4b5fd",dmg:1.5,rate:30,range:60,splash:25,slow:0.3,effect:"trap",tier:2},
    "UM+DR":{name:"Warp Shield",icon:"◇",desc:"ward(morph()) — Morphing barrier",color:"#d8b4fe",dmg:1,rate:35,range:70,splash:0,slow:0.2,effect:"warpshield",tier:2},
    "DR+UM":{name:"Warp Shield",icon:"◇",desc:"ward(morph()) — Morphing barrier",color:"#d8b4fe",dmg:1,rate:35,range:70,splash:0,slow:0.2,effect:"warpshield",tier:2},
  };
  return SPELLS[k]||{name:"Fizzle",icon:"💨",desc:"Invalid combo",color:"#475569",dmg:0,rate:99,range:40,splash:0,slow:0,effect:"fizzle",tier:0};
}

function spellCost(spell){return spell.tier===0?5:spell.tier===1?12:spell.tier===2?22:35}

function makeGrid(){
  const cells=[];let id=0;
  cells.push({id:id++,ring:0,angle:0,x:0,y:0,tower:null,claimed:true});
  for(let ring=1;ring<=5;ring++){
    const n=ring*6;
    for(let i=0;i<n;i++){
      const a=(i/n)*2*PI;
      const r=ring/5*0.88;
      cells.push({id:id++,ring,angle:a,x:cos(a)*r,y:sin(a)*r,tower:null,claimed:ring<=1});
    }
  }
  return cells;
}

function cellNeighbor(cell,cells){
  return cells.some(c=>c.claimed&&c.id!==cell.id&&sqrt((c.x-cell.x)**2+(c.y-cell.y)**2)<0.35);
}

export default function Game(){
  const cvs=useRef(null);
  const g=useRef(null);
  const [ui,setUi]=useState({gold:25,lives:20,wave:0,score:0,pick:[null,null],pickIdx:0,compiled:null,gameOver:false,discovered:{}});

  if(!g.current) g.current={
    cells:makeGrid(),enemies:[],particles:[],lasers:[],
    gold:25,lives:20,wave:0,score:0,
    waveTimer:200,spawning:false,toSpawn:0,spawnTimer:0,
    pick:[null,null],pickIdx:0,compiled:null,
    discovered:{},nid:1,combo:0,comboTimer:0,
  };

  const w2s=(x,y)=>({x:CX+x*RAD,y:CY+y*RAD});

  useEffect(()=>{
    const c=cvs.current;if(!c)return;
    const ctx=c.getContext("2d");
    let run=true,f=0,mx=CX,my=CY;

    const near=(sx,sy)=>{
      const wx=(sx-CX)/RAD,wy=(sy-CY)/RAD;
      let best=null,bd=0.14;
      g.current.cells.forEach(cl=>{const d=sqrt((cl.x-wx)**2+(cl.y-wy)**2);if(d<bd){bd=d;best=cl;}});
      return best;
    };

    function addP(x,y,col,n=5,sp=2){for(let i=0;i<n;i++){const a=random()*PI*2;g.current.particles.push({x,y,vx:cos(a)*(0.5+random()*sp),vy:sin(a)*(0.5+random()*sp),life:1,color:col,sz:1.5+random()*2});}}

    function spawnWave(){
      const s=g.current;s.wave++;
      s.toSpawn=3+s.wave*2;s.spawning=true;s.spawnTimer=0;
    }

    function onClick(e){
      const rect=c.getBoundingClientRect();const sc=W/rect.width;
      const sx=(e.clientX-rect.left)*sc,sy=(e.clientY-rect.top)*sc;
      const s=g.current;
      if(s.lives<=0){Object.assign(s,{cells:makeGrid(),enemies:[],particles:[],lasers:[],gold:25,lives:20,wave:0,score:0,waveTimer:200,spawning:false,toSpawn:0,pick:[null,null],pickIdx:0,compiled:null,discovered:{},nid:1,combo:0});return;}

      const cell=near(sx,sy);if(!cell)return;

      if(!cell.claimed){
        if(!cellNeighbor(cell,s.cells))return;
        const cost=ceil(3*pow(1.7,cell.ring));
        if(s.gold<cost)return;
        s.gold-=cost;cell.claimed=true;
        const p=w2s(cell.x,cell.y);addP(p.x,p.y,"#34d399",5);
        return;
      }

      if(cell.claimed&&!cell.tower&&s.compiled){
        const cost=spellCost(s.compiled);
        if(s.gold<cost)return;
        if(s.compiled.tier===0)return;
        s.gold-=cost;
        cell.tower={...s.compiled,cd:0,kills:0};
        const p=w2s(cell.x,cell.y);addP(p.x,p.y,s.compiled.color,10,3);
        s.discovered[s.compiled.name]=true;
        s.pick=[null,null];s.pickIdx=0;s.compiled=null;
      }
    }

    function onMove(e){const rect=c.getBoundingClientRect();const sc=W/rect.width;mx=(e.clientX-rect.left)*sc;my=(e.clientY-rect.top)*sc;}
    c.addEventListener("click",onClick);
    c.addEventListener("mousemove",onMove);

    function tick(){
      if(!run)return;f++;
      const s=g.current;

      if(s.lives>0){
        if(f%60===0)s.gold+=s.cells.filter(c=>c.claimed).length*0.25;

        if(!s.spawning){s.waveTimer--;if(s.waveTimer<=0){spawnWave();s.waveTimer=max(100,280-s.wave*12);}}
        if(s.spawning){
          s.spawnTimer--;
          if(s.spawnTimer<=0&&s.toSpawn>0){
            const a=random()*PI*2;const boss=s.wave%5===0&&s.toSpawn===1;
            s.enemies.push({id:s.nid++,x:cos(a)*1.05,y:sin(a)*1.05,
              hp:boss?12+s.wave*3:2+s.wave*0.7,maxHp:boss?12+s.wave*3:2+s.wave*0.7,
              speed:boss?0.12:0.22+random()*0.12+s.wave*0.008,
              slow:0,slowTimer:0,stunTimer:0,marked:false,
              reward:boss?20:4+floor(s.wave*0.4),size:boss?10:5,color:boss?"#fbbf24":"#ef4444"});
            s.toSpawn--;s.spawnTimer=max(5,18-s.wave);
          }
          if(s.toSpawn<=0&&s.enemies.length===0){s.spawning=false;s.score+=s.wave*25;s.gold+=4+s.wave*2;}
        }

        s.enemies.forEach(e=>{
          if(e.stunTimer>0){e.stunTimer--;return;}
          let sp=e.speed*(e.slow>0?1-e.slow:1);
          const d=sqrt(e.x*e.x+e.y*e.y);
          if(d>0.01){e.x-=e.x/d*sp*0.005;e.y-=e.y/d*sp*0.005;}
          if(e.slowTimer>0)e.slowTimer--;else e.slow=0;
        });

        s.enemies=s.enemies.filter(e=>{
          if(sqrt(e.x*e.x+e.y*e.y)<0.05){s.lives--;s.combo=0;addP(CX,CY,"#ef4444",8);return false;}
          return true;
        });

        s.cells.forEach(cell=>{
          if(!cell.tower||!cell.claimed)return;
          const tw=cell.tower;
          if(tw.cd>0){tw.cd--;return;}
          const rng=tw.range/RAD;
          let tgt=null,td=rng;
          s.enemies.forEach(e=>{const d=sqrt((e.x-cell.x)**2+(e.y-cell.y)**2);if(d<td){if(!tgt||e.marked){td=d;tgt=e;}}});
          if(!tgt)return;
          tw.cd=tw.rate;
          const sp=w2s(cell.x,cell.y),tp=w2s(tgt.x,tgt.y);

          if(tw.splash>0){
            const sr=tw.splash/RAD;
            s.enemies.forEach(e=>{const d=sqrt((e.x-tgt.x)**2+(e.y-tgt.y)**2);if(d<sr){e.hp-=tw.dmg*(1-d/sr*0.5);if(tw.slow>0){e.slow=tw.slow;e.slowTimer=50;}}});
            addP(tp.x,tp.y,tw.color,6);
          }else{
            tgt.hp-=tw.dmg*(tgt.marked?1.5:1);
            if(tw.slow>0){tgt.slow=tw.slow;tgt.slowTimer=60;}
          }
          if(tw.stun)tgt.stunTimer=tw.stun;
          if(tw.push){const d=sqrt(tgt.x**2+tgt.y**2);if(d>0.01){tgt.x+=tgt.x/d*0.06;tgt.y+=tgt.y/d*0.06;}}
          if(tw.mark)tgt.marked=true;
          s.lasers.push({x1:sp.x,y1:sp.y,x2:tp.x,y2:tp.y,color:tw.color,life:0.5});

          s.enemies=s.enemies.filter(e=>{
            if(e.hp<=0){s.gold+=e.reward;s.score+=e.reward;tw.kills++;s.combo++;s.comboTimer=90;
              const p=w2s(e.x,e.y);addP(p.x,p.y,e.color,7);return false;}
            return true;
          });
        });
      }

      if(s.comboTimer>0)s.comboTimer--;else s.combo=0;
      s.particles=s.particles.filter(p=>{p.x+=p.vx;p.y+=p.vy;p.vx*=.92;p.vy*=.92;p.life-=.03;return p.life>0;});
      s.lasers=s.lasers.filter(l=>{l.life-=.1;return l.life>0;});

      ctx.clearRect(0,0,W,H);
      const bg=ctx.createRadialGradient(CX,CY,0,CX,CY,RAD+15);
      bg.addColorStop(0,"#080c1a");bg.addColorStop(.55,"#0f172a");bg.addColorStop(1,"#1e1b4b");
      ctx.fillStyle=bg;ctx.beginPath();ctx.arc(CX,CY,RAD+8,0,2*PI);ctx.fill();
      for(let i=1;i<=5;i++){ctx.strokeStyle="rgba(99,102,241,0.05)";ctx.lineWidth=1;ctx.beginPath();ctx.arc(CX,CY,i/5*RAD*0.88,0,2*PI);ctx.stroke();}

      const hov=near(mx,my);
      s.cells.forEach(cell=>{
        const p=w2s(cell.x,cell.y);
        const sz=cell.ring===0?20:max(11,18-cell.ring*1.2);
        const isHov=hov?.id===cell.id;
        if(cell.claimed){ctx.fillStyle="rgba(52,211,153,0.05)";ctx.beginPath();ctx.arc(p.x,p.y,sz+5,0,2*PI);ctx.fill();}
        ctx.fillStyle=cell.claimed?"#152238":"#0d1117";
        ctx.strokeStyle=isHov?"#fbbf24":cell.claimed?"#34d39933":"#1e293b33";
        ctx.lineWidth=isHov?2.5:1;
        ctx.beginPath();ctx.arc(p.x,p.y,sz,0,2*PI);ctx.fill();ctx.stroke();

        if(cell.tower){
          const active=cell.claimed;
          if(isHov){ctx.strokeStyle=`${cell.tower.color}33`;ctx.lineWidth=1;ctx.beginPath();ctx.arc(p.x,p.y,cell.tower.range,0,2*PI);ctx.stroke();}
          ctx.globalAlpha=active?1:0.3;
          ctx.fillStyle=cell.tower.color;ctx.font=`${sz+4}px serif`;ctx.textAlign="center";ctx.textBaseline="middle";
          ctx.fillText(cell.tower.icon,p.x,p.y+1);
          ctx.globalAlpha=1;
          if(!active){ctx.strokeStyle="#ef444466";ctx.lineWidth=1;ctx.setLineDash([2,2]);ctx.beginPath();ctx.arc(p.x,p.y,sz+2,0,2*PI);ctx.stroke();ctx.setLineDash([]);}
        }

        if(isHov&&!cell.tower&&!cell.claimed&&cellNeighbor(cell,s.cells)){
          const cost=ceil(3*pow(1.7,cell.ring));
          ctx.fillStyle="rgba(0,0,0,.8)";ctx.fillRect(p.x+14,p.y-14,52,18);
          ctx.fillStyle=s.gold>=cost?"#34d399":"#ef4444";ctx.font="bold 9px monospace";ctx.textAlign="left";
          ctx.fillText(`⚡${cost}`,p.x+18,p.y-2);
        }
        if(isHov&&cell.claimed&&!cell.tower&&s.compiled&&s.compiled.tier>0){
          ctx.globalAlpha=0.4;ctx.fillStyle=s.compiled.color;ctx.font=`${sz+4}px serif`;ctx.textAlign="center";ctx.textBaseline="middle";
          ctx.fillText(s.compiled.icon,p.x,p.y+1);
          ctx.strokeStyle=`${s.compiled.color}44`;ctx.lineWidth=1;ctx.beginPath();ctx.arc(p.x,p.y,s.compiled.range,0,2*PI);ctx.stroke();ctx.globalAlpha=1;
          const cost=spellCost(s.compiled);
          ctx.fillStyle="rgba(0,0,0,.8)";ctx.fillRect(p.x+14,p.y-14,52,18);
          ctx.fillStyle=s.gold>=cost?"#fbbf24":"#ef4444";ctx.font="bold 9px monospace";ctx.textAlign="left";
          ctx.fillText(`⚡${cost}`,p.x+18,p.y-2);
        }
      });

      s.lasers.forEach(l=>{ctx.globalAlpha=l.life*2;ctx.strokeStyle=l.color;ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(l.x1,l.y1);ctx.lineTo(l.x2,l.y2);ctx.stroke();ctx.globalAlpha=1;});
      s.enemies.forEach(e=>{
        const p=w2s(e.x,e.y);const pulse=1+sin(f*.1+e.id)*.15;
        ctx.fillStyle=e.color;ctx.beginPath();ctx.arc(p.x,p.y,e.size*pulse,0,2*PI);ctx.fill();
        if(e.marked){ctx.strokeStyle="#22d3ee";ctx.lineWidth=1.5;ctx.beginPath();ctx.arc(p.x,p.y,e.size+4,0,2*PI);ctx.stroke();}
        if(e.slow>0){ctx.strokeStyle="#818cf8";ctx.lineWidth=1;ctx.beginPath();ctx.arc(p.x,p.y,e.size+3,0,2*PI);ctx.stroke();}
        if(e.stunTimer>0){ctx.fillStyle="#fbbf24";ctx.font="8px serif";ctx.textAlign="center";ctx.fillText("⏸",p.x,p.y-e.size-4);}
        const pct=e.hp/e.maxHp;
        if(pct<1){ctx.fillStyle="#0f172a";ctx.fillRect(p.x-8,p.y-e.size-6,16,3);ctx.fillStyle=pct>.5?"#34d399":"#ef4444";ctx.fillRect(p.x-8,p.y-e.size-6,16*pct,3);}
        ctx.strokeStyle=`${e.color}12`;ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(p.x,p.y);ctx.lineTo(CX,CY);ctx.stroke();
      });
      s.particles.forEach(p=>{ctx.globalAlpha=p.life;ctx.fillStyle=p.color;ctx.beginPath();ctx.arc(p.x,p.y,p.sz*p.life,0,2*PI);ctx.fill();ctx.globalAlpha=1;});
      const bp=.5+sin(f*.04)*.2;const bG=ctx.createRadialGradient(CX,CY,0,CX,CY,22);
      bG.addColorStop(0,`rgba(52,211,153,${bp})`);bG.addColorStop(1,"rgba(52,211,153,0)");
      ctx.fillStyle=bG;ctx.beginPath();ctx.arc(CX,CY,22,0,2*PI);ctx.fill();
      ctx.fillStyle="#34d399";ctx.font="bold 11px monospace";ctx.textAlign="center";ctx.fillText(`♥${s.lives}`,CX,CY+4);
      if(s.combo>2){ctx.fillStyle="#fbbf24";ctx.font="bold 18px monospace";ctx.textAlign="center";ctx.globalAlpha=min(1,s.comboTimer/30);ctx.fillText(`${s.combo}x`,CX,42);ctx.globalAlpha=1;}
      ctx.fillStyle="#94a3b8";ctx.font="10px monospace";ctx.textAlign="center";
      ctx.fillText(s.spawning?`⚔ WAVE ${s.wave}`:`Wave ${s.wave+1} in ${ceil(s.waveTimer/60)}s`,CX,H-14);
      ctx.strokeStyle="rgba(167,139,250,.2)";ctx.lineWidth=2;ctx.beginPath();ctx.arc(CX,CY,RAD+5,0,2*PI);ctx.stroke();
      if(s.lives<=0){ctx.fillStyle="rgba(0,0,0,.65)";ctx.fillRect(0,0,W,H);ctx.fillStyle="#ef4444";ctx.font="bold 26px sans-serif";ctx.textAlign="center";ctx.fillText("GAME OVER",CX,CY-15);ctx.fillStyle="#94a3b8";ctx.font="13px monospace";ctx.fillText(`Score: ${s.score} · Wave: ${s.wave}`,CX,CY+15);ctx.fillStyle="#a78bfa";ctx.font="12px sans-serif";ctx.fillText("Click to restart",CX,CY+42);}

      if(f%8===0)setUi({gold:round(s.gold),lives:s.lives,wave:s.wave,score:s.score,pick:[...s.pick],pickIdx:s.pickIdx,compiled:s.compiled,gameOver:s.lives<=0,discovered:{...s.discovered}});
      requestAnimationFrame(tick);
    }
    tick();
    return()=>{run=false;c.removeEventListener("click",onClick);c.removeEventListener("mousemove",onMove);};
  },[]);

  const s=g.current;
  function pickTongue(id){
    const p=[...s.pick];
    p[s.pickIdx]=id;
    s.pick=p;
    s.pickIdx=s.pickIdx===0?1:0;
    if(p[0]&&p[1]){
      s.compiled=getSpell(p[0],p[1]);
      s.discovered[s.compiled.name]=true;
    }else{s.compiled=null;}
    setUi(u=>({...u,pick:[...s.pick],pickIdx:s.pickIdx,compiled:s.compiled,discovered:{...s.discovered}}));
  }
  function clearSpell(){s.pick=[null,null];s.pickIdx=0;s.compiled=null;setUi(u=>({...u,pick:[null,null],pickIdx:0,compiled:null}));}

  const discovered=Object.keys(ui.discovered||{}).length;
  const prog=(ui.pick[0]&&ui.pick[1])?compilePair(ui.pick[0],ui.pick[1]):null;

  return(
    <div style={{background:"#0a0e1a",color:"#e2e8f0",minHeight:"100vh",fontFamily:"'Segoe UI',system-ui,sans-serif"}}>
      <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",padding:"6px 14px",borderBottom:"1px solid #1e293b"}}>
        <span style={{fontSize:15,color:"#a78bfa",fontWeight:800,letterSpacing:2}}>SPIRAL ENGINE</span>
        <div style={{display:"flex",gap:10,fontSize:12,fontFamily:"monospace"}}>
          <span style={{color:"#fbbf24"}}>⚡{ui.gold}</span>
          <span style={{color:"#ef4444"}}>♥{ui.lives}</span>
          <span style={{color:"#a78bfa"}}>W{ui.wave}</span>
          <span style={{color:"#94a3b8"}}>{ui.score}pts</span>
          <span style={{color:"#34d399"}}>📖{discovered}/36</span>
        </div>
      </div>

      <div style={{display:"flex"}}>
        <div style={{flex:1,display:"flex",justifyContent:"center",alignItems:"center",background:"#060a14",padding:4}}>
          <canvas ref={cvs} width={W} height={H} style={{width:"100%",maxWidth:620,aspectRatio:"1",borderRadius:12,cursor:ui.compiled?"crosshair":"pointer"}}/>
        </div>

        <div style={{width:220,padding:10,display:"flex",flexDirection:"column",gap:8,borderLeft:"1px solid #1e293b",background:"#0c1020"}}>
          <div style={{fontSize:10,color:"#64748b",textTransform:"uppercase",letterSpacing:1}}>Spell Forge — combine two tongues</div>

          <div style={{display:"grid",gridTemplateColumns:"1fr 1fr 1fr",gap:4}}>
            {TONGUES.map(t=>{
              const sel=ui.pick.includes(t.id);
              return(
                <button key={t.id} onClick={()=>pickTongue(t.id)} style={{
                  padding:"6px 2px",borderRadius:8,cursor:"pointer",textAlign:"center",
                  background:sel?`${t.color}22`:"#111827",border:`2px solid ${sel?t.color:"#1e293b"}`,
                  boxShadow:sel?`0 0 8px ${t.color}44`:"none",transition:"all .15s",
                }}>
                  <div style={{fontSize:20,color:t.color}}>{t.glyph}</div>
                  <div style={{fontSize:7,color:sel?t.color:"#64748b",fontFamily:"monospace"}}>{t.keyword}</div>
                </button>
              );
            })}
          </div>

          <div style={{background:"#111827",borderRadius:8,padding:10,minHeight:80,border:`1px solid ${ui.compiled?ui.compiled.color+"44":"#1e293b"}`}}>
            <div style={{fontFamily:"monospace",fontSize:11,marginBottom:6,color:"#94a3b8"}}>
              <span style={{color:"#64748b"}}>spell = </span>
              {ui.pick[0]?<span style={{color:TONGUES.find(t=>t.id===ui.pick[0])?.color}}>{TONGUES.find(t=>t.id===ui.pick[0])?.keyword}</span>:<span style={{color:"#334155"}}>___</span>}
              <span style={{color:"#64748b"}}>(</span>
              {ui.pick[1]?<span style={{color:TONGUES.find(t=>t.id===ui.pick[1])?.color}}>{TONGUES.find(t=>t.id===ui.pick[1])?.keyword}</span>:<span style={{color:"#334155"}}>___</span>}
              <span style={{color:"#64748b"}}>)</span>
            </div>
            {prog&&<div style={{fontSize:9,color:"#64748b",marginBottom:6,fontFamily:"monospace"}}>SCBE: {prog.semantics}</div>}

            {ui.compiled?(
              <>
                <div style={{display:"flex",alignItems:"center",gap:6,marginBottom:4}}>
                  <span style={{fontSize:18}}>{ui.compiled.icon}</span>
                  <div>
                    <div style={{fontSize:12,fontWeight:700,color:ui.compiled.color}}>{ui.compiled.name}</div>
                    <div style={{fontSize:9,color:"#64748b"}}>{ui.compiled.desc}</div>
                  </div>
                </div>
                <div style={{display:"flex",gap:8,fontSize:9,fontFamily:"monospace",color:"#94a3b8"}}>
                  {ui.compiled.dmg>0&&<span>DMG:{ui.compiled.dmg}</span>}
                  <span>RNG:{ui.compiled.range}</span>
                  {ui.compiled.splash>0&&<span>AOE:{ui.compiled.splash}</span>}
                  {ui.compiled.slow>0&&<span>SLOW:{ui.compiled.slow}</span>}
                </div>
                <div style={{marginTop:6,fontSize:10,fontWeight:600,color:"#fbbf24",fontFamily:"monospace"}}>
                  Cost: ⚡{spellCost(ui.compiled)} — click territory to cast
                </div>
              </>
            ):(
              <div style={{color:"#334155",fontSize:11,fontStyle:"italic",textAlign:"center",padding:8}}>
                Select two tongues to forge a spell...
              </div>
            )}
          </div>

          <button onClick={clearSpell} style={{padding:"4px",borderRadius:4,background:"#1e293b",color:"#64748b",border:"1px solid #1e293b",cursor:"pointer",fontSize:10}}>✕ Clear</button>

          <div style={{fontSize:9,color:"#475569",lineHeight:1.6,padding:8,background:"#0f1219",borderRadius:8}}>
            <strong style={{color:"#94a3b8"}}>How to play:</strong><br/>
            1. Pick two tongue glyphs above to write a spell<br/>
            2. Click <span style={{color:"#34d399"}}>green territory</span> to cast it<br/>
            3. Click dark cells to expand territory<br/>
            4. Spells auto-attack enemies<br/>
            5. Discover all 36 combinations!
          </div>

          <div style={{fontSize:9,color:"#475569",padding:8,background:"#0f1219",borderRadius:8,maxHeight:120,overflowY:"auto"}}>
            <strong style={{color:"#94a3b8"}}>📖 Spellbook ({discovered}/36)</strong><br/>
            {Object.keys(ui.discovered||{}).map(name=>(
              <div key={name} style={{color:"#94a3b8"}}>{name}</div>
            ))}
            {discovered===0&&<div style={{fontStyle:"italic"}}>Cast spells to discover them...</div>}
          </div>
        </div>
      </div>
    </div>
  );
}
