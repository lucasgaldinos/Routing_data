# GitHub Issue Title: Implement TSPLIB95 ETL System - Phase 2 Data Processing

## Issue Description

@copilot #github-pull-request_copilot-coding-agent

We need to implement **Phase 2** of our TSPLIB95 ETL system - the data processing layer that builds upon Phase 1's solid foundation. This phase adds file discovery, batch processing, data transformation, and JSON output capabilities to create a complete ETL pipeline.

### Prerequisites

**Phase 1 must be complete and working** with these components:

- ✅ `src/converter/core/parser.py` - TSPLIB95 parser integration
- ✅ `src/converter/database/operations.py` - Database CRUD operations  
- ✅ `src/converter/utils/` - Logging, exceptions, validation
- ✅ `src/converter/cli/commands.py` - Basic CLI interface
- ✅ Integration test passing for single file processing (`gr17.tsp`)

### Project Background

- Repository contains a vendored copy of `tsplib95` library under `src/tsplib95/`
- Raw TSPLIB/VRP files are located in `datasets_raw/problems/{tsp,vrp,atsp,hcp,sop,tour}/`
- Phase 1 provides: parser integration + database foundation + basic CLI
- **Phase 2 adds**: file discovery + batch processing + JSON output + directory processing
- **Target outputs**: `datasets/json/` (flattened JSON) + enhanced database capabilities

### Environment Setup

- Python ≥ 3.11 required  
- Dependencies from Phase 1: `uv add duckdb networkx click tabulate deprecated pytest pyyaml`
- Additional: JSON handling capabilities (built into Python)

## Phase 2 Implementation Requirements

### 2.1 File Scanner & Discovery

**Create `src/converter/core/scanner.py`**:

