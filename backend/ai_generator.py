"""
AI-powered question generation module
Generates multiple-choice questions from PDF content using AI
"""
import json
import logging
from typing import List, Dict
import openai
from openai import OpenAI

from config import AI_API_KEY, AI_MODEL, AI_TEMPERATURE, AI_MAX_TOKENS, ANSWERS_PER_QUESTION
from models import Question, Answer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AIQuestionGenerator:
    """
    Generates exam questions using AI based on PDF content
    """
    
    def __init__(self, api_key: str = AI_API_KEY):
        """
        Initialize AI generator
        
        Args:
            api_key: OpenAI API key (or other AI provider)
        """
        if not api_key:
            raise ValueError("AI API key not provided. Set OPENAI_API_KEY environment variable.")
        
        self.client = OpenAI(api_key=api_key)
        self.model = AI_MODEL
    
    def generate_questions(
        self,
        content: Dict[int, str],
        num_questions: int,
        difficulty: str = "medium"
    ) -> List[Question]:
        """
        Generate multiple-choice questions from PDF content
        
        Args:
            content: Dictionary mapping page numbers to text content
            num_questions: Number of questions to generate
            difficulty: Question difficulty (easy, medium, hard)
            
        Returns:
            List of Question objects
        """
        logger.info(f"Generating {num_questions} questions with {difficulty} difficulty")
        
        # Prepare content summary for AI
        content_summary = self._prepare_content_summary(content)
        
        # Create prompt
        prompt = self._create_generation_prompt(
            content_summary,
            num_questions,
            difficulty
        )
        
        try:
            # Call AI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert educator creating high-quality exam questions. Generate clear, unambiguous questions with exactly 4 answer choices."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=AI_TEMPERATURE,
                max_tokens=AI_MAX_TOKENS,
                response_format={ "type": "json_object" }
            )
            
            # Parse response
            result = json.loads(response.choices[0].message.content)
            questions = self._parse_ai_response(result, content)
            
            logger.info(f"Successfully generated {len(questions)} questions")
            return questions
            
        except Exception as e:
            logger.error(f"AI generation failed: {str(e)}")
            raise
    
    def _prepare_content_summary(self, content: Dict[int, str], max_length: int = 4000) -> str:
        """
        Prepare a summarized version of content for AI processing
        
        Args:
            content: Page-wise content dictionary
            max_length: Maximum characters to include
            
        Returns:
            Formatted content string
        """
        sections = []
        current_length = 0
        
        for page_num, text in sorted(content.items()):
            if not text.strip():
                continue
            
            # Add page marker
            section = f"\n--- Page {page_num} ---\n{text}"
            
            if current_length + len(section) > max_length:
                # Truncate if too long
                remaining = max_length - current_length
                if remaining > 100:
                    sections.append(section[:remaining] + "...")
                break
            
            sections.append(section)
            current_length += len(section)
        
        return '\n'.join(sections)
    
    def _create_generation_prompt(
        self,
        content: str,
        num_questions: int,
        difficulty: str
    ) -> str:
        """
        Create the prompt for AI question generation
        
        Args:
            content: PDF content text
            num_questions: Number of questions to generate
            difficulty: Question difficulty level
            
        Returns:
            Formatted prompt string
        """
        prompt = f"""Based on the following academic content, generate {num_questions} multiple-choice questions.

CONTENT:
{content}

REQUIREMENTS:
1. Generate exactly {num_questions} questions
2. Each question must have exactly {ANSWERS_PER_QUESTION} answer choices
3. Only ONE answer should be correct
4. Questions should be {difficulty} difficulty
5. Include a clear justification for the correct answer
6. Cite the specific page and section/topic from the source material
7. Ensure questions test understanding, not just memorization
8. Avoid ambiguous or trick questions

OUTPUT FORMAT (JSON):
{{
  "questions": [
    {{
      "question_text": "The actual question text?",
      "answers": [
        {{"text": "Answer option 1", "is_correct": false}},
        {{"text": "Answer option 2", "is_correct": true}},
        {{"text": "Answer option 3", "is_correct": false}},
        {{"text": "Answer option 4", "is_correct": false}}
      ],
      "justification": "Explanation of why the correct answer is correct",
      "source_page": 1,
      "source_section": "Introduction to Topic"
    }}
  ]
}}

Generate the questions now:"""
        
        return prompt
    
    def _parse_ai_response(self, ai_result: Dict, original_content: Dict[int, str]) -> List[Question]:
        """
        Parse AI response into Question objects
        
        Args:
            ai_result: JSON response from AI
            original_content: Original PDF content for validation
            
        Returns:
            List of Question objects
        """
        questions = []
        
        for idx, q_data in enumerate(ai_result.get('questions', [])):
            try:
                # Parse answers
                answers = []
                for ans_data in q_data.get('answers', []):
                    answers.append(Answer(
                        text=ans_data.get('text', ''),
                        is_correct=ans_data.get('is_correct', False)
                    ))
                
                # Validate: exactly 4 answers, exactly 1 correct
                if len(answers) != ANSWERS_PER_QUESTION:
                    logger.warning(f"Question {idx + 1}: Invalid number of answers ({len(answers)}), skipping")
                    continue
                
                correct_count = sum(1 for ans in answers if ans.is_correct)
                if correct_count != 1:
                    logger.warning(f"Question {idx + 1}: Invalid number of correct answers ({correct_count}), skipping")
                    continue
                
                # Create question object
                question = Question(
                    question_text=q_data.get('question_text', ''),
                    answers=answers,
                    justification=q_data.get('justification', ''),
                    source_page=q_data.get('source_page', 1),
                    source_section=q_data.get('source_section', '')
                )
                
                questions.append(question)
                
            except Exception as e:
                logger.error(f"Failed to parse question {idx + 1}: {str(e)}")
                continue
        
        return questions
    
    def regenerate_question(
        self,
        old_question: Question,
        content: Dict[int, str],
        feedback: str = ""
    ) -> Question:
        """
        Regenerate a single question with optional feedback
        
        Args:
            old_question: The question to regenerate
            content: PDF content
            feedback: Optional feedback on what to improve
            
        Returns:
            New Question object
        """
        prompt = f"""Regenerate this question with improvements:

ORIGINAL QUESTION:
{old_question.question_text}

ORIGINAL ANSWERS:
{chr(10).join(f"{i+1}. {ans.text} {'(CORRECT)' if ans.is_correct else ''}" for i, ans in enumerate(old_question.answers))}

FEEDBACK: {feedback if feedback else "Make it clearer and more challenging"}

SOURCE CONTENT (Page {old_question.source_page}):
{content.get(old_question.source_page, '')}

Generate an improved version in JSON format as specified earlier."""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert educator improving exam questions."},
                    {"role": "user", "content": prompt}
                ],
                temperature=AI_TEMPERATURE,
                response_format={ "type": "json_object" }
            )
            
            result = json.loads(response.choices[0].message.content)
            questions = self._parse_ai_response(result, content)
            
            return questions[0] if questions else old_question
            
        except Exception as e:
            logger.error(f"Question regeneration failed: {str(e)}")
            return old_question


# Example usage
if __name__ == "__main__":
    # Test with sample content
    sample_content = {
        1: "Machine learning is a subset of artificial intelligence that focuses on building systems that learn from data.",
        2: "Supervised learning uses labeled data to train models, while unsupervised learning finds patterns in unlabeled data."
    }
    
    try:
        generator = AIQuestionGenerator()
        questions = generator.generate_questions(sample_content, num_questions=2)
        
        for i, q in enumerate(questions):
            print(f"\nQuestion {i + 1}:")
            print(q.to_dict())
    except Exception as e:
        print(f"Error: {e}")
