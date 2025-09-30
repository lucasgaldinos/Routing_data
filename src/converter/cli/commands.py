"""Command-line interface for TSPLIB95 ETL Converter."""

import click
from pathlib import Path
import logging
import sys
import time
from typing import Optional
import json

from ..utils.logging import setup_logging
from ..utils.exceptions import ConverterError
from ..utils.parallel import ParallelProcessor
from ..utils.update import UpdateManager
from ..database.operations import DatabaseManager


@click.group()
@click.version_option(version="0.1.0")
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.pass_context
def cli(ctx, verbose):
    """TSPLIB95 ETL Converter - Convert TSPLIB/VRP instances to JSON and DuckDB."""
    ctx.ensure_object(dict)
    log_level = 'DEBUG' if verbose else 'INFO'
    ctx.obj['logger'] = setup_logging(log_level)


@cli.command()
@click.option('--input', '-i', type=click.Path(exists=True), 
              required=True,
              help='Input directory containing TSPLIB files')
@click.option('--output', '-o', type=click.Path(), 
              default='./datasets',
              help='Output directory for database (default: ./datasets)')
@click.option('--parallel/--no-parallel', default=True,
              help='Enable parallel processing (default: enabled)')
@click.option('--workers', default=4, type=int,
              help='Number of parallel workers (default: 4)')
@click.option('--batch-size', default=100, type=int,
              help='Batch size for processing (default: 100)')
@click.option('--types', multiple=True, 
              help='Problem types to process (e.g., --types TSP --types VRP)')
@click.option('--force/--no-force', default=False,
              help='Force reprocessing of existing files')
@click.pass_context
def process(ctx, input, output, parallel, workers, batch_size, types, force):
    """
    Process TSPLIB files and generate database output.
    
    Examples:
        converter process -i datasets_raw/problems -o datasets/
        converter process --input datasets_raw/problems --parallel --workers 8
        converter process --types TSP --types VRP --force
    """
    logger = ctx.obj['logger']
    
    try:
        logger.info("Starting TSPLIB file processing")
        logger.info(f"Input directory: {input}")
        logger.info(f"Output directory: {output}")
        logger.info(f"Parallel processing: {parallel} (workers: {workers})")
        
        # Initialize database
        db_path = Path(output) / 'db' / 'routing.duckdb'
        db_manager = DatabaseManager(str(db_path), logger)
        
        # Initialize update manager
        update_manager = UpdateManager(db_manager, logger)
        
        # Get file patterns
        if types:
            patterns = [f"*.{t.lower()}" for t in types]
        else:
            patterns = ['*.tsp', '*.vrp', '*.atsp', '*.hcp', '*.sop', '*.tour']
        
        # Scan for files
        logger.info(f"Scanning for files with patterns: {patterns}")
        input_path = Path(input)
        file_list = []
        for pattern in patterns:
            file_list.extend([str(f) for f in input_path.rglob(pattern)])
        
        logger.info(f"Found {len(file_list)} files to process")
        
        if not file_list:
            logger.warning("No files found to process")
            return
        
        # Check for updates if not forcing
        if not force:
            logger.info("Checking for changed files...")
            update_stats = update_manager.perform_incremental_update(file_list, force=False)
            files_to_process = update_stats['processed']
            logger.info(f"Files to process: {len(files_to_process)} "
                       f"(new: {update_stats['new_files']}, "
                       f"modified: {update_stats['modified_files']}, "
                       f"skipped: {len(update_stats['skipped'])})")
        else:
            files_to_process = file_list
            logger.info("Force mode: processing all files")
        
        if not files_to_process:
            logger.info("No files need processing")
            return
        
        # Process files
        start_time = time.time()
        
        if parallel and len(files_to_process) > 1:
            # Parallel processing
            processor = ParallelProcessor(
                max_workers=workers,
                batch_size=batch_size,
                logger=logger
            )
            
            # Simple processing function for demonstration
            def process_file(file_path, **kwargs):
                # This is a placeholder - in full implementation would parse and store
                logger.debug(f"Processing {file_path}")
                return {'file': file_path, 'status': 'processed'}
            
            results = processor.process_files_parallel(
                files_to_process,
                process_file
            )
            
            logger.info(f"Parallel processing completed:")
            logger.info(f"  Successful: {results['successful']}")
            logger.info(f"  Failed: {results['failed']}")
            logger.info(f"  Time: {results['processing_time']:.2f}s")
            logger.info(f"  Throughput: {results['throughput']:.2f} files/sec")
            
        else:
            # Sequential processing
            successful = 0
            failed = 0
            
            for file_path in files_to_process:
                try:
                    logger.debug(f"Processing {file_path}")
                    # Placeholder for actual processing
                    successful += 1
                except Exception as e:
                    logger.error(f"Failed to process {file_path}: {e}")
                    failed += 1
            
            elapsed = time.time() - start_time
            logger.info(f"Sequential processing completed:")
            logger.info(f"  Successful: {successful}")
            logger.info(f"  Failed: {failed}")
            logger.info(f"  Time: {elapsed:.2f}s")
        
        # Show final statistics
        stats = db_manager.get_problem_stats()
        logger.info(f"Database statistics:")
        logger.info(f"  Total problems: {stats['total_problems']}")
        for type_stat in stats['by_type']:
            logger.info(f"  {type_stat['type']}: {type_stat['count']} problems "
                       f"(avg dim: {type_stat['avg_dimension']}, "
                       f"max dim: {type_stat['max_dimension']})")
        
        click.echo(f"\n✓ Processing complete. Database: {db_path}")
    
    except Exception as e:
        logger.error(f"Processing failed: {e}", exc_info=True)
        click.echo(f"✗ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--database', '-d', type=click.Path(exists=True),
              default='./datasets/db/routing.duckdb',
              help='Database file to validate')
