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
    error_message?: string;
}

interface ApiError {
    error: string;
}

export type { Question, Section, PaperInfo, QuestionPaperData, ApiError };