```python
from pathlib import Path
from typing import List, Dict, Any, Iterator, Optional, Set
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import mimetypes
import fnmatch

class FileScanner:
    """
    Comprehensive file discovery and batch processing system.
    
    Builds upon Phase 1 parser to provide directory-level processing capabilities.
    Handles recursive traversal, file filtering, and batch organization.
    """
    
    def __init__(self, batch_size: int = 100, max_workers: int = 4, 
                 logger: Optional[logging.Logger] = None):
        self.batch_size = batch_size
        self.max_workers = max_workers
        self.logger = logger or logging.getLogger(__name__)
        
        # Supported file patterns and their problem types
        self.supported_extensions = {
            '.tsp': 'TSP',
            '.vrp': 'VRP', 
            '.atsp': 'ATSP',
            '.hcp': 'HCP',
            '.sop': 'SOP',
            '.tour': 'TOUR'
        }
        
        # File size limits (in bytes)
        self.max_file_size = 100 * 1024 * 1024  # 100MB
        self.min_file_size = 10  # 10 bytes minimum
    
    def scan_directory(self, root_path: str, patterns: List[str] = None, 
                      max_depth: int = None, 
                      problem_types: List[str] = None) -> Iterator[List[Dict[str, Any]]]:
        """
        Scan directory recursively and yield batches of file information.
        
        Args:
            root_path: Root directory to scan
            patterns: File patterns to match (e.g., ['*.tsp', '*.vrp'])
            max_depth: Maximum recursion depth (None = unlimited)
            problem_types: Filter by problem types (e.g., ['TSP', 'VRP'])
            
        Yields:
            Batches of file dictionaries with complete metadata
        """
        root = Path(root_path)
        if not root.exists():
            raise FileNotFoundError(f"Root path does not exist: {root_path}")
        
        if not root.is_dir():
            raise NotADirectoryError(f"Root path is not a directory: {root_path}")
        
        # Set default patterns if none provided
        if patterns is None:
            patterns = list(self.supported_extensions.keys())
            patterns = [f"*{ext}" for ext in patterns]
        
        # Discover all matching files
        discovered_files = []
        
        for pattern in patterns:
            if max_depth is None:
                # Use rglob for unlimited depth
                for file_path in root.rglob(pattern):
                    if self._should_include_file(file_path, problem_types):
                        file_info = self._create_file_info(file_path)
                        if file_info:
                            discovered_files.append(file_info)
            else:
                # Manual traversal with depth limit
                discovered_files.extend(
                    self._scan_with_depth_limit(root, pattern, max_depth, problem_types)
                )
        
        # Sort files for consistent processing order
        discovered_files.sort(key=lambda x: (x['problem_type'], x['file_size'], x['file_path']))
        
        self.logger.info(f"Discovered {len(discovered_files)} files matching patterns {patterns}")
        
        # Yield in batches
        for i in range(0, len(discovered_files), self.batch_size):
            batch = discovered_files[i:i + self.batch_size]
            self.logger.debug(f"Yielding batch {i//self.batch_size + 1} with {len(batch)} files")
            yield batch
    
    def _scan_with_depth_limit(self, root: Path, pattern: str, max_depth: int, 
                              problem_types: List[str] = None) -> List[Dict[str, Any]]:
        """Scan with depth limitation."""
        files = []
        
        def _recursive_scan(current_path: Path, current_depth: int):
            if current_depth > max_depth:
                return
                
            try:
                for item in current_path.iterdir():
                    if item.is_file() and fnmatch.fnmatch(item.name, pattern):
                        if self._should_include_file(item, problem_types):
                            file_info = self._create_file_info(item)
                            if file_info:
                                files.append(file_info)
                    elif item.is_dir():
                        _recursive_scan(item, current_depth + 1)
            except PermissionError:
                self.logger.warning(f"Permission denied accessing: {current_path}")
            except Exception as e:
                self.logger.warning(f"Error scanning {current_path}: {e}")
        
        _recursive_scan(root, 0)
        return files
    
    def _should_include_file(self, file_path: Path, problem_types: List[str] = None) -> bool:
        """Check if file should be included based on criteria."""
        # Check extension
        if file_path.suffix.lower() not in self.supported_extensions:
            return False
        
        # Check problem type filter
        if problem_types:
            detected_type = self.supported_extensions.get(file_path.suffix.lower())
            if detected_type not in problem_types:
                return False
        
        # Check file size constraints
        try:
            file_size = file_path.stat().st_size
            if file_size < self.min_file_size or file_size > self.max_file_size:
                return False
        except OSError:
            return False
        
        return True
    
    def _create_file_info(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Create comprehensive file information dictionary."""
        try:
            stat_info = file_path.stat()
            
            return {
                'file_path': str(file_path.absolute()),
                'file_name': file_path.name,
                'file_size': stat_info.st_size,
                'modification_time': stat_info.st_mtime,
                'problem_type': self.supported_extensions.get(file_path.suffix.lower(), 'UNKNOWN'),
                'directory': str(file_path.parent),
                'relative_path': str(file_path.relative_to(file_path.parents[2])) if len(file_path.parents) > 2 else str(file_path),
                'extension': file_path.suffix.lower(),
                'validation_status': 'pending'  # Will be updated during processing
            }
        except Exception as e:
            self.logger.warning(f"Could not create file info for {file_path}: {e}")
            return None
    
    def get_directory_statistics(self, root_path: str, patterns: List[str] = None) -> Dict[str, Any]:
        """Get comprehensive statistics about directory contents."""
        stats = {
            'total_files': 0,
            'total_size': 0,
            'by_type': {},
            'by_directory': {},
            'largest_files': [],
            'processing_estimate': {}
        }
        
        # Collect all files without yielding batches
        all_files = []
        for batch in self.scan_directory(root_path, patterns):
            all_files.extend(batch)
        
        stats['total_files'] = len(all_files)
        
        # Analyze by type and directory
        for file_info in all_files:
            problem_type = file_info['problem_type']
            directory = file_info['directory']
            file_size = file_info['file_size']
            
            stats['total_size'] += file_size
            
            # By type statistics
            if problem_type not in stats['by_type']:
                stats['by_type'][problem_type] = {'count': 0, 'total_size': 0}
            stats['by_type'][problem_type]['count'] += 1
            stats['by_type'][problem_type]['total_size'] += file_size
            
            # By directory statistics  
            if directory not in stats['by_directory']:
                stats['by_directory'][directory] = {'count': 0, 'total_size': 0}
            stats['by_directory'][directory]['count'] += 1
            stats['by_directory'][directory]['total_size'] += file_size
        
        # Find largest files
        stats['largest_files'] = sorted(all_files, key=lambda x: x['file_size'], reverse=True)[:10]
        
        # Processing estimates
        stats['processing_estimate'] = {
            'estimated_batches': len(all_files) // self.batch_size + (1 if len(all_files) % self.batch_size else 0),
            'batch_size': self.batch_size,
            'avg_file_size': stats['total_size'] / len(all_files) if all_files else 0
        }
        
        return stats
    
    def validate_files_parallel(self, file_batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate batch of files in parallel for quick health checking."""
        validated_files = []
        
        with ThreadPoolExecutor(max_workers=min(self.max_workers, len(file_batch))) as executor:
            # Submit validation tasks
            future_to_file = {
                executor.submit(self._validate_single_file, file_info): file_info 
                for file_info in file_batch
            }
            
            # Collect results
            for future in as_completed(future_to_file):
                file_info = future_to_file[future]
                try:
                    validation_result = future.result()
                    file_info['validation_status'] = validation_result['status']
                    file_info['validation_errors'] = validation_result.get('errors', [])
                    validated_files.append(file_info)
                except Exception as e:
                    file_info['validation_status'] = 'error'
                    file_info['validation_errors'] = [str(e)]
                    validated_files.append(file_info)
        
        return validated_files
    
    def _validate_single_file(self, file_info: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a single file quickly (basic checks only)."""
        errors = []
        
        try:
            file_path = Path(file_info['file_path'])
            
            # Check file still exists and is readable
            if not file_path.exists():
                errors.append("File no longer exists")
                return {'status': 'error', 'errors': errors}
            
            if not file_path.is_file():
                errors.append("Path is not a file")
                return {'status': 'error', 'errors': errors}
            
            # Basic content check - just read first few lines
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    first_lines = [f.readline().strip() for _ in range(10)]
                    
                # Look for TSPLIB indicators
                content = '\n'.join(first_lines).upper()
                if 'NAME' not in content and 'TYPE' not in content:
                    errors.append("Does not appear to be a TSPLIB file")
                    return {'status': 'warning', 'errors': errors}
                    
            except Exception as e:
                errors.append(f"Could not read file content: {e}")
                return {'status': 'error', 'errors': errors}
            
            return {'status': 'valid', 'errors': []}
            
        except Exception as e:
            return {'status': 'error', 'errors': [str(e)]}
```

