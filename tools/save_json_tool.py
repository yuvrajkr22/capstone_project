import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from loguru import logger
import hashlib
from datetime import datetime

class JSONSaveTool:
    """
    Enhanced JSON Save Tool for robust file operations with validation, backup, and versioning
    Supports automatic directory creation, data validation, and backup management
    """
    
    def __init__(self, base_path: str = "data", backup_enabled: bool = True, max_backups: int = 5):
        self.base_path = Path(base_path)
        self.backup_enabled = backup_enabled
        self.max_backups = max_backups
        self.backup_dir = self.base_path / "backups"
        
        # Ensure base directories exist
        self.base_path.mkdir(parents=True, exist_ok=True)
        if self.backup_enabled:
            self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Operation statistics
        self.stats = {
            'total_saves': 0,
            'total_backups': 0,
            'total_errors': 0,
            'last_operation': None
        }
        
        logger.info(f"JSONSaveTool initialized - Base path: {self.base_path}")

    def save_to_file(self, 
                    file_path: str, 
                    data: Union[Dict, List], 
                    ensure_ascii: bool = False,
                    indent: int = 2,
                    backup: bool = True) -> Dict[str, Any]:
        """
        Save data to JSON file with enhanced features
        
        Args:
            file_path: Path to save file (relative to base_path)
            data: Data to save (dict or list)
            ensure_ascii: Ensure ASCII output
            indent: JSON indentation
            backup: Whether to create backup
            
        Returns:
            Operation result with metadata
        """
        start_time = time.time()
        full_path = self.base_path / file_path
        
        logger.info(f"Saving data to: {full_path}")
        
        try:
            # Validate input data
            validation_result = self._validate_data(data)
            if not validation_result['valid']:
                raise ValueError(f"Data validation failed: {validation_result['errors']}")
            
            # Create directory if it doesn't exist
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create backup if requested and file exists
            if backup and self.backup_enabled and full_path.exists():
                self._create_backup(full_path)
            
            # Prepare data for saving
            prepared_data = self._prepare_data_for_saving(data)
            
            # Save to file with atomic write (write to temp file then rename)
            temp_path = full_path.with_suffix('.tmp')
            
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(prepared_data, f, ensure_ascii=ensure_ascii, indent=indent)
            
            # Atomic replace
            temp_path.replace(full_path)
            
            # Calculate file hash for integrity checking
            file_hash = self._calculate_file_hash(full_path)
            
            # Update statistics
            self._update_stats('save', True)
            
            operation_time = time.time() - start_time
            
            logger.info(f"Successfully saved {len(str(prepared_data))} bytes to {full_path} in {operation_time:.2f}s")
            
            return {
                'status': 'success',
                'file_path': str(full_path),
                'file_size': len(str(prepared_data)),
                'data_hash': file_hash,
                'backup_created': backup and full_path.exists(),
                'operation_time': operation_time,
                'timestamp': time.time()
            }
            
        except Exception as e:
            self._update_stats('save', False)
            logger.error(f"Failed to save data to {full_path}: {e}")
            
            return {
                'status': 'error',
                'file_path': str(full_path),
                'error': str(e),
                'operation_time': time.time() - start_time,
                'timestamp': time.time()
            }

    def append_to_file(self, 
                      file_path: str, 
                      data: Union[Dict, List], 
                      max_entries: Optional[int] = None) -> Dict[str, Any]:
        """
        Append data to JSON file, handling both list and object structures
        
        Args:
            file_path: Path to file (relative to base_path)
            data: Data to append
            max_entries: Maximum entries to keep (for list files)
            
        Returns:
            Operation result
        """
        start_time = time.time()
        full_path = self.base_path / file_path
        
        logger.info(f"Appending data to: {full_path}")
        
        try:
            # Read existing data if file exists
            existing_data = []
            if full_path.exists():
                existing_data = self.load_from_file(file_path)
                if not isinstance(existing_data, list):
                    # Convert single object to list
                    existing_data = [existing_data]
            
            # Append new data
            if isinstance(data, list):
                existing_data.extend(data)
            else:
                existing_data.append(data)
            
            # Apply entry limit if specified
            if max_entries and len(existing_data) > max_entries:
                existing_data = existing_data[-max_entries:]
                logger.debug(f"Trimmed data to {max_entries} entries")
            
            # Save updated data
            result = self.save_to_file(file_path, existing_data, backup=True)
            result['operation'] = 'append'
            result['entries_count'] = len(existing_data)
            result['entries_added'] = len(data) if isinstance(data, list) else 1
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to append data to {full_path}: {e}")
            return {
                'status': 'error',
                'file_path': str(full_path),
                'error': str(e),
                'operation_time': time.time() - start_time,
                'timestamp': time.time()
            }

    def load_from_file(self, 
                      file_path: str, 
                      default: Any = None,
                      validate: bool = True) -> Any:
        """
        Load data from JSON file with error handling and validation
        
        Args:
            file_path: Path to file (relative to base_path)
            default: Default value if file doesn't exist or can't be read
            validate: Whether to validate loaded data
            
        Returns:
            Loaded data or default value
        """
        full_path = self.base_path / file_path
        
        if not full_path.exists():
            logger.debug(f"File not found: {full_path}, returning default")
            return default
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Validate loaded data if requested
            if validate:
                validation_result = self._validate_data(data)
                if not validation_result['valid']:
                    logger.warning(f"Loaded data validation failed: {validation_result['errors']}")
                    # Still return data but log warning
            
            logger.debug(f"Successfully loaded data from {full_path}")
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in {full_path}: {e}")
            # Try to create backup of corrupted file
            if self.backup_enabled:
                corrupted_backup = self.backup_dir / f"corrupted_{full_path.name}_{int(time.time())}.json"
                full_path.rename(corrupted_backup)
                logger.info(f"Backed up corrupted file to {corrupted_backup}")
            
            return default
        except Exception as e:
            logger.error(f"Failed to load data from {full_path}: {e}")
            return default

    def _validate_data(self, data: Any) -> Dict[str, Any]:
        """
        Validate data before saving
        
        Args:
            data: Data to validate
            
        Returns:
            Validation result
        """
        errors = []
        
        if data is None:
            errors.append("Data cannot be None")
        
        # Check if data is JSON serializable
        try:
            json.dumps(data)
        except (TypeError, ValueError) as e:
            errors.append(f"Data not JSON serializable: {e}")
        
        # Check for circular references (basic check)
        if isinstance(data, (dict, list)):
            try:
                # This will fail if there are circular references
                json.dumps(data)
            except ValueError as e:
                if "circular" in str(e).lower():
                    errors.append("Circular reference detected in data")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'data_type': type(data).__name__
        }

    def _prepare_data_for_saving(self, data: Union[Dict, List]) -> Union[Dict, List]:
        """
        Prepare data for saving by adding metadata and handling special types
        
        Args:
            data: Original data
            
        Returns:
            Prepared data with metadata
        """
        prepared_data = data
        
        # Add metadata for tracking
        if isinstance(data, dict):
            prepared_data = data.copy()
            prepared_data['_metadata'] = {
                'saved_at': time.time(),
                'saved_at_iso': datetime.utcnow().isoformat(),
                'tool_version': '1.0',
                'data_hash': self._calculate_data_hash(data)
            }
        elif isinstance(data, list):
            # For lists, we might want to add metadata differently
            # Here we'll create a wrapper object
            prepared_data = {
                '_items': data,
                '_metadata': {
                    'saved_at': time.time(),
                    'saved_at_iso': datetime.utcnow().isoformat(),
                    'tool_version': '1.0',
                    'item_count': len(data),
                    'data_hash': self._calculate_data_hash(data)
                }
            }
        
        return prepared_data

    def _calculate_data_hash(self, data: Any) -> str:
        """Calculate hash of data for integrity checking"""
        data_string = json.dumps(data, sort_keys=True)
        return hashlib.md5(data_string.encode()).hexdigest()

    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate MD5 hash of file contents"""
        try:
            with open(file_path, 'rb') as f:
                file_hash = hashlib.md5()
                for chunk in iter(lambda: f.read(4096), b""):
                    file_hash.update(chunk)
                return file_hash.hexdigest()
        except Exception as e:
            logger.warning(f"Failed to calculate file hash for {file_path}: {e}")
            return "unknown"

    def _create_backup(self, file_path: Path):
        """Create backup of existing file"""
        try:
            timestamp = int(time.time())
            backup_name = f"{file_path.stem}_backup_{timestamp}{file_path.suffix}"
            backup_path = self.backup_dir / backup_name
            
            # Copy file to backup location
            import shutil
            shutil.copy2(file_path, backup_path)
            
            # Manage backup count
            self._cleanup_old_backups(file_path.stem)
            
            self.stats['total_backups'] += 1
            logger.debug(f"Created backup: {backup_path}")
            
        except Exception as e:
            logger.warning(f"Failed to create backup for {file_path}: {e}")

    def _cleanup_old_backups(self, file_stem: str):
        """Clean up old backups beyond the maximum count"""
        try:
            backup_pattern = f"{file_stem}_backup_*"
            backups = sorted(self.backup_dir.glob(backup_pattern))
            
            if len(backups) > self.max_backups:
                # Remove oldest backups
                backups_to_remove = backups[:-self.max_backups]
                for backup in backups_to_remove:
                    backup.unlink()
                    logger.debug(f"Removed old backup: {backup}")
                    
        except Exception as e:
            logger.warning(f"Failed to cleanup old backups: {e}")

    def _update_stats(self, operation: str, success: bool):
        """Update operation statistics"""
        self.stats['total_saves'] += 1
        if not success:
            self.stats['total_errors'] += 1
        self.stats['last_operation'] = time.time()

    def list_files(self, pattern: str = "*.json") -> List[Dict[str, Any]]:
        """
        List JSON files in base directory
        
        Args:
            pattern: File pattern to match
            
        Returns:
            List of file information
        """
        files_info = []
        
        try:
            for file_path in self.base_path.rglob(pattern):
                if file_path.is_file():
                    stat = file_path.stat()
                    files_info.append({
                        'path': str(file_path.relative_to(self.base_path)),
                        'size': stat.st_size,
                        'modified': stat.st_mtime,
                        'modified_iso': datetime.fromtimestamp(stat.st_mtime).isoformat()
                    })
            
            return sorted(files_info, key=lambda x: x['modified'], reverse=True)
            
        except Exception as e:
            logger.error(f"Failed to list files: {e}")
            return []

    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """
        Get detailed information about a file
        
        Args:
            file_path: Path to file (relative to base_path)
            
        Returns:
            File information
        """
        full_path = self.base_path / file_path
        
        if not full_path.exists():
            return {'error': 'File not found'}
        
        try:
            stat = full_path.stat()
            file_hash = self._calculate_file_hash(full_path)
            
            # Try to load data to get basic info
            data = self.load_from_file(file_path, default=None, validate=False)
            
            return {
                'path': str(full_path),
                'exists': True,
                'size': stat.st_size,
                'modified': stat.st_mtime,
                'modified_iso': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'file_hash': file_hash,
                'data_type': type(data).__name__ if data else 'unknown',
                'data_length': len(data) if hasattr(data, '__len__') else None,
                'backups_count': len(list(self.backup_dir.glob(f"{full_path.stem}_backup_*")))
            }
            
        except Exception as e:
            return {'error': str(e)}

    def delete_file(self, file_path: str, create_backup: bool = True) -> Dict[str, Any]:
        """
        Delete a file with optional backup
        
        Args:
            file_path: Path to file (relative to base_path)
            create_backup: Whether to create backup before deletion
            
        Returns:
            Operation result
        """
        full_path = self.base_path / file_path
        
        if not full_path.exists():
            return {'status': 'error', 'error': 'File not found'}
        
        try:
            # Create backup if requested
            if create_backup and self.backup_enabled:
                self._create_backup(full_path)
            
            # Delete file
            full_path.unlink()
            
            logger.info(f"Deleted file: {full_path}")
            return {
                'status': 'success',
                'file_path': str(full_path),
                'backup_created': create_backup,
                'timestamp': time.time()
            }
            
        except Exception as e:
            logger.error(f"Failed to delete file {full_path}: {e}")
            return {
                'status': 'error',
                'file_path': str(full_path),
                'error': str(e),
                'timestamp': time.time()
            }

    def get_statistics(self) -> Dict[str, Any]:
        """Get tool statistics and health information"""
        total_files = len(list(self.base_path.rglob("*.json")))
        total_backups = len(list(self.backup_dir.glob("*.json"))) if self.backup_enabled else 0
        total_size = sum(f.stat().st_size for f in self.base_path.rglob("*.json"))
        
        return {
            'base_path': str(self.base_path),
            'backup_enabled': self.backup_enabled,
            'max_backups': self.max_backups,
            'file_count': total_files,
            'backup_count': total_backups,
            'total_size_bytes': total_size,
            'operations': self.stats,
            'health': {
                'directory_writable': self._check_directory_writable(),
                'backup_directory_writable': self._check_backup_directory_writable() if self.backup_enabled else True,
                'storage_usage_percent': self._calculate_storage_usage()
            }
        }

    def _check_directory_writable(self) -> bool:
        """Check if base directory is writable"""
        try:
            test_file = self.base_path / ".write_test"
            test_file.touch()
            test_file.unlink()
            return True
        except Exception:
            return False

    def _check_backup_directory_writable(self) -> bool:
        """Check if backup directory is writable"""
        try:
            test_file = self.backup_dir / ".write_test"
            test_file.touch()
            test_file.unlink()
            return True
        except Exception:
            return False

    def _calculate_storage_usage(self) -> float:
        """Calculate storage usage percentage (simplified)"""
        try:
            # This is a simplified calculation
            # In production, you might want to check actual disk usage
            total_size = sum(f.stat().st_size for f in self.base_path.rglob("*"))
            return min(100.0, total_size / (1024 * 1024))  # Assume 1MB = 100% for demo
        except Exception:
            return 0.0

# Legacy function for backward compatibility
def save_to_file(path: str, data: dict) -> bool:
    """
    Legacy function for simple JSON saving
    Maintains compatibility with existing code
    
    Args:
        path: File path
        data: Data to save
        
    Returns:
        Success status
    """
    tool = JSONSaveTool()
    result = tool.save_to_file(path, data)
    return result['status'] == 'success'
  
