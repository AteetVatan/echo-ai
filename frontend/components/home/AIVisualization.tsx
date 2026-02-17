"use client";

export function AIVisualization() {
    return (
        <div className="relative flex items-center justify-center">
            {/* Outer glow ring */}
            <div className="absolute h-72 w-72 rounded-full sm:h-80 sm:w-80 lg:h-96 lg:w-96"
                style={{
                    background: "radial-gradient(circle, rgba(59,130,246,0.15) 0%, rgba(96,165,250,0.05) 50%, transparent 70%)",
                    animation: "pulse-glow 4s ease-in-out infinite",
                }}
            />

            {/* Mid glow */}
            <div className="absolute h-56 w-56 rounded-full sm:h-64 sm:w-64 lg:h-72 lg:w-72"
                style={{
                    background: "radial-gradient(circle, rgba(59,130,246,0.2) 0%, transparent 70%)",
                    animation: "pulse-glow 3s ease-in-out infinite 0.5s",
                }}
            />

            {/* AI Head SVG */}
            <div className="relative z-10 animate-breathe" style={{ filter: "drop-shadow(0 0 30px rgba(59,130,246,0.3))" }}>
                <svg viewBox="0 0 200 240" className="h-56 w-56 sm:h-64 sm:w-64 lg:h-80 lg:w-80" fill="none" xmlns="http://www.w3.org/2000/svg">
                    {/* Wireframe head mesh */}
                    <defs>
                        <linearGradient id="headGrad" x1="0" y1="0" x2="200" y2="240" gradientUnits="userSpaceOnUse">
                            <stop offset="0%" stopColor="#3b82f6" stopOpacity="0.8" />
                            <stop offset="50%" stopColor="#60a5fa" stopOpacity="0.5" />
                            <stop offset="100%" stopColor="#00cec9" stopOpacity="0.3" />
                        </linearGradient>
                        <linearGradient id="brainGrad" x1="60" y1="30" x2="140" y2="120" gradientUnits="userSpaceOnUse">
                            <stop offset="0%" stopColor="#ff6b6b" stopOpacity="0.9" />
                            <stop offset="100%" stopColor="#3b82f6" stopOpacity="0.4" />
                        </linearGradient>
                    </defs>

                    {/* Head outline - wireframe style */}
                    <path d="M100 20 C55 20, 30 60, 30 100 C30 130, 35 150, 50 170 L60 190 L70 210 L130 210 L140 190 L150 170 C165 150, 170 130, 170 100 C170 60, 145 20, 100 20Z"
                        stroke="url(#headGrad)" strokeWidth="1" fill="none" opacity="0.7" />

                    {/* Inner wireframe lines - horizontal */}
                    <path d="M40 65 Q100 55, 160 65" stroke="url(#headGrad)" strokeWidth="0.5" fill="none" opacity="0.3" />
                    <path d="M35 85 Q100 75, 165 85" stroke="url(#headGrad)" strokeWidth="0.5" fill="none" opacity="0.4" />
                    <path d="M33 105 Q100 95, 167 105" stroke="url(#headGrad)" strokeWidth="0.5" fill="none" opacity="0.3" />
                    <path d="M35 125 Q100 115, 165 125" stroke="url(#headGrad)" strokeWidth="0.5" fill="none" opacity="0.4" />
                    <path d="M40 145 Q100 135, 160 145" stroke="url(#headGrad)" strokeWidth="0.5" fill="none" opacity="0.3" />
                    <path d="M50 165 Q100 158, 150 165" stroke="url(#headGrad)" strokeWidth="0.5" fill="none" opacity="0.3" />

                    {/* Vertical wireframe */}
                    <path d="M70 25 Q65 120, 65 200" stroke="url(#headGrad)" strokeWidth="0.5" fill="none" opacity="0.3" />
                    <path d="M100 18 Q100 120, 100 210" stroke="url(#headGrad)" strokeWidth="0.5" fill="none" opacity="0.4" />
                    <path d="M130 25 Q135 120, 135 200" stroke="url(#headGrad)" strokeWidth="0.5" fill="none" opacity="0.3" />

                    {/* Brain area */}
                    <path d="M65 50 C75 35, 90 30, 100 32 C110 30, 125 35, 135 50 C145 65, 148 80, 145 95 C142 110, 130 120, 100 122 C70 120, 58 110, 55 95 C52 80, 55 65, 65 50Z"
                        stroke="url(#brainGrad)" strokeWidth="1.5" fill="none" opacity="0.6" />

                    {/* Brain folds */}
                    <path d="M75 55 Q100 48, 125 55" stroke="#ff6b6b" strokeWidth="0.8" fill="none" opacity="0.5" />
                    <path d="M70 70 Q90 60, 100 65 Q110 60, 130 70" stroke="#ff6b6b" strokeWidth="0.8" fill="none" opacity="0.4" />
                    <path d="M68 85 Q85 78, 100 82 Q115 78, 132 85" stroke="#60a5fa" strokeWidth="0.8" fill="none" opacity="0.4" />
                    <path d="M70 100 Q100 90, 130 100" stroke="#60a5fa" strokeWidth="0.8" fill="none" opacity="0.3" />

                    {/* Eye areas */}
                    <ellipse cx="78" cy="110" rx="10" ry="5" stroke="url(#headGrad)" strokeWidth="0.8" fill="none" opacity="0.5" />
                    <ellipse cx="122" cy="110" rx="10" ry="5" stroke="url(#headGrad)" strokeWidth="0.8" fill="none" opacity="0.5" />

                    {/* Neural glow dots */}
                    <circle cx="100" cy="45" r="2.5" fill="#ff6b6b" opacity="0.9">
                        <animate attributeName="opacity" values="0.4;1;0.4" dur="2s" repeatCount="indefinite" />
                    </circle>
                    <circle cx="75" cy="60" r="2" fill="#fdcb6e" opacity="0.8">
                        <animate attributeName="opacity" values="0.3;0.9;0.3" dur="2.5s" repeatCount="indefinite" />
                    </circle>
                    <circle cx="125" cy="60" r="2" fill="#55efc4" opacity="0.8">
                        <animate attributeName="opacity" values="0.3;0.9;0.3" dur="3s" repeatCount="indefinite" />
                    </circle>
                    <circle cx="65" cy="80" r="1.5" fill="#a29bfe" opacity="0.7">
                        <animate attributeName="opacity" values="0.3;0.8;0.3" dur="2.2s" repeatCount="indefinite" />
                    </circle>
                    <circle cx="135" cy="80" r="1.5" fill="#00cec9" opacity="0.7">
                        <animate attributeName="opacity" values="0.3;0.8;0.3" dur="2.8s" repeatCount="indefinite" />
                    </circle>
                    <circle cx="100" cy="95" r="2" fill="#60a5fa" opacity="0.8">
                        <animate attributeName="opacity" values="0.4;1;0.4" dur="2.3s" repeatCount="indefinite" />
                    </circle>

                    {/* Particle scatter */}
                    <circle cx="155" cy="40" r="1" fill="#ff6b6b" opacity="0.6">
                        <animate attributeName="opacity" values="0;0.8;0" dur="3s" repeatCount="indefinite" />
                    </circle>
                    <circle cx="170" cy="60" r="1.2" fill="#3b82f6" opacity="0.5">
                        <animate attributeName="opacity" values="0;0.7;0" dur="2.5s" repeatCount="indefinite" begin="0.5s" />
                    </circle>
                    <circle cx="180" cy="85" r="0.8" fill="#60a5fa" opacity="0.5">
                        <animate attributeName="opacity" values="0;0.6;0" dur="4s" repeatCount="indefinite" begin="1s" />
                    </circle>
                    <circle cx="25" cy="55" r="1" fill="#55efc4" opacity="0.5">
                        <animate attributeName="opacity" values="0;0.7;0" dur="3.5s" repeatCount="indefinite" begin="0.3s" />
                    </circle>
                    <circle cx="15" cy="90" r="0.8" fill="#a29bfe" opacity="0.4">
                        <animate attributeName="opacity" values="0;0.6;0" dur="3s" repeatCount="indefinite" begin="1.5s" />
                    </circle>
                </svg>
            </div>

            {/* Floating particles around the head */}
            <div className="absolute h-full w-full">
                <div className="neural-dot animate-drift" style={{ top: "10%", right: "5%", width: 4, height: 4, background: "#ff6b6b", animationDelay: "0s", animationDuration: "15s" }} />
                <div className="neural-dot animate-drift" style={{ top: "25%", right: "0%", width: 3, height: 3, background: "#3b82f6", animationDelay: "2s", animationDuration: "18s" }} />
                <div className="neural-dot animate-drift" style={{ top: "60%", right: "8%", width: 5, height: 5, background: "#60a5fa", animationDelay: "4s", animationDuration: "20s" }} />
                <div className="neural-dot animate-drift" style={{ top: "80%", left: "10%", width: 3, height: 3, background: "#00cec9", animationDelay: "1s", animationDuration: "16s" }} />
                <div className="neural-dot animate-drift" style={{ top: "15%", left: "5%", width: 4, height: 4, background: "#fdcb6e", animationDelay: "3s", animationDuration: "22s" }} />
            </div>
        </div>
    );
}
