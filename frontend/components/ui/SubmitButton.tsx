import React from "react";

interface SubmitButtonProps {
    loading: boolean;
    disabled: boolean;
}

const SubmitButton: React.FC<SubmitButtonProps> = ({ loading, disabled }) => {
    return (
        <button
            type="submit"
            disabled={disabled}
            className={`w-full py-6 px-8 rounded-2xl font-bold text-xl transition-all duration-300 transform btn-hover-lift ${
                disabled
                    ? "bg-gray-600/50 text-gray-400 cursor-not-allowed backdrop-blur-sm"
                    : "bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white shadow-lg hover:shadow-purple-500/40 animate-pulse-glow"
            }`}
        >
            {loading ? (
                <div className="flex items-center justify-center space-x-3">
                    <div className="spinner w-6 h-6"></div>
                    <span>Analyzing and Predicting...</span>
                    <div className="flex space-x-1">
                        <div className="w-2 h-2 bg-white rounded-full animate-bounce"></div>
                        <div
                            className="w-2 h-2 bg-white rounded-full animate-bounce"
                            style={{ animationDelay: "0.1s" }}
                        ></div>
                        <div
                            className="w-2 h-2 bg-white rounded-full animate-bounce"
                            style={{ animationDelay: "0.2s" }}
                        ></div>
                    </div>
                </div>
            ) : (
                <div className="flex items-center justify-center space-x-3">
                    <svg
                        className="w-6 h-6"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                    >
                        <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M13 10V3L4 14h7v7l9-11h-7z"
                        />
                    </svg>
                    <span>Generate Question Paper Prediction</span>
                    <svg
                        className="w-6 h-6"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                    >
                        <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M13 10V3L4 14h7v7l9-11h-7z"
                        />
                    </svg>
                </div>
            )}
        </button>
    );
};

export default SubmitButton;
