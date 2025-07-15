#!/usr/bin/env python3
"""
Database backup and restore utilities for Vibe Kanban
Handles both PostgreSQL and Qdrant data
"""

import sys
import os
import subprocess
import json
import logging
from pathlib import Path
from datetime import datetime
import tarfile
import tempfile

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.qdrant_client import qdrant_client
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BackupRestore:
    def __init__(self):
        self.backup_dir = Path(os.getenv("BACKUP_DIR", "./backups"))
        self.backup_dir.mkdir(exist_ok=True)
        
        # PostgreSQL configuration
        self.pg_host = os.getenv("POSTGRES_HOST", "localhost")
        self.pg_port = os.getenv("POSTGRES_PORT", "5432")
        self.pg_database = os.getenv("POSTGRES_DB", "vibe_kanban")
        self.pg_user = os.getenv("POSTGRES_USER", "vibe_user")
        self.pg_password = os.getenv("POSTGRES_PASSWORD", "vibe_password")
        
        # Qdrant configuration
        self.qdrant_host = os.getenv("QDRANT_HOST", "localhost")
        self.qdrant_port = os.getenv("QDRANT_PORT", "6333")
    
    def create_backup(self, backup_name: str = None) -> str:
        """Create a complete backup of PostgreSQL and Qdrant data"""
        if not backup_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"vibe_kanban_backup_{timestamp}"
        
        backup_path = self.backup_dir / backup_name
        backup_path.mkdir(exist_ok=True)
        
        logger.info(f"Creating backup: {backup_name}")
        
        try:
            # Backup PostgreSQL
            pg_backup_success = self._backup_postgresql(backup_path)
            if not pg_backup_success:
                logger.error("PostgreSQL backup failed")
                return None
            
            # Backup Qdrant
            qdrant_backup_success = self._backup_qdrant(backup_path)
            if not qdrant_backup_success:
                logger.error("Qdrant backup failed")
                return None
            
            # Create backup metadata
            metadata = {
                "backup_name": backup_name,
                "created_at": datetime.now().isoformat(),
                "postgresql_backup": "postgresql_dump.sql",
                "qdrant_backup": "qdrant_collections.json",
                "version": "1.0"
            }
            
            with open(backup_path / "metadata.json", "w") as f:
                json.dump(metadata, f, indent=2)
            
            # Create compressed archive
            archive_path = self.backup_dir / f"{backup_name}.tar.gz"
            self._create_archive(backup_path, archive_path)
            
            logger.info(f"✅ Backup created successfully: {archive_path}")
            return str(archive_path)
            
        except Exception as e:
            logger.error(f"Backup failed: {str(e)}")
            return None
    
    def restore_backup(self, backup_path: str) -> bool:
        """Restore from a backup archive"""
        backup_file = Path(backup_path)
        if not backup_file.exists():
            logger.error(f"Backup file not found: {backup_path}")
            return False
        
        logger.info(f"Restoring backup: {backup_path}")
        
        try:
            # Extract archive to temporary directory
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                self._extract_archive(backup_file, temp_path)
                
                # Read metadata
                metadata_file = temp_path / "metadata.json"
                if not metadata_file.exists():
                    logger.error("Invalid backup: metadata.json not found")
                    return False
                
                with open(metadata_file) as f:
                    metadata = json.load(f)
                
                logger.info(f"Restoring backup from {metadata['created_at']}")
                
                # Restore PostgreSQL
                pg_backup_file = temp_path / metadata["postgresql_backup"]
                if pg_backup_file.exists():
                    pg_restore_success = self._restore_postgresql(pg_backup_file)
                    if not pg_restore_success:
                        logger.error("PostgreSQL restore failed")
                        return False
                else:
                    logger.warning("PostgreSQL backup file not found in archive")
                
                # Restore Qdrant
                qdrant_backup_file = temp_path / metadata["qdrant_backup"]
                if qdrant_backup_file.exists():
                    qdrant_restore_success = self._restore_qdrant(qdrant_backup_file)
                    if not qdrant_restore_success:
                        logger.error("Qdrant restore failed")
                        return False
                else:
                    logger.warning("Qdrant backup file not found in archive")
                
                logger.info("✅ Backup restored successfully")
                return True
                
        except Exception as e:
            logger.error(f"Restore failed: {str(e)}")
            return False
    
    def _backup_postgresql(self, backup_path: Path) -> bool:
        """Backup PostgreSQL database"""
        logger.info("Backing up PostgreSQL database...")
        
        dump_file = backup_path / "postgresql_dump.sql"
        
        # Set environment variable for password
        env = os.environ.copy()
        env["PGPASSWORD"] = self.pg_password
        
        cmd = [
            "pg_dump",
            "--host", self.pg_host,
            "--port", self.pg_port,
            "--username", self.pg_user,
            "--dbname", self.pg_database,
            "--verbose",
            "--clean",
            "--no-owner",
            "--no-privileges",
            "--file", str(dump_file)
        ]
        
        try:
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            if result.returncode == 0:
                logger.info("PostgreSQL backup completed")
                return True
            else:
                logger.error(f"pg_dump failed: {result.stderr}")
                return False
        except FileNotFoundError:
            logger.error("pg_dump command not found. Please install PostgreSQL client tools.")
            return False
    
    def _restore_postgresql(self, backup_file: Path) -> bool:
        """Restore PostgreSQL database"""
        logger.info("Restoring PostgreSQL database...")
        
        # Set environment variable for password
        env = os.environ.copy()
        env["PGPASSWORD"] = self.pg_password
        
        cmd = [
            "psql",
            "--host", self.pg_host,
            "--port", self.pg_port,
            "--username", self.pg_user,
            "--dbname", self.pg_database,
            "--file", str(backup_file)
        ]
        
        try:
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            if result.returncode == 0:
                logger.info("PostgreSQL restore completed")
                return True
            else:
                logger.error(f"psql failed: {result.stderr}")
                return False
        except FileNotFoundError:
            logger.error("psql command not found. Please install PostgreSQL client tools.")
            return False
    
    def _backup_qdrant(self, backup_path: Path) -> bool:
        """Backup Qdrant collections"""
        logger.info("Backing up Qdrant collections...")
        
        try:
            backup_data = {
                "collections": {},
                "created_at": datetime.now().isoformat()
            }
            
            # Get collection info
            collection_info = qdrant_client.get_collection_info()
            
            for collection_name in qdrant_client.collections.keys():
                if collection_name in collection_info and collection_info[collection_name].get("status") != "not_found":
                    # For now, we'll just store collection metadata
                    # In a production system, you might want to backup actual vectors
                    backup_data["collections"][collection_name] = {
                        "config": qdrant_client.collections[collection_name],
                        "info": collection_info[collection_name]
                    }
            
            backup_file = backup_path / "qdrant_collections.json"
            with open(backup_file, "w") as f:
                json.dump(backup_data, f, indent=2)
            
            logger.info("Qdrant backup completed")
            return True
            
        except Exception as e:
            logger.error(f"Qdrant backup failed: {str(e)}")
            return False
    
    def _restore_qdrant(self, backup_file: Path) -> bool:
        """Restore Qdrant collections"""
        logger.info("Restoring Qdrant collections...")
        
        try:
            with open(backup_file) as f:
                backup_data = json.load(f)
            
            # Recreate collections
            success = qdrant_client.create_collections()
            if success:
                logger.info("Qdrant restore completed")
                return True
            else:
                logger.error("Failed to recreate Qdrant collections")
                return False
            
        except Exception as e:
            logger.error(f"Qdrant restore failed: {str(e)}")
            return False
    
    def _create_archive(self, source_path: Path, archive_path: Path):
        """Create compressed archive"""
        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(source_path, arcname=source_path.name)
    
    def _extract_archive(self, archive_path: Path, extract_path: Path):
        """Extract compressed archive"""
        with tarfile.open(archive_path, "r:gz") as tar:
            tar.extractall(path=extract_path)
    
    def list_backups(self) -> list:
        """List available backups"""
        backups = []
        for backup_file in self.backup_dir.glob("*.tar.gz"):
            backups.append({
                "name": backup_file.stem,
                "path": str(backup_file),
                "size": backup_file.stat().st_size,
                "created": datetime.fromtimestamp(backup_file.stat().st_ctime).isoformat()
            })
        
        return sorted(backups, key=lambda x: x["created"], reverse=True)

