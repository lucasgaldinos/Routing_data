# GitHub Issue Title: Implement TSPLIB95 ETL System - Phase 3 Advanced Features

## Issue Description

@copilot #github-pull-request_copilot-coding-agent

We need to implement **Phase 3** of our TSPLIB95 ETL system - the advanced features that transform our ETL pipeline into a production-ready, high-performance system. This phase adds parallel processing, comprehensive CLI interface, and incremental update capabilities.

### Prerequisites

**Phases 1 and 2 must be complete and working** with these components:

- ✅ **Phase 1**: Parser integration, database foundation, basic utilities, simple CLI
- ✅ **Phase 2**: File scanner, data transformer, JSON writer, directory processing
- ✅ Integration tests passing for both single files and directory batches
- ✅ JSON output working with organized directory structure
- ✅ Database operations handling multiple problems correctly

### Project Background

- Repository contains a vendored copy of `tsplib95` library under `src/tsplib95/`
- Phases 1-2 provide: complete parsing pipeline + batch processing + JSON output
- **Phase 3 adds**: parallel processing + production CLI + incremental updates + monitoring
- **Target outcome**: Production-ready ETL system capable of processing large datasets efficiently

### Environment Setup

- Python ≥ 3.11 required
- Dependencies from Phases 1-2: `uv add duckdb networkx click tabulate deprecated pytest pyyaml`
- Additional for Phase 3: `uv add psutil rich tqdm` (for monitoring and progress display)

## Phase 3 Implementation Requirements

### 3.1 Parallel Processing System

**Create `src/converter/utils/parallel.py`**:

