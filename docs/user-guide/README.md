# TSPLIB95 ETL Converter - User Guide

## Welcome

This comprehensive user guide covers all aspects of using the TSPLIB95 ETL Converter, from initial setup through advanced usage and development.

## Documentation Structure

### 1. [Development Journey](01-development-journey.md)
**Purpose**: Understand the thought process and design decisions behind the implementation

**Contents**:
- Initial analysis and planning
- Architecture decisions and rationale
- Development process and phases
- Technical deep dives
- Lessons learned
- Future considerations

**Read this if you want to**:
- Understand why design choices were made
- Learn from the development experience
- Contribute to the codebase
- Extend functionality for Phase 2+

---

### 2. [Environment Setup](02-environment-setup.md)
**Purpose**: Get your development environment configured and ready to use

**Contents**:
- Prerequisites and system requirements
- Step-by-step installation instructions
- Configuration setup
- Verification steps
- Troubleshooting common issues
- Development environment setup

**Read this if you want to**:
- Install the converter for the first time
- Set up a development environment
- Troubleshoot installation problems
- Configure the system for your needs

---

### 3. [User Guide](03-user-guide.md)
**Purpose**: Learn how to use the converter for daily tasks

**Contents**:
- Quick start guide
- Core concepts and data model
- Using the CLI commands
- Configuration options
- Database querying
- Common workflows
- Best practices

**Read this if you want to**:
- Get started quickly
- Understand how the system works
- Learn basic usage patterns
- Query the database
- Follow best practices

---

### 4. [Command Reference](04-command-reference.md)
**Purpose**: Detailed reference for all CLI commands

**Contents**:
- Complete command syntax
- All options and arguments
- Usage examples
- Return codes
- Error messages
- Performance tips

**Read this if you want to**:
- Look up command syntax
- Understand all available options
- Debug command issues
- Optimize command usage

---

### 5. [Examples](05-examples.md)
**Purpose**: Real-world examples and usage scenarios

**Contents**:
- Analyzing classic TSP problems
- Comparing problem types
- Working with VRP problems
- Batch processing scripts
- Data export examples
- Validation workflows
- Custom queries

**Read this if you want to**:
- See practical examples
- Learn from real scenarios
- Copy and adapt scripts
- Solve specific problems

---

### 6. [Database Schema](06-database-schema.md)
**Purpose**: Understand the database structure and write efficient queries

**Contents**:
- Table schemas and relationships
- Column descriptions
- Indexes and performance
- Common query patterns
- Data types and constraints
- Optimization tips

**Read this if you want to**:
- Write custom queries
- Understand data relationships
- Optimize database performance
- Extend the schema

---

## Quick Navigation

### For First-Time Users

1. Start with [Environment Setup](02-environment-setup.md)
2. Read the Quick Start section in [User Guide](03-user-guide.md)
3. Try examples from [Examples](05-examples.md)
4. Refer to [Command Reference](04-command-reference.md) as needed

### For Developers

1. Read [Development Journey](01-development-journey.md)
2. Review [Database Schema](06-database-schema.md)
3. Study the implementation in `src/converter/`
4. Check existing tests in `tests/`

### For Data Analysts

1. Skim [User Guide](03-user-guide.md) Core Concepts section
2. Focus on Database Querying in [User Guide](03-user-guide.md)
3. Study query examples in [Examples](05-examples.md)
4. Reference [Database Schema](06-database-schema.md) for table structures

### For System Administrators

1. Read [Environment Setup](02-environment-setup.md)
2. Review Configuration in [User Guide](03-user-guide.md)
3. Study batch processing in [Examples](05-examples.md)
4. Set up monitoring and backups

---

## Getting Help

### Within Documentation

- Use browser search (Ctrl+F / Cmd+F) to find specific topics
- Check the table of contents in each document
- Follow cross-references between documents

### Troubleshooting

1. Check [Environment Setup](02-environment-setup.md) Troubleshooting section
2. Review common errors in [Command Reference](04-command-reference.md)
3. Check log files: `logs/converter.log`
4. Run validation: `python -m src.converter.cli.commands validate`

### Additional Resources

- **Source Code**: `src/converter/` directory
- **Tests**: `tests/` directory for usage examples
- **TSPLIB Documentation**: `TSPLIB95.md` and `tsplib95.pdf`
- **Implementation Plan**: `docs/implementation-plan.md`

---

## Document Conventions

### Code Blocks

**Bash commands**:
```bash
python -m src.converter.cli.commands parse file.tsp
```

**SQL queries**:
```sql
SELECT * FROM problems WHERE type = 'TSP';
```

**Python code**:
```python
import duckdb
conn = duckdb.connect('datasets/db/routing.duckdb')
```

### Symbols

- ✅ Success indicator
- ✗ Error indicator
- 📝 Note/important information
- ⚠️ Warning/caution

### File Paths

- Paths are relative to repository root
- Examples: `datasets_raw/problems/tsp/gr17.tsp`
- Use forward slashes (works on all platforms)

---

## Contributing to Documentation

If you find errors or want to improve the documentation:

1. Documentation is in `docs/user-guide/`
2. Use Markdown format (.md files)
3. Follow existing structure and style
4. Test all code examples before committing
5. Keep language clear and concise

---

## Version Information

- **Documentation Version**: 1.0.0
- **Software Version**: 0.1.0 (Phase 1)
- **Last Updated**: 2025-09-30

---

## What's Next?

This user guide covers Phase 1 implementation. Future documentation will include:

- Phase 2: Batch processing and parallel execution
- Phase 3: JSON output and advanced features
- API reference for programmatic usage
- Performance tuning guide
- Migration guide for database updates

---

## Quick Reference Card

### Most Used Commands

```bash
# Parse a file
python -m src.converter.cli.commands parse <file>

# View statistics
python -m src.converter.cli.commands stats

# Validate data
python -m src.converter.cli.commands validate

# Create config
python -m src.converter.cli.commands init
```

### Most Used Queries

```sql
-- List all problems
SELECT * FROM problems;

-- Get problem with nodes
SELECT p.*, n.* FROM problems p
JOIN nodes n ON p.id = n.problem_id
WHERE p.name = '<problem_name>';

-- Edge statistics
SELECT MIN(weight), AVG(weight), MAX(weight)
FROM edges WHERE problem_id = <id>;
```

### Common File Paths

- Database: `datasets/db/routing.duckdb`
- Config: `config.yaml`
- Logs: `logs/converter.log`
- Problems: `datasets_raw/problems/`

---

Ready to get started? Begin with [Environment Setup](02-environment-setup.md)!
