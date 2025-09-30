import click
from pathlib import Path
import logging
import sys

from ..config import ConverterConfig, load_config, save_config
from ..core.parser import TSPLIBParser
from ..database.operations import DatabaseManager
from ..utils.logging import setup_logging

@click.group()
@click.version_option(version="0.1.0")
def cli():
    """TSPLIB95 ETL Converter - Phase 1 Core Infrastructure."""
    pass

@cli.command()
@click.argument('file_path', type=click.Path(exists=True))
@click.option('--config', '-c', type=click.Path(), help='Configuration file path')
@click.option('--output-db', '-o', help='Output database path')
def parse(file_path, config, output_db):
    """
    Parse a single TSPLIB file and store in database.
    
    Example: python -m src.converter.cli.commands parse datasets_raw/problems/tsp/gr17.tsp
    """
    # Load configuration
    if config:
        converter_config = load_config(config)
    else:
        converter_config = ConverterConfig()
    
    if output_db:
        converter_config.database_path = output_db
    
    # Setup logging
    logger = setup_logging(converter_config.log_level, converter_config.log_file)
    
    try:
        # Initialize components
        parser = TSPLIBParser(logger)
        db_manager = DatabaseManager(converter_config.database_path, logger)
        
        # Parse file
        click.echo(f"Parsing {file_path}...")
        problem_data = parser.parse_file(file_path)
        
        # Insert into database
        problem_id = db_manager.insert_complete_problem(problem_data)
        
        # Report results
        click.echo(f"✓ Successfully processed {file_path}")
        click.echo(f"  Problem: {problem_data['problem_data']['name']} ({problem_data['problem_data']['type']})")
        click.echo(f"  Dimension: {problem_data['problem_data']['dimension']}")
        click.echo(f"  Nodes: {len(problem_data['nodes'])}")
        click.echo(f"  Edges: {len(problem_data['edges'])}")
        click.echo(f"  Database ID: {problem_id}")
        click.echo(f"  Database: {converter_config.database_path}")
        
    except Exception as e:
        logger.error(f"Failed to process {file_path}: {e}")
        click.echo(f"✗ Error processing {file_path}: {e}", err=True)
        sys.exit(1)

@cli.command()
@click.option('--config', '-c', type=click.Path(), help='Configuration file path')
def stats(config):
    """Show database statistics."""
    # Load configuration
    if config:
        converter_config = load_config(config)
    else:
        converter_config = ConverterConfig()
    
    # Setup logging
    logger = setup_logging(converter_config.log_level)
    
    try:
        db_manager = DatabaseManager(converter_config.database_path, logger)
        statistics = db_manager.get_problem_statistics()
        
        click.echo("Database Statistics:")
        click.echo(f"  Total Problems: {statistics['total_problems']}")
        click.echo(f"  Total Nodes: {statistics['total_nodes']}")
        click.echo(f"  Total Edges: {statistics['total_edges']}")
        
        if statistics['by_type']:
            click.echo("\nBy Problem Type:")
            for type_stat in statistics['by_type']:
                click.echo(f"  {type_stat['type']}: {type_stat['count']} problems "
                          f"(avg dimension: {type_stat['avg_dimension']:.1f})")
                
    except Exception as e:
        click.echo(f"✗ Error getting statistics: {e}", err=True)
        sys.exit(1)

@cli.command()
@click.option('--config', '-c', type=click.Path(), help='Configuration file path')
def validate(config):
    """Validate database integrity."""
    # Load configuration
    if config:
        converter_config = load_config(config)
    else:
        converter_config = ConverterConfig()
    
    logger = setup_logging(converter_config.log_level)
    
    try:
        db_manager = DatabaseManager(converter_config.database_path, logger)
        issues = db_manager.validate_data_integrity()
        
        if not issues:
            click.echo("✓ Database integrity validation passed")
        else:
            click.echo("✗ Database integrity issues found:")
            for issue in issues:
                click.echo(f"  - {issue}")
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"✗ Error validating database: {e}", err=True)
        sys.exit(1)

@cli.command()
@click.option('--output', '-o', default='config.yaml', help='Output configuration file path')
def init(output):
    """Initialize configuration file with default settings."""
    config = ConverterConfig()
    save_config(config, output)
    click.echo(f"Configuration file created: {output}")

if __name__ == '__main__':
    cli()
