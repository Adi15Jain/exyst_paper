import re
from typing import List, Dict
from datetime import datetime

class AdvancedTextCleaner:
    def __init__(self):
        self.cleaning_patterns = [
            # Remove JSON artifacts
            (r"'prediction':\s*'[^']*'", ""),
            (r"'raw_output':\s*'[^']*'", ""),
            (r"'exception':\s*'[^']*'", ""),
            (r"\{[^}]*'prediction'[^}]*\}", ""),
            (r"Could not generate prediction", ""),
            
            # Remove markdown formatting
            (r'\*\*([^*]*)\*\*', r'\1'),  # Bold
            (r'\*([^*]*)\*', r'\1'),      # Italic
            (r'\\\\n', ' '),              # Double escaped newlines
            (r'\\n', ' '),                # Newlines
            (r'\\t', ' '),                # Tabs
            (r'\\"', '"'),                # Escaped quotes
            
            # Remove section artifacts
            (r'Section [A-C]:.*?(?=Q\d+|\n)', ''),
            (r'Answer any \d+ questions.*?(?=Q\d+|\n)', ''),
            (r'marks?\s*distribution.*?(?=Q\d+|\n)', '', re.IGNORECASE),
            
            # Clean question markers
            (r'Q\.?\s*(\d+)', r'Q\1.'),
            (r'\s+', ' '),  # Multiple spaces
        ]
    
    def deep_clean(self, text: str) -> str:
        """Apply all cleaning patterns"""
        cleaned = str(text)
        
        for pattern_data in self.cleaning_patterns:
            if len(pattern_data) == 3:
                pattern, replacement, flags = pattern_data
                cleaned = re.sub(pattern, replacement, cleaned, flags=flags)
            else:
                pattern, replacement = pattern_data
                cleaned = re.sub(pattern, replacement, cleaned)
        
        return cleaned.strip()
    
    def extract_questions_with_structure(self, text: str) -> List[Dict]:
        """Extract questions maintaining original paper structure"""
        
        cleaned_text = self.deep_clean(text)
        
        # Pattern for questions with parts and "Or" alternatives
        question_pattern = r'Q(\d+)\.\s*(.*?)(?=Q\d+\.|$)'
        questions = []
        
        for match in re.finditer(question_pattern, cleaned_text, re.DOTALL):
            q_num = int(match.group(1))
            q_content = match.group(2).strip()
            
            # Skip if content is too short or malformed
            if len(q_content) < 10 or q_content in ["Q", ""]:
                continue
            
            # Extract parts (a), (b), (c)
            parts = self.extract_question_parts(q_content)
            
            # Determine marks and type
            marks = self.extract_marks(q_content)
            question_type = self.determine_type_by_marks(marks)
            
            questions.append({
                "question_number": q_num,
                "content": self.clean_question_content(q_content),
                "parts": parts,
                "marks": marks,
                "type": question_type,
                "has_alternatives": "Or" in q_content
            })
        
        return questions
    
    def extract_question_parts(self, content: str) -> List[Dict]:
        """Extract sub-parts with alternatives"""
        parts = []
        
        # Split content by lines and process
        lines = content.split('\n')
        current_part = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check for part marker like a), b), c)
            part_match = re.match(r'([a-e])\)\s*(.*)', line)
            if part_match:
                # Save previous part if exists
                if current_part:
                    parts.append(current_part)
                
                current_part = {
                    "label": part_match.group(1),
                    "text": part_match.group(2).strip(),
                    "marks": self.extract_marks(line),
                    "alternative": None
                }
            
            # Check for "Or" alternative
            elif re.match(r'\s*Or\s*', line, re.IGNORECASE) and current_part:
                alt_text = re.sub(r'Or\s*', '', line, flags=re.IGNORECASE).strip()
                if alt_text:
                    current_part["alternative"] = alt_text
            
            # If we have a current part but no specific marker, append to text
            elif current_part and not re.match(r'[a-e]\)', line):
                current_part["text"] += " " + line
        
        # Add the last part
        if current_part:
            parts.append(current_part)
        
        return parts
    
    def extract_marks(self, text: str) -> int:
        """Extract marks from text"""
        # Look for patterns like (2 marks), [10 marks], **2**
        mark_patterns = [
            r'\((\d+)\s*marks?\)',
            r'\[(\d+)\s*marks?\]',
            r'\*\*(\d+)\*\*',
            r'(\d+)\s*marks?',
        ]
        
        for pattern in mark_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return int(match.group(1))
        
        # Default marks based on content length
        word_count = len(text.split())
        if word_count < 20:
            return 2
        elif word_count < 50:
            return 10
        else:
            return 20
    
    def determine_type_by_marks(self, marks: int) -> str:
        """Determine question type by marks"""
        if marks <= 4:
            return "short"
        elif marks <= 12:
            return "medium"
        else:
            return "long"
    
    def clean_question_content(self, content: str) -> str:
        """Clean individual question content"""
        # Remove marks indicators
        content = re.sub(r'\(\d+\s*marks?\)', '', content, flags=re.IGNORECASE)
        content = re.sub(r'\[\d+\s*marks?\]', '', content, flags=re.IGNORECASE)
        content = re.sub(r'\*\*\d+\*\*', '', content)
        
        # Clean up spacing
        content = re.sub(r'\s+', ' ', content)
        
        return content.strip()

