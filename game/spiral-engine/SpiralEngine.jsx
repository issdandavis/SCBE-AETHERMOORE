import { useState, useEffect, useRef } from "react";

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
// Each combo of two tongues compiles into a specific tower spell
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

// NOTE: original full Game component (canvas render loop + crafting UI) lives in
// the chat history this was saved from. This file preserves the language core —
// the 6 tongues and the 2-tongue spell compilation table — which is the part the
// SCBE tokenizer mirrors (see python/scbe/tongue_roles.py). Drop the full
// component body back in below to run it in a React/Vite app.

export { TONGUES, getSpell };
