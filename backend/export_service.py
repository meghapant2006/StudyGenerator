"""
Export service for exam generator
Generates professional Student Exam Papers and Teacher Answer Keys in multiple formats:
- Printable HTML / PDF templates
- Microsoft Word (.docx / Word-compatible document)
- Google Forms CSV / structured text
- Moodle LMS (GIFT syntax)
- Portable JSON backup
"""
import io
import json
import html
from typing import Optional, Dict, Any, List
from datetime import datetime

from models import Exam, Question, Answer

try:
    import docx
    from docx import Document
    from docx.shared import Inches, Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False


class ExportService:
    """
    Handles formatting and export for student exam papers, teacher keys,
    Google Forms, and Moodle LMS.
    """

    def generate_html(self, exam: Exam, export_type: str = "student") -> str:
        """
        Generate beautiful, print-ready HTML for student paper or teacher answer key.
        When printed via browser (Ctrl+P), produces a perfect, professional PDF.
        """
        is_teacher = (export_type.lower() == "teacher")
        title_prefix = "ANSWER KEY & SOLUTIONS" if is_teacher else "EXAMINATION PAPER"
        badge_color = "#10B981" if is_teacher else "#4F46E5"
        
        questions_html = []
        for idx, q in enumerate(exam.questions, 1):
            q_type = q.question_type or 'mcq'
            pts_label = f"[{q.points:.1f} pt{'s' if q.points != 1 else ''}]"
            
            # Question Body
            body_html = ""
            if q_type == 'mcq':
                options_html = []
                letters = ["A", "B", "C", "D", "E", "F"]
                for o_idx, ans in enumerate(q.answers):
                    letter = letters[o_idx] if o_idx < len(letters) else str(o_idx + 1)
                    if is_teacher and ans.is_correct:
                        options_html.append(f"""
                            <li class="option-item correct">
                                <span class="marker correct-marker">✔ ({letter})</span>
                                <span class="opt-text"><strong>{html.escape(ans.text)}</strong> <span class="badge-correct">(CORRECT)</span></span>
                            </li>
                        """)
                    else:
                        bubble = "⭕" if not is_teacher else f"({letter})"
                        options_html.append(f"""
                            <li class="option-item">
                                <span class="marker">{bubble}</span>
                                <span class="opt-text">{html.escape(ans.text)}</span>
                            </li>
                        """)
                body_html = f'<ul class="options-list">{"".join(options_html)}</ul>'
                
            elif q_type == 'true_false':
                if is_teacher:
                    corr_tf = "True" if any(a.text.lower() == 'true' and a.is_correct for a in q.answers) else "False"
                    body_html = f"""
                        <div class="tf-options">
                            <span class="tf-item {'correct' if corr_tf == 'True' else ''}">✔ True</span>
                            <span class="tf-item {'correct' if corr_tf == 'False' else ''}">✔ False</span>
                            <span class="badge-correct" style="margin-left:15px;">Correct Answer: {corr_tf}</span>
                        </div>
                    """
                else:
                    body_html = """
                        <div class="tf-options">
                            <span class="tf-item">[ &nbsp; ] True</span>
                            <span class="tf-item" style="margin-left: 30px;">[ &nbsp; ] False</span>
                        </div>
                    """
                    
            elif q_type == 'short_answer':
                if is_teacher:
                    body_html = f"""
                        <div class="solution-box">
                            <strong>Expected Model Answer:</strong>
                            <p>{html.escape(q.correct_answer or q.justification or 'Key concepts as detailed in reference material.')}</p>
                        </div>
                    """
                else:
                    body_html = """
                        <div class="ruled-lines">
                            <div class="line"></div>
                            <div class="line"></div>
                            <div class="line"></div>
                        </div>
                    """
                    
            elif q_type == 'essay':
                if is_teacher:
                    body_html = f"""
                        <div class="solution-box">
                            <strong>Grading Rubric & Model Synthesis:</strong>
                            <p>{html.escape(q.rubric or q.correct_answer or q.justification)}</p>
                        </div>
                    """
                else:
                    body_html = """
                        <div class="essay-box">
                            <div class="line"></div>
                            <div class="line"></div>
                            <div class="line"></div>
                            <div class="line"></div>
                            <div class="line"></div>
                            <div class="line"></div>
                        </div>
                    """

            # Explanation section for Teacher Key
            teacher_notes = ""
            if is_teacher:
                notes = []
                if q.justification:
                    notes.append(f"<p><strong>Explanation:</strong> {html.escape(q.justification)}</p>")
                if q.source_page:
                    notes.append(f"<p class='source-meta'>📖 <strong>Source Reference:</strong> Page {q.source_page}{' (' + html.escape(q.source_section) + ')' if q.source_section else ''}</p>")
                if notes:
                    teacher_notes = f'<div class="explanation-box">{"".join(notes)}</div>'

            questions_html.append(f"""
                <div class="question-block">
                    <div class="question-header">
                        <span class="q-num">Q{idx}.</span>
                        <span class="q-type-badge">{q_type.replace('_', ' ').upper()}</span>
                        <span class="q-pts">{pts_label}</span>
                    </div>
                    <div class="question-text">{html.escape(q.question_text)}</div>
                    {body_html}
                    {teacher_notes}
                </div>
            """)

        duration_str = f"{exam.time_limit} Minutes" if exam.time_limit else "Untimed"
        header_date = datetime.now().strftime("%B %d, %Y")

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{html.escape(exam.title)} - {title_prefix}</title>
    <style>
        @page {{
            size: A4;
            margin: 20mm;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            color: #1f2937;
            line-height: 1.5;
            background: #ffffff;
            margin: 0;
            padding: 30px;
        }}
        .exam-paper {{
            max-width: 850px;
            margin: 0 auto;
        }}
        .paper-header {{
            border-bottom: 3px double #d1d5db;
            padding-bottom: 18px;
            margin-bottom: 25px;
            text-align: center;
        }}
        .paper-type-badge {{
            display: inline-block;
            background: {badge_color};
            color: white;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 1.5px;
            text-transform: uppercase;
            padding: 4px 14px;
            border-radius: 9999px;
            margin-bottom: 8px;
        }}
        .paper-title {{
            font-size: 24px;
            font-weight: 800;
            margin: 5px 0;
            color: #111827;
        }}
        .paper-meta {{
            display: flex;
            justify-content: space-between;
            font-size: 13px;
            color: #4b5563;
            margin-top: 10px;
            padding-top: 10px;
            border-top: 1px solid #e5e7eb;
        }}
        .student-fields {{
            display: {'none' if is_teacher else 'flex'};
            justify-content: space-between;
            margin: 20px 0;
            padding: 12px 16px;
            background: #f9fafb;
            border: 1px solid #e5e7eb;
            border-radius: 6px;
            font-size: 14px;
        }}
        .instructions {{
            background: #f8fafc;
            border-left: 4px solid #64748b;
            padding: 10px 15px;
            font-size: 12px;
            color: #334155;
            margin-bottom: 25px;
        }}
        .question-block {{
            margin-bottom: 24px;
            page-break-inside: avoid;
            padding-bottom: 14px;
            border-bottom: 1px dotted #e5e7eb;
        }}
        .question-header {{
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 6px;
        }}
        .q-num {{
            font-weight: 800;
            font-size: 15px;
            color: #111827;
        }}
        .q-type-badge {{
            font-size: 10px;
            font-weight: 700;
            color: #4b5563;
            background: #f3f4f6;
            padding: 2px 8px;
            border-radius: 4px;
        }}
        .q-pts {{
            font-size: 12px;
            font-weight: 600;
            color: #6b7280;
            margin-left: auto;
        }}
        .question-text {{
            font-size: 15px;
            font-weight: 500;
            color: #1f2937;
            margin-bottom: 10px;
        }}
        .options-list {{
            list-style: none;
            padding-left: 5px;
            margin: 8px 0;
        }}
        .option-item {{
            display: flex;
            align-items: baseline;
            gap: 10px;
            padding: 5px 0;
            font-size: 14px;
        }}
        .option-item.correct {{
            color: #065f46;
            background: #ecfdf5;
            padding: 6px 10px;
            border-radius: 4px;
        }}
        .marker {{
            font-family: monospace;
            font-size: 13px;
            color: #6b7280;
        }}
        .badge-correct {{
            font-size: 11px;
            color: #059669;
            font-weight: 700;
        }}
        .tf-options {{
            margin: 10px 0;
            font-size: 14px;
        }}
        .tf-item.correct {{
            font-weight: 700;
            color: #047857;
            background: #ecfdf5;
            padding: 3px 8px;
            border-radius: 4px;
        }}
        .ruled-lines .line, .essay-box .line {{
            height: 28px;
            border-bottom: 1px solid #cbd5e1;
            margin-bottom: 2px;
        }}
        .solution-box {{
            background: #f0fdf4;
            border-left: 4px solid #10b981;
            padding: 10px 14px;
            margin: 8px 0;
            font-size: 13px;
            color: #064e3b;
        }}
        .explanation-box {{
            background: #f8fafc;
            border-left: 3px solid #6366f1;
            padding: 8px 12px;
            margin-top: 8px;
            font-size: 12px;
            color: #334155;
        }}
        .source-meta {{
            color: #64748b;
            font-size: 11px;
            margin-top: 4px;
        }}
        .print-btn-bar {{
            position: fixed;
            top: 15px;
            right: 15px;
            background: white;
            padding: 8px 16px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            display: flex;
            gap: 10px;
            z-index: 1000;
        }}
        .print-btn {{
            background: #4F46E5;
            color: white;
            border: none;
            padding: 8px 16px;
            font-weight: 600;
            font-size: 13px;
            border-radius: 6px;
            cursor: pointer;
        }}
        .print-btn:hover {{
            background: #4338CA;
        }}
        @media print {{
            body {{
                padding: 0;
            }}
            .print-btn-bar {{
                display: none !important;
            }}
        }}
    </style>