### 2.2 Data Transformer

**Create `src/converter/core/transformer.py`**:

```python
from typing import Dict, Any, List, Optional
import logging
from tsplib95.models import StandardProblem

from ..utils.exceptions import ValidationError, ConverterError

class DataTransformer:
    """
    Transform StandardProblem objects to multiple output formats.
    
    Handles conversion between Phase 1 parser output and various target formats:
    - Database-ready normalized format (from Phase 1)
    - Flattened JSON structure for Phase 2 output
    - Enhanced metadata for analysis and reporting
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
    
    def transform_to_json_format(self, problem_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform Phase 1 parser output to flattened JSON format.
        
        Args:
            problem_data: Output from Phase 1 parser with structure:
                {
                    'problem_data': {...},
                    'nodes': [...], 
                    'edges': [...],
                    'metadata': {...}
                }
        
        Returns:
            Flattened JSON structure suitable for file output:
            {
                'problem': {...},           # Basic problem info
                'nodes': [...],             # Node array with coordinates
                'edges': [...],             # Edge array with weights  
                'statistics': {...},        # Computed statistics
                'metadata': {...}           # Enhanced metadata
            }
        """
        try:
            # Extract components
            problem_info = problem_data.get('problem_data', {})
            nodes = problem_data.get('nodes', [])
            edges = problem_data.get('edges', [])
            metadata = problem_data.get('metadata', {})
            
            # Create flattened structure
            json_output = {
                'problem': {
                    'name': problem_info.get('name'),
                    'type': problem_info.get('type'),
                    'comment': problem_info.get('comment'),
                    'dimension': problem_info.get('dimension'),
                    'capacity': problem_info.get('capacity'),
                    'edge_weight_type': problem_info.get('edge_weight_type'),
                    'edge_weight_format': problem_info.get('edge_weight_format'),
                    'node_coord_type': problem_info.get('node_coord_type')
                },
                'nodes': self._transform_nodes_for_json(nodes),
                'edges': self._transform_edges_for_json(edges),
                'statistics': self._compute_statistics(nodes, edges, problem_info),
                'metadata': self._enhance_metadata(metadata, problem_data)
            }
            
            # Remove null values for cleaner JSON
            json_output = self._remove_null_values(json_output)
            
            self.logger.debug(f"Transformed {problem_info.get('name')} to JSON format with "
                            f"{len(nodes)} nodes, {len(edges)} edges")
            
            return json_output
            
        except Exception as e:
            raise ConverterError(f"JSON transformation failed: {e}")
    
    def _transform_nodes_for_json(self, nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform nodes to JSON-friendly format."""
        json_nodes = []
        
        for node in nodes:
            json_node = {
                'id': node.get('node_id'),  # Keep original TSPLIB ID
                'coordinates': {}
            }
            
            # Add coordinates if present
            if node.get('x') is not None:
                json_node['coordinates']['x'] = node['x']
            if node.get('y') is not None:
                json_node['coordinates']['y'] = node['y']  
            if node.get('z') is not None:
                json_node['coordinates']['z'] = node['z']
            
            # Add VRP-specific data
            if node.get('demand', 0) != 0:
                json_node['demand'] = node['demand']
            if node.get('is_depot', False):
                json_node['is_depot'] = True
            
            # Add display coordinates if different
            if node.get('display_x') is not None or node.get('display_y') is not None:
                json_node['display_coordinates'] = {}
                if node.get('display_x') is not None:
                    json_node['display_coordinates']['x'] = node['display_x']
                if node.get('display_y') is not None:
                    json_node['display_coordinates']['y'] = node['display_y']
            
            json_nodes.append(json_node)
        
        return json_nodes
    
    def _transform_edges_for_json(self, edges: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform edges to JSON-friendly format."""
        json_edges = []
        
        for edge in edges:
            json_edge = {
                'from': edge.get('from_node'),  # 0-based indices
                'to': edge.get('to_node'),      # 0-based indices  
                'weight': edge.get('weight', 0.0)
            }
            
            # Add optional properties
            if edge.get('is_fixed', False):
                json_edge['is_fixed'] = True
            
            json_edges.append(json_edge)
        
        return json_edges
    
    def _compute_statistics(self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]], 
                           problem_info: Dict[str, Any]) -> Dict[str, Any]:
        """Compute comprehensive statistics for the problem."""
        stats = {
            'node_count': len(nodes),
            'edge_count': len(edges),
            'has_coordinates': False,
            'has_vrp_data': False,
            'coordinate_bounds': None,
            'weight_statistics': None
        }
        
        # Analyze nodes
        coordinates = []
        total_demand = 0
        depot_count = 0
        
        for node in nodes:
            if node.get('x') is not None and node.get('y') is not None:
                coordinates.append((node['x'], node['y']))
                stats['has_coordinates'] = True
            
            if node.get('demand', 0) != 0:
                total_demand += node['demand']
                stats['has_vrp_data'] = True
            
            if node.get('is_depot', False):
                depot_count += 1
                stats['has_vrp_data'] = True
        
        # Coordinate bounds
        if coordinates:
            xs, ys = zip(*coordinates)
            stats['coordinate_bounds'] = {
                'min_x': min(xs),
                'max_x': max(xs),
                'min_y': min(ys),
                'max_y': max(ys),
                'width': max(xs) - min(xs),
                'height': max(ys) - min(ys)
            }
        
        # VRP statistics
        if stats['has_vrp_data']:
            stats['vrp_statistics'] = {
                'total_demand': total_demand,
                'depot_count': depot_count,
                'capacity': problem_info.get('capacity'),
                'avg_demand': total_demand / max(len(nodes) - depot_count, 1)
            }
        
        # Edge weight statistics
        if edges:
            weights = [edge.get('weight', 0) for edge in edges]
            weights = [w for w in weights if w > 0]  # Filter out zero weights
            
            if weights:
                stats['weight_statistics'] = {
                    'min_weight': min(weights),
                    'max_weight': max(weights),
                    'avg_weight': sum(weights) / len(weights),
                    'total_weight': sum(weights)
                }
        
        return stats
    
    def _enhance_metadata(self, original_metadata: Dict[str, Any], 
                         full_problem_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance metadata with additional information."""
        enhanced = original_metadata.copy()
        
        # Add transformation metadata
        enhanced['transformation'] = {
            'format_version': '2.0',
            'coordinate_system': 'original',  # No coordinate transformation applied
            'index_system': 'tsplib_original',  # Preserves 1-based TSPLIB IDs
            'generated_by': 'tsplib95_etl_converter_phase2'
        }
        
        # Add data completeness indicators
        problem_info = full_problem_data.get('problem_data', {})
        nodes = full_problem_data.get('nodes', [])
        
        enhanced['completeness'] = {
            'has_name': bool(problem_info.get('name')),
            'has_coordinates': any(node.get('x') is not None for node in nodes),
            'has_edge_weights': bool(full_problem_data.get('edges')),
            'has_vrp_data': any(node.get('demand', 0) != 0 or node.get('is_depot', False) for node in nodes),
            'coordinate_dimensions': self._detect_coordinate_dimensions(nodes)
        }
        
        return enhanced
    
    def _detect_coordinate_dimensions(self, nodes: List[Dict[str, Any]]) -> int:
        """Detect coordinate dimensionality (2D or 3D)."""
        for node in nodes:
            if node.get('z') is not None:
                return 3
        return 2 if any(node.get('x') is not None for node in nodes) else 0
    
    def _remove_null_values(self, obj: Any) -> Any:
        """Recursively remove null/None values from dictionary or list."""
        if isinstance(obj, dict):
            return {k: self._remove_null_values(v) for k, v in obj.items() 
                   if v is not None and v != {} and v != []}
        elif isinstance(obj, list):
            return [self._remove_null_values(item) for item in obj if item is not None]
        else:
            return obj
    
    def validate_transformation(self, original_data: Dict[str, Any], 
                              transformed_data: Dict[str, Any]) -> List[str]:
        """Validate that transformation preserved data integrity."""
        errors = []
        
        try:
            # Check basic counts
            original_nodes = len(original_data.get('nodes', []))
            transformed_nodes = len(transformed_data.get('nodes', []))
            
            if original_nodes != transformed_nodes:
                errors.append(f"Node count mismatch: {original_nodes} -> {transformed_nodes}")
            
            original_edges = len(original_data.get('edges', []))
            transformed_edges = len(transformed_data.get('edges', []))
            
            if original_edges != transformed_edges:
                errors.append(f"Edge count mismatch: {original_edges} -> {transformed_edges}")
            
            # Check essential fields
            problem_data = original_data.get('problem_data', {})
            transformed_problem = transformed_data.get('problem', {})
            
            essential_fields = ['name', 'type', 'dimension']
            for field in essential_fields:
                if problem_data.get(field) != transformed_problem.get(field):
                    errors.append(f"Field {field} mismatch: {problem_data.get(field)} -> {transformed_problem.get(field)}")
            
        except Exception as e:
            errors.append(f"Validation failed with error: {e}")
        
        return errors
```

