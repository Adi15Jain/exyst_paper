import React from "react";

interface FileUploadProps {
    file: File | null;
    dragActive: boolean;
    onFileChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
    onDrag: (e: React.DragEvent<HTMLDivElement>) => void;
    onDrop: (e: React.DragEvent<HTMLDivElement>) => void;
}

const FileUpload: React.FC<FileUploadProps> = ({
    file,
    dragActive,
    onFileChange,
    onDrag,
    onDrop,
}) => {
    return (
        <div
            className={`relative border-2 border-dashed rounded-3xl p-12 transition-all duration-500 transform ${
                dragActive
                    ? "border-purple-400 bg-purple-400/20 scale-105 shadow-lg shadow-purple-500/25"
                    : "border-gray-400/40 hover:border-purple-400/80 bg-white/5 hover:bg-white/10"
            }`}
            onDragEnter={onDrag}
            onDragLeave={onDrag}
            onDragOver={onDrag}
            onDrop={onDrop}
        >
            <input
                type="file"
                accept=".pdf"
                onChange={onFileChange}
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
                required
            />

            <div className="text-center relative z-5">
                <div
                    className={`mx-auto flex items-center justify-center h-20 w-20 rounded-full bg-gradient-to-r from-purple-500 to-pink-500 mb-6 transition-all duration-300 ${
                        dragActive
                            ? "animate-pulse scale-110"
                            : "hover:scale-110"
                    }`}
                >
                    <svg
                        className="h-10 w-10 text-white"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                    >
                        <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                        />
                    </svg>
                </div>

                {file ? (
                    <div className="space-y-3 animate-fade-in">
                        <div className="glass rounded-2xl p-4 border border-green-500/50">
                            <div className="flex items-center justify-center space-x-3">
                                <div className="w-3 h-3 bg-green-400 rounded-full animate-pulse"></div>
                                <p className="text-lg font-semibold text-white">
                                    {file.name}
                                </p>
                            </div>
                            <p className="text-sm text-green-300 mt-2">
                                Ready to process your PDF
                            </p>
                        </div>
                    </div>
                ) : (
                    <div className="space-y-4">
                        <p className="text-2xl font-bold text-white mb-2">
                            Drop your PDF here, or{" "}
                            <span className="text-gradient-purple">browse</span>
                        </p>
                        <p className="text-gray-400 text-lg">
                            Combined exam papers and syllabus PDF
                        </p>
                        <div className="flex items-center justify-center space-x-4 text-sm text-gray-500 mt-4">
                            <span className="flex items-center space-x-1">
                                <svg
                                    className="w-4 h-4"
                                    fill="currentColor"
                                    viewBox="0 0 20 20"
                                >
                                    <path
                                        fillRule="evenodd"
                                        d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z"
                                        clipRule="evenodd"
                                    />
                                </svg>
                                <span>PDF Only</span>
                            </span>
                            <span>•</span>
                            <span>Max 50MB</span>
                            <span>•</span>
                            <span>Secure Processing</span>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default FileUpload;
