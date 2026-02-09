"""
PDF text extraction module with OCR support
Extracts text from PDF documents and handles scanned/image-based PDFs using Tesseract OCR
"""
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io
from pathlib import Path
from typing import List, Dict, Tuple
import logging

from config import USE_OCR, OCR_LANGUAGE, MIN_TEXT_CONFIDENCE, CACHE_DIR

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PDFExtractor:
    """
    Handles PDF text extraction with automatic fallback to OCR for scanned documents
    """
    
    def __init__(self, pdf_path: str, use_ocr: bool = USE_OCR):
        """
        Initialize PDF extractor
        
        Args:
            pdf_path: Path to the PDF file
            use_ocr: Enable OCR for image-based pages
        """
        self.pdf_path = Path(pdf_path)
        self.use_ocr = use_ocr
        self.document = None
        self.total_pages = 0
        self.ocr_used = False
        
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    def __enter__(self):
        """Context manager entry"""
        self.document = fitz.open(self.pdf_path)
        self.total_pages = len(self.document)
        logger.info(f"Opened PDF: {self.pdf_path.name}, {self.total_pages} pages")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self.document:
            self.document.close()
    
    def extract_text_from_page(self, page_num: int) -> Tuple[str, bool]:
        """
        Extract text from a single page
        
        Args:
            page_num: Page number (0-indexed)
            
        Returns:
            Tuple of (extracted_text, ocr_was_used)
        """
        if page_num < 0 or page_num >= self.total_pages:
            raise ValueError(f"Invalid page number: {page_num}")
        
        page = self.document[page_num]
        
        # Try extracting text directly
        text = page.get_text("text").strip()
        
        # If text is empty or too short, use OCR (likely scanned page)
        if len(text) < 50 and self.use_ocr:
            logger.info(f"Page {page_num + 1}: Minimal text found, using OCR")
            text = self._ocr_page(page)
            return text, True
        
        return text, False
    
    def _ocr_page(self, page) -> str:
        """
        Perform OCR on a page
        
        Args:
            page: PyMuPDF page object
            
        Returns:
            Extracted text from OCR
        """
        try:
            self.ocr_used = True
            
            # Render page to image at higher resolution for better OCR
            zoom = 2  # Increase resolution
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)
            
            # Convert to PIL Image
            img_data = pix.tobytes("png")
            image = Image.open(io.BytesIO(img_data))
            
            # Perform OCR
            text = pytesseract.image_to_string(
                image,
                lang=OCR_LANGUAGE,
                config='--psm 6'  # Assume uniform block of text
            )
            
            return text.strip()
            
        except Exception as e:
            logger.error(f"OCR failed: {str(e)}")
            return ""
    
    def extract_all_text(self) -> Dict[int, str]:
        """
        Extract text from all pages
        
        Returns:
            Dictionary mapping page numbers (1-indexed) to extracted text
        """
        extracted_data = {}
        
        for page_num in range(self.total_pages):
            text, used_ocr = self.extract_text_from_page(page_num)
            
            if text:
                extracted_data[page_num + 1] = text  # 1-indexed for user display
                logger.info(f"Page {page_num + 1}: Extracted {len(text)} characters" + 
                          (" (OCR)" if used_ocr else ""))
            else:
                logger.warning(f"Page {page_num + 1}: No text extracted")
                extracted_data[page_num + 1] = ""
        
        return extracted_data
    
    def extract_text_by_sections(self) -> List[Dict]:
        """
        Extract text organized by sections/headings
        Attempts to identify document structure
        
        Returns:
            List of sections with text and metadata
        """
        sections = []
        current_section = None
        
        for page_num in range(self.total_pages):
            text, used_ocr = self.extract_text_from_page(page_num)
            
            if not text:
                continue
            
            # Split by paragraphs
            paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
            
            for para in paragraphs:
                # Simple heuristic: short lines in caps might be headings
                lines = para.split('\n')
                if len(lines[0]) < 100 and lines[0].isupper():
                    # Likely a heading - start new section
                    if current_section:
                        sections.append(current_section)
                    
                    current_section = {
                        'heading': lines[0],
                        'content': '\n'.join(lines[1:]) if len(lines) > 1 else '',
                        'page': page_num + 1
                    }
                else:
                    # Continue current section
                    if current_section is None:
                        current_section = {
                            'heading': 'Introduction',
                            'content': para,
                            'page': page_num + 1
                        }
                    else:
                        current_section['content'] += '\n\n' + para
        
        # Add last section
        if current_section:
            sections.append(current_section)
        
        return sections
    
    def get_text_summary(self) -> Dict:
        """
        Get a summary of extracted text
        
        Returns:
            Dictionary with extraction statistics
        """
        all_text = self.extract_all_text()
        total_chars = sum(len(text) for text in all_text.values())
        total_words = sum(len(text.split()) for text in all_text.values())
        pages_with_text = sum(1 for text in all_text.values() if text)
        
        return {
            'total_pages': self.total_pages,
            'pages_with_text': pages_with_text,
            'total_characters': total_chars,
            'total_words': total_words,
            'ocr_used': self.ocr_used,
            'avg_words_per_page': total_words / pages_with_text if pages_with_text > 0 else 0
        }


def extract_pdf_text(pdf_path: str) -> Tuple[Dict[int, str], Dict]:
    """
    Convenience function to extract text from PDF
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        Tuple of (page_text_dict, summary_dict)
    """
    with PDFExtractor(pdf_path) as extractor:
        text_data = extractor.extract_all_text()
        summary = extractor.get_text_summary()
        
    return text_data, summary


def extract_pdf_sections(pdf_path: str) -> List[Dict]:
    """
    Convenience function to extract structured sections from PDF
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        List of section dictionaries
    """
    with PDFExtractor(pdf_path) as extractor:
        sections = extractor.extract_text_by_sections()
        
    return sections


# Testing function
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python pdf_extractor.py <path_to_pdf>")
        sys.exit(1)
    
    pdf_file = sys.argv[1]
    
    print(f"\n=== Extracting text from {pdf_file} ===\n")
    
    # Extract and display summary
    text_data, summary = extract_pdf_text(pdf_file)
    
    print("Extraction Summary:")
    for key, value in summary.items():
        print(f"  {key}: {value}")
    
    print("\n--- First page content ---")
    if 1 in text_data:
        print(text_data[1][:500] + "..." if len(text_data[1]) > 500 else text_data[1])