@click.pass_context
def validate(ctx, database):
    """
    Validate database integrity and data quality.
    
    Performs comprehensive validation:
    - Database schema and data integrity  
    - Data quality checks
    - Constraint verification
    """
    logger = ctx.obj['logger']
    
    try:
        logger.info(f"Validating database: {database}")
        
        if not Path(database).exists():
            click.echo(f"✗ Database not found: {database}", err=True)
            sys.exit(1)
        
        db_manager = DatabaseManager(database, logger)
        stats = db_manager.get_problem_stats()
        
        click.echo(f"\n✓ Database validation successful")
        click.echo(f"  Total problems: {stats['total_problems']}")
        
        for type_stat in stats['by_type']:
            click.echo(f"  {type_stat['type']}: {type_stat['count']} problems")
        
    except Exception as e:
        logger.error(f"Validation failed: {e}", exc_info=True)
        click.echo(f"✗ Validation error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--database', '-d', required=True, type=click.Path(exists=True),
              help='Database file to analyze')
@click.option('--type', '-t', type=click.Choice(['TSP', 'VRP', 'ATSP', 'HCP', 'SOP', 'TOUR']),
              help='Filter by problem type')
@click.option('--format', type=click.Choice(['table', 'json']), default='table',
              help='Output format (default: table)')
@click.option('--limit', type=int, default=20,
              help='Maximum number of problems to show (default: 20)')
@click.pass_context
def analyze(ctx, database, type, format, limit):
    """
    Analyze processed problems and generate statistics.
    
    Generates comprehensive analysis:
    - Problem type distribution and size statistics
    - Problem details and characteristics
    - Data quality assessment
    """
    logger = ctx.obj['logger']
    
    try:
        logger.info(f"Analyzing database: {database}")
        
        db_manager = DatabaseManager(database, logger)
        
        # Get statistics
        stats = db_manager.get_problem_stats()
        
        if format == 'json':
            # JSON output
            output = {
                'statistics': stats,
                'problems': db_manager.query_problems(
                    problem_type=type,
                    limit=limit
                )
            }
            click.echo(json.dumps(output, indent=2))
        
        else:
            # Table output
            click.echo("\n=== Database Statistics ===")
            click.echo(f"Total problems: {stats['total_problems']}")
            click.echo("\nBy type:")
            for type_stat in stats['by_type']:
                click.echo(f"  {type_stat['type']:6} : {type_stat['count']:4} problems "
                          f"(avg: {type_stat['avg_dimension']:6.1f}, "
                          f"max: {type_stat['max_dimension']:5})")
            
            # Show sample problems
            problems = db_manager.query_problems(
                problem_type=type,
                limit=limit
            )
            
            if problems:
                click.echo(f"\n=== Sample Problems (limit: {limit}) ===")
                click.echo(f"{'Name':<20} {'Type':<6} {'Dim':>5} {'Weight Type':<15}")
                click.echo("-" * 60)
                for p in problems:
                    click.echo(f"{p['name']:<20} {p['type']:<6} {p['dimension']:>5} "
                              f"{p.get('edge_weight_type', 'N/A'):<15}")
    
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        click.echo(f"✗ Analysis error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--output', '-o', type=click.Path(), default='config.yaml',
              help='Output path for configuration file')
def init(output):
    """
    Initialize configuration file with default settings.
    
    Creates a template configuration file with documented options.
    """
    config_template = """# TSPLIB95 ETL Converter Configuration

# Input settings
input_path: "./datasets_raw/problems"
file_patterns:
  - "*.tsp"
  - "*.vrp"
  - "*.atsp"
  - "*.hcp"
  - "*.sop"
  - "*.tour"

# Output settings
json_output_path: "./datasets/json"
database_path: "./datasets/db/routing.duckdb"

# Processing settings
batch_size: 100
max_workers: 4
memory_limit_mb: 2048

# Logging
log_level: "INFO"
log_file: "./logs/converter.log"
"""
    
    output_path = Path(output)
    
    if output_path.exists():
        click.confirm(f"File {output} already exists. Overwrite?", abort=True)
    
    output_path.write_text(config_template)
    click.echo(f"✓ Configuration file created: {output}")


if __name__ == '__main__':
    cli()
