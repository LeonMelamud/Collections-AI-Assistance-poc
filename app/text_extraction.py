import os
import csv
import io
from typing import Optional
from pathlib import Path
import aiofiles
from PyPDF2 import PdfReader
from docx import Document


class TextExtractor:
    """Handles text extraction from various document formats."""
    
    def __init__(self):
        self.max_text_length = 50000  # Limit extracted text to prevent memory issues
    
    async def extract_text(self, file_path: str, mime_type: str) -> Optional[str]:
        """Extract text from file based on MIME type."""
        try:
            if mime_type == 'application/pdf':
                return await self._extract_from_pdf(file_path)
            elif mime_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
                return await self._extract_from_docx(file_path)
            elif mime_type == 'text/plain':
                return await self._extract_from_txt(file_path)
            elif mime_type == 'text/csv':
                return await self._extract_from_csv(file_path)
            elif mime_type == 'text/markdown':
                return await self._extract_from_markdown(file_path)
            else:
                # Try to read as plain text
                return await self._extract_from_txt(file_path)
        except Exception as e:
            print(f"Error extracting text from {file_path}: {e}")
            return None
    
    async def _extract_from_pdf(self, file_path: str) -> Optional[str]:
        """Extract text from PDF file."""
        try:
            reader = PdfReader(file_path)
            text_parts = []
            
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
                
                # Check length limit
                combined_text = '\n'.join(text_parts)
                if len(combined_text) > self.max_text_length:
                    return combined_text[:self.max_text_length]
            
            return '\n'.join(text_parts)
        except Exception as e:
            print(f"Error extracting from PDF: {e}")
            return None
    
    async def _extract_from_docx(self, file_path: str) -> Optional[str]:
        """Extract text from DOCX file."""
        try:
            doc = Document(file_path)
            text_parts = []
            
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    text_parts.append(paragraph.text)
                
                # Check length limit
                combined_text = '\n'.join(text_parts)
                if len(combined_text) > self.max_text_length:
                    return combined_text[:self.max_text_length]
            
            return '\n'.join(text_parts)
        except Exception as e:
            print(f"Error extracting from DOCX: {e}")
            return None
    
    async def _extract_from_txt(self, file_path: str) -> Optional[str]:
        """Extract text from plain text file."""
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
                return content[:self.max_text_length] if len(content) > self.max_text_length else content
        except UnicodeDecodeError:
            # Try with different encoding
            try:
                async with aiofiles.open(file_path, 'r', encoding='latin-1') as f:
                    content = await f.read()
                    return content[:self.max_text_length] if len(content) > self.max_text_length else content
            except Exception as e:
                print(f"Error reading text file: {e}")
                return None
        except Exception as e:
            print(f"Error extracting from TXT: {e}")
            return None
    
    async def _extract_from_csv(self, file_path: str) -> Optional[str]:
        """Extract text from CSV file."""
        try:
            text_parts = []
            
            with open(file_path, 'r', encoding='utf-8', newline='') as csvfile:
                # Try to detect delimiter
                sample = csvfile.read(1024)
                csvfile.seek(0)
                sniffer = csv.Sniffer()
                delimiter = sniffer.sniff(sample).delimiter
                
                reader = csv.reader(csvfile, delimiter=delimiter)
                
                for row_num, row in enumerate(reader):
                    if row_num == 0:
                        # Header row
                        text_parts.append("Headers: " + ", ".join(row))
                    else:
                        # Data rows
                        text_parts.append("Row {}: {}".format(row_num, ", ".join(row)))
                    
                    # Check length limit
                    combined_text = '\n'.join(text_parts)
                    if len(combined_text) > self.max_text_length:
                        return combined_text[:self.max_text_length]
            
            return '\n'.join(text_parts)
        except Exception as e:
            print(f"Error extracting from CSV: {e}")
            return None
    
    async def _extract_from_markdown(self, file_path: str) -> Optional[str]:
        """Extract text from Markdown file."""
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
                
                # Simple markdown processing - remove basic formatting
                processed_content = self._clean_markdown(content)
                
                return processed_content[:self.max_text_length] if len(processed_content) > self.max_text_length else processed_content
        except Exception as e:
            print(f"Error extracting from Markdown: {e}")
            return None
    
    def _clean_markdown(self, content: str) -> str:
        """Basic markdown cleanup - remove formatting but keep structure."""
        lines = content.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Remove markdown headers
            if line.startswith('#'):
                cleaned_lines.append(line.lstrip('#').strip())
            # Remove code blocks
            elif line.startswith('```'):
                continue
            # Remove inline code formatting
            elif '`' in line:
                cleaned_lines.append(line.replace('`', ''))
            # Remove bold/italic formatting
            elif '**' in line or '*' in line:
                cleaned_line = line.replace('**', '').replace('*', '')
                cleaned_lines.append(cleaned_line)
            # Remove links but keep text
            elif '[' in line and ']' in line:
                import re
                # Simple regex to extract link text
                cleaned_line = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', line)
                cleaned_lines.append(cleaned_line)
            else:
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def get_text_summary(self, text: str, max_length: int = 500) -> str:
        """Get a summary of extracted text."""
        if not text:
            return ""
        
        if len(text) <= max_length:
            return text
        
        # Find the last complete sentence within the limit
        truncated = text[:max_length]
        last_sentence = truncated.rfind('.')
        
        if last_sentence > max_length * 0.7:  # If we can find a sentence ending within 70% of limit
            return truncated[:last_sentence + 1]
        else:
            return truncated + "..."