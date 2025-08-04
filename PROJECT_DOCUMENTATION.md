# Deep Action Agent - Comprehensive Project Documentation

## Table of Contents
1. [Project Overview](#project-overview)
2. [System Architecture](#system-architecture)
3. [Core Components](#core-components)
4. [Tools and Capabilities](#tools-and-capabilities)
5. [Sub-Agents](#sub-agents)
6. [Workflow and Processes](#workflow-and-processes)
7. [Configuration and Setup](#configuration-and-setup)
8. [Usage Examples](#usage-examples)
9. [Technical Specifications](#technical-specifications)
10. [Security and Safety](#security-and-safety)
11. [Performance and Optimization](#performance-and-optimization)
12. [Troubleshooting](#troubleshooting)
13. [Future Enhancements](#future-enhancements)

---

## Project Overview

The **Deep Action Agent** is a sophisticated, multi-agent AI system designed for complex research, analysis, and action tasks. It employs a hierarchical architecture with a central manager agent orchestrating specialized sub-agents, each equipped with domain-specific tools and capabilities.

### Key Features
- **🤖 Multi-Agent Architecture**: Central manager with specialized sub-agents
- **🌐 Advanced Web Research**: Browser automation with anti-detection measures
- **📊 Real-time Progress Tracking**: Live monitoring of task execution
- **⚡ Smart Rate Limiting**: Intelligent API management with fallback strategies
- **🔍 Content Quality Assessment**: Automated evaluation of source credibility
- **📁 Resilient File Management**: Robust file operations with progress tracking
- **💻 Safe Code Execution**: Sandboxed Python code execution environment
- **🎯 Todo-Driven Workflow**: Systematic task breakdown and execution
- **🔄 Multi-Provider LLM Support**: OpenRouter and Gemini with round-robin key management

### What the Project Can Do

#### Research Capabilities
- **Comprehensive Web Research**: Multi-phase research with browser automation
- **Source Evaluation**: Automatic credibility and relevance assessment
- **Academic Paper Analysis**: Access to scholarly databases and citation tracking
- **Social Media Monitoring**: Real-time trend analysis and sentiment tracking
- **Multi-language Research**: Cross-language information gathering

#### Analysis Capabilities
- **Data Processing**: Complex dataset analysis and pattern recognition
- **Statistical Analysis**: Advanced statistical modeling and hypothesis testing
- **Visualization Creation**: Automated chart and graph generation
- **Trend Analysis**: Temporal pattern identification and forecasting
- **Comparative Analysis**: Multi-source data comparison and synthesis

#### Development Capabilities
- **Code Generation**: Python script creation and automation
- **Data Analysis Scripts**: Custom analysis pipeline development
- **Web Scraping Tools**: Automated data collection from websites
- **API Integration**: Third-party service integration and automation
- **Testing and Debugging**: Code quality assessment and optimization

#### Quality Assurance
- **Fact-checking**: Automated verification of claims and data
- **Bias Detection**: Identification of potential biases in sources
- **Logical Fallacy Detection**: Critical evaluation of arguments
- **Source Validation**: Credibility assessment of information sources
- **Code Review**: Automated code quality and security analysis

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Deep Action Agent                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐    ┌─────────────────────────────────┐ │
│  │  Manager Agent  │    │        Progress Tracker         │ │
│  │   (Orchestrator)│    │      (Real-time Monitoring)     │ │
│  └─────────────────┘    └─────────────────────────────────┘ │
│           │                           │                     │
│           ▼                           ▼                     │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │              Sub-Agent Layer                            │ │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐       │ │
│  │  │ Researcher  │ │    Coder    │ │   Analyst   │       │ │
│  │  │   Agent     │ │   Agent     │ │   Agent     │       │ │
│  │  └─────────────┘ └─────────────┘ └─────────────┘       │ │
│  │  ┌─────────────┐                                       │ │
│  │  │   Critic    │                                       │ │
│  │  │   Agent     │                                       │ │
│  │  └─────────────┘                                       │ │
│  └─────────────────────────────────────────────────────────┘ │
│           │                                                 │
│           ▼                                                 │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │              Tool Layer                                 │ │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐       │ │
│  │  │ Web Research│ │File Manager │ │Code Interpr.│       │ │
│  │  │    Tools    │ │   Tools     │ │   Tools     │       │ │
│  │  └─────────────┘ └─────────────┘ └─────────────┘       │ │
│  │  ┌─────────────┐ ┌─────────────┐                       │ │
│  │  │Progress Trak│ │Rate Limit   │                       │ │
│  │  │   Tools     │ │  Manager    │                       │ │
│  │  └─────────────┘ └─────────────┘                       │ │
│  └─────────────────────────────────────────────────────────┘ │
│           │                                                 │
│           ▼                                                 │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │              Infrastructure Layer                       │ │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐       │ │
│  │  │ LLM Provider│ │  Workspace  │ │   Security  │       │ │
│  │  │   Handler   │ │  Management │ │   Layer     │       │ │
│  │  └─────────────┘ └─────────────┘ └─────────────┘       │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Component Interaction Flow

1. **Task Initiation**: User provides task description to main entry point
2. **Workspace Creation**: System creates isolated workspace for task
3. **Manager Planning**: Manager agent breaks down task into subtasks
4. **Sub-agent Dispatch**: Manager delegates specialized work to sub-agents
5. **Tool Execution**: Sub-agents use specialized tools to complete work
6. **Progress Tracking**: Real-time monitoring of all operations
7. **Quality Control**: Critic agent validates outputs
8. **Result Synthesis**: Manager combines results into final output
9. **Report Generation**: Comprehensive report creation and storage

---

## Core Components

### 1. Manager Agent (`agents/manager_agent.py`)

**Purpose**: Central orchestrator that coordinates all system activities

**Key Responsibilities**:
- Task decomposition and planning
- Sub-agent coordination and dispatch
- Progress monitoring and workflow management
- Result synthesis and report generation
- Error handling and recovery

**Core Methods**:
```python
class ManagerAgent:
    def execute_task(self, task_description: str) -> str
    def execute_research_task(self, task_description: str) -> Dict[str, Any]
    def _dispatch_sub_agent(self, agent_type: str, task_description: str) -> str
    def _execute_todo_workflow(self, todo: Dict) -> str
    def _create_research_plan(self, task_description: str) -> Dict[str, Any]
```

**Features**:
- Todo-driven workflow management
- Multi-phase research execution
- Browser automation integration
- Progress tracking integration
- Resilient file creation
- Comprehensive logging

### 2. LLM Provider Handler (`llm_providers/provider_handler.py`)

**Purpose**: Manages API calls to multiple LLM providers with intelligent fallback

**Supported Providers**:
- **OpenRouter**: Access to multiple models (Claude, GPT, etc.)
- **Google Gemini**: Google's advanced language models

**Key Features**:
- Round-robin API key rotation
- Exponential backoff for rate limits
- Automatic provider fallback
- Request/response format conversion
- Health monitoring and reporting

**Core Methods**:
```python
class LLMProviderHandler:
    def call_llm(self, provider: str, model: str, messages: List[Dict], tools: List[Dict]) -> Dict
    def _call_openrouter(self, model: str, messages: List[Dict], tools: List[Dict]) -> Dict
    def _call_gemini(self, model: str, messages: List[Dict], tools: List[Dict]) -> Dict
    def _handle_rate_limit(self, provider: str, api_key: str)
    def _get_next_key(self, provider: str) -> str
```

### 3. Configuration System (`config.py`)

**Purpose**: Centralized configuration management with environment variable support

**Configuration Areas**:
- API keys and endpoints
- Model selection for different agents
- Workspace and file system settings
- Security and execution limits
- Timeout and retry settings

**Key Functions**:
```python
def validate_config() -> bool
def get_provider_from_model(model_name: str) -> str
def clean_model_name(model_name: str) -> str
def clean_api_keys(keys_string: str) -> List[str]
```

---

## Tools and Capabilities

### 1. Web Research Tools (`tools/web_research.py`)

**Purpose**: Advanced web research with browser automation and content quality assessment

**Core Capabilities**:

#### Browser Automation
```python
class WebResearch:
    def navigate_to(self, url: str) -> bool
    def scroll_page(self, direction: str = "down", amount: str = "full") -> bool
    def extract_content(self, selectors: Dict[str, str] = None) -> Dict[str, Any]
    def get_page_screenshot(self, filename: str = None) -> str
```

**Features**:
- **Anti-detection measures**: Human-like behavior simulation
- **Captcha handling**: Automatic detection and avoidance strategies
- **Content extraction**: Intelligent content parsing with custom selectors
- **Screenshot capture**: Visual documentation of research process
- **Session management**: Persistent browser sessions with state preservation

#### Web Search Capabilities
```python
def web_search(self, query: str, num_results: int = 10) -> Dict[str, Any]
def search_and_extract(self, query: str, max_pages: int = 3) -> List[Dict[str, Any]]
def _search_duckduckgo_html(self, query: str, num_results: int) -> List[Dict]
```

**Features**:
- **Multi-engine search**: DuckDuckGo integration with fallback options
- **Result filtering**: Quality-based result ranking and filtering
- **Deep extraction**: Multi-page content extraction and synthesis
- **Query optimization**: Intelligent search query construction

#### Content Quality Assessment
```python
class ContentQuality:
    @staticmethod
    def assess_source_credibility(url: str) -> float
    @staticmethod
    def assess_content_relevance(content: str, query: str) -> float
    @staticmethod
    def assess_content_freshness(publish_date: Optional[str] = None) -> float
```

**Features**:
- **Credibility scoring**: Domain-based source reliability assessment
- **Relevance evaluation**: Content-to-query relevance scoring
- **Freshness analysis**: Publication date and content currency assessment
- **Bias detection**: Potential bias identification in sources

### 2. File Manager Tools (`tools/file_manager.py`)

**Purpose**: Comprehensive file system operations with progress tracking and resilience

**Core Capabilities**:

#### File Operations
```python
class FileManager:
    def read_file(self, file_path: str, encoding: str = 'utf-8') -> Dict[str, Any]
    def write_file(self, file_path: str, content: str, encoding: str = 'utf-8') -> Dict[str, Any]
    def append_file(self, file_path: str, content: str, encoding: str = 'utf-8') -> Dict[str, Any]
    def copy_file(self, source: str, destination: str) -> Dict[str, Any]
    def delete_file(self, file_path: str) -> Dict[str, Any]
```

**Features**:
- **Path validation**: Security-focused path resolution and validation
- **Encoding support**: Multi-encoding file handling
- **Progress tracking**: Real-time operation progress monitoring
- **Error recovery**: Graceful handling of file system errors
- **MIME type detection**: Automatic file type identification

#### Advanced File Operations
```python
def create_markdown_report(self, title: str, sections: List[Dict], output_path: str) -> str
def create_research_archive(self, research_data: Dict, output_dir: str = "research_archive") -> str
def list_files(self, directory: str = ".", pattern: str = "*") -> Dict[str, Any]
def create_directory(self, directory: str) -> Dict[str, Any]
```

**Features**:
- **Report generation**: Automated markdown report creation
- **Research archiving**: Comprehensive research data packaging
- **Pattern matching**: Advanced file filtering and search
- **Directory management**: Hierarchical directory structure handling

### 3. Code Interpreter Tools (`tools/code_interpreter.py`)

**Purpose**: Safe Python code execution with security controls and resource management

**Core Capabilities**:

#### Code Execution
```python
class CodeInterpreter:
    def execute_python_code(self, code: str, timeout: int = 30, capture_output: bool = True) -> Dict[str, Any]
    def create_and_run_script(self, script_content: str, script_name: str = "script.py", timeout: int = 30) -> Dict[str, Any]
```

**Features**:
- **Sandboxed execution**: Isolated code execution environment
- **Timeout protection**: Configurable execution time limits
- **Output capture**: Comprehensive stdout/stderr capture
- **Error handling**: Detailed error reporting and recovery
- **Workspace integration**: Seamless integration with project workspace

#### Package Management
```python
def install_package(self, package: str) -> Dict[str, Any]
def run_shell_command(self, command: str, timeout: int = 30) -> Dict[str, Any]
```

**Features**:
- **Safe package installation**: Controlled package management
- **Command validation**: Security-focused command execution
- **Dependency management**: Automatic dependency resolution
- **Shell integration**: Safe shell command execution

#### Security Features
- **Dangerous command blocking**: Comprehensive security rule enforcement
- **Path validation**: Workspace-restricted file access
- **Resource limits**: Memory and CPU usage monitoring
- **Input sanitization**: Code input validation and cleaning

### 4. Progress Tracker Tools (`tools/progress_tracker.py`)

**Purpose**: Real-time progress monitoring and task management

**Core Capabilities**:

#### Task Management
```python
class ProgressTracker:
    def create_task(self, task_id: str, task_name: str, total_steps: int = 1) -> str
    def update_task(self, task_id: str, **kwargs) -> bool
    def start_task(self, task_id: str, current_step: str = "Starting")
    def complete_task(self, task_id: str, current_step: str = "Completed")
    def fail_task(self, task_id: str, error_message: str)
```

**Features**:
- **Real-time updates**: Live progress monitoring and display
- **Step tracking**: Granular step-by-step progress tracking
- **Status management**: Comprehensive task status handling
- **Error tracking**: Detailed error logging and reporting
- **Metadata storage**: Rich task metadata and history

#### Display and Reporting
```python
def create_progress_display(self) -> Layout
def start_live_display(self)
def stop_live_display(self)
def generate_progress_report(self, task_id: str) -> str
```

**Features**:
- **Rich UI**: Beautiful terminal-based progress display
- **Live updates**: Real-time progress visualization
- **Report generation**: Comprehensive progress reporting
- **Historical analysis**: Task performance analytics

### 5. Rate Limit Manager (`tools/rate_limit_manager.py`)

**Purpose**: Intelligent API rate limiting with multiple strategies and fallback mechanisms

**Core Capabilities**:

#### Rate Limiting Strategies
```python
class RateLimitStrategy(Enum):
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIXED_DELAY = "fixed_delay"
    ADAPTIVE = "adaptive"
```

**Features**:
- **Multiple strategies**: Configurable rate limiting approaches
- **Adaptive behavior**: Dynamic strategy selection based on performance
- **Jitter implementation**: Prevents thundering herd problems
- **Success tracking**: Performance-based strategy optimization

#### Provider Management
```python
class RateLimitManager:
    def configure_provider(self, provider: str, config: RateLimitConfig)
    def execute_with_backoff(self, func: Callable, provider: str, *args, **kwargs)
    def execute_with_fallback(self, primary_func: Callable, fallback_func: Callable, primary_provider: str, fallback_provider: str, *args, **kwargs)
    def get_health_report(self) -> Dict[str, Dict[str, Any]]
```

**Features**:
- **Provider health monitoring**: Real-time provider performance tracking
- **Automatic fallback**: Seamless provider switching on failures
- **Load balancing**: Intelligent load distribution across providers
- **Health reporting**: Comprehensive provider health analytics

---

## Sub-Agents

### 1. Researcher Agent (`agents/sub_agents/researcher/agent.py`)

**Purpose**: Specialized in web research, information gathering, and source analysis

**Core Capabilities**:
- **Web Research**: Comprehensive web search and content extraction
- **Source Analysis**: Credibility and relevance assessment
- **Information Synthesis**: Multi-source information integration
- **Citation Management**: Source tracking and reference management

**Specialized Tools**:
- Web search and scraping tools
- Content quality assessment
- File system tools for data storage
- URL content extraction

**System Prompt Focus**:
- Authoritative source identification
- Efficient information extraction
- Source diversity and bias awareness
- Structured research organization

**Example Tasks**:
```python
# Research task examples
"Research the latest developments in quantum computing"
"Find authoritative sources on climate change impacts"
"Gather information on AI safety research papers"
"Analyze market trends in renewable energy"
```

### 2. Coder Agent (`agents/sub_agents/coder/agent.py`)

**Purpose**: Specialized in programming, data analysis, automation, and script creation

**Core Capabilities**:
- **Code Generation**: Python script creation and optimization
- **Data Analysis**: Statistical analysis and visualization
- **Automation**: Task automation and workflow creation
- **Debugging**: Code troubleshooting and optimization

**Specialized Tools**:
- Code interpreter tools
- File system tools for code management
- Package installation and management
- Shell command execution

**System Prompt Focus**:
- Clean, efficient code writing
- Best practices and security
- Documentation and maintainability
- Performance optimization

**Example Tasks**:
```python
# Coding task examples
"Create a data analysis script for CSV files"
"Build a web scraping automation tool"
"Develop a machine learning pipeline"
"Create a data visualization dashboard"
```

### 3. Analyst Agent (`agents/sub_agents/analyst/agent.py`)

**Purpose**: Specialized in data processing, pattern recognition, synthesis, and categorization

**Core Capabilities**:
- **Data Processing**: Complex dataset analysis and transformation
- **Pattern Recognition**: Trend identification and pattern analysis
- **Statistical Analysis**: Advanced statistical modeling and testing
- **Insight Generation**: Actionable insights and recommendations

**Specialized Tools**:
- Code interpreter for data analysis
- File system tools for data management
- Statistical analysis libraries
- Visualization tools

**System Prompt Focus**:
- Objective data analysis
- Pattern identification and interpretation
- Statistical rigor and validation
- Clear insight communication

**Example Tasks**:
```python
# Analysis task examples
"Analyze customer satisfaction survey data"
"Identify trends in sales performance"
"Perform statistical analysis on experimental data"
"Create predictive models for business forecasting"
```

### 4. Critic Agent (`agents/sub_agents/critic/agent.py`)

**Purpose**: Specialized in quality control, fact-checking, bias detection, and validation

**Core Capabilities**:
- **Fact-checking**: Verification of claims and data accuracy
- **Bias Detection**: Identification of potential biases and fallacies
- **Quality Assessment**: Evaluation of work quality and completeness
- **Validation**: Cross-reference verification and source validation

**Specialized Tools**:
- Web tools for fact-checking
- File system tools for document analysis
- Content quality assessment tools
- Source credibility evaluation

**System Prompt Focus**:
- Objective critical evaluation
- Evidence-based assessment
- Bias identification and mitigation
- Constructive feedback provision

**Example Tasks**:
```python
# Criticism task examples
"Fact-check the claims in this research report"
"Identify potential biases in this analysis"
"Validate the methodology of this study"
"Assess the quality of this code implementation"
```

---

## Workflow and Processes

### 1. Task Execution Workflow

#### Phase 1: Task Initialization
1. **Task Reception**: User provides task description
2. **Workspace Creation**: System creates isolated workspace
3. **Configuration Validation**: Verify all system components
4. **Manager Initialization**: Initialize manager agent with workspace

#### Phase 2: Task Planning
1. **Task Analysis**: Manager analyzes task requirements
2. **Subtask Decomposition**: Break down into manageable subtasks
3. **Dependency Mapping**: Identify task dependencies and order
4. **Resource Allocation**: Assign appropriate sub-agents to tasks
5. **Todo Creation**: Generate structured todo.json file

#### Phase 3: Task Execution
1. **Sub-agent Dispatch**: Manager delegates tasks to specialized agents
2. **Parallel Execution**: Execute independent tasks concurrently
3. **Progress Monitoring**: Real-time tracking of all operations
4. **Tool Utilization**: Sub-agents use specialized tools
5. **Result Collection**: Gather outputs from all sub-agents

#### Phase 4: Quality Control
1. **Critic Review**: Critic agent evaluates all outputs
2. **Fact-checking**: Verify claims and data accuracy
3. **Bias Assessment**: Identify potential biases or issues
4. **Quality Validation**: Ensure output meets quality standards

#### Phase 5: Result Synthesis
1. **Data Integration**: Combine results from all sub-agents
2. **Report Generation**: Create comprehensive final report
3. **Archive Creation**: Package all data and outputs
4. **Cleanup**: Organize and store final results

### 2. Research Workflow

#### Multi-Phase Research Process
1. **Initial Research Phase**
   - Broad overview and key source identification
   - Search query optimization
   - Source diversity assessment

2. **Deep Analysis Phase**
   - Detailed examination of specific aspects
   - Content quality evaluation
   - Source credibility assessment

3. **Data Collection Phase**
   - Statistics and factual data gathering
   - Supporting evidence collection
   - Cross-reference verification

4. **Synthesis Phase**
   - Information integration and organization
   - Pattern identification and analysis
   - Insight generation and conclusions

5. **Report Creation Phase**
   - Comprehensive report generation
   - Visual data presentation
   - Executive summary creation

### 3. Error Handling and Recovery

#### Error Detection
- **API Failures**: Automatic detection of API errors and rate limits
- **Network Issues**: Connection timeout and retry mechanisms
- **File System Errors**: Graceful handling of file operation failures
- **Code Execution Errors**: Safe error capture and reporting

#### Recovery Strategies
- **Automatic Retry**: Exponential backoff for transient failures
- **Provider Fallback**: Switch to alternative LLM providers
- **Task Resumption**: Resume interrupted tasks from last checkpoint
- **Graceful Degradation**: Continue operation with reduced functionality

---

## Configuration and Setup

### Environment Configuration

#### Required Environment Variables
```env
# OpenRouter API Keys (comma-separated for round-robin)
OPENROUTER_API_KEYS=key1,key2,key3

# Gemini API Keys (comma-separated for round-robin)
GEMINI_API_KEYS=key1,key2,key3

# Model Selection
DEFAULT_OPENROUTER_MODEL=anthropic/claude-3.5-sonnet
DEFAULT_GEMINI_MODEL=gemini-1.5-pro

# Agent-specific Model Overrides
MANAGER_MODEL=anthropic/claude-3.5-sonnet
RESEARCHER_MODEL=anthropic/claude-3.5-sonnet
CODER_MODEL=anthropic/claude-3.5-sonnet
ANALYST_MODEL=anthropic/claude-3.5-sonnet
CRITIC_MODEL=anthropic/claude-3.5-sonnet
```

#### Optional Configuration
```env
# API Configuration
OPENROUTER_API_URL=https://openrouter.ai/api/v1
GEMINI_API_URL=https://generativelanguage.googleapis.com/v1beta/models

# Timeout Settings
REQUEST_TIMEOUT=60
MAX_RETRIES=3

# Workspace Settings
WORKSPACE_BASE=workspace
TEMP_CODE_DIR=temp_code
OUTPUTS_DIR=outputs
LOGS_DIR=logs
DATA_DIR=data

# Security Settings
MAX_CODE_EXECUTION_TIME=30
ALLOWED_FILE_EXTENSIONS=.py,.txt,.json,.csv,.md
MAX_FILE_SIZE_MB=10
```

### Installation Process

#### Prerequisites
- Python 3.12 or higher
- pip package manager
- Git (for version control)

#### Installation Steps
```bash
# 1. Clone the repository
git clone <repository-url>
cd deep-agent-project

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env
# Edit .env with your API keys

# 5. Validate configuration
python config.py
```

### Dependencies

#### Core Dependencies
```
loguru>=0.7.0          # Advanced logging
rich>=13.0.0           # Rich terminal output
typer>=0.9.0           # CLI framework
python-dotenv>=1.0.0   # Environment variable management
requests>=2.31.0       # HTTP client
beautifulsoup4>=4.12.0 # HTML parsing
lxml>=4.9.0            # XML/HTML processing
```

#### Optional Dependencies
```
playwright>=1.40.0     # Browser automation
selenium>=4.15.0       # Web scraping
pandas>=2.1.0          # Data analysis
numpy>=1.24.0          # Numerical computing
matplotlib>=3.7.0      # Data visualization
```

---

## Usage Examples

### Basic Usage

#### Command Line Interface
```bash
# Run a research task
python main.py run "Analyze the impact of AI on job markets in 2024"

# Run with verbose output
python main.py run "Research quantum computing developments" --verbose

# List existing workspaces
python main.py list-workspaces

# Show progress for specific task
python main.py show-progress task_12345678

# Check system health
python main.py health-check
```

#### Programmatic Usage
```python
from agents.manager_agent import ManagerAgent

# Initialize manager agent
manager = ManagerAgent("workspace/research_task")

# Execute a task
result = manager.execute_task("Research renewable energy trends")

# Execute research task with browser automation
research_result = await manager.execute_research_task("Analyze AI safety research")
```

### Advanced Usage Examples

#### Complex Research Task
```python
# Multi-faceted research with analysis
task = """
Research the current state of renewable energy adoption globally, 
analyze the data to identify key trends, create visualizations, 
and provide recommendations for policy makers.
"""

result = await manager.execute_research_task(task)
```

#### Data Analysis Task
```python
# Data processing and analysis
task = """
Analyze the customer_satisfaction.csv file, 
perform statistical analysis on the data, 
create visualizations showing key patterns, 
and generate a comprehensive report with insights.
"""

result = manager.execute_task(task)
```

#### Code Generation Task
```python
# Automated code creation
task = """
Create a Python script that processes log files, 
extracts error patterns, generates a summary report, 
and sends notifications for critical errors.
"""

result = manager.execute_task(task)
```

### Workspace Structure

#### Generated Workspace Layout
```
workspace/
└── enhanced_task_20240115_143022/
    ├── task_metadata.json          # Task information and configuration
    ├── todo.json                   # Task breakdown and progress tracking
    ├── journal.log                 # Detailed action log
    ├── data/                       # Raw and processed data
    │   ├── research_data.json      # Collected research data
    │   ├── analysis_results.json   # Analysis outputs
    │   └── sources/                # Source documents and files
    ├── outputs/                    # Final reports and results
    │   ├── research_report.md      # Comprehensive research report
    │   ├── analysis_report.md      # Data analysis report
    │   └── visualizations/         # Generated charts and graphs
    ├── temp_code/                  # Temporary code files
    │   ├── analysis_script.py      # Generated analysis scripts
    │   └── data_processor.py       # Data processing utilities
    ├── logs/                       # System logs
    │   ├── task_log.log           # Task execution log
    │   ├── api_calls.log          # API call history
    │   └── errors.log             # Error tracking
    ├── screenshots/                # Browser screenshots
    │   ├── page_1.png             # Research page captures
    │   └── page_2.png
    └── progress/                   # Progress tracking data
        ├── task_progress.json     # Current progress state
        └── performance_metrics.json # Performance analytics
```

---

## Technical Specifications

### System Requirements

#### Minimum Requirements
- **Python**: 3.12 or higher
- **RAM**: 4GB minimum, 8GB recommended
- **Storage**: 2GB available space
- **Network**: Stable internet connection
- **OS**: Windows 10+, macOS 10.15+, or Linux

#### Recommended Requirements
- **Python**: 3.12 or higher
- **RAM**: 16GB or more
- **Storage**: 10GB available space
- **Network**: High-speed internet connection
- **OS**: Latest stable version

### Performance Characteristics

#### API Performance
- **Request Rate**: Up to 10 requests/second per provider
- **Response Time**: 1-5 seconds average
- **Timeout**: 60 seconds maximum
- **Retry Logic**: Exponential backoff with 3 retries

#### File Operations
- **File Size Limit**: 10MB per file
- **Supported Formats**: .py, .txt, .json, .csv, .md
- **Concurrent Operations**: Up to 5 simultaneous file operations
- **Backup Strategy**: Automatic workspace backup

#### Code Execution
- **Execution Timeout**: 30 seconds maximum
- **Memory Limit**: 512MB per execution
- **Sandbox**: Isolated execution environment
- **Security**: Comprehensive command validation

### Scalability Features

#### Multi-Provider Support
- **Provider Rotation**: Automatic round-robin key rotation
- **Load Balancing**: Intelligent load distribution
- **Fallback Strategy**: Automatic provider switching
- **Health Monitoring**: Real-time provider health tracking

#### Concurrent Processing
- **Parallel Execution**: Independent task parallelization
- **Resource Management**: Intelligent resource allocation
- **Queue Management**: Task queuing and prioritization
- **Progress Tracking**: Real-time progress monitoring

### Security Features

#### Code Execution Security
- **Sandboxed Environment**: Isolated code execution
- **Command Validation**: Comprehensive command filtering
- **Path Restrictions**: Workspace-only file access
- **Resource Limits**: Memory and CPU usage controls

#### API Security
- **Key Rotation**: Automatic API key rotation
- **Rate Limiting**: Intelligent rate limit management
- **Error Handling**: Secure error message handling
- **Input Validation**: Comprehensive input sanitization

#### File System Security
- **Path Validation**: Secure path resolution
- **Access Control**: Workspace-restricted access
- **File Type Validation**: Allowed file type enforcement
- **Size Limits**: File size restrictions

---

## Security and Safety

### Security Measures

#### Code Execution Safety
```python
# Dangerous command blocking
dangerous_commands = [
    'rm -rf', 'sudo', 'su', 'chmod 777',
    'dd if=', 'mkfs', 'fdisk', 'mount',
    'shutdown', 'reboot', 'halt',
    'killall', 'pkill -9', 'kill -9'
]

# Safe command whitelist
safe_commands = [
    'ls', 'pwd', 'cat', 'head', 'tail',
    'grep', 'find', 'wc', 'sort', 'uniq',
    'python', 'pip', 'git', 'docker'
]
```

#### File System Security
```python
# Path validation and restriction
def _resolve_path(self, path: str) -> Path:
    path_obj = Path(path)
    if path_obj.is_absolute():
        # Ensure absolute paths are within workspace
        try:
            path_obj.relative_to(self.workspace_path)
            return path_obj
        except ValueError:
            # Path is outside workspace, make it relative
            return self.workspace_path / path_obj.name
    else:
        return self.workspace_path / path_obj
```

#### API Security
```python
# Input validation and sanitization
def clean_api_keys(keys_string: str) -> list:
    # Remove whitespace and validate keys
    cleaned = re.sub(r'\s+', '', keys_string)
    keys = [key.strip() for key in cleaned.split(',') if key.strip()]
    # Filter out placeholder keys
    keys = [key for key in keys if key not in ['key1', 'key2', ''] and len(key) > 10]
    return keys
```

### Safety Features

#### Error Handling
- **Graceful Degradation**: Continue operation with reduced functionality
- **Error Recovery**: Automatic recovery from transient failures
- **Error Logging**: Comprehensive error tracking and reporting
- **User Notification**: Clear error messages and status updates

#### Resource Management
- **Memory Monitoring**: Real-time memory usage tracking
- **CPU Limiting**: Execution time and CPU usage controls
- **Network Monitoring**: Connection health and timeout management
- **Storage Management**: Disk space monitoring and cleanup

#### Data Protection
- **Workspace Isolation**: Complete task isolation
- **Data Encryption**: Sensitive data encryption (future enhancement)
- **Access Control**: Role-based access control (future enhancement)
- **Audit Logging**: Comprehensive audit trail

---

## Performance and Optimization

### Performance Monitoring

#### Real-time Metrics
```python
# Performance tracking
class PerformanceMetrics:
    def __init__(self):
        self.api_call_times = []
        self.file_operation_times = []
        self.code_execution_times = []
        self.memory_usage = []
        self.cpu_usage = []
```

#### Optimization Strategies
- **Caching**: Intelligent result caching
- **Connection Pooling**: HTTP connection reuse
- **Batch Processing**: Efficient batch operations
- **Resource Pooling**: Shared resource management

### Optimization Features

#### API Optimization
- **Request Batching**: Batch multiple API requests
- **Response Caching**: Cache frequently requested data
- **Connection Reuse**: Persistent HTTP connections
- **Compression**: Request/response compression

#### File System Optimization
- **Async Operations**: Non-blocking file operations
- **Buffer Management**: Efficient buffer handling
- **Compression**: Automatic file compression
- **Deduplication**: Remove duplicate data

#### Code Execution Optimization
- **JIT Compilation**: Just-in-time code compilation
- **Memory Pooling**: Efficient memory management
- **Parallel Execution**: Multi-threaded execution
- **Result Caching**: Cache computation results

---

## Troubleshooting

### Common Issues

#### API Key Issues
```bash
# Check API key configuration
python config.py

# Verify API key validity
curl -H "Authorization: Bearer YOUR_API_KEY" \
     https://openrouter.ai/api/v1/models
```

#### Network Issues
```bash
# Test network connectivity
ping openrouter.ai
ping generativelanguage.googleapis.com

# Check DNS resolution
nslookup openrouter.ai
```

#### File Permission Issues
```bash
# Check workspace permissions
ls -la workspace/

# Fix permissions if needed
chmod -R 755 workspace/
```

#### Package Installation Issues
```bash
# Update pip
python -m pip install --upgrade pip

# Install dependencies with verbose output
pip install -r requirements.txt -v

# Check for conflicts
pip check
```

### Debug Mode

#### Enable Debug Logging
```python
# Set debug level logging
import loguru
loguru.logger.add("debug.log", level="DEBUG")

# Enable verbose output
python main.py run "task" --verbose
```

#### Debug Information
```python
# Check system health
python main.py health-check

# View detailed logs
tail -f workspace/task_*/logs/task_log.log

# Monitor API calls
tail -f workspace/task_*/logs/api_calls.log
```

### Performance Issues

#### Memory Usage
```python
# Monitor memory usage
import psutil
process = psutil.Process()
memory_info = process.memory_info()
print(f"Memory usage: {memory_info.rss / 1024 / 1024:.2f} MB")
```

#### API Rate Limits
```python
# Check rate limit status
health_report = rate_limit_manager.get_health_report()
for provider, health in health_report.items():
    print(f"{provider}: {health['success_rate']:.1%} success rate")
```

#### File System Performance
```python
# Check disk space
import shutil
total, used, free = shutil.disk_usage("workspace/")
print(f"Free space: {free // 1024 // 1024} MB")
```

---


## Conclusion

The Deep Action Agent represents a sophisticated, multi-agent AI system designed for complex research, analysis, and action tasks. With its modular architecture, specialized sub-agents, comprehensive tooling, and robust error handling, it provides a powerful platform for automated intelligence work.

### Key Strengths
- **Modular Design**: Easily extensible and maintainable architecture
- **Specialized Agents**: Domain-specific expertise for different task types
- **Comprehensive Tooling**: Rich set of tools for various operations
- **Robust Error Handling**: Graceful failure recovery and resilience
- **Real-time Monitoring**: Live progress tracking and performance monitoring
- **Security Focus**: Comprehensive security measures and safety controls

### Use Cases
- **Research and Analysis**: Academic research, market analysis, trend identification
- **Data Processing**: Large-scale data analysis, visualization, reporting
- **Automation**: Task automation, workflow optimization, process improvement
- **Quality Assurance**: Fact-checking, bias detection, validation
- **Development**: Code generation, testing, documentation

### Future Direction
The system is designed for continuous evolution and enhancement, with planned features including advanced AI capabilities, enhanced tooling, improved scalability, and broader integration capabilities. The modular architecture ensures that new features can be added seamlessly while maintaining system stability and performance.

This documentation provides a comprehensive overview of the Deep Action Agent's capabilities, architecture, and usage. For specific implementation details, refer to the individual component documentation and source code. 