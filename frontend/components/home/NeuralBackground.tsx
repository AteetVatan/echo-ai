"use client";

import { useEffect, useRef } from "react";

interface Node {
    x: number;
    y: number;
    vx: number;
    vy: number;
    radius: number;
    color: string;
    glowColor: string;
    pulseSpeed: number;
    pulsePhase: number;
}

const NODE_COLORS = [
    { color: "#ff6b6b", glow: "rgba(255,107,107,0.4)" },
    { color: "#3b82f6", glow: "rgba(59,130,246,0.4)" },
    { color: "#00cec9", glow: "rgba(0,206,201,0.4)" },
    { color: "#fdcb6e", glow: "rgba(253,203,110,0.4)" },
    { color: "#55efc4", glow: "rgba(85,239,196,0.4)" },
    { color: "#a29bfe", glow: "rgba(162,155,254,0.4)" },
    { color: "#74b9ff", glow: "rgba(116,185,255,0.4)" },
    { color: "#60a5fa", glow: "rgba(96,165,250,0.4)" },
    { color: "#e17055", glow: "rgba(225,112,85,0.4)" },
];

export function NeuralBackground() {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const nodesRef = useRef<Node[]>([]);
    const animRef = useRef<number>(0);

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const ctx = canvas.getContext("2d");
        if (!ctx) return;

        function resize() {
            if (!canvas) return;
            canvas.width = canvas.offsetWidth * window.devicePixelRatio;
            canvas.height = canvas.offsetHeight * window.devicePixelRatio;
            ctx!.scale(window.devicePixelRatio, window.devicePixelRatio);
        }
        resize();
        window.addEventListener("resize", resize);

        // Create nodes
        const w = canvas.offsetWidth;
        const h = canvas.offsetHeight;
        const isMobile = w < 768;
        const count = Math.min(Math.floor((w * h) / (isMobile ? 18000 : 12000)), isMobile ? 30 : 60);
        const nodes: Node[] = [];
        for (let i = 0; i < count; i++) {
            const c = NODE_COLORS[i % NODE_COLORS.length];
            nodes.push({
                x: Math.random() * w,
                y: Math.random() * h,
                vx: (Math.random() - 0.5) * 0.4,
                vy: (Math.random() - 0.5) * 0.4,
                radius: Math.random() * 3 + 2,
                color: c.color,
                glowColor: c.glow,
                pulseSpeed: Math.random() * 0.02 + 0.01,
                pulsePhase: Math.random() * Math.PI * 2,
            });
        }
        nodesRef.current = nodes;

        const CONNECTION_DIST = isMobile ? 100 : 160;
        let time = 0;

        function draw() {
            if (!canvas || !ctx) return;
            const cw = canvas.offsetWidth;
            const ch = canvas.offsetHeight;
            ctx.clearRect(0, 0, cw, ch);
            time++;

            // Update positions
            for (const n of nodes) {
                n.x += n.vx;
                n.y += n.vy;
                if (n.x < 0 || n.x > cw) n.vx *= -1;
                if (n.y < 0 || n.y > ch) n.vy *= -1;
                n.x = Math.max(0, Math.min(cw, n.x));
                n.y = Math.max(0, Math.min(ch, n.y));
            }

            // Draw connections
            for (let i = 0; i < nodes.length; i++) {
                for (let j = i + 1; j < nodes.length; j++) {
                    const dx = nodes[i].x - nodes[j].x;
                    const dy = nodes[i].y - nodes[j].y;
                    const dist = Math.sqrt(dx * dx + dy * dy);
                    if (dist < CONNECTION_DIST) {
                        const alpha = (1 - dist / CONNECTION_DIST) * 0.15;
                        ctx.beginPath();
                        ctx.moveTo(nodes[i].x, nodes[i].y);
                        ctx.lineTo(nodes[j].x, nodes[j].y);
                        ctx.strokeStyle = `rgba(255,255,255,${alpha})`;
                        ctx.lineWidth = 0.5;
                        ctx.stroke();
                    }
                }
            }

            // Draw nodes
            for (const n of nodes) {
                const pulse = Math.sin(time * n.pulseSpeed + n.pulsePhase) * 0.5 + 0.5;
                const r = n.radius + pulse * 1.5;

                // Glow
                ctx.beginPath();
                ctx.arc(n.x, n.y, r * 3, 0, Math.PI * 2);
                ctx.fillStyle = n.glowColor.replace("0.4", String(0.1 + pulse * 0.1));
                ctx.fill();

                // Core
                ctx.beginPath();
                ctx.arc(n.x, n.y, r, 0, Math.PI * 2);
                ctx.fillStyle = n.color;
                ctx.fill();
            }

            animRef.current = requestAnimationFrame(draw);
        }

        draw();

        return () => {
            window.removeEventListener("resize", resize);
            cancelAnimationFrame(animRef.current);
        };
    }, []);

    return (
        <canvas
            ref={canvasRef}
            className="absolute inset-0 h-full w-full"
            style={{ opacity: 0.6 }}
        />
    );
}
