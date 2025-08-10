import React from "react";

const Header: React.FC = () => {
    return (
        <div className="text-center mb-12 animate-fade-in">
            <h1 className="text-6xl md:text-8xl font-black text-gradient-purple mb-6 tracking-tight">
                EXYST
            </h1>
            <p className="text-xl md:text-2xl text-gray-300 font-light mb-4 animate-slide-in-left">
                AI-Powered Exam Paper Predictor
            </p>
            <p className="text-sm text-gray-400 max-w-md mx-auto animate-slide-in-right">
                Upload your combined exam papers and syllabus to get intelligent
                predictions for your next exam
            </p>
            <div className="w-32 h-1 bg-gradient-to-r from-purple-400 via-pink-400 to-cyan-400 mx-auto mt-6 rounded-full animate-shimmer"></div>
        </div>
    );
};

export default Header;