### 2.3 JSON Output Writer

**Create `src/converter/output/json_writer.py`**:

```python
import json
import gzip
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime

from ..utils.exceptions import ConverterError

class JSONWriter:
    """
    Write normalized problem data to structured JSON files.
    
    Creates organized directory structure and handles file naming,
    compression, and metadata for JSON output files.
    """
    
    def __init__(self, output_path: str, compress_large_files: bool = True,
                 compression_threshold: int = 50 * 1024,  # 50KB
                 logger: Optional[logging.Logger] = None):
        self.output_path = Path(output_path)
        self.compress_large_files = compress_large_files
        self.compression_threshold = compression_threshold
        self.logger = logger or logging.getLogger(__name__)
        
        # Ensure output directory exists
        self._create_output_structure()
        
        # Track writing statistics
        self.write_stats = {
            'files_written': 0,
            'total_size': 0,
            'compressed_files': 0,
            'errors': []
        }
    
    def write_problem(self, problem_data: Dict[str, Any], 
                     source_file_path: str = None) -> str:
        """
        Write complete problem data to JSON file.
        
        Output structure: {output_path}/{type}/{problem_name}.json[.gz]
        
        Args:
            problem_data: Transformed problem data from Phase 2 transformer
            source_file_path: Original source file path for reference
            
        Returns:
            Path to written file
        """
        try:
            # Extract problem information
            problem_info = problem_data.get('problem', {})
            problem_name = problem_info.get('name')
            problem_type = problem_info.get('type', 'UNKNOWN')
            
            if not problem_name:
                raise ConverterError("Problem name is required for JSON output")
            
            # Determine output file path
            type_dir = self.output_path / problem_type.lower()
            type_dir.mkdir(exist_ok=True)
            
            # Clean filename (remove invalid characters)
            safe_filename = self._sanitize_filename(problem_name)
            output_file = type_dir / f"{safe_filename}.json"
            
            # Add source reference to metadata if provided
            if source_file_path:
                if 'metadata' not in problem_data:
                    problem_data['metadata'] = {}
                problem_data['metadata']['source_file'] = source_file_path
                problem_data['metadata']['output_generated'] = datetime.now().isoformat()
            
            # Convert to JSON string with formatting
            json_content = json.dumps(problem_data, indent=2, ensure_ascii=False, sort_keys=True)
            json_bytes = json_content.encode('utf-8')
            
            # Determine if compression is needed
            should_compress = (
                self.compress_large_files and 
                len(json_bytes) > self.compression_threshold
            )
            
            if should_compress:
                # Write compressed file
                compressed_file = output_file.with_suffix('.json.gz')
                with gzip.open(compressed_file, 'wt', encoding='utf-8') as f:
                    f.write(json_content)
                
                final_path = str(compressed_file)
                file_size = compressed_file.stat().st_size
                self.write_stats['compressed_files'] += 1
                
                self.logger.debug(f"Wrote compressed JSON: {compressed_file} "
                                f"({len(json_bytes)} -> {file_size} bytes)")
            else:
                # Write uncompressed file
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(json_content)
                
                final_path = str(output_file)
                file_size = output_file.stat().st_size
                
                self.logger.debug(f"Wrote JSON: {output_file} ({file_size} bytes)")
            
            # Update statistics
            self.write_stats['files_written'] += 1
            self.write_stats['total_size'] += file_size
            
            return final_path
            
        except Exception as e:
            error_msg = f"Failed to write JSON for {problem_name}: {e}"
            self.write_stats['errors'].append(error_msg)
            raise ConverterError(error_msg)
    
    def write_batch_summary(self, batch_results: List[Dict[str, Any]], 
                           batch_id: str = None) -> str:
        """Write summary file for a batch of processed problems."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            batch_name = batch_id or f"batch_{timestamp}"
            
            summary_file = self.output_path / f"{batch_name}_summary.json"
            
            # Create batch summary
            summary = {
                'batch_info': {
                    'batch_id': batch_name,
                    'timestamp': datetime.now().isoformat(),
                    'total_problems': len(batch_results)
                },
                'statistics': {
                    'successful': len([r for r in batch_results if r.get('status') == 'success']),
                    'failed': len([r for r in batch_results if r.get('status') == 'error']),
                    'by_type': {}
                },
                'problems': batch_results,
                'writer_statistics': self.write_stats.copy()
            }
            
            # Analyze by problem type
            for result in batch_results:
                if result.get('problem_type'):
                    ptype = result['problem_type']
                    if ptype not in summary['statistics']['by_type']:
                        summary['statistics']['by_type'][ptype] = {'count': 0, 'successful': 0}
                    summary['statistics']['by_type'][ptype]['count'] += 1
                    if result.get('status') == 'success':
                        summary['statistics']['by_type'][ptype]['successful'] += 1
            
            # Write summary
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Wrote batch summary: {summary_file}")
            return str(summary_file)
            
        except Exception as e:
            raise ConverterError(f"Failed to write batch summary: {e}")
    
    def _create_output_structure(self):
        """Create directory structure for JSON output."""
        self.output_path.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories for each problem type
        problem_types = ['tsp', 'vrp', 'atsp', 'hcp', 'sop', 'tour', 'unknown']
        
        for ptype in problem_types:
            type_dir = self.output_path / ptype
            type_dir.mkdir(exist_ok=True)
        
        self.logger.debug(f"Created JSON output structure at {self.output_path}")
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for filesystem compatibility."""
        # Remove or replace invalid characters
        invalid_chars = '<>:"/\\|?*'
        sanitized = filename
        
        for char in invalid_chars:
            sanitized = sanitized.replace(char, '_')
        
        # Limit length and strip whitespace
        sanitized = sanitized.strip()[:100]
        
        # Ensure not empty
        if not sanitized:
            sanitized = "unnamed"
        
        return sanitized
    
    def validate_json_schema(self, data: Dict[str, Any]) -> List[str]:
        """Validate JSON structure against expected schema."""
        errors = []
        
        # Check top-level structure
        required_sections = ['problem', 'nodes', 'statistics', 'metadata']
        for section in required_sections:
            if section not in data:
                errors.append(f"Missing required section: {section}")
        
        # Validate problem section
        if 'problem' in data:
            problem = data['problem']
            required_problem_fields = ['name', 'type', 'dimension']
            for field in required_problem_fields:
                if not problem.get(field):
                    errors.append(f"Missing required problem field: {field}")
        
        # Validate nodes structure
        if 'nodes' in data:
            nodes = data['nodes']
            if not isinstance(nodes, list):
                errors.append("Nodes must be an array")
            elif nodes:
                # Check first node structure
                first_node = nodes[0]
                if not isinstance(first_node, dict):
                    errors.append("Node items must be objects")
                elif 'id' not in first_node:
                    errors.append("Nodes must have 'id' field")
        
        # Validate statistics
        if 'statistics' in data:
            stats = data['statistics']
            if not isinstance(stats, dict):
                errors.append("Statistics must be an object")
        
        return errors
    
    def get_output_statistics(self) -> Dict[str, Any]:
        """Get comprehensive output statistics."""
        stats = self.write_stats.copy()
        
        # Add directory analysis
        if self.output_path.exists():
            stats['output_directory'] = str(self.output_path)
            stats['directory_size'] = self._calculate_directory_size()
            stats['file_breakdown'] = self._analyze_output_files()
        
        return stats
    
    def _calculate_directory_size(self) -> int:
        """Calculate total size of output directory."""
        total_size = 0
        try:
            for file_path in self.output_path.rglob('*'):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
        except Exception as e:
            self.logger.warning(f"Could not calculate directory size: {e}")
        
        return total_size
    
    def _analyze_output_files(self) -> Dict[str, Any]:
        """Analyze output files by type and compression."""
        analysis = {
            'by_type': {},
            'compressed': 0,
            'uncompressed': 0,
            'total_files': 0
        }
        
        try:
            for file_path in self.output_path.rglob('*.json*'):
                analysis['total_files'] += 1
                
                # Check compression
                if file_path.suffix == '.gz':
                    analysis['compressed'] += 1
                else:
                    analysis['uncompressed'] += 1
                
                # Analyze by problem type (directory name)
                problem_type = file_path.parent.name
                if problem_type not in analysis['by_type']:
                    analysis['by_type'][problem_type] = 0
                analysis['by_type'][problem_type] += 1
                
        except Exception as e:
            self.logger.warning(f"Could not analyze output files: {e}")
        
        return analysis
```