class QuestionPaperValidator:
    def __init__(self):
        self.min_questions = 3
        self.max_questions = 15
    
    def validate_and_improve(self, questions: List[Dict], max_iterations: int = 2) -> List[Dict]:
        """Iteratively validate and improve question quality"""
        
        current_questions = questions
        
        for iteration in range(max_iterations):
            # Remove malformed questions
            current_questions = self.remove_malformed_questions(current_questions)
            
            # Fill missing questions if needed
            if len(current_questions) < self.min_questions:
                current_questions = self.add_fallback_questions(current_questions)
            
            # Limit questions if too many
            if len(current_questions) > self.max_questions:
                current_questions = current_questions[:self.max_questions]
            
            # Check quality
            if self.is_quality_acceptable(current_questions):
                break
        
        return current_questions
    
    def remove_malformed_questions(self, questions: List[Dict]) -> List[Dict]:
        """Remove questions with malformed content"""
        valid_questions = []
        
        for question in questions:
            content = str(question.get("content", ""))
            
            # Check for malformed indicators
            malformed_indicators = [
                "{'prediction':",
                "Could not generate prediction",
                "raw_output",
                "exception",
                len(content.strip()) < 5,
                content.strip() == "Q"
            ]
            
            if not any(indicator in content for indicator in malformed_indicators):
                valid_questions.append(question)
        
        return valid_questions
    
    def add_fallback_questions(self, questions: List[Dict]) -> List[Dict]:
        """Add fallback questions if we don't have enough"""
        fallback_questions = [
            {
                "question_number": len(questions) + 1,
                "content": "Define genetic algorithms and explain their basic components.",
                "parts": [],
                "marks": 10,
                "type": "medium",
                "has_alternatives": False
            },
            {
                "question_number": len(questions) + 2,
                "content": "Explain the role of selection operators in genetic algorithms with suitable examples.",
                "parts": [],
                "marks": 10,
                "type": "medium",
                "has_alternatives": False
            },
            {
                "question_number": len(questions) + 3,
                "content": "Compare genetic algorithms with other evolutionary computation techniques.",
                "parts": [],
                "marks": 20,
                "type": "long",
                "has_alternatives": False
            }
        ]
        
        needed = max(0, self.min_questions - len(questions))
        return questions + fallback_questions[:needed]
    
    def is_quality_acceptable(self, questions: List[Dict]) -> bool:
        """Check if overall quality is acceptable"""
        if len(questions) < self.min_questions:
            return False
        
        # Check if at least 70% of questions have meaningful content
        meaningful_count = sum(1 for q in questions if len(str(q.get("content", ""))) > 10)
        return meaningful_count / len(questions) >= 0.7

class ProfessionalQuestionPaperFormatter:
    def __init__(self):
        pass
    
    def format_question_paper(self, questions: List[Dict], metadata: Dict) -> Dict:
        """Format questions into professional paper structure"""
        
        formatted_questions = []
        
        for question in questions:
            if question.get("parts") and len(question["parts"]) > 0:
                # Multi-part question
                formatted_q = self.format_multipart_question(question)
            else:
                # Single question
                formatted_q = self.format_single_question(question)
            
            formatted_questions.append(formatted_q)
        
        return {
            "header": {
                "university": metadata.get("university", "TEERTHANKER MAHAVEER UNIVERSITY – MORADABAD"),
                "exam_title": f"B.Tech VI (Sixth) Semester Examination {datetime.now().year}-{datetime.now().year + 1}",
                "course_code": metadata.get("course_code", "EAI602"),
                "paper_id": self.generate_paper_id(),
                "subject": metadata.get("subject", "Genetic Algorithms"),
                "time": "3 Hours",
                "max_marks": "60",
                "note": "Attempt all questions."
            },
            "questions": formatted_questions,
            "total_questions": len(formatted_questions),
            "generated_at": datetime.now().isoformat(),
            "ai_generated": True,
            "formatting_success": True
        }
    
    def format_multipart_question(self, question: Dict) -> Dict:
        """Format questions with sub-parts (a), (b), (c)"""
        
        main_text = question["content"]
        if not main_text or len(main_text.strip()) < 5:
            main_text = "Answer the following:"
        
        formatted_parts = []
        
        for part in question["parts"]:
            part_text = f"{part['label']}) {part['text']}"
            
            if part["marks"]:
                part_text += f" ({part['marks']} marks)"
            
            if part.get("alternative"):
                part_text += f"\n       Or\n       {part['alternative']}"
                if part["marks"]:
                    part_text += f" ({part['marks']} marks)"
            
            formatted_parts.append({
                "label": part["label"],
                "text": part["text"],
                "marks": part["marks"],
                "alternative": part.get("alternative"),
                "formatted_text": part_text
            })
        
        return {
            "number": question["question_number"],
            "main_question": main_text,
            "parts": formatted_parts,
            "total_marks": question["marks"],
            "type": question["type"],
            "has_parts": True
        }
    
    def format_single_question(self, question: Dict) -> Dict:
        """Format single questions without parts"""
        
        main_text = question["content"]
        
        return {
            "number": question["question_number"],
            "main_question": main_text,
            "parts": [],
            "total_marks": question["marks"],
            "type": question["type"],
            "has_parts": False
        }
    
    def generate_paper_id(self) -> str:
        """Generate a paper ID matching the original format"""
        year = datetime.now().year
        return f"096{year % 100}{datetime.now().month:02d}26"