```python
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from typing import List, Dict, Any, Callable, Iterator, Optional, Tuple
import threading
import logging
from queue import Queue, Empty
import time
import psutil
from dataclasses import dataclass

@dataclass
class ProcessingResult:
    """Result of parallel processing operation."""
    file_path: str
    status: str  # 'success', 'error', 'skipped'
    problem_id: Optional[int] = None
    json_path: Optional[str] = None
    error_message: Optional[str] = None
    processing_time: float = 0.0
    memory_used: int = 0

class ParallelProcessor:
    """
    Production-grade parallel processing for TSPLIB conversion.
    
    Provides thread-safe processing with resource management, progress tracking,
    and comprehensive error handling for large-scale ETL operations.
    """
    
    def __init__(self, max_workers: int = 4, batch_size: int = 100,
                 memory_limit_mb: int = 2048, 
                 use_processes: bool = False,
                 logger: Optional[logging.Logger] = None):
        self.max_workers = max_workers
        self.batch_size = batch_size 
        self.memory_limit_mb = memory_limit_mb
        self.use_processes = use_processes  # Thread vs Process based
        self.logger = logger or logging.getLogger(__name__)
        
        # Progress tracking
        self._progress_queue = Queue()
        self._total_items = 0
        self._completed_items = 0
        self._failed_items = 0
        self._start_time = None
        
        # Resource monitoring
        self._memory_warnings = 0
        self._max_memory_used = 0
        
        # Thread safety
        self._lock = threading.Lock()
        
    def process_files_parallel(self, file_list: List[str], 
                              process_func: Callable[[str], ProcessingResult],
                              progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        Process files in parallel with comprehensive monitoring and error handling.
        
        Args:
            file_list: List of file paths to process
            process_func: Function that processes a single file and returns ProcessingResult
            progress_callback: Optional callback for progress updates
            
        Returns:
            {
                'results': List[ProcessingResult],
                'summary': {
                    'total': int,
                    'successful': int,
                    'failed': int,
                    'skipped': int,
                    'processing_time': float,
                    'throughput': float,  # files per second
                    'memory_stats': dict
                }
            }
        """
        self._total_items = len(file_list)
        self._completed_items = 0
        self._failed_items = 0
        self._start_time = time.time()
        
        results = []
        executor_class = ProcessPoolExecutor if self.use_processes else ThreadPoolExecutor
        
        try:
            with executor_class(max_workers=self.max_workers) as executor:
                # Submit all tasks
                future_to_file = {
                    executor.submit(self._safe_process_file, file_path, process_func): file_path
                    for file_path in file_list
                }
                
                # Process results as they complete
                for future in as_completed(future_to_file):
                    file_path = future_to_file[future]
                    
                    try:
                        result = future.result()
                        results.append(result)
                        
                        if result.status == 'success':
                            self._completed_items += 1
                        else:
                            self._failed_items += 1
                        
                        # Update progress
                        if progress_callback:
                            progress_callback(self._completed_items + self._failed_items, self._total_items)
                        
                        # Monitor memory
                        self._check_memory_usage()
                        
                    except Exception as e:
                        # Handle executor-level errors
                        error_result = ProcessingResult(
                            file_path=file_path,
                            status='error',
                            error_message=f"Executor error: {str(e)}"
                        )
                        results.append(error_result)
                        self._failed_items += 1
                        
                        self.logger.error(f"Executor error for {file_path}: {e}")
            
            # Generate summary
            end_time = time.time()
            processing_time = end_time - self._start_time
            
            summary = {
                'total': len(results),
                'successful': len([r for r in results if r.status == 'success']),
                'failed': len([r for r in results if r.status == 'error']),
                'skipped': len([r for r in results if r.status == 'skipped']),
                'processing_time': processing_time,
                'throughput': len(results) / processing_time if processing_time > 0 else 0,
                'memory_stats': {
                    'max_memory_mb': self._max_memory_used,
                    'memory_warnings': self._memory_warnings,
                    'current_memory_mb': self._get_memory_usage()
                }
            }
            
            return {
                'results': results,
                'summary': summary
            }
            
        except Exception as e:
            self.logger.error(f"Parallel processing failed: {e}")
            raise
    
    def _safe_process_file(self, file_path: str, 
                          process_func: Callable[[str], ProcessingResult]) -> ProcessingResult:
        """Safely process single file with error handling and monitoring."""
        start_time = time.time()
        start_memory = self._get_memory_usage()
        
        try:
            # Call the actual processing function
            result = process_func(file_path)
            
            # Add timing and memory info
            result.processing_time = time.time() - start_time
            result.memory_used = self._get_memory_usage() - start_memory
            
            return result
            
        except Exception as e:
            # Create error result
            return ProcessingResult(
                file_path=file_path,
                status='error',
                error_message=str(e),
                processing_time=time.time() - start_time,
                memory_used=self._get_memory_usage() - start_memory
            )
    
    def _get_memory_usage(self) -> int:
        """Get current memory usage in MB."""
        try:
            process = psutil.Process()
            memory_mb = process.memory_info().rss // (1024 * 1024)
            
            # Update max memory tracking
            with self._lock:
                if memory_mb > self._max_memory_used:
                    self._max_memory_used = memory_mb
            
            return memory_mb
        except Exception:
            return 0
    
    def _check_memory_usage(self):
        """Monitor memory usage and log warnings."""
        current_memory = self._get_memory_usage()
        
        if current_memory > self.memory_limit_mb:
            with self._lock:
                self._memory_warnings += 1
            
            self.logger.warning(f"Memory usage ({current_memory}MB) exceeds limit ({self.memory_limit_mb}MB)")
    
    def process_batches_parallel(self, batches: Iterator[List[str]], 
                               process_func: Callable[[str], ProcessingResult],
                               progress_callback: Optional[Callable] = None) -> Iterator[Dict[str, Any]]:
        """Process batches in parallel, yielding results as they complete."""
        batch_number = 0
        
        for batch in batches:
            batch_number += 1
            
            self.logger.info(f"Processing batch {batch_number} with {len(batch)} files")
            
            # Process batch in parallel
            batch_result = self.process_files_parallel(batch, process_func, progress_callback)
            
            # Add batch metadata
            batch_result['batch_number'] = batch_number
            batch_result['batch_size'] = len(batch)
            
            yield batch_result
    
    def estimate_processing_time(self, total_files: int, 
                               sample_processing_time: float = None) -> Dict[str, float]:
        """Estimate processing time based on file count and sample timing."""
        if sample_processing_time is None:
            # Use conservative estimate of 1 second per file
            sample_processing_time = 1.0
        
        # Account for parallelization
        parallel_efficiency = 0.7  # Assume 70% efficiency due to overhead
        
        sequential_time = total_files * sample_processing_time
        parallel_time = sequential_time / (self.max_workers * parallel_efficiency)
        
        return {
            'sequential_estimate_seconds': sequential_time,
            'parallel_estimate_seconds': parallel_time,
            'parallel_estimate_minutes': parallel_time / 60,
            'speedup_factor': sequential_time / parallel_time if parallel_time > 0 else 1
        }
    
    def get_system_resources(self) -> Dict[str, Any]:
        """Get current system resource information."""
        try:
            cpu_count = psutil.cpu_count()
            cpu_usage = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            
            return {
                'cpu_count': cpu_count,
                'cpu_usage_percent': cpu_usage,
                'memory_total_mb': memory.total // (1024 * 1024),
                'memory_available_mb': memory.available // (1024 * 1024),
                'memory_usage_percent': memory.percent,
                'recommended_workers': min(cpu_count, 8)  # Cap at 8 for I/O bound tasks
            }
        except Exception as e:
            self.logger.warning(f"Could not get system resources: {e}")
            return {'error': str(e)}
```

### 3.2 Incremental Update System

**Create `src/converter/utils/update.py`**:

