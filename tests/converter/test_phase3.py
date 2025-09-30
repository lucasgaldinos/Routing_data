"""Tests for Phase 3 components: parallel processing, update management, and CLI."""

import pytest
import tempfile
from pathlib import Path
import time

from src.converter.utils.parallel import ParallelProcessor
from src.converter.utils.update import UpdateManager
from src.converter.utils.logging import setup_logging
from src.converter.database.operations import DatabaseManager


class TestParallelProcessor:
    """Test parallel processing functionality."""
    
    def test_parallel_processor_init(self):
        """Test ParallelProcessor initialization."""
        processor = ParallelProcessor(max_workers=4, batch_size=100)
        assert processor.max_workers == 4
        assert processor.batch_size == 100
        assert processor._total_items == 0
        assert processor._completed_items == 0
    
    def test_process_files_parallel(self, tmp_path):
        """Test parallel file processing."""
        # Create test files
        test_files = []
        for i in range(10):
            test_file = tmp_path / f"test_{i}.txt"
            test_file.write_text(f"test content {i}")
            test_files.append(str(test_file))
        
        # Simple processing function
        def process_file(file_path):
            time.sleep(0.01)  # Simulate work
            return Path(file_path).name
        
        processor = ParallelProcessor(max_workers=4)
        results = processor.process_files_parallel(test_files, process_file)
        
        assert results['successful'] == 10
        assert results['failed'] == 0
        assert results['processing_time'] > 0
        assert results['throughput'] > 0
    
    def test_process_files_with_errors(self, tmp_path):
        """Test parallel processing handles errors correctly."""
        test_files = [str(tmp_path / f"test_{i}.txt") for i in range(5)]
        
        def failing_process(file_path):
            if '3' in file_path:
                raise ValueError("Test error")
            return True
        
        processor = ParallelProcessor(max_workers=2)
        results = processor.process_files_parallel(test_files, failing_process)
        
        assert results['successful'] == 4
        assert results['failed'] == 1
        assert len(results['errors']) == 1
        assert 'test_3' in results['errors'][0]['file']
    
    def test_memory_monitoring(self):
        """Test memory usage monitoring."""
        processor = ParallelProcessor()
        memory_stats = processor.monitor_memory_usage()
        
        assert 'used_mb' in memory_stats
        assert 'available_mb' in memory_stats
        assert 'percent' in memory_stats
        assert memory_stats['percent'] >= 0
        assert memory_stats['percent'] <= 100
    
    def test_progress_tracking(self, tmp_path):
        """Test progress tracking during parallel processing."""
        test_files = [str(tmp_path / f"test_{i}.txt") for i in range(5)]
        
        def simple_process(file_path):
            return True
        
        processor = ParallelProcessor(max_workers=2)
        processor.process_files_parallel(test_files, simple_process)
        
        stats = processor.get_progress_stats()
        assert stats['total'] == 5
        assert stats['completed'] == 5
        assert stats['progress_percent'] == 100.0


