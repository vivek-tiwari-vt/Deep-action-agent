# Deep Action Agent

A sophisticated multi-agent AI system for research, analysis, and action tasks with browser automation, progress tracking, and intelligent file management.

## 🚀 Features

### Core Capabilities
- **Multi-Agent Architecture**: Manager, Researcher, Analyst, and Coder agents working together
- **Browser Automation**: Human-like web browsing with Playwright
- **Progress Tracking**: Real-time task monitoring and progress updates
- **Consolidated Workspace**: Single folder per task run with organized file structure
- **Link Clicking**: Advanced link clicking with human-like behavior and data extraction
- **API Integration**: RESTful API for task execution and monitoring

### Advanced Features
- **Human-Like Behavior**: Natural scrolling, mouse movement, and click timing
- **Content Quality Assessment**: Automatic evaluation of extracted content
- **Rate Limiting**: Intelligent request management to avoid detection
- **Error Recovery**: Resilient file creation and error handling
- **Task Monitoring**: Real-time activity tracking and deviation detection
- **Live Streaming**: SSE (`/events/{task_id}`) and WebSocket (`/ws/{task_id}`) stream tokens and tool events

## 📁 Project Structure

```
deep-agent-project/
├── agents/                    # Agent implementations
│   ├── manager_agent.py      # Main orchestrator agent
│   └── sub_agents/           # Specialized sub-agents
│       ├── researcher/       # Web research agent
│       ├── analyst/          # Data analysis agent
│       └── coder/            # Code generation agent
├── tools/                    # Utility tools and functions
│   ├── web_research.py       # Web automation and research tools
│   ├── progress_tracker.py   # Progress tracking system
│   ├── task_monitor.py       # Task monitoring and compliance
│   └── file_manager.py       # File management utilities
├── main.py                   # FastAPI server and main entry point
├── config.py                 # Configuration management
└── requirements.txt          # Python dependencies
```

## 🛠️ Installation

### Prerequisites
- Python 3.8+
- Git

### Setup
1. **Clone the repository**
   ```bash
   git clone https://github.com/vivek-tiwari-vt/Deep-action-agent.git
   cd Deep-action-agent
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Install Playwright browsers**
   ```bash
   playwright install
   ```

5. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and configuration
   ```

## 🚀 Usage

### API Server
Start the FastAPI server:
```bash
python main.py
```

The server will be available at `http://localhost:8000`

### API Endpoints

#### Execute Task
```bash
curl -X POST "http://localhost:8000/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "task_description": "Research recent AI developments and create a summary report",
    "task_type": "research",
    "priority": "normal"
  }'
```

#### Check Task Status
```bash
curl "http://localhost:8000/status/{task_id}"
```

#### Monitor Task
```bash
curl "http://localhost:8000/monitor/{task_id}"
```

#### Health Check
#### Live Events (SSE)
```bash
curl -N "http://localhost:8000/events/{task_id}"
```

#### Live Events (WebSocket)
Minimal JS client example:
```javascript
const ws = new WebSocket(`ws://localhost:8000/ws/${taskId}`);
ws.onmessage = (e) => {
  const evt = JSON.parse(e.data);
  console.log('event', evt);
};
```
```bash
curl "http://localhost:8000/health"
```

### Task Types
- **research**: Web research and content extraction
- **analysis**: Data analysis and insights generation
- **coding**: Code generation and development tasks
- **mixed**: Combination of multiple task types

## 📊 Workspace Organization

Each task creates a consolidated workspace with organized file structure:

```
workspace/
└── api_task_YYYYMMDD_HHMMSS_task_id/
    ├── task_metadata.json    # Task information and status
    ├── data/                 # Raw and processed data
    ├── outputs/              # Final reports and results
    ├── logs/                 # Detailed system logs
    ├── screenshots/          # Page screenshots
    ├── progress/             # Progress tracking files
    ├── metadata/             # Task metadata and monitoring
    └── activities/           # Activity logs
```

## 🔧 Configuration

### Environment Variables
Create a `.env` file with the following variables:

```env
# API Keys
OPENAI_API_KEY=your_openai_api_key
GOOGLE_API_KEY=your_google_api_key
GOOGLE_CSE_ID=your_google_cse_id

# Browser Configuration
BROWSER_HEADLESS=false
BROWSER_SLOW_MO=1000
WEB_RESEARCH_SHOW_PROGRESS=true

# Workspace Configuration
WORKSPACE_BASE=workspace

# Logging
LOG_LEVEL=INFO
```

### Browser Settings
- `BROWSER_HEADLESS`: Set to `false` to see browser actions
- `BROWSER_SLOW_MO`: Delay between actions (milliseconds)
- `WEB_RESEARCH_SHOW_PROGRESS`: Show progress updates

## 🎯 Advanced Features

### Link Clicking Tool
The system includes an advanced link clicking tool with human-like behavior:

```python
# Example usage in research tasks
result = await web_research.click_link_and_extract(
    link_text="Read More",
    scroll_behavior="human",
    extract_data=True,
    save_data=True,
    task_id="your_task_id"
)
```

### Progress Tracking
Real-time progress tracking with callbacks:

```python
# Monitor task progress
progress_tracker.create_task("task_id", "Task Name", total_steps=10)
progress_tracker.update_task("task_id", current_step="Processing", progress=0.5)
```

### Task Monitoring
Automatic task compliance monitoring:

```python
# Log activities for monitoring
log_task_activity(
    task_id="task_id",
    activity_type="search",
    description="Performing web search",
    details={"query": "AI developments"}
)
```

## 🔒 Security

- **Environment Variables**: Sensitive data stored in `.env` file (not committed)
- **API Key Management**: Secure handling of API keys
- **File Permissions**: Proper file access controls
- **Rate Limiting**: Built-in rate limiting to prevent abuse

## 📝 Development

### Adding New Tools
1. Create tool in `tools/` directory
2. Add to appropriate agent's tool list
3. Update documentation

### Adding New Agents
1. Create agent in `agents/sub_agents/`
2. Register in `manager_agent.py`
3. Add to system prompts

### Testing
```bash
# Run tests
python -m pytest tests/

# Run specific test
python test_consolidated_workspace.py
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- Browser automation with [Playwright](https://playwright.dev/)
- AI integration with OpenAI and Google APIs
- Progress tracking with custom implementation

## 📞 Support

For support and questions:
- Create an issue on GitHub
- Check the documentation
- Review the examples in the codebase

---

**Note**: This is a sophisticated AI agent system. Ensure you have proper API keys and follow usage guidelines for the integrated services.