```python
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Set
import logging
import hashlib
import pickle
from datetime import datetime
import sqlite3
import json

from ..database.operations import DatabaseManager
from ..utils.exceptions import ConverterError

class UpdateManager:
    """
    Manage incremental updates and change detection for TSPLIB files.
    
    Tracks file modifications, manages incremental processing,
    and provides rollback capabilities for interrupted updates.
    """
    
    def __init__(self, database_manager: DatabaseManager, 
                 cache_path: str = "./cache/update_cache.db",
                 logger: Optional[logging.Logger] = None):
        self.db_manager = database_manager
        self.cache_path = Path(cache_path)
        self.logger = logger or logging.getLogger(__name__)
        
        # Ensure cache directory exists
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize cache database
        self._initialize_cache()
    
    def _initialize_cache(self):
        """Initialize SQLite cache for tracking file states."""
        try:
            with sqlite3.connect(str(self.cache_path)) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS file_cache (
                        file_path TEXT PRIMARY KEY,
                        last_modified REAL,
                        file_size INTEGER,
                        content_hash TEXT,
                        last_processed TEXT,
                        problem_id INTEGER,
                        processing_status TEXT,
                        error_count INTEGER DEFAULT 0
                    )
                """)
                
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS processing_sessions (
                        session_id TEXT PRIMARY KEY,
                        start_time TEXT,
                        end_time TEXT,
                        files_processed INTEGER,
                        files_failed INTEGER,
                        status TEXT,
                        summary TEXT
                    )
                """)
                
                conn.commit()
                
        except Exception as e:
            raise ConverterError(f"Failed to initialize update cache: {e}")
    
    def detect_changes(self, file_paths: List[str]) -> Dict[str, List[str]]:
        """
        Detect changes in list of files compared to cache.
        
        Returns:
            {
                'new': List[str],        # New files not in cache
                'modified': List[str],   # Files with changes
                'unchanged': List[str],  # Files with no changes
                'deleted': List[str]     # Files in cache but not found
            }
        """
        changes = {
            'new': [],
            'modified': [],
            'unchanged': [],
            'deleted': []
        }
        
        try:
            with sqlite3.connect(str(self.cache_path)) as conn:
                # Get cached file info
                cached_files = {}
                cursor = conn.execute("SELECT file_path, last_modified, file_size, content_hash FROM file_cache")
                for row in cursor:
                    cached_files[row[0]] = {
                        'last_modified': row[1],
                        'file_size': row[2],
                        'content_hash': row[3]
                    }
                
                # Check each current file
                current_file_set = set(file_paths)
                
                for file_path in file_paths:
                    if not Path(file_path).exists():
                        continue
                    
                    file_stat = Path(file_path).stat()
                    current_modified = file_stat.st_mtime
                    current_size = file_stat.st_size
                    
                    if file_path not in cached_files:
                        # New file
                        changes['new'].append(file_path)
                    else:
                        cached_info = cached_files[file_path]
                        
                        # Quick check: modification time and size
                        if (current_modified != cached_info['last_modified'] or 
                            current_size != cached_info['file_size']):
                            
                            # Double-check with content hash
                            current_hash = self._calculate_file_hash(file_path)
                            if current_hash != cached_info['content_hash']:
                                changes['modified'].append(file_path)
                            else:
                                changes['unchanged'].append(file_path)
                        else:
                            changes['unchanged'].append(file_path)
                
                # Find deleted files (in cache but not in current list)
                cached_file_set = set(cached_files.keys())
                deleted_files = cached_file_set - current_file_set
                
                for deleted_file in deleted_files:
                    if not Path(deleted_file).exists():
                        changes['deleted'].append(deleted_file)
        
        except Exception as e:
            self.logger.error(f"Change detection failed: {e}")
            # If cache fails, treat all files as new
            changes['new'] = file_paths
            changes['modified'] = []
            changes['unchanged'] = []
            changes['deleted'] = []
        
        self.logger.info(f"Change detection: {len(changes['new'])} new, "
                        f"{len(changes['modified'])} modified, "
                        f"{len(changes['unchanged'])} unchanged, "
                        f"{len(changes['deleted'])} deleted")
        
        return changes
    
    def update_file_cache(self, file_path: str, problem_id: Optional[int] = None, 
                         status: str = 'success', error_message: str = None):
        """Update cache entry for a processed file."""
        try:
            if not Path(file_path).exists():
                return
            
            file_stat = Path(file_path).stat()
            content_hash = self._calculate_file_hash(file_path)
            
            with sqlite3.connect(str(self.cache_path)) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO file_cache 
                    (file_path, last_modified, file_size, content_hash, 
                     last_processed, problem_id, processing_status, error_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 
                            COALESCE((SELECT error_count FROM file_cache WHERE file_path = ?), 0) + 
                            CASE WHEN ? = 'error' THEN 1 ELSE 0 END)
                """, [
                    file_path, file_stat.st_mtime, file_stat.st_size, content_hash,
                    datetime.now().isoformat(), problem_id, status, file_path, status
                ])
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Failed to update file cache for {file_path}: {e}")
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA-256 hash of file content."""
        try:
            hasher = hashlib.sha256()
            with open(file_path, 'rb') as f:
                # Read in chunks to handle large files
                for chunk in iter(lambda: f.read(8192), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception as e:
            self.logger.warning(f"Could not calculate hash for {file_path}: {e}")
            return "unknown"
    
    def create_processing_session(self) -> str:
        """Create new processing session and return session ID."""
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            with sqlite3.connect(str(self.cache_path)) as conn:
                conn.execute("""
                    INSERT INTO processing_sessions (session_id, start_time, status)
                    VALUES (?, ?, 'running')
                """, [session_id, datetime.now().isoformat()])
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Failed to create processing session: {e}")
        
        return session_id
    
    def complete_processing_session(self, session_id: str, 
                                  files_processed: int, files_failed: int,
                                  summary: Dict[str, Any] = None):
        """Complete processing session with results."""
        try:
            with sqlite3.connect(str(self.cache_path)) as conn:
                conn.execute("""
                    UPDATE processing_sessions 
                    SET end_time = ?, files_processed = ?, files_failed = ?, 
                        status = 'completed', summary = ?
                    WHERE session_id = ?
                """, [
                    datetime.now().isoformat(), files_processed, files_failed,
                    json.dumps(summary) if summary else None, session_id
                ])
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Failed to complete processing session: {e}")
    
    def get_failed_files(self, max_error_count: int = 3) -> List[str]:
        """Get list of files that have failed processing multiple times."""
        failed_files = []
        
        try:
            with sqlite3.connect(str(self.cache_path)) as conn:
                cursor = conn.execute("""
                    SELECT file_path, error_count 
                    FROM file_cache 
                    WHERE processing_status = 'error' AND error_count < ?
                    ORDER BY error_count, last_processed
                """, [max_error_count])
                
                failed_files = [row[0] for row in cursor]
                
        except Exception as e:
            self.logger.error(f"Failed to get failed files: {e}")
        
        return failed_files
    
    def get_processing_statistics(self) -> Dict[str, Any]:
        """Get comprehensive processing statistics from cache."""
        stats = {
            'total_files_tracked': 0,
            'successful_files': 0,
            'failed_files': 0,
            'pending_files': 0,
            'recent_sessions': [],
            'error_summary': {}
        }
        
        try:
            with sqlite3.connect(str(self.cache_path)) as conn:
                # File statistics
                cursor = conn.execute("""
                    SELECT processing_status, COUNT(*) 
                    FROM file_cache 
                    GROUP BY processing_status
                """)
                
                for status, count in cursor:
                    stats['total_files_tracked'] += count
                    if status == 'success':
                        stats['successful_files'] = count
                    elif status == 'error':
                        stats['failed_files'] = count
                    elif status is None:
                        stats['pending_files'] = count
                
                # Recent sessions
                cursor = conn.execute("""
                    SELECT session_id, start_time, end_time, files_processed, files_failed, status
                    FROM processing_sessions 
                    ORDER BY start_time DESC 
                    LIMIT 10
                """)
                
                stats['recent_sessions'] = [
                    {
                        'session_id': row[0],
                        'start_time': row[1],
                        'end_time': row[2],
                        'files_processed': row[3],
                        'files_failed': row[4],
                        'status': row[5]
                    }
                    for row in cursor
                ]
                
                # Error analysis
                cursor = conn.execute("""
                    SELECT error_count, COUNT(*) 
                    FROM file_cache 
                    WHERE processing_status = 'error'
                    GROUP BY error_count
                    ORDER BY error_count
                """)
                
                for error_count, file_count in cursor:
                    stats['error_summary'][f'{error_count}_errors'] = file_count
                
        except Exception as e:
            self.logger.error(f"Failed to get processing statistics: {e}")
        
        return stats
    
    def cleanup_cache(self, keep_days: int = 30):
        """Clean up old cache entries."""
        try:
            cutoff_date = datetime.now().timestamp() - (keep_days * 24 * 3600)
            
            with sqlite3.connect(str(self.cache_path)) as conn:
                # Remove old session records
                conn.execute("""
                    DELETE FROM processing_sessions 
                    WHERE start_time < ?
                """, [datetime.fromtimestamp(cutoff_date).isoformat()])
                
                # Remove cache entries for files that no longer exist
                cursor = conn.execute("SELECT file_path FROM file_cache")
                to_remove = []
                
                for (file_path,) in cursor:
                    if not Path(file_path).exists():
                        to_remove.append(file_path)
                
                for file_path in to_remove:
                    conn.execute("DELETE FROM file_cache WHERE file_path = ?", [file_path])
                
                conn.commit()
                
                self.logger.info(f"Cleaned up {len(to_remove)} stale cache entries")
                
        except Exception as e:
            self.logger.error(f"Cache cleanup failed: {e}")
```

