# TSPLIB95 ETL System - Documentation

> **Complete documentation for the TSPLIB95 ETL System** - A 3-phase pipeline for converting TSPLIB95/VRP routing problems into JSON and DuckDB formats.

---

## 📖 Documentation Structure

### 🚀 **User Guides** (`guides/`)

*Get started and learn to use the system effectively*

| Document | Purpose | Audience |
|----------|---------|----------|
| **[Getting Started](guides/GETTING_STARTED.md)** | 3-step quick start guide | New users |
| **[User Guide](guides/USER_GUIDE.md)** | Complete usage reference | All users |
| **[Troubleshooting](guides/TROUBLESHOOTING.md)** | Issue resolution & edge cases | All users |

### 📚 **Technical Reference** (`reference/`)

*Deep technical documentation for developers and architects*

| Document | Purpose | Audience |
|----------|---------|----------|
| **[API Reference](reference/API_REFERENCE.md)** | Complete programmatic interface | Developers |
| **[Architecture Guide](reference/ARCHITECTURE.md)** | System design & technical decisions | Architects, developers |

### 🛠️ **Development** (`development/`)

*Resources for contributors and maintainers*

| Document | Purpose | Audience |
|----------|---------|----------|
| **[Developer Workflow](development/DEVELOPER_WORKFLOW.md)** | Essential development patterns | Contributors |
| **[Development Guide](development/DEVELOPMENT_GUIDE.md)** | Complete implementation journey | Contributors |
| **[Project Status](development/PROJECT_STATUS.md)** | Current state & roadmap | Project managers |

### 🎨 **Visual Documentation** (`diagrams/`)

*Technical diagrams and system visualizations*

| Diagram | Purpose | Content |
|---------|---------|---------|
| `converter-architecture.mmd` | System overview | Component relationships & data flow |
| `database-schema.mmd` | Database design | Tables, relationships, indexes |
| `database-queries.mmd` | Query patterns | Example queries & performance tips |
| `data-structures-algorithms.mmd` | Technical internals | Memory layout, algorithms, complexity |
| `processing-pipeline-flow.mmd` | Workflow visualization | Complete ETL process flow |
| `error-handling-edge-cases.mmd` | Error scenarios | Comprehensive error handling |
| `performance-scalability.mmd` | Performance analysis | Metrics, limits, optimization |

### 📦 **External Resources** (`tsplib95_docs/`)

*Third-party documentation (TSPLIB95 library)*

### 📁 **Archive** (`archive/`)

*Historical documents and development artifacts*

---

## 🎯 Quick Start Navigation

### New to the System?

1. **[Getting Started Guide](guides/GETTING_STARTED.md)** - 3 steps to success
2. **[User Guide](guides/USER_GUIDE.md)** - Complete usage documentation
3. **[Troubleshooting](guides/TROUBLESHOOTING.md)** - When things go wrong

### Want to Use the API?

1. **[API Reference](reference/API_REFERENCE.md)** - All functions with examples
2. **[Architecture Guide](reference/ARCHITECTURE.md)** - Understand the design

### Contributing to Development?

1. **[Developer Workflow](development/DEVELOPER_WORKFLOW.md)** - Essential setup & patterns
2. **[Development Guide](development/DEVELOPMENT_GUIDE.md)** - Complete implementation story
3. **[Project Status](development/PROJECT_STATUS.md)** - Current state & roadmap

### Need Visual Understanding?

- **System Overview**: `diagrams/converter-architecture.mmd`
- **Database Design**: `diagrams/database-schema.mmd`
- **Performance**: `diagrams/performance-scalability.mmd`
- **Error Handling**: `diagrams/error-handling-edge-cases.mmd`

---

## 📊 System Overview

### What is the TSPLIB95 ETL System?

A **3-phase Extract-Transform-Load pipeline** that converts TSPLIB95 and VRP problem instances into modern, queryable formats:

```
TSPLIB Files → Parser → Transformer → [JSON + DuckDB Database]
```

### Key Capabilities

- **File Processing**: Parse TSP, VRP, ATSP, HCP, SOP, TOUR formats
- **Data Transformation**: Convert 1-based TSPLIB indexing to 0-based database format
- **Dual Output**: Generate both JSON files and DuckDB database
- **Parallel Processing**: Multi-worker processing for large datasets
- **Change Detection**: Incremental updates based on file content
- **Query Interface**: SQL queries on routing problem characteristics

### Technology Stack

- **Language**: Python 3.11+
- **Dependencies**: DuckDB, tsplib95 (vendored)
- **Package Manager**: uv (modern Python packaging)
- **Database**: DuckDB (embedded analytics)
- **Testing**: pytest with comprehensive coverage

---

## 💡 Common Use Cases

### Research & Analysis

```bash
# Process academic datasets
uv run converter process -i datasets_raw/problems -o datasets/

# Query database for specific problem types
duckdb datasets/db/routing.duckdb "SELECT * FROM problems WHERE type='TSP' AND dimension > 1000"
```

### Integration & Development  

```python
# Python API usage
import converter

# Parse single file
data = converter.parse_file("problem.tsp")
converter.to_json(data, "output.json")
converter.to_database(data, "routing.duckdb")
```

### Batch Processing & Automation

```bash
# Parallel processing with progress tracking
uv run converter process --workers 8 --batch-size 200 --progress
```

---

## 🔗 External Resources

- **TSPLIB95 Specification**: See `tsplib95.pdf` in project root
- **Academic Papers**: Research citations in code comments
- **GitHub Repository**: Source code and issue tracking
- **Performance Benchmarks**: See `PHASE3_TEST_RESULTS.md`

---

## 📞 Support & Contributing

### Getting Help

- **Issues**: Check [Troubleshooting Guide](guides/TROUBLESHOOTING.md) first
- **Questions**: Open GitHub discussions
- **Bug Reports**: Use GitHub issues with error details

### Contributing  

- **Code**: Follow [Developer Workflow](development/DEVELOPER_WORKFLOW.md)
- **Documentation**: Improve guides based on user feedback
- **Testing**: Add test cases for edge cases

### Documentation Updates

- **User Feedback**: Update troubleshooting based on common issues
- **API Changes**: Keep API reference synchronized with code
- **Performance**: Update benchmarks with new optimizations

---

*This documentation is organized for maximum accessibility - from quick-start newcomers to deep-diving system architects. Each section serves specific needs while maintaining comprehensive cross-references.*
