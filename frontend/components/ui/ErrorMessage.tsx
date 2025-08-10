import React from "react";

interface ErrorMessageProps {
    error: string | null;
}

const ErrorMessage: React.FC<ErrorMessageProps> = ({ error }) => {
    if (!error) return null;

    return (
        <div className="glass bg-red-500/20 border border-red-500/50 rounded-2xl p-6 animate-slide-in-left">
            <div className="flex items-start space-x-4">
                <div className="flex-shrink-0">
                    <svg
                        className="w-6 h-6 text-red-400"
                        fill="currentColor"
                        viewBox="0 0 20 20"
                    >
                        <path
                            fillRule="evenodd"
                            d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"
                            clipRule="evenodd"
                        />
                    </svg>
                </div>
                <div>
                    <h3 className="text-red-300 font-semibold">
                        Processing Error
                    </h3>
                    <p className="text-red-200 mt-1">{error}</p>
                </div>
            </div>
        </div>
    );
};

export default ErrorMessage;