### 3.3 Production CLI Interface

**Update `src/converter/cli/commands.py`** to add comprehensive Phase 3 commands:

```python
# Add these imports to existing CLI file
import rich.console
import rich.table
import rich.progress
from rich.panel import Panel
from rich.columns import Columns
import sys
from datetime import datetime

# Add rich console for better output formatting
console = rich.console.Console()

@cli.command()
@click.argument('input_dir', type=click.Path(exists=True))
@click.option('--output-db', '-d', help='Database output path')
@click.option('--output-json', '-j', help='JSON output directory')
@click.option('--config', '-c', type=click.Path(), help='Configuration file')
@click.option('--workers', default=4, help='Number of parallel workers')
@click.option('--batch-size', default=100, help='Batch size for processing')
@click.option('--types', multiple=True, help='Problem types to process')
@click.option('--incremental/--full', default=True, help='Incremental vs full processing')
@click.option('--force-reprocess', is_flag=True, help='Force reprocessing of existing files')
@click.option('--memory-limit', default=2048, help='Memory limit in MB')
@click.option('--dry-run', is_flag=True, help='Show what would be processed without doing it')
def process_parallel(input_dir, output_db, output_json, config, workers, batch_size, 
                    types, incremental, force_reprocess, memory_limit, dry_run):
    """
    Process TSPLIB files with parallel processing and incremental updates.
    
    Production-grade command with full monitoring, progress tracking, and error recovery.
    
    Examples:
        converter process-parallel datasets_raw/problems --workers 8 --output-json datasets/json
        converter process-parallel datasets_raw/problems --incremental --types TSP --types VRP
        converter process-parallel datasets_raw/problems --dry-run
    """
    from ..core.scanner import FileScanner
    from ..core.parser import TSPLIBParser  
    from ..core.transformer import DataTransformer
    from ..database.operations import DatabaseManager
    from ..output.json_writer import JSONWriter
    from ..utils.parallel import ParallelProcessor, ProcessingResult
    from ..utils.update import UpdateManager
    from ..config import ConverterConfig, load_config
    from ..utils.logging import setup_logging
    
    # Load configuration
    if config:
        converter_config = load_config(config)
    else:
        converter_config = ConverterConfig()
    
    # Override with command line options
    if output_db:
        converter_config.database_path = output_db
    if batch_size:
        converter_config.batch_size = batch_size
    
    # Setup logging
    logger = setup_logging(converter_config.log_level, converter_config.log_file)
    
    # Display system information
    console.print(Panel.fit("TSPLIB95 ETL System - Parallel Processing", style="bold blue"))
    
    # Initialize components
    scanner = FileScanner(batch_size=converter_config.batch_size, logger=logger)
    parser = TSPLIBParser(logger)
    transformer = DataTransformer(logger)
    db_manager = DatabaseManager(converter_config.database_path, logger)
    parallel_processor = ParallelProcessor(
        max_workers=workers, 
        memory_limit_mb=memory_limit,
        logger=logger
    )
    
    json_writer = None
    if output_json:
        json_writer = JSONWriter(output_json, logger=logger)
    
    update_manager = None
    if incremental:
        update_manager = UpdateManager(db_manager, logger=logger)
    
    try:
        # Scan directory
        console.print("\n[cyan]Scanning directory...[/cyan]")
        
        file_patterns = [f"*.{ext}" for ext in ['tsp', 'vrp', 'atsp', 'hcp', 'sop', 'tour']]
        dir_stats = scanner.get_directory_statistics(input_dir, patterns=file_patterns)
        
        # Display scan results
        stats_table = rich.table.Table(title="Directory Scan Results")
        stats_table.add_column("Metric", style="cyan")
        stats_table.add_column("Value", style="white")
        
        stats_table.add_row("Total Files", f"{dir_stats['total_files']:,}")
        stats_table.add_row("Total Size", f"{dir_stats['total_size']:,} bytes")
        stats_table.add_row("Estimated Batches", f"{dir_stats['processing_estimate']['estimated_batches']}")
        
        console.print(stats_table)
        
        # Show breakdown by type
        if dir_stats['by_type']:
            type_table = rich.table.Table(title="Files by Problem Type")
            type_table.add_column("Type", style="cyan")
            type_table.add_column("Count", style="white")
            type_table.add_column("Size", style="white")
            
            for ptype, pstats in dir_stats['by_type'].items():
                type_table.add_row(ptype, str(pstats['count']), f"{pstats['total_size']:,} bytes")
            
            console.print(type_table)
        
        if dry_run:
            console.print("\n[yellow]Dry run mode - no processing performed[/yellow]")
            return
        
        # Collect all files for processing
        all_files = []
        for batch in scanner.scan_directory(input_dir, problem_types=list(types) if types else None):
            all_files.extend([f['file_path'] for f in batch])
        
        # Handle incremental processing
        files_to_process = all_files
        if incremental and not force_reprocess:
            console.print("\n[cyan]Detecting changes for incremental processing...[/cyan]")
            changes = update_manager.detect_changes(all_files)
            
            files_to_process = changes['new'] + changes['modified']
            
            if not files_to_process:
                console.print("[green]No changes detected - all files are up to date[/green]")
                return
            
            console.print(f"[yellow]Processing {len(files_to_process)} changed files "
                         f"({len(changes['new'])} new, {len(changes['modified'])} modified)[/yellow]")
        
        # Create processing function
        def process_single_file(file_path: str) -> ProcessingResult:
            try:
                # Parse file
                problem_data = parser.parse_file(file_path)
                
                # Transform for JSON if requested
                json_path = None
                if json_writer:
                    json_data = transformer.transform_to_json_format(problem_data)
                    json_path = json_writer.write_problem(json_data, file_path)
                
                # Insert into database
                problem_id = db_manager.insert_complete_problem(problem_data)
                
                # Update cache if incremental
                if update_manager:
                    update_manager.update_file_cache(file_path, problem_id, 'success')
                
                return ProcessingResult(
                    file_path=file_path,
                    status='success',
                    problem_id=problem_id,
                    json_path=json_path
                )
                
            except Exception as e:
                # Update cache with error if incremental
                if update_manager:
                    update_manager.update_file_cache(file_path, None, 'error', str(e))
                
                return ProcessingResult(
                    file_path=file_path,
                    status='error',
                    error_message=str(e)
                )
        
        # Process files with progress tracking
        console.print(f"\n[cyan]Processing {len(files_to_process)} files with {workers} workers...[/cyan]")
        
        # Create session for tracking
        session_id = None
        if update_manager:
            session_id = update_manager.create_processing_session()
        
        with rich.progress.Progress(
            rich.progress.TextColumn("[bold blue]{task.fields[filename]}", justify="right"),
            rich.progress.BarColumn(bar_width=None),
            "[progress.percentage]{task.percentage:>3.1f}%",
            "•", 
            rich.progress.DownloadColumn(),
            "•",
            rich.progress.TransferSpeedColumn(),
            "•",
            rich.progress.TimeRemainingColumn(),
        ) as progress:
            
            task = progress.add_task("Processing", filename="Starting...", total=len(files_to_process))
            
            def progress_callback(completed: int, total: int):
                progress.update(task, completed=completed, filename=f"File {completed}/{total}")
            
            # Process files in parallel
            result = parallel_processor.process_files_parallel(
                files_to_process, 
                process_single_file,
                progress_callback
            )
        
        # Complete session tracking
        if update_manager and session_id:
            update_manager.complete_processing_session(
                session_id, 
                result['summary']['successful'],
                result['summary']['failed'],
                result['summary']
            )
        
        # Display final results
        summary = result['summary']
        
        results_panel = Panel(
            f"[green]✓ Processed: {summary['successful']:,} files[/green]\n"
            f"[red]✗ Failed: {summary['failed']:,} files[/red]\n"
            f"[blue]⏱ Time: {summary['processing_time']:.1f} seconds[/blue]\n"
            f"[yellow]⚡ Throughput: {summary['throughput']:.1f} files/sec[/yellow]\n"
            f"[magenta]🧠 Peak Memory: {summary['memory_stats']['max_memory_mb']}MB[/magenta]",
            title="Processing Results",
            style="bold"
        )
        
        console.print(results_panel)
        
        # Show errors if any
        failed_results = [r for r in result['results'] if r.status == 'error']
        if failed_results:
            console.print("\n[red]Failed Files:[/red]")
            for fail in failed_results[:10]:  # Show first 10 errors
                console.print(f"  {fail.file_path}: {fail.error_message}")
            
            if len(failed_results) > 10:
                console.print(f"  ... and {len(failed_results) - 10} more errors")
        
    except Exception as e:
        logger.error(f"Parallel processing failed: {e}")
        console.print(f"[red]✗ Error: {e}[/red]")
        sys.exit(1)

@cli.command()
@click.option('--config', '-c', type=click.Path(), help='Configuration file')
@click.option('--detailed', is_flag=True, help='Show detailed statistics')
def system_info(config, detailed):
    """Display system information and resource usage."""
    from ..utils.parallel import ParallelProcessor
    from ..utils.update import UpdateManager
    from ..database.operations import DatabaseManager
    from ..config import ConverterConfig, load_config
    
    # Load configuration
    if config:
        converter_config = load_config(config)
    else:
        converter_config = ConverterConfig()
    
    console.print(Panel.fit("System Information", style="bold green"))
    
    # Get system resources
    parallel_processor = ParallelProcessor()
    resources = parallel_processor.get_system_resources()
    
    # System table
    system_table = rich.table.Table(title="System Resources")
    system_table.add_column("Resource", style="cyan")
    system_table.add_column("Value", style="white")
    
    system_table.add_row("CPU Cores", str(resources.get('cpu_count', 'Unknown')))
    system_table.add_row("CPU Usage", f"{resources.get('cpu_usage_percent', 0):.1f}%")
    system_table.add_row("Memory Total", f"{resources.get('memory_total_mb', 0):,} MB")
    system_table.add_row("Memory Available", f"{resources.get('memory_available_mb', 0):,} MB")
    system_table.add_row("Memory Usage", f"{resources.get('memory_usage_percent', 0):.1f}%")
    system_table.add_row("Recommended Workers", str(resources.get('recommended_workers', 4)))
    
    console.print(system_table)
    
    if detailed:
        # Database statistics
        try:
            db_manager = DatabaseManager(converter_config.database_path)
            db_stats = db_manager.get_problem_statistics()
            
            db_table = rich.table.Table(title="Database Statistics")
            db_table.add_column("Metric", style="cyan")
            db_table.add_column("Value", style="white")
            
            db_table.add_row("Total Problems", f"{db_stats['total_problems']:,}")
            db_table.add_row("Total Nodes", f"{db_stats['total_nodes']:,}")
            db_table.add_row("Total Edges", f"{db_stats['total_edges']:,}")
            
            console.print(db_table)
            
            # Problem type breakdown
            if db_stats['by_type']:
                type_table = rich.table.Table(title="Problems by Type")
                type_table.add_column("Type", style="cyan")
                type_table.add_column("Count", style="white")
                type_table.add_column("Avg Dimension", style="white")
                
                for type_info in db_stats['by_type']:
                    type_table.add_row(
                        type_info['type'],
                        str(type_info['count']),
                        f"{type_info['avg_dimension']:.1f}"
                    )
                
                console.print(type_table)
            
        except Exception as e:
            console.print(f"[red]Database statistics unavailable: {e}[/red]")
        
        # Update manager statistics if available
        try:
            update_manager = UpdateManager(db_manager)
            update_stats = update_manager.get_processing_statistics()
            
            update_table = rich.table.Table(title="Processing History")
            update_table.add_column("Metric", style="cyan")
            update_table.add_column("Value", style="white")
            
            update_table.add_row("Files Tracked", str(update_stats['total_files_tracked']))
            update_table.add_row("Successful", str(update_stats['successful_files']))
            update_table.add_row("Failed", str(update_stats['failed_files']))
            update_table.add_row("Pending", str(update_stats['pending_files']))
            
            console.print(update_table)
            
        except Exception as e:
            console.print(f"[yellow]Processing history unavailable: {e}[/yellow]")

@cli.command()
@click.option('--config', '-c', type=click.Path(), help='Configuration file')
@click.option('--keep-days', default=30, help='Keep cache entries for N days')
def cleanup(config, keep_days):
    """Clean up cache files and temporary data."""
    from ..utils.update import UpdateManager
    from ..database.operations import DatabaseManager
    from ..config import ConverterConfig, load_config
    
    if config:
        converter_config = load_config(config)
    else:
        converter_config = ConverterConfig()
    
    try:
        db_manager = DatabaseManager(converter_config.database_path)
        update_manager = UpdateManager(db_manager)
        
        console.print("[cyan]Cleaning up cache and temporary files...[/cyan]")
        
        # Cleanup cache
        update_manager.cleanup_cache(keep_days)
        
        console.print(f"[green]✓ Cleanup completed[/green]")
        console.print(f"  Removed entries older than {keep_days} days")
        console.print(f"  Removed cache entries for deleted files")
        
    except Exception as e:
        console.print(f"[red]✗ Cleanup failed: {e}[/red]")
        sys.exit(1)
```

