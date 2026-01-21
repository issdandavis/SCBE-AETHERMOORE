/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
*/
import React, { useEffect, useRef, useState } from 'react';
import { Play, RotateCcw, Shield, Zap, Sparkles, Trophy } from 'lucide-react';

type PowerUpType = 'MULTISHOT' | 'RAPIDFIRE' | 'SHIELD';

interface GameState {
    playerX: number;
    playerH: number;
    playerW: number;
    health: number;
    bullets: { x: number; y: number; w: number; h: number; type: 'NORMAL' | 'POWERED' }[];
    enemies: { x: number; y: number; w: number; h: number; speed: number; id: number; health: number }[];
    powerups: { x: number; y: number; type: PowerUpType; id: number }[];
    particles: { x: number; y: number; vx: number; vy: number; life: number; color: string }[];
    score: number;
    combo: number;
    lastShot: number;
    lastSpawn: number;
    wave: number;
    activePowerups: Map<PowerUpType, number>; // type -> duration
    idCounter: number;
    pointerX: number | null;
    isPointerDown: boolean;
}

export const AlienDefense: React.FC = () => {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);
    const audioCtxRef = useRef<AudioContext | null>(null);
    
    const [score, setScore] = useState(0);
    const [highScore, setHighScore] = useState(Number(localStorage.getItem('alien-high-score') || 0));
    const [gameOver, setGameOver] = useState(false);
    const [isPlaying, setIsPlaying] = useState(false);
    const [health, setHealth] = useState(3);
    const [wave, setWave] = useState(1);

    const state = useRef<GameState>({
        playerX: 0,
        playerH: 24,
        playerW: 44,
        health: 3,
        bullets: [],
        enemies: [],
        powerups: [],
        particles: [],
        score: 0,
        combo: 0,
        lastShot: 0,
        lastSpawn: 0,
        wave: 1,
        activePowerups: new Map(),
        idCounter: 0,
        pointerX: null,
        isPointerDown: false
    });

    const keys = useRef(new Set<string>());
    const animationFrameRef = useRef<number | undefined>(undefined);

    // Synth Audio Engine
    const playSound = (type: 'shoot' | 'explode' | 'powerup' | 'damage') => {
        try {
            if (!audioCtxRef.current) audioCtxRef.current = new (window.AudioContext || (window as any).webkitAudioContext)();
            const ctx = audioCtxRef.current;
            if (ctx.state === 'suspended') ctx.resume();
            
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();

            if (type === 'shoot') {
                osc.type = 'triangle';
                osc.frequency.setValueAtTime(600, ctx.currentTime);
                osc.frequency.exponentialRampToValueAtTime(40, ctx.currentTime + 0.1);
                gain.gain.setValueAtTime(0.05, ctx.currentTime);
                gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.1);
            } else if (type === 'explode') {
                osc.type = 'square';
                osc.frequency.setValueAtTime(100, ctx.currentTime);
                osc.frequency.exponentialRampToValueAtTime(10, ctx.currentTime + 0.3);
                gain.gain.setValueAtTime(0.05, ctx.currentTime);
                gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.3);
            } else if (type === 'powerup') {
                osc.type = 'sine';
                osc.frequency.setValueAtTime(400, ctx.currentTime);
                osc.frequency.linearRampToValueAtTime(800, ctx.currentTime + 0.2);
                gain.gain.setValueAtTime(0.1, ctx.currentTime);
                gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.2);
            } else if (type === 'damage') {
                osc.type = 'sawtooth';
                osc.frequency.setValueAtTime(80, ctx.currentTime);
                gain.gain.setValueAtTime(0.1, ctx.currentTime);
                gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.5);
            }

            osc.connect(gain);
            gain.connect(ctx.destination);
            osc.start();
            osc.stop(ctx.currentTime + 0.5);
        } catch (e) {
            // Ignore audio errors if context fails
        }
    };

    const spawnParticles = (x: number, y: number, color: string, count = 10) => {
        for (let i = 0; i < count; i++) {
            state.current.particles.push({
                x, y,
                vx: (Math.random() - 0.5) * 8,
                vy: (Math.random() - 0.5) * 8,
                life: 1.0,
                color
            });
        }
    };

    const initGame = () => {
        const width = containerRef.current?.clientWidth || 500;
        const height = containerRef.current?.clientHeight || 600;
        state.current = {
            ...state.current,
            playerX: width / 2 - 22,
            playerH: 24,
            playerW: 44,
            health: 3,
            bullets: [],
            enemies: [],
            powerups: [],
            particles: [],
            score: 0,
            combo: 0,
            lastShot: 0,
            lastSpawn: 0,
            wave: 1,
            activePowerups: new Map(),
            idCounter: 0,
            isPointerDown: false
        };
        setHealth(3);
        setScore(0);
        setWave(1);
        setGameOver(false);
        setIsPlaying(true);
    };

    const gameLoop = (timestamp: number) => {
        if (!isPlaying || gameOver) return;
        const canvas = canvasRef.current;
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        const s = state.current;
        const width = canvas.width;
        const height = canvas.height;

        // --- UPDATE ---
        
        // Power-up durations
        for (const [type, time] of s.activePowerups) {
            if (time < timestamp) s.activePowerups.delete(type);
        }

        // Movement Logic (Keyboard + Pointer)
        if (s.pointerX !== null) {
            // Smoothly move ship towards pointer
            const targetX = s.pointerX - s.playerW / 2;
            s.playerX += (targetX - s.playerX) * 0.2;
            s.playerX = Math.max(0, Math.min(width - s.playerW, s.playerX));
        } else {
            if (keys.current.has('ArrowLeft')) s.playerX = Math.max(0, s.playerX - 10);
            if (keys.current.has('ArrowRight')) s.playerX = Math.min(width - s.playerW, s.playerX + 10);
        }

        // Shooting Logic (Keyboard Space or Pointer Down)
        const fireRate = s.activePowerups.has('RAPIDFIRE') ? 100 : 250;
        if ((keys.current.has('Space') || s.isPointerDown) && timestamp - s.lastShot > fireRate) {
            playSound('shoot');
            if (s.activePowerups.has('MULTISHOT')) {
                s.bullets.push({ x: s.playerX + s.playerW/2 - 2, y: height - 50, w: 4, h: 12, type: 'NORMAL' });
                s.bullets.push({ x: s.playerX + s.playerW/2 - 15, y: height - 50, w: 4, h: 12, type: 'NORMAL' });
                s.bullets.push({ x: s.playerX + s.playerW/2 + 11, y: height - 50, w: 4, h: 12, type: 'NORMAL' });
            } else {
                s.bullets.push({ x: s.playerX + s.playerW/2 - 2, y: height - 50, w: 4, h: 12, type: 'NORMAL' });
            }
            s.lastShot = timestamp;
        }

        // Update Bullets
        for (let i = s.bullets.length - 1; i >= 0; i--) {
            s.bullets[i].y -= 15;
            if (s.bullets[i].y < -20) s.bullets.splice(i, 1);
        }

        // Spawn Enemies
        const spawnRate = Math.max(200, 1000 - (s.wave * 100));
        if (timestamp - s.lastSpawn > spawnRate) {
            const size = 30 + Math.random() * 15;
            s.enemies.push({
                x: Math.random() * (width - size),
                y: -size,
                w: size, h: size,
                speed: 1.5 + (s.wave * 0.5) + Math.random() * 2,
                id: s.idCounter++,
                health: 1 + Math.floor(s.wave / 3)
            });
            s.lastSpawn = timestamp;
        }

        // Update Particles
        for (let i = s.particles.length - 1; i >= 0; i--) {
            const p = s.particles[i];
            p.x += p.vx; p.y += p.vy; p.life -= 0.02;
            if (p.life <= 0) s.particles.splice(i, 1);
        }

        // Update Powerups
        for (let i = s.powerups.length - 1; i >= 0; i--) {
            const pu = s.powerups[i];
            pu.y += 3;
            if (pu.y > height) s.powerups.splice(i, 1);

            // Collision with player
            if (pu.x < s.playerX + s.playerW && pu.x + 20 > s.playerX && pu.y < height - 20 && pu.y + 20 > height - 50) {
                s.activePowerups.set(pu.type, timestamp + 10000);
                playSound('powerup');
                s.powerups.splice(i, 1);
            }
        }

        // Update Enemies
        for (let i = s.enemies.length - 1; i >= 0; i--) {
            const e = s.enemies[i];
            e.y += e.speed;

            // Collision with Player
            if (e.y + e.h > height - 50 && e.x < s.playerX + s.playerW && e.x + e.w > s.playerX) {
                if (s.activePowerups.has('SHIELD')) {
                    s.activePowerups.delete('SHIELD');
                    playSound('explode');
                } else {
                    s.health--;
                    setHealth(s.health);
                    playSound('damage');
                    if (s.health <= 0) {
                        setGameOver(true);
                        setIsPlaying(false);
                        if (s.score > highScore) {
                            setHighScore(s.score);
                            localStorage.setItem('alien-high-score', s.score.toString());
                        }
                    }
                }
                spawnParticles(e.x + e.w/2, e.y + e.h/2, '#ef4444', 20);
                s.enemies.splice(i, 1);
                continue;
            }

            // Remove if off bottom
            if (e.y > height) {
                s.enemies.splice(i, 1);
                s.combo = 0; // Reset combo if an enemy escapes
            }
        }

        // Collision: Bullets <-> Enemies
        for (let i = s.bullets.length - 1; i >= 0; i--) {
            for (let j = s.enemies.length - 1; j >= 0; j--) {
                const b = s.bullets[i];
                const e = s.enemies[j];
                if (b.x < e.x + e.w && b.x + b.w > e.x && b.y < e.y + e.h && b.y + b.h > e.y) {
                    e.health--;
                    s.bullets.splice(i, 1);
                    if (e.health <= 0) {
                        playSound('explode');
                        spawnParticles(e.x + e.w/2, e.y + e.h/2, '#22c55e');
                        s.enemies.splice(j, 1);
                        
                        s.combo = Math.min(5, s.combo + 1);
                        const gain = 100 * s.combo;
                        s.score += gain;
                        setScore(s.score);

                        // Progressive wave
                        const newWave = Math.floor(s.score / 2500) + 1;
                        if (newWave > s.wave) {
                            s.wave = newWave;
                            setWave(newWave);
                        }

                        // Chance to drop powerup
                        if (Math.random() < 0.15) {
                            const types: PowerUpType[] = ['MULTISHOT', 'RAPIDFIRE', 'SHIELD'];
                            s.powerups.push({
                                x: e.x, y: e.y,
                                type: types[Math.floor(Math.random() * types.length)],
                                id: s.idCounter++
                            });
                        }
                    }
                    break;
                }
            }
        }

        // --- DRAW ---
        ctx.fillStyle = '#05050a';
        ctx.fillRect(0, 0, width, height);

        // Grid Background
        ctx.strokeStyle = '#1e1b4b';
        ctx.lineWidth = 1;
        for (let x = 0; x < width; x += 40) {
            ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, height); ctx.stroke();
        }
        for (let y = 0; y < height; y += 40) {
            ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(width, y); ctx.stroke();
        }

        // Particles
        s.particles.forEach(p => {
            ctx.globalAlpha = p.life;
            ctx.fillStyle = p.color;
            ctx.fillRect(p.x, p.y, 3, 3);
        });
        ctx.globalAlpha = 1.0;

        // Player
        ctx.shadowBlur = 15;
        ctx.shadowColor = s.activePowerups.has('SHIELD') ? '#06b6d4' : '#3b82f6';
        ctx.fillStyle = s.activePowerups.has('SHIELD') ? '#06b6d4' : '#3b82f6';
        ctx.beginPath();
        ctx.moveTo(s.playerX, height - 20);
        ctx.lineTo(s.playerX + s.playerW/2, height - 50);
        ctx.lineTo(s.playerX + s.playerW, height - 20);
        ctx.closePath();
        ctx.fill();

        // Bullets
        ctx.shadowBlur = 10;
        ctx.shadowColor = '#facc15';
        ctx.fillStyle = '#facc15';
        s.bullets.forEach(b => ctx.fillRect(b.x, b.y, b.w, b.h));

        // Enemies
        s.enemies.forEach(e => {
            ctx.shadowBlur = 15;
            ctx.shadowColor = '#4ade80';
            ctx.fillStyle = '#16a34a';
            ctx.fillRect(e.x, e.y, e.w, e.h);
            ctx.fillStyle = '#4ade80';
            ctx.fillRect(e.x + 4, e.y + 4, e.w - 8, e.h - 8);
        });

        // Powerups
        s.powerups.forEach(pu => {
            ctx.shadowBlur = 10;
            ctx.shadowColor = '#fff';
            ctx.fillStyle = pu.type === 'SHIELD' ? '#06b6d4' : pu.type === 'MULTISHOT' ? '#3b82f6' : '#eab308';
            ctx.beginPath(); ctx.arc(pu.x + 10, pu.y + 10, 10, 0, Math.PI * 2); ctx.fill();
        });
        ctx.shadowBlur = 0;

        animationFrameRef.current = requestAnimationFrame(gameLoop);
    };

    // Pointer Event Handlers
    const handlePointerDown = (e: React.PointerEvent) => {
        if (!isPlaying || gameOver) return;
        const rect = canvasRef.current?.getBoundingClientRect();
        if (!rect) return;
        state.current.isPointerDown = true;
        state.current.pointerX = e.clientX - rect.left;
    };

    const handlePointerMove = (e: React.PointerEvent) => {
        if (!isPlaying || gameOver) return;
        const rect = canvasRef.current?.getBoundingClientRect();
        if (!rect) return;
        state.current.pointerX = e.clientX - rect.left;
    };

    const handlePointerUp = () => {
        state.current.isPointerDown = false;
        state.current.pointerX = null;
    };

    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => keys.current.add(e.code);
        const handleKeyUp = (e: KeyboardEvent) => keys.current.delete(e.code);
        window.addEventListener('keydown', handleKeyDown);
        window.addEventListener('keyup', handleKeyUp);
        return () => {
            window.removeEventListener('keydown', handleKeyDown);
            window.removeEventListener('keyup', handleKeyUp);
        };
    }, []);

    useEffect(() => {
        if (isPlaying && !gameOver) {
            animationFrameRef.current = requestAnimationFrame(gameLoop);
        }
        return () => { if (animationFrameRef.current) cancelAnimationFrame(animationFrameRef.current); };
    }, [isPlaying, gameOver]);

    useEffect(() => {
        const resize = () => {
            if (containerRef.current && canvasRef.current) {
                canvasRef.current.width = containerRef.current.clientWidth;
                canvasRef.current.height = containerRef.current.clientHeight;
            }
        };
        resize();
        window.addEventListener('resize', resize);
        return () => window.removeEventListener('resize', resize);
    }, []);

    return (
        <div 
            ref={containerRef} 
            className="h-full w-full bg-black relative overflow-hidden flex flex-col items-center justify-center select-none touch-none" 
            tabIndex={0}
            onPointerDown={handlePointerDown}
            onPointerMove={handlePointerMove}
            onPointerUp={handlePointerUp}
            onPointerLeave={handlePointerUp}
        >
            <canvas ref={canvasRef} className="absolute inset-0 z-0 block pointer-events-none" />

            {/* HUD */}
            <div className="absolute top-6 inset-x-6 flex justify-between items-start pointer-events-none z-10">
                <div className="flex flex-col gap-1">
                    <div className="text-emerald-400 font-mono text-2xl font-black drop-shadow-[0_0_10px_#10b981] uppercase tracking-tighter">Score: {score}</div>
                    <div className="text-zinc-500 font-mono text-xs uppercase font-bold">Best: {highScore}</div>
                    {state.current.combo > 1 && (
                        <div className="text-yellow-400 font-black italic text-xl animate-bounce">x{state.current.combo} COMBO!</div>
                    )}
                </div>
                
                <div className="flex flex-col items-end gap-2">
                    <div className="flex gap-1.5">
                        {[...Array(3)].map((_, i) => (
                            <div key={i} className={`w-6 h-6 rounded-sm rotate-45 border-2 ${i < health ? 'bg-blue-500 border-blue-400 shadow-[0_0_10px_#3b82f6]' : 'bg-zinc-900 border-zinc-800'}`} />
                        ))}
                    </div>
                    <div className="px-3 py-1 bg-zinc-900/80 border border-zinc-700 rounded text-zinc-100 text-[10px] font-bold uppercase tracking-widest">
                        Wave {wave}
                    </div>
                </div>
            </div>

            {/* Screens */}
            {(!isPlaying || gameOver) && (
                <div className="absolute inset-0 z-20 bg-black/90 backdrop-blur-xl flex flex-col items-center justify-center text-white px-10 text-center">
                    <div className="mb-2 p-3 bg-emerald-500/10 rounded-2xl border border-emerald-500/20">
                        <Trophy size={48} className="text-emerald-500" />
                    </div>
                    <h1 className="text-5xl font-black text-white italic tracking-tighter mb-2 uppercase drop-shadow-[0_0_30px_rgba(255,255,255,0.3)]">
                        Alien Defense
                    </h1>
                    <p className="text-zinc-400 text-[10px] font-mono uppercase tracking-[0.3em] mb-12">Orbital Asset Protection System</p>
                    
                    {gameOver && (
                        <div className="mb-12 space-y-2">
                            <div className="text-red-500 font-black text-4xl uppercase italic tracking-widest animate-pulse">Critical Failure</div>
                            <div className="text-zinc-500 font-mono text-sm uppercase">Mission Score: {score}</div>
                        </div>
                    )}

                    {!gameOver && (
                        <div className="grid grid-cols-2 gap-8 mb-12 text-zinc-400">
                            <div className="flex flex-col items-center gap-2">
                                <div className="flex gap-2">
                                    <div className="px-4 py-2 rounded border border-zinc-700 bg-zinc-800 flex items-center justify-center font-bold text-white text-[10px] uppercase">Mouse / Touch</div>
                                </div>
                                <span className="text-[10px] font-bold uppercase tracking-widest">Move Ship</span>
                            </div>
                            <div className="flex flex-col items-center gap-2">
                                <div className="px-4 py-2 rounded border border-zinc-700 bg-zinc-800 flex items-center justify-center font-bold text-white text-[10px] uppercase">Hold Down</div>
                                <span className="text-[10px] font-bold uppercase tracking-widest">Auto Fire</span>
                            </div>
                        </div>
                    )}

                    <button 
                        onPointerDown={(e) => { e.stopPropagation(); initGame(); }} 
                        className="group relative px-12 py-4 bg-white text-black font-black uppercase italic tracking-widest rounded-full transition-all hover:scale-105 active:scale-95 shadow-[0_0_30px_rgba(255,255,255,0.2)] flex items-center gap-3"
                    >
                        {gameOver ? <RotateCcw size={20} /> : <Play size={20} fill="currentColor" />}
                        {gameOver ? "Reboot System" : "Initiate Defense"}
                    </button>

                    <div className="mt-12 text-[10px] text-zinc-600 font-mono flex gap-4 uppercase">
                        <span>// Rapid Fire Drops</span>
                        <span>// Multi-Shot Powerup</span>
                        <span>// Touch Optimized</span>
                    </div>
                </div>
            )}
        </div>
    );
};