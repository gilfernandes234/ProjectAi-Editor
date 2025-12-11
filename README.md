# ProjectAI -- AI-Powered Code Editor

A modern, feature-rich code editor with integrated AI assistance

Designed for developers who want intelligent coding support with
professional editing tools.

------------------------------------------------------------------------

## 📝 Code Editing

-   Multi-tab interface with support for multiple files simultaneously\
-   Syntax highlighting for 15+ languages:\
    **Python, Lua, JavaScript, TypeScript, C, C++, C#, Java, PHP, Go,
    Swift, Ruby, SQL, HTML, CSS, XML, OTUI/OTML**\
-   Smart encoding detection (UTF-8, ANSI, Windows-1252, UTF-16)\
-   Auto-save with encoding preservation

------------------------------------------------------------------------

## ⚡ Productivity Tools

### Keyboard Shortcuts

-   **Ctrl+D** -- Duplicate line/selection\
-   **Ctrl+/** -- Toggle comment (auto-detects language)\
-   **Ctrl+F** -- Find and replace\
-   **Ctrl+S** -- Save file\
-   **Ctrl+Shift+D** -- Compare files/tabs

Additional tools:\
- Code folding\
- Line operations\
- Undo/Redo support

------------------------------------------------------------------------

## 🔍 Advanced Search & Replace

### Find Features

-   Next/Previous navigation\
-   Case sensitive matching\
-   Whole word search\
-   Highlight all occurrences

### Replace Features

-   Replace current occurrence\
-   Replace all (with confirmation)\
-   Regex support

------------------------------------------------------------------------

## 🤖 AI Integration

### Multi-provider support

-   ✅ Google Gemini\
-   🔜 Anthropic Claude (planned)\
-   🔜 OpenAI GPT (planned)

### Context-aware AI

-   Analyze current file\
-   Explain selected code\
-   Full project analysis mode\
-   Smart code suggestions\
-   One-click application of AI suggestions\
-   Conversation history

------------------------------------------------------------------------

## 📊 File Comparison (Diff Viewer)

-   Side-by-side comparison\
-   Syntax highlighting:
    -   🟢 Additions\
    -   🔴 Deletions\
-   Statistics: line additions/removals\
-   Synchronized scrolling\
-   Resizable window

------------------------------------------------------------------------

## 🎨 Visual Tools

-   Color picker integration\
-   Automatic color preview\
-   Highlight all color codes\
-   Dark theme via **qdarktheme**

------------------------------------------------------------------------

## 📁 Project Management

-   Workspace explorer (file tree)\
-   Multi-file context for AI\
-   Smart file filtering: ignores `.git`, `node_modules`, `__pycache__`

------------------------------------------------------------------------

## 🛠️ Installation

### Requirements

    Python 3.10+

### Install Dependencies

``` bash
py -m pip install PyQt6 qdarktheme chardet google-generativeai
```

`requirements.txt`:
    
    PyQt6>=6.0.0
    qdarktheme>=2.1.0
    chardet>=5.0.0
    google-generativeai>=0.3.0
    markdown>=3.4.0

------------------------------------------------------------------------

## 🚀 Quick Start

``` bash
git clone https://github.com/gilfernandes234/ProjectAI.git
cd ProjectAI
py -m pip install PyQt6 qdarktheme chardet google-generativeai
python ProjectAI.py
```

------------------------------------------------------------------------

## 🔑 Setup AI Provider

1.  Open the AI panel (right sidebar)\
2.  Select provider\
3.  Paste your API key\
4.  Click **Connect**

------------------------------------------------------------------------

## 📖 Usage Examples

### Using AI Assistant

``` python
# 1. Open a file or select code
# 2. Click "Explain Selection"
# 3. Click "Analyze File"
# 4. Enable "Full Project Mode"
# 5. Ask questions in chat
# 6. Click "Apply Code"
```

### Comparing Files

    1. Press Ctrl+Shift+D
    2. Choose two tabs or files
    3. View side-by-side diff

### Color Picker

    1. Double-click a hex color (#FF5733)
    2. Select new color
    3. Changes apply automatically

------------------------------------------------------------------------

## 🏗️ Architecture

    ProjectAI/
    ├── ProjectAI.py
    ├── ai_providers/
    │   ├── __init__.py
    │   ├── base_ai.py
    │   └── gemini_ai.py
    └── README.md

### Adding New AI Providers

``` python
from .base_ai import BaseAI

class ClaudeAI(BaseAI):
    def connect(self, api_key: str) -> tuple[bool, str]:
        pass

    def generate_response(self, prompt: str) -> str:
        pass
```

Register provider:

``` python
self.available_providers = {
    "Google Gemini": GeminiAI,
    "Anthropic Claude": ClaudeAI,
}
```

------------------------------------------------------------------------

## 🎯 Keyboard Shortcuts Reference

  Shortcut       Action
  -------------- ---------------------------
  Ctrl+N         New file
  Ctrl+O         Open file
  Ctrl+S         Save file
  Ctrl+Shift+S   Save with encoding
  Ctrl+D         Duplicate line
  Ctrl+/         Toggle comment
  Ctrl+F         Find & replace
  Ctrl+Shift+D   Compare files
  Ctrl+Shift+C   Toggle color highlighting
  Ctrl+B         Toggle file explorer
  Ctrl+Shift+A   Toggle AI chat

------------------------------------------------------------------------

## 🤝 Contributing

1.  Fork the project\
2.  Create a feature branch\
3.  Commit changes\
4.  Push to branch\
5.  Open Pull Request

------------------------------------------------------------------------

## 📝 License

This project is licensed under the **MIT License**.

------------------------------------------------------------------------

## 📧 Contact
Project Link: https://github.com/gilfernandes234/ProjectAi-Editor

⭐ *Star this repository if you found it useful!*