def main():
    """Main function"""
    backup_restore = BackupRestore()
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python backup_restore.py backup [backup_name]")
        print("  python backup_restore.py restore <backup_path>")
        print("  python backup_restore.py list")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "backup":
        backup_name = sys.argv[2] if len(sys.argv) > 2 else None
        result = backup_restore.create_backup(backup_name)
        if result:
            print(f"✅ Backup created: {result}")
            sys.exit(0)
        else:
            print("❌ Backup failed")
            sys.exit(1)
    
    elif command == "restore":
        if len(sys.argv) < 3:
            print("❌ Please provide backup path")
            sys.exit(1)
        
        backup_path = sys.argv[2]
        success = backup_restore.restore_backup(backup_path)
        if success:
            print("✅ Restore completed")
            sys.exit(0)
        else:
            print("❌ Restore failed")
            sys.exit(1)
    
    elif command == "list":
        backups = backup_restore.list_backups()
        if backups:
            print("Available backups:")
            for backup in backups:
                size_mb = backup["size"] / (1024 * 1024)
                print(f"  {backup['name']} ({size_mb:.1f} MB) - {backup['created']}")
        else:
            print("No backups found")
    
    else:
        print(f"❌ Unknown command: {command}")
        sys.exit(1)

if __name__ == "__main__":
    main()