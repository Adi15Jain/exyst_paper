import React from "react";

// Define all necessary interfaces within this file
interface Question {
    question_number: number;
    question_text: string;
    marks: number;
    type: string;
}

interface Section {
    title: string;
    description: string;
    questions: Question[];
}

interface PaperInfo {
    title: string;
    academic_year: string;
    subject: string;
    duration: string;
    max_marks: string;
    date: string;
    instructions: string[];
}

interface QuestionPaperData {
    paper_info: PaperInfo;
    sections: Record<string, Section>;
    total_questions: number;
    generated_at: string;
    ai_generated: boolean;
    raw_prediction?: any;
    formatting_error?: string;
    parsing_success?: boolean;
}

// Define the props interface
interface QuestionPaperProps {
    paperData: QuestionPaperData;
    onDownloadPDF: () => void;
    onDownloadJSON: () => void;
}

const QuestionPaper: React.FC<QuestionPaperProps> = ({
    paperData,
    onDownloadPDF,
    onDownloadJSON,
}) => {
    const { paper_info, sections } = paperData;

    // Check if we have valid sections
    const hasValidSections = sections && Object.keys(sections).length > 0;
    const hasQuestions =
        hasValidSections &&
        Object.values(sections).some(
            (section) => section.questions?.length > 0
        );

    if (!hasQuestions) {
        return (
            <div className="mt-16 animate-fade-in">
                <div className="glass-strong rounded-3xl p-8 border border-red-500/50">
                    <div className="text-center">
                        <div className="w-12 h-12 bg-red-500 rounded-full flex items-center justify-center mx-auto mb-4">
                            <svg
                                className="w-6 h-6 text-white"
                                fill="none"
                                viewBox="0 0 24 24"
                                stroke="currentColor"
                            >
                                <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    strokeWidth={2}
                                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.96-.833-2.73 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z"
                                />
                            </svg>
                        </div>
                        <h3 className="text-xl font-bold text-red-400 mb-2">
                            Question Paper Generation Failed
                        </h3>
                        <p className="text-gray-300">
                            Unable to generate a properly formatted question
                            paper. This might be due to:
                        </p>
                        <ul className="text-left text-gray-400 mt-4 space-y-2">
                            <li>
                                • Complex or unstructured content in the
                                uploaded PDF
                            </li>
                            <li>• LLM response formatting issues</li>
                            <li>• Insufficient question content to parse</li>
                        </ul>
                        <button
                            onClick={() => window.location.reload()}
                            className="mt-6 bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg transition-colors duration-200"
                        >
                            Try Again
                        </button>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="mt-16 animate-fade-in">
            <div className="glass-strong rounded-3xl p-8 border border-white/30">
                {/* Header with Download Options */}
                <div className="flex items-center justify-between mb-8">
                    <div className="flex items-center space-x-4">
                        <div className="w-12 h-12 bg-gradient-to-r from-green-400 to-emerald-500 rounded-full flex items-center justify-center animate-pulse-glow">
                            <svg
                                className="w-6 h-6 text-white"
                                fill="none"
                                viewBox="0 0 24 24"
                                stroke="currentColor"
                            >
                                <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    strokeWidth={2}
                                    d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                                />
                            </svg>
                        </div>
                        <div>
                            <h2 className="text-3xl font-bold text-gradient-cyan">
                                Generated Question Paper
                            </h2>
                            <p className="text-gray-400 mt-1">
                                AI-generated examination paper ready for use
                            </p>
                        </div>
                    </div>

                    <div className="flex space-x-3">
                        <button
                            onClick={onDownloadPDF}
                            className="glass bg-blue-600/80 hover:bg-blue-700/80 text-white rounded-xl px-4 py-2 font-semibold transition-all duration-200 btn-hover-lift flex items-center space-x-2"
                        >
                            <svg
                                className="w-4 h-4"
                                fill="none"
                                viewBox="0 0 24 24"
                                stroke="currentColor"
                            >
                                <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    strokeWidth={2}
                                    d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                                />
                            </svg>
                            <span>PDF</span>
                        </button>
                        <button
                            onClick={onDownloadJSON}
                            className="glass bg-indigo-600/80 hover:bg-indigo-700/80 text-white rounded-xl px-4 py-2 font-semibold transition-all duration-200 btn-hover-lift flex items-center space-x-2"
                        >
                            <svg
                                className="w-4 h-4"
                                fill="none"
                                viewBox="0 0 24 24"
                                stroke="currentColor"
                            >
                                <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    strokeWidth={2}
                                    d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                                />
                            </svg>
                            <span>JSON</span>
                        </button>
                    </div>
                </div>

                {/* Question Paper Content */}
                <div className="bg-white text-black rounded-2xl p-8 shadow-2xl font-serif max-h-96 overflow-y-auto custom-scroll">
                    {/* Paper Header */}
                    <div className="text-center border-b-2 border-gray-800 pb-6 mb-6">
                        <h1 className="text-2xl font-bold mb-2">
                            {paper_info.title}
                        </h1>
                        <h2 className="text-xl font-semibold mb-2">
                            {paper_info.subject}
                        </h2>
                        <div className="flex justify-between items-center text-sm">
                            <span>
                                <strong>Academic Year:</strong>{" "}
                                {paper_info.academic_year}
                            </span>
                            <span>
                                <strong>Duration:</strong> {paper_info.duration}
                            </span>
                            <span>
                                <strong>Max Marks:</strong>{" "}
                                {paper_info.max_marks}
                            </span>
                        </div>
                        <p className="text-sm mt-2">
                            <strong>Date:</strong> {paper_info.date}
                        </p>
                    </div>

                    {/* Instructions */}
                    <div className="mb-6">
                        <h3 className="text-lg font-bold mb-3">
                            Instructions:
                        </h3>
                        <ol className="list-decimal list-inside space-y-1 text-sm">
                            {paper_info.instructions.map(
                                (instruction, index) => (
                                    <li key={index}>{instruction}</li>
                                )
                            )}
                        </ol>
                    </div>

                    {/* Sections */}
                    {Object.entries(sections).map(
                        ([sectionKey, section]: [string, Section]) => (
                            <div key={sectionKey} className="mb-8">
                                <div className="bg-gray-100 p-3 rounded-lg mb-4">
                                    <h3 className="text-xl font-bold">
                                        {sectionKey}: {section.title}
                                    </h3>
                                    <p className="text-sm text-gray-600 mt-1">
                                        {section.description}
                                    </p>
                                </div>

                                <div className="space-y-4">
                                    {section.questions.map(
                                        (question: Question) => (
                                            <div
                                                key={question.question_number}
                                                className="border-l-4 border-blue-500 pl-4"
                                            >
                                                <div className="flex justify-between items-start">
                                                    <div className="flex-1">
                                                        <span className="font-bold">
                                                            {
                                                                question.question_number
                                                            }
                                                            .{" "}
                                                        </span>
                                                        <span className="text-gray-800">
                                                            {
                                                                question.question_text
                                                            }
                                                        </span>
                                                    </div>
                                                    <span className="ml-4 text-sm font-semibold bg-blue-100 px-2 py-1 rounded">
                                                        [{question.marks} marks]
                                                    </span>
                                                </div>
                                            </div>
                                        )
                                    )}
                                </div>
                            </div>
                        )
                    )}

                    {/* Footer */}
                    <div className="mt-8 pt-4 border-t border-gray-300 text-center text-xs text-gray-500">
                        <p>
                            Generated by EXYST AI •{" "}
                            {new Date().toLocaleDateString()}
                        </p>
                        <p className="mt-1">
                            This is an AI-generated question paper for practice
                            purposes
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default QuestionPaper;
