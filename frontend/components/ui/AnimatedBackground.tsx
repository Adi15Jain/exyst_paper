import React from "react";

const AnimatedBackground: React.FC = () => {
    return (
        <div className="absolute inset-0 overflow-hidden">
            <div className="absolute -top-40 -right-40 w-96 h-96 bg-purple-500/20 rounded-full blur-3xl animate-pulse-glow"></div>
            <div
                className="absolute -bottom-32 -left-32 w-80 h-80 bg-pink-500/20 rounded-full blur-3xl animate-pulse-glow"
                style={{ animationDelay: "1s" }}
            ></div>
            <div
                className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-72 h-72 bg-cyan-500/10 rounded-full blur-3xl animate-pulse-glow"
                style={{ animationDelay: "2s" }}
            ></div>
        </div>
    );
};

export default AnimatedBackground;
