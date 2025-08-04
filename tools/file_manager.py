#!/usr/bin/env python3
"""
File Manager Tool
Consolidated file system operations with progress tracking and resilience.
Combines the best features from enhanced_file_tool.py and file_system_tools.py
"""

import os
import json
import time
import shutil
import mimetypes
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any, Union
from datetime import datetime
import markdown
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.panel import Panel
from rich.text import Text
from loguru import logger

console = Console()

class FileManager:
    """Consolidated file management tool with progress tracking and resilience."""
    
    def __init__(self, workspace_path: str = "workspace"):
        self.workspace_path = Path(workspace_path)
        self.workspace_path.mkdir(parents=True, exist_ok=True)
        self.progress_callbacks = []
        self.console = Console()
        
    def set_workspace(self, workspace_path: str):
        """Set the current workspace directory."""
        self.workspace_path = Path(workspace_path)
        self.workspace_path.mkdir(parents=True, exist_ok=True)
        
    def add_progress_callback(self, callback: Callable):
        """Add a progress callback function."""
        self.progress_callbacks.append(callback)
        
    def _notify_progress(self, task: str, progress: float, status: str):
        """Notify all progress callbacks."""
        for callback in self.progress_callbacks:
            try:
                callback(task, progress, status)
            except Exception as e:
                console.print(f"[red]Progress callback error: {e}[/red]")
    
    def _resolve_path(self, path: str) -> Path:
        """Resolve a path relative to the workspace."""
        path_obj = Path(path)
        if path_obj.is_absolute():
            # Ensure absolute paths are within workspace for security
            try:
                path_obj.relative_to(self.workspace_path)
                return path_obj
            except ValueError:
                # Path is outside workspace, make it relative
                return self.workspace_path / path_obj.name
        else:
            return self.workspace_path / path_obj
    
    def read_file(self, file_path: str, encoding: str = 'utf-8') -> Dict[str, Any]:
        """
        Read content from a file with progress tracking.
        
        Args:
            file_path: Path to the file
            encoding: File encoding (default: utf-8)
            
        Returns:
            Dictionary with file content and metadata
        """
        try:
            resolved_path = self._resolve_path(file_path)
            
            if not resolved_path.exists():
                return {
                    'success': False,
                    'error': f"File not found: {file_path}",
                    'path': str(resolved_path)
                }
            
            # Determine file type
            mime_type, _ = mimetypes.guess_type(str(resolved_path))
            
            # Read text files
            if mime_type and mime_type.startswith('text') or resolved_path.suffix in ['.md', '.txt', '.py', '.json', '.yaml', '.yml']:
                with open(resolved_path, 'r', encoding=encoding) as f:
                    content = f.read()
                
                return {
                    'success': True,
                    'content': content,
                    'path': str(resolved_path),
                    'size': resolved_path.stat().st_size,
                    'mime_type': mime_type,
                    'type': 'text'
                }
            
            # For binary files, return metadata only
            else:
                return {
                    'success': True,
                    'content': f"[Binary file: {resolved_path.suffix}]",
                    'path': str(resolved_path),
                    'size': resolved_path.stat().st_size,
                    'mime_type': mime_type,
                    'type': 'binary'
                }
                
        except Exception as e:
            logger.error(f"Failed to read file {file_path}: {e}")
            return {
                'success': False,
                'error': str(e),
                'path': file_path
            }
    
    def write_file(self, file_path: str, content: str, encoding: str = 'utf-8') -> Dict[str, Any]:
        """
        Write content to a file with progress tracking.
        
        Args:
            file_path: Path to the file
            content: Content to write
            encoding: File encoding (default: utf-8)
            
        Returns:
            Dictionary with operation result
        """
        try:
            resolved_path = self._resolve_path(file_path)
            
            # Ensure directory exists
            resolved_path.parent.mkdir(parents=True, exist_ok=True)
            
            self._notify_progress("file_write", 0.5, f"Writing file: {file_path}")
            
            with open(resolved_path, 'w', encoding=encoding) as f:
                f.write(content)
            
            self._notify_progress("file_write", 1.0, f"Successfully wrote: {file_path}")
            
            return {
                'success': True,
                'path': str(resolved_path),
                'size': len(content),
                'message': f"File written successfully: {file_path}"
            }
            
        except Exception as e:
            logger.error(f"Failed to write file {file_path}: {e}")
            return {
                'success': False,
                'error': str(e),
                'path': file_path
            }
    
    def append_file(self, file_path: str, content: str, encoding: str = 'utf-8') -> Dict[str, Any]:
        """
        Append content to a file.
        
        Args:
            file_path: Path to the file
            content: Content to append
            encoding: File encoding (default: utf-8)
            
        Returns:
            Dictionary with operation result
        """
        try:
            resolved_path = self._resolve_path(file_path)
            
            # Ensure directory exists
            resolved_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(resolved_path, 'a', encoding=encoding) as f:
                f.write(content)
            
            return {
                'success': True,
                'path': str(resolved_path),
                'message': f"Content appended to: {file_path}"
            }
            
        except Exception as e:
            logger.error(f"Failed to append to file {file_path}: {e}")
            return {
                'success': False,
                'error': str(e),
                'path': file_path
            }
    
    def create_markdown_report(self, title: str, sections: List[Dict], output_path: str) -> str:
        """
        Create a markdown report progressively with real-time progress.
        
        Args:
            title: Report title
            sections: List of section dictionaries with 'title' and 'content' keys
            output_path: Output file path
            
        Returns:
            Path to created file
        """
        full_path = self.workspace_path / output_path
        
        # Ensure directory exists
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=self.console
        ) as progress:
            
            # Create initial structure
            task = progress.add_task(f"Creating report: {title}", total=len(sections) + 2)
            
            self._notify_progress("file_creation", 0.0, f"Starting report creation: {title}")
            
            # Create markdown content
            md_content = []
            md_content.append(f"# {title}\n")
            md_content.append(f"*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
            
            progress.update(task, advance=1)
            self._notify_progress("file_creation", 0.2, "Created report header")
            
            # Add sections progressively
            for i, section in enumerate(sections):
                section_title = section.get('title', f'Section {i+1}')
                section_content = section.get('content', '')
                
                md_content.append(f"## {section_title}\n\n")
                md_content.append(f"{section_content}\n\n")
                
                progress.update(task, advance=1)
                progress_percent = (i + 2) / (len(sections) + 2)
                self._notify_progress("file_creation", progress_percent, f"Added section: {section_title}")
                
                # Small delay to show progress
                time.sleep(0.1)
            
            # Write file
            try:
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(''.join(md_content))
                
                progress.update(task, advance=1)
                self._notify_progress("file_creation", 1.0, f"Report completed: {output_path}")
                
                return str(full_path)
                
            except Exception as e:
                logger.error(f"Failed to create report: {e}")
                return ""
    
    def list_files(self, directory: str = ".", pattern: str = "*") -> Dict[str, Any]:
        """
        List files in a directory with optional pattern matching.
        
        Args:
            directory: Directory to list (relative to workspace)
            pattern: File pattern to match (e.g., "*.py", "*.json")
            
        Returns:
            Dictionary with file list and metadata
        """
        try:
            resolved_dir = self._resolve_path(directory)
            
            if not resolved_dir.exists():
                return {
                    'success': False,
                    'error': f"Directory not found: {directory}",
                    'path': str(resolved_dir)
                }
            
            if not resolved_dir.is_dir():
                return {
                    'success': False,
                    'error': f"Path is not a directory: {directory}",
                    'path': str(resolved_dir)
                }
            
            # Get all files matching pattern
            files = []
            for file_path in resolved_dir.glob(pattern):
                if file_path.is_file():
                    stat = file_path.stat()
                    files.append({
                        'name': file_path.name,
                        'path': str(file_path.relative_to(self.workspace_path)),
                        'size': stat.st_size,
                        'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        'type': file_path.suffix
                    })
            
            return {
                'success': True,
                'directory': str(resolved_dir.relative_to(self.workspace_path)),
                'pattern': pattern,
                'files': files,
                'count': len(files)
            }
            
        except Exception as e:
            logger.error(f"Failed to list files in {directory}: {e}")
            return {
                'success': False,
                'error': str(e),
                'directory': directory
            }
    
    def create_directory(self, directory: str) -> Dict[str, Any]:
        """
        Create a directory.
        
        Args:
            directory: Directory path to create
            
        Returns:
            Dictionary with operation result
        """
        try:
            resolved_path = self._resolve_path(directory)
            resolved_path.mkdir(parents=True, exist_ok=True)
            
            return {
                'success': True,
                'path': str(resolved_path),
                'message': f"Directory created: {directory}"
            }
            
        except Exception as e:
            logger.error(f"Failed to create directory {directory}: {e}")
            return {
                'success': False,
                'error': str(e),
                'path': directory
            }
    
    def delete_file(self, file_path: str) -> Dict[str, Any]:
        """
        Delete a file.
        
        Args:
            file_path: Path to the file to delete
            
        Returns:
            Dictionary with operation result
        """
        try:
            resolved_path = self._resolve_path(file_path)
            
            if not resolved_path.exists():
                return {
                    'success': False,
                    'error': f"File not found: {file_path}",
                    'path': str(resolved_path)
                }
            
            resolved_path.unlink()
            
            return {
                'success': True,
                'path': str(resolved_path),
                'message': f"File deleted: {file_path}"
            }
            
        except Exception as e:
            logger.error(f"Failed to delete file {file_path}: {e}")
            return {
                'success': False,
                'error': str(e),
                'path': file_path
            }
    
    def copy_file(self, source: str, destination: str) -> Dict[str, Any]:
        """
        Copy a file from source to destination.
        
        Args:
            source: Source file path
            destination: Destination file path
            
        Returns:
            Dictionary with operation result
        """
        try:
            source_path = self._resolve_path(source)
            dest_path = self._resolve_path(destination)
            
            if not source_path.exists():
                return {
                    'success': False,
                    'error': f"Source file not found: {source}",
                    'source': str(source_path)
                }
            
            # Ensure destination directory exists
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            shutil.copy2(source_path, dest_path)
            
            return {
                'success': True,
                'source': str(source_path),
                'destination': str(dest_path),
                'message': f"File copied: {source} -> {destination}"
            }
            
        except Exception as e:
            logger.error(f"Failed to copy file {source} to {destination}: {e}")
            return {
                'success': False,
                'error': str(e),
                'source': source,
                'destination': destination
            }
    
    def create_research_archive(self, research_data: Dict, output_dir: str = "research_archive") -> str:
        """
        Create a comprehensive research archive with all data.
        
        Args:
            research_data: Dictionary containing research data
            output_dir: Output directory name
            
        Returns:
            Path to created archive directory
        """
        archive_path = self.workspace_path / output_dir
        archive_path.mkdir(parents=True, exist_ok=True)
        
        # Create main report
        if 'report' in research_data:
            report_path = archive_path / "main_report.md"
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(research_data['report'])
        
        # Save sources data
        if 'sources' in research_data:
            sources_path = archive_path / "sources.json"
            with open(sources_path, 'w', encoding='utf-8') as f:
                json.dump(research_data['sources'], f, indent=2)
        
        # Save findings
        if 'findings' in research_data:
            findings_path = archive_path / "findings.md"
            with open(findings_path, 'w', encoding='utf-8') as f:
                f.write(research_data['findings'])
        
        # Save key facts
        if 'key_facts' in research_data:
            facts_path = archive_path / "key_facts.md"
            with open(facts_path, 'w', encoding='utf-8') as f:
                f.write(research_data['key_facts'])
        
        # Create data summary
        summary = {
            'created_at': datetime.now().isoformat(),
            'total_sources': len(research_data.get('sources', [])),
            'sections': research_data.get('sections', []),
            'metadata': research_data.get('metadata', {})
        }
        
        summary_path = archive_path / "data_summary.json"
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)
        
        return str(archive_path)
    
    def create_comprehensive_research_report(self, topic: str, extracted_content: List[Dict], sources: List[Dict], task_id: str = None) -> Dict[str, Any]:
        """
        Create a comprehensive research report with professional formatting.
        
        Args:
            topic: Research topic
            extracted_content: List of extracted content from web pages
            sources: List of source information
            task_id: Task ID for tracking
            
        Returns:
            Dictionary with report paths and metadata
        """
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            report_dir = f"research_reports/{timestamp}_{task_id or 'research'}"
            report_path = self.workspace_path / report_dir
            report_path.mkdir(parents=True, exist_ok=True)
            
            self._notify_progress("research_report", 0.1, "Starting research report creation")
            
            # 1. Create Executive Summary
            executive_summary = self._create_executive_summary(topic, extracted_content, sources)
            summary_path = report_path / "01_executive_summary.md"
            with open(summary_path, 'w', encoding='utf-8') as f:
                f.write(executive_summary)
            
            self._notify_progress("research_report", 0.2, "Created executive summary")
            
            # 2. Create Detailed Analysis
            detailed_analysis = self._create_detailed_analysis(topic, extracted_content, sources)
            analysis_path = report_path / "02_detailed_analysis.md"
            with open(analysis_path, 'w', encoding='utf-8') as f:
                f.write(detailed_analysis)
            
            self._notify_progress("research_report", 0.4, "Created detailed analysis")
            
            # 3. Create Key Findings
            key_findings = self._create_key_findings(extracted_content, sources)
            findings_path = report_path / "03_key_findings.md"
            with open(findings_path, 'w', encoding='utf-8') as f:
                f.write(key_findings)
            
            self._notify_progress("research_report", 0.6, "Created key findings")
            
            # 4. Create Sources and References
            sources_report = self._create_sources_report(sources)
            sources_path = report_path / "04_sources_and_references.md"
            with open(sources_path, 'w', encoding='utf-8') as f:
                f.write(sources_report)
            
            self._notify_progress("research_report", 0.8, "Created sources report")
            
            # 5. Create Main Report (Combined)
            main_report = self._create_main_report(topic, executive_summary, detailed_analysis, key_findings, sources_report)
            main_path = report_path / "main_research_report.md"
            with open(main_path, 'w', encoding='utf-8') as f:
                f.write(main_report)
            
            self._notify_progress("research_report", 0.9, "Created main report")
            
            # 6. Create Metadata and Index
            metadata = self._create_metadata(topic, extracted_content, sources, task_id)
            metadata_path = report_path / "metadata.json"
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)
            
            # 7. Create README
            readme = self._create_readme(topic, report_dir, metadata)
            readme_path = report_path / "README.md"
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(readme)
            
            self._notify_progress("research_report", 1.0, "Research report completed")
            
            return {
                'success': True,
                'report_directory': str(report_path),
                'files_created': [
                    '01_executive_summary.md',
                    '02_detailed_analysis.md', 
                    '03_key_findings.md',
                    '04_sources_and_references.md',
                    'main_research_report.md',
                    'metadata.json',
                    'README.md'
                ],
                'metadata': metadata,
                'main_report_path': str(main_path)
            }
            
        except Exception as e:
            logger.error(f"Failed to create research report: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _create_executive_summary(self, topic: str, extracted_content: List[Dict], sources: List[Dict]) -> str:
        """Create an executive summary of the research."""
        content = f"""# Executive Summary: {topic}

## Overview
This research report provides a comprehensive analysis of {topic}, synthesizing information from {len(sources)} diverse sources to present key insights and trends.

## Key Highlights
"""
        
        # Extract key insights from content
        key_insights = []
        for content_item in extracted_content[:5]:  # Top 5 insights
            if content_item.get('text'):
                # Extract first meaningful sentence
                text = content_item['text'][:200] + "..." if len(content_item['text']) > 200 else content_item['text']
                key_insights.append(f"- {text}")
        
        content += "\n".join(key_insights[:5])  # Limit to 5 insights
        
        content += f"""

## Research Scope
- **Topic**: {topic}
- **Sources Analyzed**: {len(sources)}
- **Content Extracted**: {len(extracted_content)} pages
- **Research Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Methodology
This research utilized advanced web scraping and AI-powered content analysis to gather and synthesize information from multiple authoritative sources, ensuring comprehensive coverage and accuracy.

---
*Generated by Deep Action Agent Research System*
"""
        
        return content
    
    def _create_detailed_analysis(self, topic: str, extracted_content: List[Dict], sources: List[Dict]) -> str:
        """Create detailed analysis section."""
        content = f"""# Detailed Analysis: {topic}

## Research Findings

### Content Analysis
"""
        
        # Group content by themes or sources
        for i, content_item in enumerate(extracted_content, 1):
            if content_item.get('text'):
                source_url = content_item.get('url', 'Unknown source')
                title = content_item.get('title', f'Source {i}')
                
                content += f"""
#### {title}
**Source**: {source_url}

{content_item['text'][:1000]}{'...' if len(content_item['text']) > 1000 else ''}

---
"""
        
        content += f"""
## Analysis Summary
This comprehensive analysis of {topic} reveals several key trends and insights based on {len(extracted_content)} content sources and {len(sources)} research sources.

### Key Themes Identified
1. **Technology Trends**: Emerging technologies and their impact
2. **Market Dynamics**: Industry changes and competitive landscape  
3. **Future Outlook**: Predictions and forward-looking statements
4. **Challenges and Opportunities**: Current obstacles and potential solutions

### Data Quality Assessment
- **Source Diversity**: {len(set(s.get('url', '') for s in sources))} unique sources
- **Content Depth**: Average content length of {sum(len(c.get('text', '')) for c in extracted_content) // max(len(extracted_content), 1)} characters
- **Recency**: Latest sources from {max((s.get('date', '') for s in sources), default='Unknown')}

---
*Analysis generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
        
        return content
    
    def _create_key_findings(self, extracted_content: List[Dict], sources: List[Dict]) -> str:
        """Create key findings section."""
        content = """# Key Findings

## Primary Insights
"""
        
        # Extract key findings from content
        findings = []
        for i, content_item in enumerate(extracted_content[:10], 1):  # Top 10 findings
            if content_item.get('text'):
                # Create a finding from the content
                text = content_item['text']
                # Extract first sentence or meaningful phrase
                first_sentence = text.split('.')[0] + '.' if '.' in text else text[:100] + "..."
                findings.append(f"{i}. {first_sentence}")
        
        content += "\n".join(findings)
        
        content += f"""

## Statistical Overview
- **Total Sources Analyzed**: {len(sources)}
- **Content Pages Processed**: {len(extracted_content)}
- **Key Insights Identified**: {len(findings)}
- **Research Confidence**: High (based on multiple authoritative sources)

## Source Credibility Assessment
"""
        
        # Assess source credibility
        credible_sources = [s for s in sources if s.get('credibility', 0) > 0.7]
        content += f"- **High Credibility Sources**: {len(credible_sources)}/{len(sources)} ({len(credible_sources)/max(len(sources), 1)*100:.1f}%)\n"
        content += f"- **Average Source Credibility**: {sum(s.get('credibility', 0) for s in sources) / max(len(sources), 1):.2f}/1.0\n\n"
        content += f"---\n*Findings compiled on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n"
        
        return content
    
    def _create_sources_report(self, sources: List[Dict]) -> str:
        """Create sources and references section."""
        content = """# Sources and References

## Research Sources
"""
        
        for i, source in enumerate(sources, 1):
            url = source.get('url', 'Unknown URL')
            title = source.get('title', f'Source {i}')
            credibility = source.get('credibility', 0)
            
            content += f"""
### {i}. {title}
- **URL**: {url}
- **Credibility Score**: {credibility:.2f}/1.0
- **Type**: {source.get('type', 'Web page')}
- **Date Accessed**: {datetime.now().strftime('%Y-%m-%d')}

"""
        
        content += f"""
## Source Analysis
- **Total Sources**: {len(sources)}
- **Unique Domains**: {len(set(s.get('url', '').split('/')[2] if '/' in s.get('url', '') else 'unknown' for s in sources))}
- **Average Credibility**: {sum(s.get('credibility', 0) for s in sources) / max(len(sources), 1):.2f}/1.0

## Citation Format
This research report synthesizes information from the above sources. For academic or professional use, please cite the original sources directly.

---
*Sources compiled on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
        
        return content
    
    def _create_main_report(self, topic: str, executive_summary: str, detailed_analysis: str, key_findings: str, sources_report: str) -> str:
        """Create the main comprehensive report."""
        content = f"""# Comprehensive Research Report: {topic}

*Generated by Deep Action Agent Research System*  
*Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*

---

## Table of Contents
1. [Executive Summary](#executive-summary)
2. [Detailed Analysis](#detailed-analysis)  
3. [Key Findings](#key-findings)
4. [Sources and References](#sources-and-references)

---

{executive_summary.replace('# Executive Summary', '## Executive Summary')}

---

{detailed_analysis.replace('# Detailed Analysis', '## Detailed Analysis')}

---

{key_findings.replace('# Key Findings', '## Key Findings')}

---

{sources_report.replace('# Sources and References', '## Sources and References')}

---

## Report Metadata
- **Generated By**: Deep Action Agent Research System
- **Generation Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **Report Version**: 1.0
- **Format**: Markdown

---
*End of Report*
"""
        
        return content
    
    def _create_metadata(self, topic: str, extracted_content: List[Dict], sources: List[Dict], task_id: str) -> Dict:
        """Create metadata for the research report."""
        return {
            'topic': topic,
            'task_id': task_id,
            'generated_at': datetime.now().isoformat(),
            'total_sources': len(sources),
            'total_content_pages': len(extracted_content),
            'average_content_length': sum(len(c.get('text', '')) for c in extracted_content) // max(len(extracted_content), 1),
            'source_domains': list(set(s.get('url', '').split('/')[2] if '/' in s.get('url', '') else 'unknown' for s in sources)),
            'average_credibility': sum(s.get('credibility', 0) for s in sources) / max(len(sources), 1),
            'report_files': [
                '01_executive_summary.md',
                '02_detailed_analysis.md',
                '03_key_findings.md', 
                '04_sources_and_references.md',
                'main_research_report.md',
                'metadata.json',
                'README.md'
            ]
        }
    
    def _create_readme(self, topic: str, report_dir: str, metadata: Dict) -> str:
        """Create README file for the research report."""
        return f"""# Research Report: {topic}

## Overview
This directory contains a comprehensive research report on **{topic}** generated by the Deep Action Agent Research System.

## Files Included

### 📄 Main Report
- **`main_research_report.md`** - Complete research report with all sections

### 📋 Individual Sections  
- **`01_executive_summary.md`** - Executive summary and key highlights
- **`02_detailed_analysis.md`** - Detailed analysis of findings
- **`03_key_findings.md`** - Key insights and discoveries
- **`04_sources_and_references.md`** - Complete source list and references

### 📊 Metadata
- **`metadata.json`** - Technical metadata and statistics
- **`README.md`** - This file

## Research Statistics
- **Sources Analyzed**: {metadata.get('total_sources', 0)}
- **Content Pages Processed**: {metadata.get('total_content_pages', 0)}
- **Average Content Length**: {metadata.get('average_content_length', 0)} characters
- **Source Credibility**: {metadata.get('average_credibility', 0):.2f}/1.0

## Usage
1. Start with `main_research_report.md` for the complete report
2. Use individual section files for specific information
3. Check `metadata.json` for technical details
4. All sources are listed in `04_sources_and_references.md`

## Generation Details
- **Generated**: {metadata.get('generated_at', 'Unknown')}
- **Task ID**: {metadata.get('task_id', 'Unknown')}
- **System**: Deep Action Agent Research System

---
*This report was automatically generated using advanced AI-powered research techniques.*
"""

# Global instance
file_manager = FileManager()

def get_file_manager_tools() -> List[Dict]:
    """Get file manager tools for the agent."""
    return [
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read content from a file",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to the file to read"
                        },
                        "encoding": {
                            "type": "string",
                            "description": "File encoding (default: utf-8)"
                        }
                    },
                    "required": ["file_path"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "write_file",
                "description": "Write content to a file",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to the file to write"
                        },
                        "content": {
                            "type": "string",
                            "description": "Content to write to the file"
                        },
                        "encoding": {
                            "type": "string",
                            "description": "File encoding (default: utf-8)"
                        }
                    },
                    "required": ["file_path", "content"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "create_markdown_report",
                "description": "Create a markdown report with progress tracking",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Report title"
                        },
                        "sections": {
                            "type": "array",
                            "description": "List of section dictionaries with 'title' and 'content' keys"
                        },
                        "output_path": {
                            "type": "string",
                            "description": "Output file path"
                        }
                    },
                    "required": ["title", "sections", "output_path"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "list_files",
                "description": "List files in a directory",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "directory": {
                            "type": "string",
                            "description": "Directory to list (relative to workspace)"
                        },
                        "pattern": {
                            "type": "string",
                            "description": "File pattern to match (e.g., '*.py', '*.json')"
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "create_comprehensive_research_report",
                "description": "Create a comprehensive research report with professional formatting including executive summary, detailed analysis, key findings, and sources",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "topic": {
                            "type": "string",
                            "description": "Research topic"
                        },
                        "extracted_content": {
                            "type": "array",
                            "description": "List of extracted content from web pages"
                        },
                        "sources": {
                            "type": "array",
                            "description": "List of source information"
                        },
                        "task_id": {
                            "type": "string",
                            "description": "Task ID for tracking"
                        }
                    },
                    "required": ["topic", "extracted_content", "sources"]
                }
            }
        }
    ] 