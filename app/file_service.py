import os
import uuid
import hashlib
import mimetypes
from typing import Optional, List, Dict, Any
from pathlib import Path
import aiofiles
import magic
from sqlalchemy.orm import Session
from fastapi import UploadFile, HTTPException
from secure_filename import secure_filename

from .models import File, User, Project, Task
from .database import get_db
from .text_extraction import TextExtractor
from .audio_processing import AudioProcessor


class FileService:
    def __init__(self, upload_dir: str = "uploads"):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(exist_ok=True)
        self.text_extractor = TextExtractor()
        self.audio_processor = AudioProcessor()
        
        # File type configurations
        self.allowed_extensions = {
            'document': ['.pdf', '.docx', '.txt', '.csv', '.md'],
            'audio': ['.mp3', '.wav', '.m4a'],
            'image': ['.jpg', '.jpeg', '.png', '.gif'],
            'other': ['.zip', '.json', '.xml']
        }
        
        self.max_file_size = 50 * 1024 * 1024  # 50MB
        
    def get_file_type(self, filename: str) -> str:
        """Determine file type category based on extension."""
        ext = Path(filename).suffix.lower()
        for file_type, extensions in self.allowed_extensions.items():
            if ext in extensions:
                return file_type
        return 'other'
    
    def validate_file(self, file: UploadFile) -> Dict[str, Any]:
        """Validate uploaded file for security and size constraints."""
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        # Check file size
        if file.size and file.size > self.max_file_size:
            raise HTTPException(
                status_code=413, 
                detail=f"File too large. Maximum size is {self.max_file_size // (1024*1024)}MB"
            )
        
        # Secure filename
        secure_name = secure_filename(file.filename)
        if not secure_name:
            raise HTTPException(status_code=400, detail="Invalid filename")
        
        # Check allowed extensions
        file_type = self.get_file_type(secure_name)
        ext = Path(secure_name).suffix.lower()
        
        all_allowed = []
        for extensions in self.allowed_extensions.values():
            all_allowed.extend(extensions)
        
        if ext not in all_allowed:
            raise HTTPException(
                status_code=415, 
                detail=f"File type not allowed. Supported: {', '.join(all_allowed)}"
            )
        
        return {
            'secure_filename': secure_name,
            'file_type': file_type,
            'extension': ext
        }
    
    async def save_file(self, file: UploadFile) -> str:
        """Save uploaded file to disk and return file path."""
        unique_filename = f"{uuid.uuid4()}{Path(file.filename).suffix}"
        file_path = self.upload_dir / unique_filename
        
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        return str(file_path)
    
    def get_file_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract file metadata using python-magic."""
        try:
            mime_type = magic.from_file(file_path, mime=True)
            file_size = os.path.getsize(file_path)
            
            return {
                'mime_type': mime_type,
                'file_size': file_size,
                'hash': self._calculate_file_hash(file_path)
            }
        except Exception as e:
            return {
                'mime_type': 'application/octet-stream',
                'file_size': os.path.getsize(file_path) if os.path.exists(file_path) else 0,
                'hash': None,
                'error': str(e)
            }
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA256 hash of file."""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    async def upload_file(
        self,
        file: UploadFile,
        uploaded_by: str,
        db: Session,
        project_id: Optional[str] = None,
        task_id: Optional[str] = None
    ) -> File:
        """Handle complete file upload process."""
        
        # Validate file
        validation_result = self.validate_file(file)
        
        # Save file to disk
        file_path = await self.save_file(file)
        
        try:
            # Get file metadata
            metadata = self.get_file_metadata(file_path)
            
            # Create file record
            file_record = File(
                filename=validation_result['secure_filename'],
                original_filename=file.filename,
                file_path=file_path,
                file_size=metadata['file_size'],
                mime_type=metadata['mime_type'],
                file_type=validation_result['file_type'],
                uploaded_by=uploaded_by,
                project_id=project_id,
                task_id=task_id,
                metadata=metadata,
                processing_status="pending"
            )
            
            db.add(file_record)
            db.commit()
            db.refresh(file_record)
            
            # Process file asynchronously
            await self.process_file(file_record, db)
            
            return file_record
            
        except Exception as e:
            # Clean up file if database operation fails
            if os.path.exists(file_path):
                os.remove(file_path)
            raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")
    
    async def process_file(self, file_record: File, db: Session):
        """Process uploaded file for text extraction or audio processing."""
        try:
            file_record.processing_status = "processing"
            db.commit()
            
            extracted_text = None
            
            if file_record.file_type == "document":
                extracted_text = await self.text_extractor.extract_text(
                    file_record.file_path, 
                    file_record.mime_type
                )
            elif file_record.file_type == "audio":
                # For audio files, we might want to extract metadata or prepare for transcription
                audio_metadata = await self.audio_processor.get_metadata(file_record.file_path)
                file_record.metadata = {**file_record.metadata, **audio_metadata}
            
            if extracted_text:
                file_record.extracted_text = extracted_text
            
            file_record.processing_status = "completed"
            db.commit()
            
        except Exception as e:
            file_record.processing_status = "failed"
            file_record.metadata = {
                **file_record.metadata, 
                'processing_error': str(e)
            }
            db.commit()
    
    def get_file(self, file_id: str, db: Session) -> Optional[File]:
        """Retrieve file record by ID."""
        return db.query(File).filter(File.id == file_id).first()
    
    def list_files(
        self,
        db: Session,
        project_id: Optional[str] = None,
        task_id: Optional[str] = None,
        file_type: Optional[str] = None,
        uploaded_by: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[File]:
        """List files with optional filters."""
        query = db.query(File)
        
        if project_id:
            query = query.filter(File.project_id == project_id)
        if task_id:
            query = query.filter(File.task_id == task_id)
        if file_type:
            query = query.filter(File.file_type == file_type)
        if uploaded_by:
            query = query.filter(File.uploaded_by == uploaded_by)
        
        return query.order_by(File.created_at.desc()).offset(offset).limit(limit).all()
    
    def delete_file(self, file_id: str, db: Session) -> bool:
        """Delete file record and physical file."""
        file_record = self.get_file(file_id, db)
        if not file_record:
            return False
        
        # Delete physical file
        if os.path.exists(file_record.file_path):
            os.remove(file_record.file_path)
        
        # Delete database record
        db.delete(file_record)
        db.commit()
        
        return True
    
    def cleanup_orphaned_files(self, db: Session) -> int:
        """Clean up files that exist on disk but not in database."""
        db_files = {f.file_path for f in db.query(File).all()}
        disk_files = set()
        
        for file_path in self.upload_dir.rglob('*'):
            if file_path.is_file():
                disk_files.add(str(file_path))
        
        orphaned_files = disk_files - db_files
        
        for file_path in orphaned_files:
            try:
                os.remove(file_path)
            except OSError:
                pass
        
        return len(orphaned_files)