</head>
<body>
    <div class="print-btn-bar">
        <button class="print-btn" onclick="window.print()">🖨️ Print / Save as PDF</button>
    </div>

    <div class="exam-paper">
        <header class="paper-header">
            <span class="paper-type-badge">{title_prefix}</span>
            <h1 class="paper-title">{html.escape(exam.title)}</h1>
            <div class="paper-meta">
                <span><strong>Questions:</strong> {len(exam.questions)}</span>
                <span><strong>Total Marks:</strong> {exam.total_points:.1f} pts</span>
                <span><strong>Duration:</strong> {duration_str}</span>
                <span><strong>Date:</strong> {header_date}</span>
            </div>
        </header>

        <div class="student-fields">
            <span><strong>Student Name:</strong> ____________________________________</span>
            <span><strong>Roll / ID:</strong> ______________</span>
            <span><strong>Score:</strong> _____ / {exam.total_points:.0f}</span>
        </div>

        <div class="instructions">
            <strong>INSTRUCTIONS:</strong> Please read each question carefully. Write your answers clearly in the designated spaces. For multiple-choice questions, fill or circle the corresponding option. Check your work before final submission.
        </div>

        <div class="questions-container">
            {"".join(questions_html)}
        </div>

        <footer style="margin-top: 40px; text-align: center; font-size: 11px; color: #9ca3af; border-top: 1px solid #f3f4f6; padding-top: 15px;">
            Generated by StudyWise AI Exam Platform • exam-generator.com
        </footer>
    </div>
