#!/usr/bin/env python3
"""
TSPLIB95 Converter CLI Entry Point

A proper CLI script that can be called directly without using 'python -m'.
This provides a more user-friendly interface for the converter.
"""

import sys
import os

# Add src to path so we can import converter modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from converter.cli.commands import cli

if __name__ == '__main__':
    cli()