## Phase 3 Integration & Testing

**Create `tests/test_phase3_integration.py`**:

```python
import pytest
import tempfile
from pathlib import Path
import time

from src.converter.utils.parallel import ParallelProcessor, ProcessingResult
from src.converter.utils.update import UpdateManager
from src.converter.database.operations import DatabaseManager
from src.converter.core.parser import TSPLIBParser
from src.converter.utils.logging import setup_logging

def test_parallel_processing():
    """Test parallel processing system."""
    # Create sample files list
    test_files = [
        "datasets_raw/problems/tsp/gr17.tsp",
        "datasets_raw/problems/tsp/gr21.tsp"
    ]
    
    # Filter to existing files
    existing_files = [f for f in test_files if Path(f).exists()]
    
    if not existing_files:
        pytest.skip("No test files available")
    
    # Setup components
    logger = setup_logging("DEBUG")
    processor = ParallelProcessor(max_workers=2, logger=logger)
    parser = TSPLIBParser(logger)
    
    # Create processing function
    def process_file(file_path: str) -> ProcessingResult:
        try:
            problem_data = parser.parse_file(file_path)
            return ProcessingResult(
                file_path=file_path,
                status='success',
                problem_id=1  # Mock ID
            )
        except Exception as e:
            return ProcessingResult(
                file_path=file_path,
                status='error',
                error_message=str(e)
            )
    
    # Process files in parallel
    result = processor.process_files_parallel(existing_files, process_file)
    
    # Validate results
    assert 'results' in result
    assert 'summary' in result
    assert len(result['results']) == len(existing_files)
    assert result['summary']['total'] == len(existing_files)

def test_update_manager():
    """Test incremental update functionality."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Setup
        db_path = f"{temp_dir}/test.duckdb"
        cache_path = f"{temp_dir}/cache.db"
        
        logger = setup_logging("DEBUG")
        db_manager = DatabaseManager(db_path, logger)
        update_manager = UpdateManager(db_manager, cache_path, logger)
        
        # Test file list
        test_files = [
            "datasets_raw/problems/tsp/gr17.tsp",
        ]
        
        existing_files = [f for f in test_files if Path(f).exists()]
        
        if not existing_files:
            pytest.skip("No test files available")
        
        # First run - all files should be new
        changes = update_manager.detect_changes(existing_files)
        assert len(changes['new']) == len(existing_files)
        assert len(changes['modified']) == 0
        assert len(changes['unchanged']) == 0
        
        # Update cache for files
        for file_path in existing_files:
            update_manager.update_file_cache(file_path, 1, 'success')
        
        # Second run - all files should be unchanged
        changes = update_manager.detect_changes(existing_files)
        assert len(changes['new']) == 0
        assert len(changes['modified']) == 0
        assert len(changes['unchanged']) == len(existing_files)
        
        # Test processing session
        session_id = update_manager.create_processing_session()
        assert session_id is not None
        
        update_manager.complete_processing_session(session_id, 1, 0)
        
        # Test statistics
        stats = update_manager.get_processing_statistics()
        assert isinstance(stats, dict)
        assert 'total_files_tracked' in stats

def test_system_resources():
    """Test system resource monitoring."""
    processor = ParallelProcessor()
    resources = processor.get_system_resources()
    
    assert isinstance(resources, dict)
    assert 'cpu_count' in resources
    assert 'memory_total_mb' in resources
    
    # Test processing time estimation
    estimates = processor.estimate_processing_time(100, 0.5)
    assert isinstance(estimates, dict)
    assert 'parallel_estimate_seconds' in estimates
    assert estimates['parallel_estimate_seconds'] > 0

def test_complete_phase3_workflow():
    """
    End-to-end test of Phase 3 with parallel processing and incremental updates.
    """
    test_dir = Path("datasets_raw/problems/tsp")
    if not test_dir.exists():
        pytest.skip("Test directory not found")
    
    # Get first few TSP files
    tsp_files = list(test_dir.glob("*.tsp"))[:3]
    
    if not tsp_files:
        pytest.skip("No TSP files found")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Setup components
        db_path = f"{temp_dir}/test.duckdb"
        cache_path = f"{temp_dir}/cache.db"
        
        logger = setup_logging("DEBUG")
        db_manager = DatabaseManager(db_path, logger)
        update_manager = UpdateManager(db_manager, cache_path, logger)
        parser = TSPLIBParser(logger)
        processor = ParallelProcessor(max_workers=2, logger=logger)
        
        file_paths = [str(f) for f in tsp_files]
        
        # Create processing function with update tracking
        def process_with_updates(file_path: str) -> ProcessingResult:
            try:
                problem_data = parser.parse_file(file_path)
                problem_id = db_manager.insert_complete_problem(problem_data)
                
                # Update cache
                update_manager.update_file_cache(file_path, problem_id, 'success')
                
                return ProcessingResult(
                    file_path=file_path,
                    status='success',
                    problem_id=problem_id
                )
            except Exception as e:
                update_manager.update_file_cache(file_path, None, 'error', str(e))
                return ProcessingResult(
                    file_path=file_path,
                    status='error', 
                    error_message=str(e)
                )
        
        # First processing run
        session_id = update_manager.create_processing_session()
        
        result = processor.process_files_parallel(file_paths, process_with_updates)
        
        update_manager.complete_processing_session(
            session_id,
            result['summary']['successful'],
            result['summary']['failed']
        )
        
        # Validate first run
        assert result['summary']['successful'] > 0
        
        # Test incremental processing
        changes = update_manager.detect_changes(file_paths)
        assert len(changes['unchanged']) == result['summary']['successful']
        assert len(changes['new']) == 0
        assert len(changes['modified']) == 0
        
        # Validate processing statistics
        stats = update_manager.get_processing_statistics()
        assert stats['successful_files'] > 0
        assert len(stats['recent_sessions']) > 0
        
        logger.info("Phase 3 integration test completed successfully!")
```