class TestUpdateManager:
    """Test update management and change detection."""
    
    def test_update_manager_init(self):
        """Test UpdateManager initialization."""
        manager = UpdateManager()
        assert manager.db_manager is None
        assert manager._change_cache == {}
    
    def test_calculate_checksum(self, tmp_path):
        """Test file checksum calculation."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        
        manager = UpdateManager()
        checksum1 = manager._calculate_checksum(str(test_file))
        checksum2 = manager._calculate_checksum(str(test_file))
        
        assert checksum1 == checksum2
        assert len(checksum1) == 64  # SHA256 hex digest
        
        # Change file and verify checksum changes
        test_file.write_text("different content")
        checksum3 = manager._calculate_checksum(str(test_file))
        assert checksum3 != checksum1
    
    def test_detect_changes_new_file(self, tmp_path):
        """Test change detection for new files."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        
        manager = UpdateManager()
        result = manager.detect_changes(str(test_file))
        
        assert result['needs_update'] is True
        assert result['change_type'] in ['new', 'unknown']
        assert result['file_checksum'] is not None
    
    def test_detect_changes_missing_file(self, tmp_path):
        """Test change detection for missing files."""
        test_file = tmp_path / "missing.txt"
        
        manager = UpdateManager()
        result = manager.detect_changes(str(test_file))
        
        assert result['needs_update'] is False
        assert result['change_type'] == 'missing'
        assert result['file_checksum'] is None
    
    def test_get_update_candidates(self, tmp_path):
        """Test finding files that need updating."""
        # Create test files
        (tmp_path / "test1.tsp").write_text("content1")
        (tmp_path / "test2.vrp").write_text("content2")
        (tmp_path / "test3.txt").write_text("content3")  # Should be ignored
        
        manager = UpdateManager()
        candidates = manager.get_update_candidates(
            str(tmp_path),
            patterns=['*.tsp', '*.vrp']
        )
        
        assert len(candidates) == 2
        assert all('.tsp' in c or '.vrp' in c for c in candidates)
    
    def test_perform_incremental_update(self, tmp_path):
        """Test incremental update processing."""
        # Create test files
        test_files = []
        for i in range(5):
            test_file = tmp_path / f"test_{i}.tsp"
            test_file.write_text(f"content {i}")
            test_files.append(str(test_file))
        
        manager = UpdateManager()
        stats = manager.perform_incremental_update(test_files, force=False)
        
        assert 'new_files' in stats
        assert 'processed' in stats
        assert 'skipped' in stats
        assert len(stats['processed']) > 0


