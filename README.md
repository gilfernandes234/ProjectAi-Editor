#   ---------- ProjectAI Editor ----------
um Editor com intuito de ter IA como ajuda

<img width="1919" height="1046" alt="Screenshot_2" src="https://github.com/user-attachments/assets/664fee14-fa51-431c-abce-8bcc9b825d32" />

#   ---------- Site API ----------
https://aistudio.google.com/app/api-keys

#   ---------- Required ----------

- Python 3.10+
  - py -m pip install PyQt6 qdarktheme chardet google-generativea

  - Resolution: 1920x1080
  - 2gb Ram
  - Processor Dual Core
  - Hd: 4gb


  A modern, feature-rich code editor with integrated AI assistance, built with PyQt6. Designed for developers who want intelligent coding support with professional editing tools.

![Python](https://img.shields.io/badge/Python-3.10+-eenlue 📝 Code Editing

Multi-tab interface with support for multiple files simultaneously

Syntax highlighting for 15+ languages:

Python, Lua, JavaScript, TypeScript

C, C++, C#, Java, PHP, Go, Swift, Ruby

SQL, HTML, CSS, XML

OTUI/OTML (OTClient UI files)

Smart encoding detection (UTF-8, ANSI, Windows-1252, UTF-16)

Auto-save with encoding preservation

⚡ Productivity Tools
Keyboard shortcuts:

Ctrl+D - Duplicate line/selection

Ctrl+/ - Toggle comment (auto-detects language)

Ctrl+F - Find and replace

Ctrl+S - Save file

Ctrl+Shift+D - Compare files/tabs

Code folding and line operations

Undo/Redo support

🔍 Advanced Search & Replace
Find dialog with:

Next/Previous navigation

Case sensitive matching

Whole word search

Highlight all occurrences

Replace functionality:

Replace current occurrence

Replace all with confirmation

Regex support

🤖 AI Integration
Multi-provider support (modular architecture):

✅ Google Gemini

🔜 Anthropic Claude (planned)

🔜 OpenAI GPT (planned)

Context-aware AI:

Analyze current file

Explain selected code

Full project analysis mode

Smart code suggestions

One-click code application - Apply AI suggestions directly to your code

Conversation history - Chat-based interface

📊 File Comparison (Diff Viewer)
Side-by-side comparison of files or open tabs

Syntax highlighting in diff:

🟢 Green highlight for additions

🔴 Red highlight for deletions

Statistics - Count of added/removed lines

Synchronized scrolling between panels

Resizable comparison window

🎨 Visual Tools
Color picker integration:

Double-click on hex colors (#RRGGBB, #RRGGBBAA)

Visual color selector with alpha channel support

Automatic color preview in editor

Color highlighting - View all color codes with background preview

Dark theme - Professional dark UI (via qdarktheme)

📁 Project Management
Workspace explorer - Built-in file tree

Multi-file context - AI can analyze entire project structure

Smart file filtering - Ignores .git, node_modules, __pycache__

🛠️ Installation
Requirements
Python 3.10 or higher

PyQt6

Google Generative AI (for Gemini support)

Install Dependencies
bash
pip install -r requirements.txt
requirements.txt:

text
PyQt6>=6.0.0
qdarktheme>=2.1.0
chardet>=5.0.0
google-generativeai>=0.3.0
markdown>=3.4.0
Quick Start
Clone the repository:

bash
git clone https://github.com/yourusername/ProjectAI.git
cd ProjectAI
Install dependencies:

bash
pip install -r requirements.txt
Run the editor:

bash
python ProjectAI.py
🔑 Setup AI Provider
Get your API key:

Google Gemini

In the editor:

Open the AI panel (right sidebar)

Select provider from dropdown

Paste your API key

Click "Connect"

📖 Usage Examples
Using AI Assistant
python
# 1. Open a file or select code
# 2. Click "Explain Selection" to understand code
# 3. Click "Analyze File" for full file review
# 4. Enable "Full Project Mode" for multi-file analysis
# 5. Type questions in the chat
# 6. Click "Apply Code" to insert AI suggestions
Comparing Files
text
1. Press Ctrl+Shift+D or Menu → View → Compare Files
2. Choose two tabs OR select files from disk
3. View side-by-side diff with color highlighting
Color Picker
text
1. Double-click on any hex color (e.g., #FF5733)
2. Choose new color in picker
3. Color updates automatically in code
🏗️ Architecture
text
ProjectAI/
├── ProjectAI.py              # Main application
├── ai_providers/             # AI provider modules
│   ├── __init__.py
│   ├── base_ai.py           # Abstract base class
│   ├── gemini_ai.py         # Google Gemini implementation
│   ├── claude_ai.py         # Anthropic Claude (template)
│   └── openai_ai.py         # OpenAI GPT (template)
├── requirements.txt
└── README.md
Adding New AI Providers
Create new file in ai_providers/ (e.g., claude_ai.py)

Implement BaseAI abstract class:

python
from .base_ai import BaseAI

class ClaudeAI(BaseAI):
    def connect(self, api_key: str) -> tuple[bool, str]:
        # Implementation
        pass
    
    def generate_response(self, prompt: str) -> str:
        # Implementation
        pass
Register in ProjectAI.py:

python
self.available_providers = {
    "Google Gemini": GeminiAI,
    "Anthropic Claude": ClaudeAI,  # Add here
}
🎯 Keyboard Shortcuts Reference
Shortcut	Action
Ctrl+N	New file
Ctrl+O	Open file
Ctrl+S	Save file
Ctrl+Shift+S	Save with encoding
Ctrl+D	Duplicate line
Ctrl+/	Toggle comment
Ctrl+F	Find and replace
Ctrl+Shift+D	Compare files
Ctrl+Shift+C	Toggle color highlighting
Ctrl+B	Toggle file explorer
Ctrl+Shift+A	Toggle AI chat

🤝 Contributing
Contributions are welcome! Please feel free to submit a Pull Request.

Fork the project

Create your feature branch (git checkout -b feature/AmazingFeature)

Commit your changes (git commit -m 'Add some AmazingFeature')

Push to the branch (git push origin feature/AmazingFeature)

Open a Pull Request

📝 License
This project is licensed under the MIT License - see the LICENSE file for details.

🙏 Acknowledgments
Built with PyQt6

Dark theme by qdarktheme

AI support via Google Generative AI

⭐ Star this repository if you find it useful!