### 2.4 Enhanced CLI Commands

**Update `src/converter/cli/commands.py`** to add Phase 2 commands:

```python
# Add these commands to the existing CLI from Phase 1

@cli.command()
@click.argument('input_dir', type=click.Path(exists=True))
@click.option('--output-db', '-d', help='Database output path')
@click.option('--output-json', '-j', help='JSON output directory')
@click.option('--config', '-c', type=click.Path(), help='Configuration file')
@click.option('--batch-size', default=50, help='Batch size for processing')
@click.option('--types', multiple=True, help='Problem types to process')
@click.option('--max-files', type=int, help='Maximum files to process (for testing)')
def process_directory(input_dir, output_db, output_json, config, batch_size, types, max_files):
    """
    Process entire directory of TSPLIB files.
    
    Example: converter process-directory datasets_raw/problems --output-json datasets/json
    """
    from ..core.scanner import FileScanner
    from ..core.parser import TSPLIBParser  
    from ..core.transformer import DataTransformer
    from ..database.operations import DatabaseManager
    from ..output.json_writer import JSONWriter
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
    
    # Initialize components
    scanner = FileScanner(batch_size=converter_config.batch_size, logger=logger)
    parser = TSPLIBParser(logger)
    transformer = DataTransformer(logger)
    db_manager = DatabaseManager(converter_config.database_path, logger)
    
    json_writer = None
    if output_json:
        json_writer = JSONWriter(output_json, logger=logger)
    
    try:
        # Get directory statistics first
        click.echo("Scanning directory...")
        dir_stats = scanner.get_directory_statistics(
            input_dir, 
            patterns=[f"*.{ext}" for ext in ['tsp', 'vrp', 'atsp', 'hcp', 'sop', 'tour']]
        )
        
        click.echo(f"Found {dir_stats['total_files']} files")
        click.echo(f"Estimated {dir_stats['processing_estimate']['estimated_batches']} batches")
        
        if types:
            click.echo(f"Filtering for types: {', '.join(types)}")
        
        # Process files in batches
        total_processed = 0
        total_errors = 0
        batch_results = []
        
        with click.progressbar(length=dir_stats['total_files'], label='Processing files') as bar:
            for batch in scanner.scan_directory(
                input_dir, 
                problem_types=list(types) if types else None
            ):
                batch_result = []
                
                for file_info in batch:
                    if max_files and total_processed >= max_files:
                        break
                    
                    try:
                        # Parse file
                        problem_data = parser.parse_file(file_info['file_path'])
                        
                        # Transform for JSON if requested
                        json_data = None
                        json_path = None
                        if json_writer:
                            json_data = transformer.transform_to_json_format(problem_data)
                            json_path = json_writer.write_problem(json_data, file_info['file_path'])
                        
                        # Insert into database
                        problem_id = db_manager.insert_complete_problem(problem_data)
                        
                        # Track success
                        result = {
                            'file_path': file_info['file_path'],
                            'problem_name': problem_data['problem_data']['name'],
                            'problem_type': problem_data['problem_data']['type'],
                            'status': 'success',
                            'problem_id': problem_id,
                            'json_path': json_path,
                            'nodes': len(problem_data['nodes']),
                            'edges': len(problem_data['edges'])
                        }
                        batch_result.append(result)
                        total_processed += 1
                        
                    except Exception as e:
                        # Track error
                        result = {
                            'file_path': file_info['file_path'],
                            'status': 'error',
                            'error': str(e)
                        }
                        batch_result.append(result)
                        total_errors += 1
                        logger.error(f"Failed to process {file_info['file_path']}: {e}")
                    
                    bar.update(1)
                
                batch_results.extend(batch_result)
                
                # Write batch summary if JSON output enabled
                if json_writer and batch_result:
                    json_writer.write_batch_summary(batch_result)
        
        # Final summary
        click.echo(f"\n✓ Processing complete!")
        click.echo(f"  Processed: {total_processed} files")
        click.echo(f"  Errors: {total_errors} files")
        click.echo(f"  Success rate: {(total_processed/(total_processed+total_errors)*100):.1f}%")
        
        if json_writer:
            json_stats = json_writer.get_output_statistics()
            click.echo(f"  JSON files written: {json_stats['files_written']}")
            click.echo(f"  JSON output size: {json_stats['total_size']} bytes")
        
    except Exception as e:
        logger.error(f"Directory processing failed: {e}")
        click.echo(f"✗ Error: {e}", err=True)
        sys.exit(1)

@cli.command()
@click.argument('directory', type=click.Path(exists=True))
@click.option('--types', multiple=True, help='Problem types to analyze')
def scan(directory, types):
    """Scan directory and show file statistics without processing."""
    from ..core.scanner import FileScanner
    from ..utils.logging import setup_logging
    
    logger = setup_logging("INFO")
    scanner = FileScanner(logger=logger)
    
    try:
        # Get comprehensive statistics
        stats = scanner.get_directory_statistics(
            directory,
            patterns=[f"*.{ext}" for ext in ['tsp', 'vrp', 'atsp', 'hcp', 'sop', 'tour']]
        )
        
        click.echo("Directory Scan Results:")
        click.echo(f"  Total files: {stats['total_files']}")
        click.echo(f"  Total size: {stats['total_size']:,} bytes")
        
        click.echo("\nBy Problem Type:")
        for ptype, type_stats in stats['by_type'].items():
            click.echo(f"  {ptype}: {type_stats['count']} files "
                      f"({type_stats['total_size']:,} bytes)")
        
        click.echo("\nProcessing Estimates:")
        est = stats['processing_estimate']
        click.echo(f"  Estimated batches: {est['estimated_batches']}")
        click.echo(f"  Batch size: {est['batch_size']}")
        click.echo(f"  Average file size: {est['avg_file_size']:.0f} bytes")
        
        if stats['largest_files']:
            click.echo("\nLargest files:")
            for i, file_info in enumerate(stats['largest_files'][:5]):
                click.echo(f"  {i+1}. {file_info['file_name']} "
                          f"({file_info['file_size']:,} bytes)")
        
    except Exception as e:
        click.echo(f"✗ Scan failed: {e}", err=True)
        sys.exit(1)
```