## Success Criteria

Phase 3 is complete when:

- [ ] Parallel processing handles multiple files efficiently with configurable workers
- [ ] Update manager detects file changes and supports incremental processing
- [ ] Production CLI provides rich output formatting and comprehensive commands
- [ ] System monitoring tracks memory usage and processing performance
- [ ] Processing sessions are tracked with detailed statistics
- [ ] Integration test processes files with parallel workers and update tracking
- [ ] CLI commands work with rich formatting and progress tracking
- [ ] Error handling maintains system stability under high load
- [ ] Cache management provides reliable change detection

## Validation Commands

```bash
# Test parallel processing with monitoring
python -m src.converter.cli.commands process-parallel datasets_raw/problems/tsp --workers 4 --output-json datasets/json

# Check system information
python -m src.converter.cli.commands system-info --detailed

# Test incremental processing
python -m src.converter.cli.commands process-parallel datasets_raw/problems --incremental

# Run Phase 3 integration tests
pytest tests/test_phase3_integration.py -v

# Cleanup old cache data
python -m src.converter.cli.commands cleanup --keep-days 7
```

This Phase 3 implementation completes the ETL system with production-grade parallel processing, incremental updates, and comprehensive monitoring capabilities. The system is now ready for processing large-scale TSPLIB datasets efficiently and reliably.
