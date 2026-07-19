"""
Analysis and validation tools for KiCad projects.
"""
import os
from typing import Dict, Any, Optional
from mcp.server.fastmcp import FastMCP, Context, Image

from kicad_mcp.utils.file_utils import get_project_files
from kicad_mcp.utils.path_validator import validate_kicad_file, PathValidationError


def register_analysis_tools(mcp: FastMCP) -> None:
    """Register analysis and validation tools with the MCP server.
    
    Args:
        mcp: The FastMCP server instance
    """
    
    @mcp.tool()
    def validate_project(project_path: str) -> Dict[str, Any]:
        """Basic validation of a KiCad project."""
        try:
            project_path = validate_kicad_file(project_path, "project", must_exist=True)
        except PathValidationError as e:
            return {"valid": False, "error": f"Invalid project path: {e}"}

        issues = []
        files = get_project_files(project_path)
        
        # Check for essential files
        if "pcb" not in files:
            issues.append("Missing PCB layout file")
        
        if "schematic" not in files:
            issues.append("Missing schematic file")
        
        # Validate project file
        try:
            with open(project_path, 'r') as f:
                import json
                json.load(f)
        except json.JSONDecodeError:
            issues.append("Invalid project file format (JSON parsing error)")
        except Exception as e:
            issues.append(f"Error reading project file: {str(e)}")
        
        return {
            "valid": len(issues) == 0,
            "path": project_path,
            "issues": issues if issues else None,
            "files_found": list(files.keys())
        }