</body>
</html>"""
        return html_content

    def generate_docx(self, exam: Exam, export_type: str = "student") -> bytes:
        """
        Generate Word (.docx) document.
        Uses python-docx if available, otherwise generates a Word-compatible XML document.
        """
        is_teacher = (export_type.lower() == "teacher")
        
        if HAS_DOCX:
            doc = Document()
            # Title
            title_p = doc.add_paragraph()
            title_run = title_p.add_run(exam.title)
            title_run.font.size = Pt(20)
            title_run.font.bold = True
            
            sub_p = doc.add_paragraph()
            sub_run = sub_p.add_run("TEACHER SOLUTION & ANSWER KEY" if is_teacher else "EXAMINATION QUESTION PAPER")
            sub_run.font.size = Pt(12)
            sub_run.font.color.rgb = RGBColor(16, 185, 129) if is_teacher else RGBColor(79, 70, 229)
            sub_run.font.bold = True

            # Meta table
            doc.add_paragraph(f"Total Questions: {len(exam.questions)}   |   Total Points: {exam.total_points:.1f}   |   Time Limit: {exam.time_limit or 'Untimed'} Mins")
            
            if not is_teacher:
                doc.add_paragraph("Candidate Name: __________________________   Roll No: ____________   Score: ______ / " + str(int(exam.total_points)))
            doc.add_paragraph("―" * 55)

            for idx, q in enumerate(exam.questions, 1):
                p = doc.add_paragraph()
                p.add_run(f"Q{idx}. [{q.question_type.upper()}] {q.question_text} ").bold = True
                p.add_run(f"({q.points} pts)")
                
                if q.question_type == 'mcq':
                    letters = ["A", "B", "C", "D", "E"]
                    for o_idx, ans in enumerate(q.answers):
                        lp = doc.add_paragraph(f"    ({letters[o_idx] if o_idx < len(letters) else str(o_idx+1)}) {ans.text}")
                        if is_teacher and ans.is_correct:
                            lp.runs[0].bold = True
                            lp.add_run("  <-- [CORRECT ANSWER]").bold = True
                elif q.question_type == 'true_false':
                    if is_teacher:
                        doc.add_paragraph(f"    Correct Answer: {q.correct_answer or 'True'}")
                    else:
                        doc.add_paragraph("    [   ] True      [   ] False")
                elif q.question_type == 'short_answer':
                    if is_teacher:
                        doc.add_paragraph(f"    Expected Answer: {q.correct_answer or q.justification}")
                    else:
                        doc.add_paragraph("    _________________________________________________________________\n    _________________________________________________________________")
                elif q.question_type == 'essay':
                    if is_teacher:
                        doc.add_paragraph(f"    Rubric & Key Evaluation Criteria: {q.rubric or q.justification}")
                    else:
                        doc.add_paragraph("    [Written Response Area - 10-15 lines]\n\n\n\n\n")

                if is_teacher and q.justification:
                    jp = doc.add_paragraph(f"    Rationale: {q.justification}")
                    jp.runs[0].italic = True

                doc.add_paragraph("")  # spacing
                
            buffer = io.BytesIO()
            doc.save(buffer)
            return buffer.getvalue()
        else:
            # Fallback to Word-compatible formatted HTML document
            html_doc = self.generate_html(exam, export_type)
            return html_doc.encode('utf-8')

    def generate_gift(self, exam: Exam) -> str:
        """
        Generate Moodle GIFT format for direct LMS import
        """
        lines = [f"// Exam: {exam.title}", f"// Generated by StudyWise AI (exam-generator.com)", ""]
        
        for idx, q in enumerate(exam.questions, 1):
            q_name = f"::Q{idx}_{q.question_type}::"
            clean_text = q.question_text.replace("{", r"\{").replace("}", r"\}").replace("=", r"\=").replace("~", r"\~")
            
            if q.question_type == 'mcq':
                opt_lines = []
                for ans in q.answers:
                    clean_ans = ans.text.replace("{", r"\{").replace("}", r"\}").replace("=", r"\=").replace("~", r"\~")
                    if ans.is_correct:
                        opt_lines.append(f"  ={clean_ans} # {q.justification}")
                    else:
                        opt_lines.append(f"  ~{clean_ans}")
                opts_block = "\n".join(opt_lines)
                lines.append(f"{q_name} {clean_text} {{\n{opts_block}\n}}")
                
            elif q.question_type == 'true_false':
                is_true = any(a.text.lower() == 'true' and a.is_correct for a in q.answers) or str(q.correct_answer).lower() == 'true'
                tf_marker = "TRUE" if is_true else "FALSE"
                lines.append(f"{q_name} {clean_text} {{{tf_marker}#{q.justification}}}")
                
            elif q.question_type == 'short_answer':
                corr = (q.correct_answer or "Model response").replace("{", r"\{").replace("}", r"\}").replace("=", r"\=")
                lines.append(f"{q_name} {clean_text} {{={corr}#{q.justification}}}")
                
            elif q.question_type == 'essay':
                lines.append(f"{q_name} {clean_text} {{}}")
                
            lines.append("")  # Blank separator
            
        return "\n".join(lines)

    def generate_google_forms_csv(self, exam: Exam) -> str:
        """
        Generate CSV format suitable for Google Forms / Quiz spreadsheet import
        Columns: Question, Type, Option 1, Option 2, Option 3, Option 4, Correct Answer, Explanation, Points
        """
        import csv
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            "Question", "Question Type", "Option 1", "Option 2", "Option 3", "Option 4",
            "Correct Answer", "Points", "Explanation"
        ])
        
        for q in exam.questions:
            q_type = q.question_type
            opt1 = opt2 = opt3 = opt4 = ""
            corr = q.correct_answer or ""
            
            if q_type == 'mcq' and q.answers:
                if len(q.answers) > 0: opt1 = q.answers[0].text
                if len(q.answers) > 1: opt2 = q.answers[1].text
                if len(q.answers) > 2: opt3 = q.answers[2].text
                if len(q.answers) > 3: opt4 = q.answers[3].text
                for a in q.answers:
                    if a.is_correct:
                        corr = a.text
            elif q_type == 'true_false':
                opt1 = "True"
                opt2 = "False"
                corr = "True" if any(a.text.lower() == 'true' and a.is_correct for a in q.answers) else "False"
                
            writer.writerow([
                q.question_text,
                q_type,
                opt1,
                opt2,
                opt3,
                opt4,
                corr,
                q.points,
                q.justification
            ])
            
        return output.getvalue()