## Phase 2 Integration & Testing

**Create `tests/test_phase2_integration.py`**:

```python
import pytest
import tempfile
from pathlib import Path
import json

from src.converter.core.scanner import FileScanner
from src.converter.core.parser import TSPLIBParser
from src.converter.core.transformer import DataTransformer
from src.converter.database.operations import DatabaseManager
from src.converter.output.json_writer import JSONWriter
from src.converter.config import ConverterConfig
from src.converter.utils.logging import setup_logging

def test_complete_phase2_workflow():
    """
    End-to-end test of Phase 2 functionality processing multiple files.
    Tests the complete directory processing pipeline.
    """
    # Setup test directory
    test_dir = Path("datasets_raw/problems")
    if not test_dir.exists():
        pytest.skip("Test directory not found")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Configure components
        config = ConverterConfig(
            database_path=f"{temp_dir}/test.duckdb",
            log_level="DEBUG",
            batch_size=10
        )
        
        json_output_dir = Path(temp_dir) / "json"
        
        # Initialize components
        logger = setup_logging(config.log_level)
        scanner = FileScanner(batch_size=config.batch_size, logger=logger)
        parser = TSPLIBParser(logger)
        transformer = DataTransformer(logger)
        db_manager = DatabaseManager(config.database_path, logger)
        json_writer = JSONWriter(str(json_output_dir), logger=logger)
        
        # Get directory statistics
        stats = scanner.get_directory_statistics(str(test_dir))
        assert stats['total_files'] > 0
        
        # Process first batch only (for testing)
        processed_count = 0
        for batch in scanner.scan_directory(str(test_dir)):
            for file_info in batch[:3]:  # Limit to first 3 files
                # Parse file
                problem_data = parser.parse_file(file_info['file_path'])
                
                # Transform to JSON format
                json_data = transformer.transform_to_json_format(problem_data)
                
                # Validate transformation
                validation_errors = transformer.validate_transformation(problem_data, json_data)
                assert len(validation_errors) == 0, f"Validation errors: {validation_errors}"
                
                # Write JSON output
                json_path = json_writer.write_problem(json_data, file_info['file_path'])
                assert Path(json_path).exists()
                
                # Validate JSON content
                with open(json_path, 'r') as f:
                    loaded_json = json.load(f)
                    assert loaded_json['problem']['name'] == json_data['problem']['name']
                
                # Insert into database
                problem_id = db_manager.insert_complete_problem(problem_data)
                assert problem_id > 0
                
                processed_count += 1
                logger.info(f"Successfully processed {file_info['file_path']}")
            
            break  # Only process first batch for testing
        
        # Validate results
        assert processed_count > 0
        
        # Check database contents
        db_stats = db_manager.get_problem_statistics()
        assert db_stats['total_problems'] == processed_count
        
        # Check JSON output statistics
        json_stats = json_writer.get_output_statistics()
        assert json_stats['files_written'] == processed_count
        
        # Validate directory structure was created
        assert json_output_dir.exists()
        type_dirs = [d for d in json_output_dir.iterdir() if d.is_dir()]
        assert len(type_dirs) > 0
        
        logger.info("Phase 2 integration test completed successfully!")

def test_file_scanner():
    """Test file scanner independently."""
    test_dir = Path("datasets_raw/problems")
    if not test_dir.exists():
        pytest.skip("Test directory not found")
    
    scanner = FileScanner(batch_size=5)
    
    # Test directory statistics
    stats = scanner.get_directory_statistics(str(test_dir))
    assert isinstance(stats, dict)
    assert 'total_files' in stats
    assert stats['total_files'] >= 0
    
    # Test batch iteration
    file_count = 0
    for batch in scanner.scan_directory(str(test_dir)):
        assert isinstance(batch, list)
        assert len(batch) <= 5  # Batch size limit
        
        for file_info in batch:
            assert 'file_path' in file_info
            assert 'problem_type' in file_info
            file_count += 1
        
        break  # Only test first batch
    
    assert file_count > 0

def test_data_transformer():
    """Test data transformer independently."""
    # Create sample parser output
    sample_data = {
        'problem_data': {
            'name': 'test_problem',
            'type': 'TSP', 
            'dimension': 3,
            'comment': 'Test problem'
        },
        'nodes': [
            {'node_id': 1, 'x': 0.0, 'y': 0.0, 'demand': 0, 'is_depot': False},
            {'node_id': 2, 'x': 1.0, 'y': 1.0, 'demand': 0, 'is_depot': False},
            {'node_id': 3, 'x': 2.0, 'y': 0.0, 'demand': 0, 'is_depot': False}
        ],
        'edges': [
            {'from_node': 0, 'to_node': 1, 'weight': 1.414, 'is_fixed': False},
            {'from_node': 1, 'to_node': 2, 'weight': 1.414, 'is_fixed': False}
        ],
        'metadata': {
            'file_path': 'test.tsp',
            'file_size': 100
        }
    }
    
    transformer = DataTransformer()
    
    # Transform to JSON format
    json_data = transformer.transform_to_json_format(sample_data)
    
    # Validate structure
    assert 'problem' in json_data
    assert 'nodes' in json_data
    assert 'edges' in json_data
    assert 'statistics' in json_data
    assert 'metadata' in json_data
    
    # Validate content
    assert json_data['problem']['name'] == 'test_problem'
    assert len(json_data['nodes']) == 3
    assert len(json_data['edges']) == 2
    
    # Validate transformation integrity
    errors = transformer.validate_transformation(sample_data, json_data)
    assert len(errors) == 0

def test_json_writer():
    """Test JSON writer independently."""
    with tempfile.TemporaryDirectory() as temp_dir:
        json_writer = JSONWriter(temp_dir)
        
        # Sample JSON data
        sample_json = {
            'problem': {
                'name': 'test_json_write',
                'type': 'TSP',
                'dimension': 2
            },
            'nodes': [
                {'id': 1, 'coordinates': {'x': 0, 'y': 0}},
                {'id': 2, 'coordinates': {'x': 1, 'y': 1}}
            ],
            'edges': [
                {'from': 0, 'to': 1, 'weight': 1.414}
            ],
            'statistics': {'node_count': 2, 'edge_count': 1},
            'metadata': {'test': True}
        }
        
        # Write JSON
        output_path = json_writer.write_problem(sample_json)
        
        # Validate output
        assert Path(output_path).exists()
        
        # Validate content
        with open(output_path, 'r') as f:
            loaded = json.load(f)
            assert loaded['problem']['name'] == 'test_json_write'
        
        # Validate schema
        errors = json_writer.validate_json_schema(sample_json)
        assert len(errors) == 0
```

## Success Criteria

Phase 2 is complete when:

- [ ] All Phase 2 modules are implemented with working code (no TODO placeholders)
- [ ] File scanner can discover and batch TSPLIB files from `datasets_raw/problems/`
- [ ] Data transformer converts Phase 1 output to clean JSON format
- [ ] JSON writer creates organized output structure in `datasets/json/`
- [ ] CLI command `process-directory` successfully processes multiple files
- [ ] Integration test processes at least 3 different problem types
- [ ] JSON output validates against defined schema
- [ ] Batch processing handles errors gracefully without stopping
- [ ] Directory scanning provides accurate statistics

## Validation Commands

```bash
# Scan directory without processing
python -m src.converter.cli.commands scan datasets_raw/problems

# Process small batch for testing  
python -m src.converter.cli.commands process-directory datasets_raw/problems/tsp --max-files 5 --output-json datasets/json

# Run Phase 2 integration tests
pytest tests/test_phase2_integration.py -v

# Check JSON output structure
ls -la datasets/json/
```

This Phase 2 implementation builds solidly on Phase 1 to provide complete directory processing, JSON output, and batch handling capabilities. The focused scope ensures high success probability while delivering significant value.
