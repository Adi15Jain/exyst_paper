"use client";
import React, { useState } from "react";
import AnimatedBackground from "@/ui/AnimatedBackground";
import Header from "@/ui/Header";
import MainCard from "@/layout/MainCard";
import FileUpload from "@/ui/FileUpload";
import ErrorMessage from "@/ui/ErrorMessage";
import SubmitButton from "@/ui/SubmitButton";
import QuestionPaper from "@/ui/QuestionPaper";
import Footer from "@/ui/Footer";
import {
    QuestionPaperData,
    Section,
    Question,
    ApiError,
} from "@/types/prediction";

const Home: React.FC = () => {
    const [file, setFile] = useState<File | null>(null);
    const [questionPaper, setQuestionPaper] =
        useState<QuestionPaperData | null>(null);
    const [loading, setLoading] = useState<boolean>(false);
    const [dragActive, setDragActive] = useState<boolean>(false);
    const [error, setError] = useState<string | null>(null);

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>): void => {
        if (e.target.files) {
            setFile(e.target.files[0]);
            setError(null);
        }
    };

    const handleDrag = (e: React.DragEvent<HTMLDivElement>): void => {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === "dragenter" || e.type === "dragover") {
            setDragActive(true);
        } else if (e.type === "dragleave") {
            setDragActive(false);
        }
    };

    const handleDrop = (e: React.DragEvent<HTMLDivElement>): void => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(false);
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            setFile(e.dataTransfer.files[0]);
            setError(null);
        }
    };

    const handleSubmit = async (
        e: React.FormEvent<HTMLFormElement>
    ): Promise<void> => {
        e.preventDefault();
        if (!file) return;

        setLoading(true);
        setQuestionPaper(null);
        setError(null);

        const formData = new FormData();
        formData.append("file", file);

        try {
            // Single API call since backend now returns formatted data directly
            const response = await fetch(
                "http://localhost:8000/predict-question-paper/",
                {
                    method: "POST",
                    body: formData,
                }
            );

            if (!response.ok) {
                throw new Error(`Upload failed: ${response.status}`);
            }

            const paperData: QuestionPaperData | ApiError =
                await response.json();

            if ("error" in paperData) {
                throw new Error(paperData.error);
            }

            // Check if parsing was successful
            if (!paperData.parsing_success) {
                console.warn(
                    "Question paper parsing had issues:",
                    paperData.error_message
                );
            }

            setQuestionPaper(paperData);
        } catch (error) {
            console.error("Error:", error);
            setError(
                error instanceof Error
                    ? error.message
                    : "An unexpected error occurred"
            );
        } finally {
            setLoading(false);
        }
    };

    const handleDownloadPDF = (): void => {
        if (!questionPaper) return;

        // Create printable version with enhanced styling
        const printWindow = window.open("", "_blank");
        if (printWindow) {
            const { paper_info, sections } = questionPaper;

            printWindow.document.write(`
        <!DOCTYPE html>
        <html>
          <head>
            <title>${paper_info.title}</title>
            <meta charset="utf-8">
            <style>
              @page { 
                margin: 2cm; 
                size: A4;
              }
              * {
                box-sizing: border-box;
              }
              body { 
                font-family: 'Times New Roman', serif; 
                margin: 0;
                padding: 0;
                line-height: 1.6;
                color: #000;
                background: #fff;
              }
              .header { 
                text-align: center; 
                border-bottom: 3px solid #000; 
                padding-bottom: 1cm; 
                margin-bottom: 1cm;
              }
              .header h1 {
                font-size: 24px;
                margin: 0 0 0.5cm 0;
                font-weight: bold;
              }
              .header h2 {
                font-size: 20px;
                margin: 0 0 0.5cm 0;
                font-weight: normal;
              }
              .paper-info {
                display: flex;
                justify-content: space-between;
                margin: 0.5cm 0;
                font-size: 14px;
              }
              .paper-info span {
                font-weight: bold;
              }
              .instructions {
                margin: 1cm 0;
                page-break-inside: avoid;
              }
              .instructions h3 {
                font-size: 16px;
                margin: 0 0 0.5cm 0;
                font-weight: bold;
              }
              .instructions ol {
                margin: 0;
                padding-left: 1.5cm;
              }
              .instructions li {
                margin-bottom: 0.2cm;
              }
              .section { 
                margin: 1.5cm 0; 
                page-break-inside: avoid;
              }
              .section-header {
                background: #f8f8f8;
                padding: 0.5cm;
                font-weight: bold;
                margin-bottom: 0.5cm;
                border: 1px solid #ddd;
                font-size: 16px;
              }
              .section-description {
                font-size: 12px;
                font-weight: normal;
                margin-top: 0.2cm;
                color: #666;
              }
              .question { 
                margin: 0.8cm 0; 
                padding: 0.3cm 0 0.3cm 0.5cm; 
                border-left: 3px solid #333;
                page-break-inside: avoid;
                position: relative;
                min-height: 1.5cm;
              }
              .question-content {
                display: flex;
                justify-content: space-between;
                align-items: flex-start;
              }
              .question-text {
                flex: 1;
                padding-right: 1cm;
              }
              .marks {
                font-weight: bold;
                font-size: 12px;
                background: #f0f0f0;
                padding: 0.1cm 0.3cm;
                border: 1px solid #ccc;
                border-radius: 3px;
                white-space: nowrap;
              }
              .footer {
                text-align: center;
                margin-top: 2cm;
                font-size: 10px;
                color: #666;
                border-top: 1px solid #ddd;
                padding-top: 0.5cm;
              }
              @media print {
                body { font-size: 12pt; }
                .section { page-break-inside: avoid; }
                .question { page-break-inside: avoid; }
              }
            </style>
          </head>
          <body>
            <div class="header">
              <h1>${paper_info.title}</h1>
              <h2>${paper_info.subject}</h2>
              <div class="paper-info">
                <span>Academic Year: ${paper_info.academic_year}</span>
                <span>Duration: ${paper_info.duration}</span>
                <span>Max Marks: ${paper_info.max_marks}</span>
              </div>
              <p><strong>Date: ${paper_info.date}</strong></p>
            </div>
            
            <div class="instructions">
              <h3>Instructions:</h3>
              <ol>
                ${paper_info.instructions
                    .map((instruction) => `<li>${instruction}</li>`)
                    .join("")}
              </ol>
            </div>
            
            ${Object.entries(sections)
                .map(
                    ([sectionKey, section]: [string, Section]) => `
              <div class="section">
                <div class="section-header">
                  ${sectionKey}: ${section.title}
                  <div class="section-description">${section.description}</div>
                </div>
                ${section.questions
                    .map(
                        (question: Question) => `
                  <div class="question">
                    <div class="question-content">
                      <div class="question-text">
                        <strong>${question.question_number}.</strong> ${question.question_text}
                      </div>
                      <div class="marks">[${question.marks} marks]</div>
                    </div>
                  </div>
                `
                    )
                    .join("")}
              </div>
            `
                )
                .join("")}
            
            <div class="footer">
              <p>Generated by EXYST AI • ${new Date().toLocaleDateString()}</p>
              <p>This is an AI-generated question paper for practice purposes</p>
            </div>
          </body>
        </html>
      `);

            printWindow.document.close();

            // Wait for content to load before printing
            setTimeout(() => {
                printWindow.focus();
                printWindow.print();
            }, 500);
        }
    };

    const handleDownloadJSON = (): void => {
        if (!questionPaper) return;

        const dataStr = JSON.stringify(questionPaper, null, 2);
        const dataBlob = new Blob([dataStr], { type: "application/json" });
        const url = URL.createObjectURL(dataBlob);
        const link = document.createElement("a");
        link.href = url;
        link.download = `exyst_question_paper_${new Date().getTime()}.json`;
        link.click();
        URL.revokeObjectURL(url);
    };

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 relative">
            <AnimatedBackground />

            <div className="relative z-10 flex flex-col items-center justify-center min-h-screen px-4 py-8">
                <Header />

                <MainCard>
                    <form onSubmit={handleSubmit} className="space-y-8">
                        <FileUpload
                            file={file}
                            dragActive={dragActive}
                            onFileChange={handleFileChange}
                            onDrag={handleDrag}
                            onDrop={handleDrop}
                        />

                        <ErrorMessage error={error} />

                        <SubmitButton
                            loading={loading}
                            disabled={loading || !file}
                        />
                    </form>

                    {questionPaper && (
                        <QuestionPaper
                            paperData={questionPaper}
                            onDownloadPDF={handleDownloadPDF}
                            onDownloadJSON={handleDownloadJSON}
                        />
                    )}
                </MainCard>

                <Footer />
            </div>
        </div>
    );
};

export default Home;