class TestDatabaseManager:
    """Test database operations."""
    
    def test_database_init(self, tmp_path):
        """Test database initialization."""
        db_path = tmp_path / "test.duckdb"
        db_manager = DatabaseManager(str(db_path))
        
        assert db_path.exists()
        assert db_manager.db_path == db_path
    
    def test_insert_problem(self, tmp_path):
        """Test inserting problem data."""
        db_path = tmp_path / "test.duckdb"
        db_manager = DatabaseManager(str(db_path))
        
        problem_data = {
            'name': 'test_problem',
            'type': 'TSP',
            'comment': 'Test problem',
            'dimension': 10,
            'edge_weight_type': 'EUC_2D'
        }
        
        problem_id = db_manager.insert_problem(problem_data)
        assert problem_id is not None
        assert problem_id > 0
    
    def test_insert_nodes(self, tmp_path):
        """Test inserting node data."""
        db_path = tmp_path / "test.duckdb"
        db_manager = DatabaseManager(str(db_path))
        
        # Insert problem first
        problem_id = db_manager.insert_problem({
            'name': 'test',
            'type': 'TSP',
            'dimension': 3
        })
        
        # Insert nodes
        nodes = [
            {'node_id': 1, 'x': 0.0, 'y': 0.0},
            {'node_id': 2, 'x': 1.0, 'y': 1.0},
            {'node_id': 3, 'x': 2.0, 'y': 2.0}
        ]
        
        count = db_manager.insert_nodes(problem_id, nodes)
        assert count == 3
    
    def test_insert_edges(self, tmp_path):
        """Test inserting edge data."""
        db_path = tmp_path / "test.duckdb"
        db_manager = DatabaseManager(str(db_path))
        
        # Insert problem first
        problem_id = db_manager.insert_problem({
            'name': 'test',
            'type': 'TSP',
            'dimension': 3
        })
        
        # Insert edges
        edges = [
            {'from_node': 0, 'to_node': 1, 'weight': 1.414},
            {'from_node': 1, 'to_node': 2, 'weight': 1.414},
            {'from_node': 0, 'to_node': 2, 'weight': 2.828}
        ]
        
        count = db_manager.insert_edges(problem_id, edges)
        assert count == 3
    
    def test_get_problem_stats(self, tmp_path):
        """Test getting problem statistics."""
        db_path = tmp_path / "test.duckdb"
        db_manager = DatabaseManager(str(db_path))
        
        # Insert some problems
        for i in range(3):
            db_manager.insert_problem({
                'name': f'test_{i}',
                'type': 'TSP',
                'dimension': 10 + i
            })
        
        stats = db_manager.get_problem_stats()
        assert stats['total_problems'] == 3
        assert len(stats['by_type']) > 0
        assert stats['by_type'][0]['type'] == 'TSP'
        assert stats['by_type'][0]['count'] == 3
    
    def test_query_problems(self, tmp_path):
        """Test querying problems with filters."""
        db_path = tmp_path / "test.duckdb"
        db_manager = DatabaseManager(str(db_path))
        
        # Insert problems of different types and dimensions
        db_manager.insert_problem({'name': 'tsp1', 'type': 'TSP', 'dimension': 10})
        db_manager.insert_problem({'name': 'tsp2', 'type': 'TSP', 'dimension': 20})
        db_manager.insert_problem({'name': 'vrp1', 'type': 'VRP', 'dimension': 15})
        
        # Query all TSP problems
        tsp_problems = db_manager.query_problems(problem_type='TSP')
        assert len(tsp_problems) == 2
        assert all(p['type'] == 'TSP' for p in tsp_problems)
        
        # Query by dimension
        large_problems = db_manager.query_problems(min_dimension=15)
        assert len(large_problems) == 2
    
    def test_file_tracking(self, tmp_path):
        """Test file tracking operations."""
        db_path = tmp_path / "test.duckdb"
        db_manager = DatabaseManager(str(db_path))
        
        # Insert problem
        problem_id = db_manager.insert_problem({
            'name': 'test',
            'type': 'TSP',
            'dimension': 10
        })
        
        # Update file tracking
        from datetime import datetime
        tracking_info = {
            'file_path': '/path/to/test.tsp',
            'problem_id': problem_id,
            'checksum': 'abc123',
            'last_processed': datetime.now(),
            'file_size': 1024
        }
        
        db_manager.update_file_tracking(tracking_info)
        
        # Retrieve tracking info
        retrieved = db_manager.get_file_info('/path/to/test.tsp')
        assert retrieved is not None
        assert retrieved['problem_id'] == problem_id
        assert retrieved['checksum'] == 'abc123'
    
    def test_export_problem(self, tmp_path):
        """Test exporting complete problem data."""
        db_path = tmp_path / "test.duckdb"
        db_manager = DatabaseManager(str(db_path))
        
        # Insert complete problem
        problem_id = db_manager.insert_problem({
            'name': 'test',
            'type': 'TSP',
            'dimension': 2
        })
        
        db_manager.insert_nodes(problem_id, [
            {'node_id': 1, 'x': 0.0, 'y': 0.0},
            {'node_id': 2, 'x': 1.0, 'y': 1.0}
        ])
        
        db_manager.insert_edges(problem_id, [
            {'from_node': 0, 'to_node': 1, 'weight': 1.414}
        ])
        
        # Export
        exported = db_manager.export_problem(problem_id)
        
        assert exported['problem']['name'] == 'test'
        assert len(exported['nodes']) == 2
        assert len(exported['edges']) == 1


class TestCLI:
    """Test CLI commands."""
    
    def test_cli_init_command(self, tmp_path):
        """Test CLI init command."""
        from click.testing import CliRunner
        from src.converter.cli.commands import cli
        
        runner = CliRunner()
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ['init', '--output', 'test_config.yaml'])
            
            assert result.exit_code == 0
            assert '✓' in result.output
            assert Path('test_config.yaml').exists()
    
    def test_cli_help(self):
        """Test CLI help output."""
        from click.testing import CliRunner
        from src.converter.cli.commands import cli
        
        runner = CliRunner()
        result = runner.invoke(cli, ['--help'])
        
        assert result.exit_code == 0
        assert 'TSPLIB95 ETL Converter' in result.output
        assert 'process' in result.output
        assert 'validate' in result.output
        assert 'analyze' in result.output


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
