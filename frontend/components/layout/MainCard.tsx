import React, { ReactNode } from "react";

interface MainCardProps {
    children: ReactNode;
}

const MainCard: React.FC<MainCardProps> = ({ children }) => {
    return (
        <div className="w-full max-w-5xl glass-strong rounded-3xl shadow-2xl p-8 md:p-12 animate-scale-in card-hover">
            {children}
        </div>
    );
};

export default MainCard;
