"""
Security Configuration
Centralized security settings for the deep action agent.
"""

# Dangerous Python modules that should be blocked
DANGEROUS_MODULES = [
    'os.system', 'os.popen', 'subprocess.call', 'subprocess.Popen',
    'eval', 'exec', 'compile', '__import__', 'importlib.import_module',
    'sys.modules', 'sys.path', 'sys.executable',
    'ctypes', 'ctypes.util', 'ctypes.windll', 'ctypes.cdll',
    'platform', 'socket', 'urllib', 'urllib2', 'requests',
    'pickle', 'marshal', 'shelve', 'dbm', 'sqlite3',
    'multiprocessing', 'threading', 'concurrent.futures',
    'tempfile', 'shutil', 'glob', 'fnmatch', 'pathlib',
    'builtins', '__builtins__', '__builtin__'
]

# Safe Python modules that are allowed
SAFE_MODULES = [
    'math', 'random', 'datetime', 'time', 'json', 'csv',
    're', 'string', 'collections', 'itertools', 'functools',
    'operator', 'statistics', 'decimal', 'fractions',
    'numpy', 'pandas', 'matplotlib', 'seaborn', 'plotly',
    'scipy', 'sklearn', 'tensorflow', 'torch', 'keras',
    'requests', 'urllib3', 'beautifulsoup4', 'selenium',
    'pytest', 'unittest', 'doctest', 'logging', 'argparse',
    'pathlib', 'os.path', 'sys', 'builtins'
]

# Maximum execution time for code (seconds)
MAX_EXECUTION_TIME = 60

# Maximum file size for operations (bytes)
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# Allowed file extensions for reading/writing
ALLOWED_EXTENSIONS = [
    '.txt', '.md', '.py', '.json', '.csv', '.xml', '.html', '.htm',
    '.css', '.js', '.sql', '.log', '.ini', '.cfg', '.conf',
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg',
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx'
]

# Blocked file paths/patterns
BLOCKED_PATHS = [
    '/etc/', '/var/', '/usr/', '/bin/', '/sbin/', '/dev/',
    '/proc/', '/sys/', '/boot/', '/root/', '/home/',
    '~/.ssh/', '~/.bashrc', '~/.zshrc', '~/.profile',
    '.env', '.git/', '.svn/', '.hg/'
] 