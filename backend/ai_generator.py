"""
AI-powered question generation and evaluation module
Supports Google Gemini, OpenAI, and intelligent Offline Demo mode
Generates multiple-choice, true/false, short answer, and essay questions
Includes single-question regeneration and AI rubric-based grading
"""
import json
import logging
import os
import re
import time
import urllib.request
import urllib.error
from typing import List, Dict, Any, Optional, Union, Tuple

from config import AI_API_KEY, AI_MODEL, AI_TEMPERATURE, AI_MAX_TOKENS
from models import Question, Answer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AIQuestionGenerator:
    """
    Multi-provider AI question generator and evaluator
    """
    
    def __init__(
        self,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None
    ):
        """
        Initialize AI generator with specific provider and credentials
        
        Args:
            provider: 'gemini', 'openai', or 'demo'
            api_key: API key for chosen provider
            model: Model name (e.g. 'gemini-1.5-flash', 'gpt-4o-mini')
            base_url: Custom base URL for OpenAI-compatible endpoints
        """
        # Determine provider
        env_openai_key = os.getenv('OPENAI_API_KEY', '')
        env_gemini_key = os.getenv('GEMINI_API_KEY', '')
        
        self.api_key = api_key or env_gemini_key or env_openai_key or AI_API_KEY
        
        if provider:
            self.provider = provider.lower()
        elif env_gemini_key:
            self.provider = 'gemini'
        elif env_openai_key:
            self.provider = 'openai'
        elif self.api_key and self.api_key.startswith('AIza'):
            self.provider = 'gemini'
        elif self.api_key and self.api_key.startswith('sk-'):
            self.provider = 'openai'
        else:
            self.provider = 'demo'
            
        self.base_url = base_url
        
        if model:
            self.model = model
        elif self.provider == 'gemini':
            self.model = 'gemini-1.5-flash'
        elif self.provider == 'openai':
            self.model = AI_MODEL or 'gpt-4o-mini'
        else:
            self.model = 'demo-engine'
            
        logger.info(f"Initialized AIQuestionGenerator with provider='{self.provider}', model='{self.model}'")

    def generate_questions(
        self,
        content: Union[Dict[int, str], str],
        question_config: Dict[str, int],
        difficulty: str = "medium",
        target_audience: str = "General",
        source_type: str = "pdf",
        subject: str = "General",
        language: str = "English"
    ) -> List[Question]:
        """
        Generate questions across requested types based on source content
        
        Args:
            content: Dict of page -> text, or string of raw text/topic
            question_config: Dict like {'mcq': 5, 'true_false': 3, 'short_answer': 2, 'essay': 1, 'fill_blank': 2}
            difficulty: 'easy' | 'medium' | 'hard' | 'mixed'
            target_audience: Target level
            source_type: 'pdf' | 'text' | 'topic' | 'url'
            subject: Academic subject domain
            language: Target exam language
        """
        # Normalize text content
        text_context, page_refs = self._normalize_content(content)
        
        total_requested = sum(question_config.values())
        if total_requested <= 0:
            question_config = {'mcq': 5, 'true_false': 3, 'short_answer': 2}
            total_requested = 10
            
        logger.info(f"Generating {total_requested} questions ({question_config}) using {self.provider} [Subject: {subject}, Lang: {language}]")

        # If provider is demo or no API key, use the intelligent offline generator
        if self.provider == 'demo' or not self.api_key:
            return self._generate_offline(text_context, question_config, difficulty, page_refs, subject=subject, language=language)
            
        # Try LLM generation with schema validation and retry loop, fallback to demo if API fails
        try:
            if self.provider == 'gemini':
                return self._generate_with_gemini(text_context, question_config, difficulty, target_audience, page_refs, subject=subject, language=language)
            elif self.provider == 'openai':
                return self._generate_with_openai(text_context, question_config, difficulty, target_audience, page_refs, subject=subject, language=language)
            else:
                return self._generate_offline(text_context, question_config, difficulty, page_refs, subject=subject, language=language)
        except Exception as e:
            logger.warning(f"AI API failed ({str(e)}). Falling back to offline question generator.")
            return self._generate_offline(text_context, question_config, difficulty, page_refs, subject=subject, language=language)

    def regenerate_question(
        self,
        old_question: Question,
        context: Union[Dict[int, str], str],
        instruction: str = ""
    ) -> Question:
        """
        Regenerate a single question based on user feedback or instruction
        """
        text_context, page_refs = self._normalize_content(context)
        
        if self.provider != 'demo' and self.api_key:
            try:
                prompt = f"""You are an expert exam creator.
Existing question:
Type: {old_question.question_type}
Question: {old_question.question_text}
Answers: {[a.text for a in old_question.answers]}
Explanation: {old_question.justification}

Instruction from teacher: "{instruction or 'Generate an alternative high-quality question on the same topic'}"

Source Context:
{text_context[:3000]}

Return JSON format with a single question object:
{{
  "question_text": "...",
  "question_type": "{old_question.question_type}",
  "answers": [
    {{"text": "Option A", "is_correct": false}},
    {{"text": "Option B", "is_correct": true}},
    {{"text": "Option C", "is_correct": false}},
    {{"text": "Option D", "is_correct": false}}
  ],
  "correct_answer": "...",
  "points": {old_question.points},
  "justification": "...",
  "rubric": "...",
  "source_page": {old_question.source_page},
  "source_section": "{old_question.source_section}"
}}"""
                if self.provider == 'gemini':
                    raw = self._call_gemini_api(prompt)
                else:
                    raw = self._call_openai_api(prompt)
                    
                parsed = self._extract_json(raw)
                if isinstance(parsed, dict):
                    q_data = parsed.get('question', parsed)
                    if 'question_text' in q_data:
                        q_data['id'] = old_question.id
                        q_data['exam_id'] = old_question.exam_id
                        q_data['order_index'] = old_question.order_index
                        return Question.from_dict(q_data)
            except Exception as e:
                logger.error(f"Regeneration via API failed: {e}")

        # Fallback offline regeneration
        return self._regenerate_offline(old_question, text_context, instruction)

    def grade_subjective_answers(
        self,
        exam_id: int,
        questions: List[Question],
        user_answers: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        """
        AI evaluation of short answers and essays against rubrics
        Returns: {question_id_str: {"score": float, "feedback": str}}
        """
        results = {}
        for q in questions:
            q_id = str(q.id)
            user_ans = str(user_answers.get(q.id, user_answers.get(q_id, ''))).strip()
            
            if q.question_type in ('short_answer', 'essay'):
                if not user_ans:
                    results[q_id] = {'score': 0.0, 'feedback': 'No answer submitted.'}
                    continue
                    
                if self.provider != 'demo' and self.api_key:
                    try:
                        eval_prompt = f"""Evaluate this student response:
Question ({q.points} points): {q.question_text}
Expected Model Answer / Criteria: {q.correct_answer or q.justification or q.rubric}
Student Answer: {user_ans}

Assign a numerical score between 0.0 and {q.points}.
Provide constructive 1-2 sentence feedback explaining the score.

Respond ONLY with valid JSON:
{{"score": 4.5, "feedback": "Well explained key points with slight omission of..."}}"""
                        if self.provider == 'gemini':
                            raw = self._call_gemini_api(eval_prompt)
                        else:
                            raw = self._call_openai_api(eval_prompt)
                        parsed = self._extract_json(raw)
                        if 'score' in parsed and 'feedback' in parsed:
                            score_val = min(float(q.points), max(0.0, float(parsed['score'])))
                            results[q_id] = {'score': round(score_val, 1), 'feedback': parsed['feedback']}
                            continue
                    except Exception as e:
                        logger.warning(f"AI grading error for Q{q.id}: {e}")
                
                # Rule-based rubric grading fallback
                exp_words = set(re.findall(r'\w+', (q.correct_answer + " " + q.justification).lower()))
                student_words = set(re.findall(r'\w+', user_ans.lower()))
                overlap = len(exp_words.intersection(student_words)) if exp_words else 1
                ratio = min(1.0, overlap / max(3, len(exp_words) * 0.4)) if exp_words else 0.8
                
                # Length check
                length_mult = min(1.0, len(user_ans) / (50 if q.question_type == 'short_answer' else 150))
                final_ratio = max(0.2, (ratio * 0.6) + (length_mult * 0.4))
                score_val = round(q.points * final_ratio, 1)
                
                feedback = (
                    "Good understanding demonstrated." if final_ratio >= 0.7 
                    else "Partially correct; review the key concepts in the solution key."
                )
                results[q_id] = {'score': score_val, 'feedback': feedback}

        return results

    # Provider Implementations
    def _generate_with_gemini(
        self,
        content: str,
        q_config: Dict[str, int],
        difficulty: str,
        target_audience: str,
        page_refs: Dict[int, str],
        subject: str = "General",
        language: str = "English"
    ) -> List[Question]:
        """Generate questions using Google Gemini API via REST with retry & validation"""
        prompt = self._build_prompt(content, q_config, difficulty, target_audience, subject=subject, language=language)
        max_retries = 3
        last_error = ""
        
        for attempt in range(max_retries):
            try:
                curr_prompt = prompt if attempt == 0 else f"{prompt}\n\nIMPORTANT: Previous attempt failed validation with error: {last_error}. Ensure strictly valid JSON matching the exact schema."
                raw_response = self._call_gemini_api(curr_prompt)
                parsed = self._extract_json(raw_response)
                is_valid, err_msg = self._validate_questions_schema(parsed)
                if is_valid:
                    return self._parse_questions_json(parsed, page_refs)
                last_error = err_msg
                logger.warning(f"Gemini schema validation failed on attempt {attempt + 1}: {err_msg}")
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Gemini API attempt {attempt + 1} encountered error: {e}")
            time.sleep(1)
            
        raise RuntimeError(f"Gemini question generation failed after {max_retries} attempts: {last_error}")

    def _call_gemini_api(self, prompt: str) -> str:
        """Call Gemini REST API"""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": AI_TEMPERATURE,
                "maxOutputTokens": AI_MAX_TOKENS,
                "responseMimeType": "application/json"
            }
        }
        
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=40) as response:
            result = json.loads(response.read().decode('utf-8'))
            candidates = result.get('candidates', [])
            if candidates and 'content' in candidates[0]:
                parts = candidates[0]['content'].get('parts', [])
                if parts:
                    return parts[0].get('text', '')
        raise RuntimeError("Empty response from Gemini API")

    def _generate_with_openai(
        self,
        content: str,
        q_config: Dict[str, int],
        difficulty: str,
        target_audience: str,
        page_refs: Dict[int, str],
        subject: str = "General",
        language: str = "English"
    ) -> List[Question]:
        """Generate questions using OpenAI API with retry & validation"""
        prompt = self._build_prompt(content, q_config, difficulty, target_audience, subject=subject, language=language)
        max_retries = 3
        last_error = ""
        
        for attempt in range(max_retries):
            try:
                curr_prompt = prompt if attempt == 0 else f"{prompt}\n\nIMPORTANT: Previous attempt failed validation with error: {last_error}. Ensure strictly valid JSON matching the exact schema."
                raw_response = self._call_openai_api(curr_prompt)
                parsed = self._extract_json(raw_response)
                is_valid, err_msg = self._validate_questions_schema(parsed)
                if is_valid:
                    return self._parse_questions_json(parsed, page_refs)
                last_error = err_msg
                logger.warning(f"OpenAI schema validation failed on attempt {attempt + 1}: {err_msg}")
            except Exception as e:
                last_error = str(e)
                logger.warning(f"OpenAI API attempt {attempt + 1} encountered error: {e}")
            time.sleep(1)
            
        raise RuntimeError(f"OpenAI question generation failed after {max_retries} attempts: {last_error}")

    def _call_openai_api(self, prompt: str) -> str:
        """Call OpenAI or compatible chat completion endpoint"""
        endpoint = f"{self.base_url or 'https://api.openai.com/v1'}/chat/completions"
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a professional educational assessment designer like Exam-Generator.com. Output valid JSON only."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": AI_TEMPERATURE,
            "max_tokens": AI_MAX_TOKENS,
            "response_format": {"type": "json_object"}
        }
        
        req = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode('utf-8'),
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.api_key}'
            },
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=45) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            return res_data['choices'][0]['message']['content']

    def _build_prompt(
        self,
        content: str,
        q_config: Dict[str, int],
        difficulty: str,
        target_audience: str,
        subject: str = "General",
        language: str = "English"
    ) -> str:
        """Construct structured prompt for LLM"""
        req_lines = []
        if q_config.get('mcq', 0) > 0:
            req_lines.append(f"- {q_config['mcq']} Multiple Choice Questions (4 options, exactly 1 correct)")
        if q_config.get('true_false', 0) > 0:
            req_lines.append(f"- {q_config['true_false']} True/False Questions")
        if q_config.get('fill_blank', 0) > 0:
            req_lines.append(f"- {q_config['fill_blank']} Fill-in-the-Blank Questions (use '[blank]' in the question_text, provide the exact 'correct_answer', and include common acceptable alternative variations in answers: [{{'text': '...', 'is_correct': true}}])")
        if q_config.get('short_answer', 0) > 0:
            req_lines.append(f"- {q_config['short_answer']} Short Answer Questions with model answer and grading rubric")
        if q_config.get('essay', 0) > 0:
            req_lines.append(f"- {q_config['essay']} Essay / Analytical Questions with comprehensive grading criteria")
            
        req_str = "\n".join(req_lines)
        
        return f"""Create a balanced educational exam based on the following material.

SOURCE MATERIAL:
{content[:5000]}

REQUIREMENTS:
1. Subject / Domain: {subject}
2. Target Language: {language} (ALL questions, options, explanations, and rubrics MUST be written in {language})
3. Target Audience: {target_audience}
4. Difficulty: {difficulty}
5. Question Breakdown:
{req_str}
6. For each question provide:
   - "question_text": Clear, precise question (for fill_blank, use '[blank]' where the word/phrase belongs)
   - "question_type": "mcq", "true_false", "fill_blank", "short_answer", or "essay"
   - "answers": For MCQ, list 4 options [{{"text": "...", "is_correct": true/false}}]. For true_false, [{{"text": "True", "is_correct": true/false}}, {{"text": "False", "is_correct": true/false}}]. For fill_blank, list acceptable synonyms/casings [{{"text": "...", "is_correct": true}}]. For short_answer/essay, empty array.
   - "correct_answer": The exact correct answer string / model response
   - "points": Point value (1.0 for MCQ/TrueFalse/fill_blank, 2.0-5.0 for Short Answer, 5.0-10.0 for Essay)
   - "justification": Detailed pedagogical explanation of why this answer is correct
   - "rubric": For short_answer/essay, key criteria for scoring
   - "source_page": Page number if identified, else 1
   - "source_section": Section heading or topic name

OUTPUT JSON FORMAT:
{{
  "questions": [
    {{
      "question_text": "...",
      "question_type": "mcq",
      "answers": [
        {{"text": "Option 1", "is_correct": false}},
        {{"text": "Option 2", "is_correct": true}},
        {{"text": "Option 3", "is_correct": false}},
        {{"text": "Option 4", "is_correct": false}}
      ],
      "correct_answer": "Option 2",
      "points": 1.0,
      "justification": "Explanation...",
      "rubric": "",
      "source_page": 1,
      "source_section": "Topic A"
    }}
  ]
}}"""

    def _validate_questions_schema(self, data: Any) -> Tuple[bool, str]:
        """Validate JSON against strict exam question schema"""
        if not isinstance(data, dict):
            if isinstance(data, list):
                data = {'questions': data}
            else:
                return False, "Root data must be a JSON object with a 'questions' array"
                
        questions = data.get('questions')
        if not isinstance(questions, list) or len(questions) == 0:
            return False, "'questions' array is missing or empty"
            
        valid_types = {'mcq', 'true_false', 'fill_blank', 'short_answer', 'essay'}
        for i, q in enumerate(questions):
            if not isinstance(q, dict):
                return False, f"Question at index {i} is not a valid JSON object"
            q_text = q.get('question_text')
            if not q_text or not isinstance(q_text, str) or not q_text.strip():
                return False, f"Question at index {i} missing non-empty 'question_text'"
            q_type = q.get('question_type')
            if q_type not in valid_types:
                return False, f"Question at index {i} has invalid question_type: {q_type}"
            if q_type in ('mcq', 'true_false'):
                answers = q.get('answers')
                if not isinstance(answers, list) or len(answers) < 2:
                    return False, f"Question at index {i} of type '{q_type}' must have at least 2 answers"
            if not q.get('correct_answer'):
                return False, f"Question at index {i} missing 'correct_answer'"
            try:
                pts = float(q.get('points', 1.0))
                if pts <= 0:
                    return False, f"Question at index {i} points must be > 0"
            except (ValueError, TypeError):
                return False, f"Question at index {i} has non-numeric points"
                
        return True, ""

    def _extract_json(self, raw_text: str) -> Any:
        """Extract JSON object from string even if wrapped in markdown codeblocks"""
        text = raw_text.strip()
        # Remove markdown fences
        if text.startswith("```"):
            lines = text.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines).strip()
            
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Match outermost brackets
            match = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])', text)
            if match:
                return json.loads(match.group(1))
            raise ValueError(f"Could not parse valid JSON from AI response: {text[:200]}")

    def _parse_questions_json(self, data: Dict[str, Any], page_refs: Dict[int, str]) -> List[Question]:
        """Convert parsed JSON into Question objects with validation"""
        q_list = data.get('questions', data if isinstance(data, list) else [])
        results = []
        for idx, item in enumerate(q_list):
            try:
                q_obj = Question.from_dict(item)
                q_obj.order_index = idx
                results.append(q_obj)
            except Exception as e:
                logger.warning(f"Error parsing question item {idx}: {e}")
        return results

    # Offline / Demo Generator Implementation
    def _generate_offline(
        self,
        content: str,
        q_config: Dict[str, int],
        difficulty: str,
        page_refs: Dict[int, str],
        subject: str = "General",
        language: str = "English"
    ) -> List[Question]:
        """
        High quality rule-based question generator.
        Extracts key sentences, entities, and definitions from source material.
        Generates genuine questions across mcq, true_false, fill_blank, short_answer, and essay.
        """
        questions: List[Question] = []
        
        # Extract meaningful sentences
        sentences = [
            s.strip() for s in re.split(r'[.\n]\s*', content)
            if len(s.strip()) > 35 and not s.strip().startswith('http') and not s.strip().startswith('#')
        ]
        if not sentences:
            sentences = [
                "Artificial intelligence enables machines to learn from experience and adapt to new inputs.",
                "Process scheduling is an essential task of the operating system kernel.",
                "Data structures organize and store data for efficient access and modification.",
                "Encapsulation is one of the fundamental concepts in object-oriented programming.",
                "HTTP is an application layer protocol used for distributed, collaborative hypermedia information systems."
            ]

        # Extract keywords/terms
        words = [w for w in re.findall(r'\b[A-Za-z]{4,}\b', content) if w.lower() not in ('with', 'from', 'this', 'that', 'have', 'were', 'which')]
        vocab = list(dict.fromkeys(words))[:30] if words else ["Efficiency", "Protocol", "Framework", "System", "Function"]
        
        q_idx = 0
        
        # 1. Generate Multiple Choice Questions
        mcq_count = q_config.get('mcq', 0)
        for i in range(mcq_count):
            sent = sentences[i % len(sentences)]
            words_in_sent = [w for w in re.findall(r'\b[A-Za-z]{4,}\b', sent) if w.lower() not in ('with', 'from', 'this', 'that', 'were', 'which', 'about', 'their')]
            keyword = words_in_sent[-1] if words_in_sent else "key component"
            
            # Create question
            blank_sent = re.sub(re.escape(keyword), "_______", sent, flags=re.IGNORECASE)
            q_text = f"According to the source material, complete the statement: \"{blank_sent}\""
            
            correct = keyword
            distractors = [v for v in vocab if v.lower() != correct.lower()][:3]
            while len(distractors) < 3:
                distractors.append(f"Alternative {len(distractors)+1}")
                
            answers = [
                Answer(text=distractors[0], is_correct=False),
                Answer(text=correct, is_correct=True),
                Answer(text=distractors[1], is_correct=False),
                Answer(text=distractors[2], is_correct=False)
            ]
            
            questions.append(Question(
                question_text=q_text,
                question_type="mcq",
                answers=answers,
                correct_answer=correct,
                points=1.0,
                justification=f"As stated in the source text: \"{sent}\"",
                source_page=1,
                source_section=f"{subject} - Key Concepts",
                order_index=q_idx
            ))
            q_idx += 1

        # 2. Generate True / False Questions
        tf_count = q_config.get('true_false', 0)
        for i in range(tf_count):
            sent = sentences[(i + mcq_count) % len(sentences)]
            is_true = (i % 2 == 0)
            
            if is_true:
                stmt = sent
                just = f"This statement directly matches the text: \"{sent}\""
            else:
                stmt = f"It is NOT the case that {sent[0].lower() + sent[1:]}"
                just = f"This is false because the text establishes: \"{sent}\""
                
            answers = [
                Answer(text="True", is_correct=is_true),
                Answer(text="False", is_correct=not is_true)
            ]
            
            questions.append(Question(
                question_text=f"True or False: {stmt}",
                question_type="true_false",
                answers=answers,
                correct_answer="True" if is_true else "False",
                points=1.0,
                justification=just,
                source_page=1,
                source_section=f"{subject} - Comprehension",
                order_index=q_idx
            ))
            q_idx += 1

        # 3. Generate Fill-in-the-Blank Questions
        fb_count = q_config.get('fill_blank', 0)
        for i in range(fb_count):
            sent = sentences[(i + mcq_count + tf_count) % len(sentences)]
            words_in_sent = [w for w in re.findall(r'\b[A-Za-z]{4,}\b', sent) if w.lower() not in ('with', 'from', 'this', 'that', 'were', 'which', 'about', 'their')]
            target_word = words_in_sent[len(words_in_sent) // 2] if words_in_sent else "system"
            
            blank_sent = re.sub(r'\b' + re.escape(target_word) + r'\b', "[blank]", sent, count=1, flags=re.IGNORECASE)
            if "[blank]" not in blank_sent:
                blank_sent = f"{sent} [blank]"
                
            alt_answers = [
                Answer(text=target_word, is_correct=True),
                Answer(text=target_word.lower(), is_correct=True),
                Answer(text=target_word.capitalize(), is_correct=True)
            ]
            
            questions.append(Question(
                question_text=f"Fill in the blank: \"{blank_sent}\"",
                question_type="fill_blank",
                answers=alt_answers,
                correct_answer=target_word,
                points=1.0,
                justification=f"Context from source material: \"{sent}\"",
                rubric=f"Exact match or acceptable variant of '{target_word}'.",
                source_page=1,
                source_section=f"{subject} - Cloze Assessment",
                order_index=q_idx
            ))
            q_idx += 1

        # 4. Generate Short Answer Questions
        sa_count = q_config.get('short_answer', 0)
        for i in range(sa_count):
            sent = sentences[(i + mcq_count + tf_count + fb_count) % len(sentences)]
            q_text = f"Explain the significance of the following principle mentioned in the material: \"{sent[:80]}...\""
            
            questions.append(Question(
                question_text=q_text,
                question_type="short_answer",
                answers=[],
                correct_answer=sent,
                points=2.0,
                justification=f"Key reference: \"{sent}\"",
                rubric="Student should articulate the concept and state its practical significance.",
                source_page=1,
                source_section=f"{subject} - Analysis",
                order_index=q_idx
            ))
            q_idx += 1

        # 5. Generate Essay Questions
        essay_count = q_config.get('essay', 0)
        for i in range(essay_count):
            topic_hint = sentences[0][:60]
            q_text = f"Analyze the core themes discussed regarding \"{topic_hint}...\". Discuss practical applications and potential challenges."
            
            questions.append(Question(
                question_text=q_text,
                question_type="essay",
                answers=[],
                correct_answer=f"Comprehensive analysis covering key definitions, contextual applications, and critical analysis based on: {topic_hint}",
                points=5.0,
                justification="Requires synthetic understanding and critical evaluation of the subject matter.",
                rubric="1. Accuracy of core definitions (2 pts)\n2. Practical applications (2 pts)\n3. Critical analysis and clarity (1 pt)",
                source_page=1,
                source_section=f"{subject} - Synthesis & Evaluation",
                order_index=q_idx
            ))
            q_idx += 1

        return questions

    def _regenerate_offline(self, old_q: Question, context: str, instruction: str) -> Question:
        """Regenerate a single question in offline mode"""
        sentences = [s.strip() for s in re.split(r'[.\n]\s*', context) if len(s.strip()) > 30]
        seed = sentences[len(sentences) // 2] if sentences else "Key domain concept"
        
        new_q = Question(
            id=old_q.id,
            exam_id=old_q.exam_id,
            question_text=f"Alternative assessment: {old_q.question_text} (Focus: {instruction or 'Practical Application'})",
            question_type=old_q.question_type,
            answers=old_q.answers,
            correct_answer=old_q.correct_answer,
            points=old_q.points,
            justification=f"Updated reference: {seed[:100]}",
            rubric=old_q.rubric,
            source_page=old_q.source_page,
            source_section=old_q.source_section,
            order_index=old_q.order_index
        )
        return new_q

    def _normalize_content(self, content: Union[Dict[int, str], str]) -> (str, Dict[int, str]):
        """Convert page dict or text string into single string and page map"""
        if isinstance(content, dict):
            page_refs = {k: v for k, v in content.items()}
            text_blocks = [f"\n--- Page {page} ---\n{text}" for page, text in sorted(content.items())]
            return "\n".join(text_blocks), page_refs
        else:
            text = str(content)
            return text, {1: text[:2000]}
