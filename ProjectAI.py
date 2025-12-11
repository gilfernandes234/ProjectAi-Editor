# py -m pip install PyQt6 qdarktheme chardet google-generativeai pygments  openai


import sys
import os
import shutil
import subprocess
import qdarktheme  
import chardet
import re
import difflib

from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter
from data import BaseAI, GeminiAI, PerplexityAI, DiffViewerDialog

from data.base_ai import AIThread



from PyQt6.QtGui import (QAction, QFont, QSyntaxHighlighter, QTextCharFormat, 
                        QColor, QKeySequence, QFileSystemModel, QTextCursor, QTextDocument)
                                                             
from PyQt6.QtCore import Qt, QRegularExpression, QDir, QThread, pyqtSignal

from PyQt6.QtWidgets import (QApplication, QMainWindow, QTextEdit, QFileDialog, 
                             QVBoxLayout, QWidget, QMenuBar, QMenu, QToolBar, 
                             QStatusBar, QMessageBox, QTabWidget, QComboBox, QLabel,
                             QTreeView, QSplitter, QPushButton, QLineEdit, 
                             QScrollArea, QFrame, QHBoxLayout, QCheckBox, QColorDialog,
                             QDialog, QListWidget, QPlainTextEdit)
                             
                             

                             
class AIChatWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.conversation_history = []

        # Provedores disponíveis
        self.available_providers = {
            "Google Gemini": GeminiAI,
            "Perplexity AI": PerplexityAI,  # <- ADICIONE ESTA LINHA

           
            # "Anthropic Claude": ClaudeAI,  # Descomentar quando implementar
            # "OpenAI GPT": OpenAIAI,        # Descomentar quando implementar
        }
        
        self.current_provider: BaseAI = None
        self.conversation_history = []
        self.last_code_suggestion = None
        self.last_file_suggestion = None
        
        self.setup_ui()
    
    def on_provider_changed(self, provider_name):
        """Chamado quando o usuário troca de provedor"""
        self.status_label.setText(f"Provedor selecionado: {provider_name}")
        self.status_label.setStyleSheet("color: #2196f3; padding: 5px;")
        
        # Limpar conexão anterior
        if self.current_provider:
            self.current_provider.disconnect()
            self.current_provider = None
    
    def connect_ai(self):
        """Conecta ao provedor de IA selecionado"""
        api_key = self.api_input.text().strip()
        if not api_key:
            QMessageBox.warning(self, "Aviso", "Por favor, insira uma API Key válida")
            return
        
        provider_name = self.provider_combo.currentText()
        provider_class = self.available_providers.get(provider_name)
        
        if not provider_class:
            QMessageBox.critical(self, "Erro", "Provedor não encontrado")
            return
        
        try:
            self.current_provider = provider_class()
            success, message = self.current_provider.connect(api_key)
            
            if success:
                self.status_label.setText(f"✓ {message}")
                self.status_label.setStyleSheet("color: #4caf50; padding: 5px;")
                self.chat_display.append(f"<b>Sistema:</b> {message}! Como posso ajudar?<br><br>")
            else:
                QMessageBox.critical(self, "Erro", message)
                self.status_label.setText(f"✗ {message}")
                self.status_label.setStyleSheet("color: #f44336; padding: 5px;")
                
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao conectar: {str(e)}")


    
    def send_message(self):
        """Envia mensagem para a IA"""
        if not self.current_provider or not self.current_provider.is_connected:
            QMessageBox.warning(self, "Aviso", "Conecte-se à IA primeiro!")
            return
        
        message = self.message_input.toPlainText().strip()
        if not message:
            return
        
        self.chat_display.append(f"<b>Você:</b> {message}<br><br>")
        self.message_input.clear()
        self.message_input.setEnabled(False)
        self.status_label.setText("Processando...")
        self.status_label.setStyleSheet("color: #2196f3; padding: 5px;")
        
        # Obter contexto do arquivo atual
        context_prompt = self.build_context_prompt(message)
        
        # Criar thread para processar
        self.ai_thread = AIThread(self.current_provider, context_prompt)
        self.ai_thread.response_ready.connect(self.display_response)
        self.ai_thread.error_occurred.connect(self.display_error)
        self.ai_thread.start()
      
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Title
        title_label = QLabel("AI Assistant (Experimental)")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px; padding: 5px;")
        layout.addWidget(title_label)
        
        
        
        # NOVO: Seletor de provedor de IA
        provider_layout = QHBoxLayout()
        provider_label = QLabel("Provedor:")
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(list(self.available_providers.keys()))
        self.provider_combo.currentTextChanged.connect(self.on_provider_changed)
        provider_layout.addWidget(provider_label)
        provider_layout.addWidget(self.provider_combo)
        layout.addLayout(provider_layout)        
        
        # API key field
        api_layout = QHBoxLayout()
        api_label = QLabel("API Key:")
        self.api_input = QLineEdit()
        self.api_input.setPlaceholderText("Paste your Api key here")
        self.api_input.setEchoMode(QLineEdit.EchoMode.Password)
        connect_btn = QPushButton("Connect")
        connect_btn.clicked.connect(self.connect_ai)
        api_layout.addWidget(api_label)
        api_layout.addWidget(self.api_input)
        api_layout.addWidget(connect_btn)
        layout.addLayout(api_layout)
        
        # Checkbox for project mode
        project_mode_layout = QHBoxLayout()
        self.project_mode_checkbox = QCheckBox("Full Project Mode")
        self.project_mode_checkbox.setToolTip("Includes all .lua files in the folder in the context")
        project_mode_layout.addWidget(self.project_mode_checkbox)
        project_mode_layout.addStretch()
        layout.addLayout(project_mode_layout)
        
        # Conversation view
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e; 
                padding: 10px;
                font-size: 13px;
                line-height: 1.5;
            }
            code {
                background-color: #2d2d2d;
                padding: 2px 5px;
                border-radius: 3px;
                font-family: 'Consolas', monospace;
            }
            pre {
                background-color: #2d2d2d;
                padding: 10px;
                border-radius: 5px;
                overflow-x: auto;
            }
        """)
        layout.addWidget(self.chat_display)
       
        # Campo de entrada
        input_layout = QHBoxLayout()
        self.message_input = QTextEdit()
        self.message_input.setMaximumHeight(80)
        self.message_input.setPlaceholderText("Type your question here... (Ctrl+Enter to send)")
        self.message_input.installEventFilter(self)
        
        send_btn = QPushButton("Send")
        send_btn.clicked.connect(self.send_message)
        send_btn.setMinimumHeight(60)
        
        input_layout.addWidget(self.message_input)
        input_layout.addWidget(send_btn)
        layout.addLayout(input_layout)
        
        # Extra buttons
        buttons_layout = QHBoxLayout()
        
        clear_btn = QPushButton("Clear Chat")
        clear_btn.clicked.connect(self.clear_chat)

        
        apply_btn = QPushButton("Apply Code")
        apply_btn.clicked.connect(self.apply_code_suggestion)
        apply_btn.setStyleSheet("background-color: #2d5016; color: white;")
        apply_btn.setToolTip("Applies the last code suggested by the AI")

        buttons_layout.addWidget(clear_btn)
        buttons_layout.addWidget(apply_btn)
        layout.addLayout(buttons_layout)
        
        self.status_label = QLabel("Connect to the AI first")
        self.status_label.setStyleSheet("color: #ff9800; padding: 5px;")
        layout.addWidget(self.status_label)
        
        # Store last suggested code
        self.last_code_suggestion = None
        self.last_file_suggestion = None
        
    def build_context_prompt(self, user_message):

        try:
            main_window = self.window()
            current_editor = None
            if hasattr(main_window, "tabs"):
                current_editor = main_window.tabs.currentWidget()

            context_parts = []

            file_path = None
            file_content = ""
            selected_text = ""

            if isinstance(current_editor, CodeEditor):
                file_path = getattr(current_editor, "file_path", None)
                file_content = current_editor.toPlainText()

                cursor = current_editor.textCursor()
                selected_text = cursor.selectedText()
                # Ajuste para quebras de linha do Qt
                selected_text = selected_text.replace("\u2029", "\n")

            if file_path:
                file_name = os.path.basename(file_path)
                file_ext = os.path.splitext(file_path)[1]
                context_parts.append(f"Arquivo atual: {file_name} ({file_ext})")

            # Se o modo projeto estiver ativo, varrer arquivos da pasta de trabalho
            if self.project_mode_checkbox.isChecked() and hasattr(main_window, "working_directory") and main_window.working_directory:
                context_parts.append("\nCONTEXTO DO PROJETO (arquivos relevantes em subpastas):\n")
                project_files = self.scan_project_files(main_window.working_directory)

                def _lang_from_ext(path):
                    ext = os.path.splitext(path)[1].lower()
                    mapping = {
                        ".py": "python",
                        ".js": "javascript",
                        ".lua": "lua",
                        ".json": "json",
                        ".html": "html",
                        ".css": "css",
                        ".xml": "xml"
                    }
                    return mapping.get(ext, "")

                for pfile in project_files:
                    try:
                        with open(pfile, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()
                        if len(content) > 1200:
                            preview = content[:1200] + "\n# ... (conteúdo cortado para caber no contexto)\n"
                        else:
                            preview = content

                        lang = _lang_from_ext(pfile)
                        context_parts.append(
                            f"\n--- {os.path.basename(pfile)} ---\n```{lang}\n{preview}\n```"
                        )
                    except Exception as e:
                        print(f"Erro ao ler arquivo do projeto para contexto: {pfile}: {e}")

            # Conteúdo do arquivo atual (ou somente o trecho selecionado)
            if selected_text:
                context_parts.append("\nTrecho selecionado do arquivo atual:\n```")
                context_parts.append(selected_text)
                context_parts.append("```")
            elif file_content.strip():
                max_chars = 4000
                if len(file_content) > max_chars:
                    preview = file_content[:max_chars]
                    context_parts.append(f"\nConteúdo do arquivo atual (primeiros {max_chars} caracteres):\n```")
                    context_parts.append(preview)
                    context_parts.append("\n# ... (restante omitido)```")
                else:
                    context_parts.append("\nConteúdo completo do arquivo atual:\n```")
                    context_parts.append(file_content)
                    context_parts.append("```")

            # Pergunta do usuário
            context_parts.append("\nPergunta do usuário:")
            context_parts.append(user_message)

            context_parts.append(
                "\nIMPORTANTE: se você sugerir código para correção ou reprogramação, "
                "retorne APENAS o código completo dentro de um bloco markdown ``` sem comentários extras fora do bloco."
            )
            context_parts.append("\nResponda sempre em português do Brasil.")

            return "\n".join(context_parts)
        except Exception as e:
            print(f"Erro ao montar contexto para IA: {e}")
            # Em caso de erro, ainda assim envia a mensagem original
            return user_message + "\n\nResponda em português do Brasil."
                                       
    def get_current_file_context(self, user_message):
        try:
            main_window = self.window()
            if not hasattr(main_window, "tabs"):
                return user_message

            current_editor = main_window.tabs.currentWidget()
            if not isinstance(current_editor, CodeEditor):
                return user_message

            context_parts = []

            # -----------------------------
            # Current file info
            # -----------------------------
            file_path = getattr(current_editor, "file_path", None)
            file_content = current_editor.toPlainText()
            selected_text = current_editor.textCursor().selectedText().replace("\u2029", "\n")

            if file_path:
                file_name = os.path.basename(file_path)
                file_ext = os.path.splitext(file_path)[1]
                context_parts.append(f"Current file: {file_name} ({file_ext})")

            # -----------------------------
            # Full Project Mode (optional)
            # -----------------------------
            if self.project_mode_checkbox.isChecked() and hasattr(main_window, "working_directory"):
                context_parts.append("\nFULL PROJECT CONTEXT:\n")

                project_files = self.scan_project_files(main_window.working_directory)

                for pfile in project_files[:10]:  # limit preview
                    try:
                        with open(pfile, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()

                        preview = content[:500] + "..." if len(content) > 500 else content
                        
                        context_parts.append(
                            f"\n--- {os.path.basename(pfile)} ---\n```text\n{preview}\n```"
                        )
                    except Exception:
                        pass

            if selected_text:
                context_parts.append("\nSelected code:\n```")
                context_parts.append(selected_text)
                context_parts.append("```")

            elif file_content.strip():
                if len(file_content) > 4000:
                    preview = file_content[:4000]
                    context_parts.append("\nContent (first 4000 chars):\n```")
                    context_parts.append(preview)
                    context_parts.append("\n# ... (remaining omitted)\n```")
                else:
                    context_parts.append("\nFull content:\n```")
                    context_parts.append(file_content)
                    context_parts.append("```")

            # -----------------------------
            # User question
            # -----------------------------
            context_parts.append(f"\nQuestion: {user_message}")
            context_parts.append(
                "\nIMPORTANT: If you suggest code, provide ONLY the full code ready to replace,"
                " with no explanations inside the code block."
            )
            context_parts.append("\nRespond in English.")

            return "\n".join(context_parts)

        except Exception as e:
            print(f"Error getting context: {e}")
            return user_message + "\n\nPlease respond in English."


    def scan_project_files(self, directory, extensions=None):
        project_files = []  
        
        if extensions is None:
            extensions = ['.lua', '.py', '.js', '.ts', '.json', '.xml', 
                         '.html', '.css', '.otui', '.otml', '.txt']
        
        try:
            for root, dirs, files in os.walk(directory):
                dirs[:] = [d for d in dirs if d not in ['.git', 'node_modules', '__pycache__', '.vscode']]
                
                for file in files:
                    if any(file.endswith(ext) for ext in extensions):
                        project_files.append(os.path.join(root, file))
                        
                    if len(project_files) >= 15:
                        break
                if len(project_files) >= 15:
                    break
        except Exception as e:
            print(f"Error scanning project: {e}")
        
        return project_files

    
    def apply_code_suggestion(self):
        if not self.last_code_suggestion:
            QMessageBox.warning(self, "Warning", "No code has been suggested yet")
            return
        
        main_window = self.window()
        if hasattr(main_window, 'tabs'):
            current_editor = main_window.tabs.currentWidget()
            if current_editor and isinstance(current_editor, CodeEditor):
                # Check if there is a selection
                cursor = current_editor.textCursor()
                if cursor.hasSelection():
                    reply = QMessageBox.question(
                        self, 
                        'Replace selection?', 
                        'Do you want to replace the selected text with the suggested code?',
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )
                    if reply == QMessageBox.StandardButton.Yes:
                        cursor.insertText(self.last_code_suggestion)
                        self.chat_display.append("<b>System:</b> Code applied to selection!<br><br>")
                else:
                    reply = QMessageBox.question(
                        self, 
                        'Replace file?', 
                        'Do you want to replace the entire file content with the suggested code?',
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )
                    if reply == QMessageBox.StandardButton.Yes:
                        current_editor.setPlainText(self.last_code_suggestion)
                        self.chat_display.append("<b>System:</b> Code applied to entire file!<br><br>")
            else:
                QMessageBox.information(self, "Info", "No file open")
    
    def eventFilter(self, obj, event):
        if obj == self.message_input and event.type() == event.Type.KeyPress:
            if event.key() == Qt.Key.Key_Return and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                self.send_message()
                return True
        return super().eventFilter(obj, event)
       
    def display_response(self, response):
        """Exibe resposta da IA com código formatado em boxes"""
        import re
        from html import escape
        
        # Detectar blocos de código ``````
        code_block_pattern = r'``````'
        
        def create_code_box(match):
            language = match.group(1) or 'text'
            code = match.group(2)
# Detectar lexer pela linguagem
            try:
                from pygments.lexers import get_lexer_by_name
                from pygments.formatters import HtmlFormatter
                from pygments import highlight as pygments_highlight
                
                if language:
                    lexer = get_lexer_by_name(language, stripall=True)
                else:
                    lexer = get_lexer_by_name('text', stripall=True)
                
                formatter = HtmlFormatter(
                    style='monokai',  # ou 'github-dark', 'dracula'
                    noclasses=True,   # inline styles
                    cssclass='',
                    prestyles='margin: 0; padding: 0; background: transparent;'
                )
                escaped_code = pygments_highlight(code, lexer, formatter)
                # Remove o <div> e <pre> externo do pygments (já temos nossa box)
                escaped_code = re.sub(r'^<div[^>]*><pre[^>]*>', '', escaped_code)
                escaped_code = re.sub(r'</pre></div>$', '', escaped_code)
            except:
                # Fallback se linguagem não for reconhecida
                escaped_code = escape(code)

            
            # ID único para cada bloco
            import random
            box_id = f"code_{random.randint(1000, 9999)}"
            
            # HTML da box com botão de copiar
            return f'''
            <div style="position: relative; margin: 10px 0; background: #2b2b2b; border-radius: 8px; border: 1px solid #3d3d3d;">
                <div style="display: flex; justify-content: space-between; align-items: center; 
                            background: #1e1e1e; padding: 8px 12px; border-radius: 8px 8px 0 0; border-bottom: 1px solid #3d3d3d;">
                    <span style="color: #888; font-size: 12px; font-family: Consolas, monospace;">{language}</span>
                    <button onclick="copyCode_{box_id}()" id="btn_{box_id}" 
                            style="background: #3d3d3d; color: #ccc; border: none; padding: 4px 12px; 
                                   border-radius: 4px; cursor: pointer; font-size: 11px; font-family: Arial;">
                        📋 Copiar
                    </button>
                </div>
                <pre id="{box_id}" style="margin: 0; padding: 15px; overflow-x: auto; 
                                          background: #2b2b2b; color: #d4d4d4; 
                                          font-family: Consolas, Monaco, monospace; font-size: 13px; 
                                          line-height: 1.5; border-radius: 0 0 8px 8px;"><code>{escaped_code}</code></pre>
            </div>
            <script>
            function copyCode_{box_id}() {{
                const code = document.getElementById('{box_id}').innerText;
                const btn = document.getElementById('btn_{box_id}');
                
                // Copiar para clipboard (método compatível com Qt)
                const textarea = document.createElement('textarea');
                textarea.value = code;
                document.body.appendChild(textarea);
                textarea.select();
                document.execCommand('copy');
                document.body.removeChild(textarea);
                
                // Feedback visual
                btn.innerHTML = '✅ Copiado!';
                btn.style.background = '#2d5016';
                setTimeout(() => {{
                    btn.innerHTML = '📋 Copiar';
                    btn.style.background = '#3d3d3d';
                }}, 2000);
            }}
            </script>
            '''
        

        code_pattern = r'``````'
        formatted_response = re.sub(code_pattern, create_code_box, response, flags=re.DOTALL)
        
        # Exibir no chat
        self.chat_display.append(f"<b>AI:</b><br>{formatted_response}<br>")
        self.message_input.setEnabled(True)
        self.message_input.setFocus()
        self.status_label.setText("Ready")
        self.status_label.setStyleSheet("color: #4caf50; padding: 5px;")

        

    def update_last_code_suggestion(self, raw_text):
        """Extrai o último bloco de código da resposta da IA para permitir aplicar no editor."""
        try:
            # Procurar blocos de código em markdown ```lang ... ```
            code_blocks = re.findall(r"```(?:[a-zA-Z0-9_+-]+)?\n(.*?)```", raw_text, re.DOTALL)
            if code_blocks:
                self.last_code_suggestion = code_blocks[-1].strip()
                return

            # Se não há cercas de código mas o texto parece ser predominantemente código, usar tudo
            stripped = raw_text.strip()
            lines = stripped.splitlines()
            if len(lines) > 1 and any(kw in stripped for kw in ("def ", "class ", "{", "}", "function ", "local ")):
                self.last_code_suggestion = stripped
        except Exception as e:
            # Em caso de erro, apenas registra no console e não quebra a interface
            print(f"Erro ao extrair código da resposta da IA: {e}")
        
    def markdown_to_html(self, text):
        # Replace double line breaks with paragraphs
        text = text.replace('\n\n', '</p><p>')
             
        # Inline code (`code`)
        text = re.sub(r'`([^`]+)`', r'<code style="background-color: #2d2d2d; padding: 2px 5px; border-radius: 3px;">\1</code>', text)
        

        text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
        text = re.sub(r'__(.+?)__', r'<b>\1</b>', text)
        

        text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
        text = re.sub(r'_(.+?)_', r'<i>\1</i>', text)
        
        # Headings
        text = re.sub(r'^### (.+)$', r'<h3 style="color: #569CD6; margin-top: 10px;">\1</h3>', text, flags=re.MULTILINE)
        text = re.sub(r'^## (.+)$', r'<h2 style="color: #569CD6; margin-top: 10px;">\1</h2>', text, flags=re.MULTILINE)
        text = re.sub(r'^# (.+)$', r'<h1 style="color: #569CD6; margin-top: 10px;">\1</h1>', text, flags=re.MULTILINE)
        
        # Unordered lists
        text = re.sub(r'^\* (.+)$', r'<li>\1</li>', text, flags=re.MULTILINE)
        text = re.sub(r'^- (.+)$', r'<li>\1</li>', text, flags=re.MULTILINE)
        
        # Ordered lists
        text = re.sub(r'^\d+\. (.+)$', r'<li>\1</li>', text, flags=re.MULTILINE)
        
        # Wrap list items with <ul> or <ol>
        text = re.sub(r'(<li>.*?</li>)(?=\n(?!<li>))', r'<ul>\1</ul>', text, flags=re.DOTALL)
        
        # Links [text](url)
        text = re.sub(r'\[([^\]]+)\]\(([^\)]+)\)', r'<a href="\2" style="color: #4A9EFF;">\1</a>', text)
        
        # Single line breaks
        text = text.replace('\n', '<br>')
        
        # Wrap everything in a paragraph
        text = f'<p>{text}</p>'
        
        return text
   
    def display_error(self, error):
        self.chat_display.append(f"<b>Error:</b> {error}<br><br>")
        self.message_input.setEnabled(True)
        self.status_label.setText("Error during request")
        self.status_label.setStyleSheet("color: #f44336; padding: 5px;")
    
    def clear_chat(self):
        """Clears the chat history"""
        self.chat_display.clear()
        self.conversation_history = []
    
    
            
class SyntaxHighlighter(QSyntaxHighlighter):
    def __init__(self, parent, file_extension):
        super().__init__(parent)
        self.file_extension = file_extension.lower()
        self.highlighting_rules = []
        
        # Definir cores para o tema escuro
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#569CD6"))  # Azul
        keyword_format.setFontWeight(QFont.Weight.Bold)
        
        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#CE9178"))  # Laranja
        
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#6A9955"))  # Verde
        
        function_format = QTextCharFormat()
        function_format.setForeground(QColor("#DCDCAA"))  # Amarelo
        
        number_format = QTextCharFormat()
        number_format.setForeground(QColor("#B5CEA8"))  # Verde claro
        
        # NOVO: Formato para propriedades OTUI
        property_format = QTextCharFormat()
        property_format.setForeground(QColor("#9CDCFE"))  # Azul claro
        
        # NOVO: Formato para valores booleanos
        boolean_format = QTextCharFormat()
        boolean_format.setForeground(QColor("#569CD6"))  # Azul
        
        # NOVO: Formato para widgets OTUI
        widget_format = QTextCharFormat()
        widget_format.setForeground(QColor("#4EC9B0"))  # Verde-azulado
        widget_format.setFontWeight(QFont.Weight.Bold)        
        
        # Keywords por linguagem
        keywords = {
            '.py': ['def', 'class', 'import', 'from', 'as', 'if', 'elif', 'else', 
                   'for', 'while', 'return', 'try', 'except', 'finally', 'with', 
                   'True', 'False', 'None', 'and', 'or', 'not', 'in', 'is', 'lambda'],
                   
            '.js': ['var', 'let', 'const', 'function', 'if', 'else', 'for', 'while', 
                   'return', 'class', 'extends', 'import', 'export', 'async', 'await', 
                   'try', 'catch', 'finally', 'new', 'this', 'null', 'undefined'],
                   
            '.ts': ['var', 'let', 'const', 'function', 'if', 'else', 'for', 'while', 
                   'return', 'class', 'interface', 'type', 'extends', 'implements', 
                   'import', 'export', 'async', 'await', 'public', 'private', 'protected'],
                   
            '.java': ['public', 'private', 'protected', 'class', 'interface', 'extends', 
                     'implements', 'void', 'int', 'String', 'boolean', 'if', 'else', 
                     'for', 'while', 'return', 'new', 'this', 'static', 'final'],
                     
            '.cs': ['public', 'private', 'protected', 'class', 'interface', 'namespace', 
                   'using', 'void', 'int', 'string', 'bool', 'if', 'else', 'for', 
                   'while', 'return', 'new', 'this', 'static', 'async', 'await'],
                   
            '.cpp': ['class', 'namespace', 'public', 'private', 'protected', 'virtual', 
                    'void', 'int', 'char', 'bool', 'if', 'else', 'for', 'while', 
                    'return', 'new', 'delete', 'this', 'nullptr', 'const', 'static'],
                    
            '.c': ['int', 'char', 'float', 'double', 'void', 'if', 'else', 'for', 
                  'while', 'return', 'struct', 'typedef', 'const', 'static', 'extern'],
                  
            '.php': ['class', 'function', 'if', 'else', 'elseif', 'for', 'while', 
                    'return', 'public', 'private', 'protected', 'static', 'namespace', 
                    'use', 'new', 'this', 'echo', 'require', 'include'],
                    
            '.rb': ['def', 'class', 'module', 'if', 'elsif', 'else', 'unless', 'for', 
                   'while', 'return', 'require', 'include', 'attr_accessor', 'end'],
                   
            '.go': ['func', 'package', 'import', 'var', 'const', 'type', 'struct', 
                   'interface', 'if', 'else', 'for', 'return', 'defer', 'go', 'chan'],
                   
            '.swift': ['func', 'class', 'struct', 'enum', 'protocol', 'var', 'let', 
                      'if', 'else', 'for', 'while', 'return', 'import', 'self', 'init'],
                      
            '.lua': ['function', 'local', 'if', 'then', 'else', 'elseif', 'end', 
                    'for', 'while', 'do', 'return', 'nil', 'true', 'false', 'and', 'or', 'not'],
                    
            '.otui': ['anchors', 'margin', 'padding', 'size', 'color', 'background-color',
                     'text', 'font', 'opacity', 'visible', 'enabled', 'focusable',
                     'phantom', 'draggable', 'image-source', 'image-clip', 'image-border',
                     'layout', 'image-color', 'text-offset', 'text-align', 'text-wrap',
                     'on', 'id', '@onLoad', '@onDestroy', '@onSetup'],
            
            '.otml': ['anchors', 'margin', 'padding', 'size', 'color', 'background-color',
                     'text', 'font', 'opacity', 'visible', 'enabled', 'focusable',
                     'phantom', 'draggable', 'image-source', 'image-clip', 'image-border',
                     'layout', 'image-color', 'text-offset', 'text-align', 'text-wrap',
                     'on', 'id', '@onLoad', '@onDestroy', '@onSetup'],                    
                    
                    
                    
        }
        
        # Adicionar keywords
        otui_widgets = [
            'UIWidget', 'UIButton', 'UILabel', 'UITextEdit', 'UICheckBox',
            'UIWindow', 'UIScrollArea', 'UIScrollBar', 'UIProgressBar',
            'UISpinBox', 'UIComboBox', 'UITabBar', 'UILineEdit',
            'UIItem', 'UICreature', 'UIMap', 'UIMinimap', 'Panel',
            'Button', 'Label', 'TextEdit', 'CheckBox', 'Window',
            'ScrollArea', 'VerticalScrollBar', 'HorizontalScrollBar',
            'MainWindow', 'MiniWindow', 'Item', 'Creature'
        ]
        
        # Adicionar keywords
        current_keywords = keywords.get(self.file_extension, [])
        for word in current_keywords:
            pattern = QRegularExpression(f'\\b{word}\\b')
            self.highlighting_rules.append((pattern, keyword_format))
        
        # NOVO: Adicionar widgets OTUI
        if self.file_extension in ['.otui', '.otml']:
            for widget in otui_widgets:
                pattern = QRegularExpression(f'\\b{widget}\\b')
                self.highlighting_rules.append((pattern, widget_format))
            
            # Propriedades (palavras seguidas de :)
            property_pattern = QRegularExpression(r'\b[\w-]+(?=\s*:)')
            self.highlighting_rules.append((property_pattern, property_format))
            
            # Valores booleanos
            bool_pattern = QRegularExpression(r'\b(true|false)\b')
            self.highlighting_rules.append((bool_pattern, boolean_format))
            
            # IDs (start with #)
            id_pattern = QRegularExpression(r'#[\w-]+')
            self.highlighting_rules.append((id_pattern, widget_format))
            
            # Cores hexadecimais
            color_pattern = QRegularExpression(r'#[0-9A-Fa-f]{6,8}\b')
            color_format = QTextCharFormat()
            color_format.setForeground(QColor("#CE9178"))
            self.highlighting_rules.append((color_pattern, color_format))
        
        # Strings
        self.highlighting_rules.append((QRegularExpression(r'"[^"]*"'), string_format))
        self.highlighting_rules.append((QRegularExpression(r"'[^']*'"), string_format))
        
        # Numbers
        self.highlighting_rules.append((QRegularExpression(r'\b\d+\b'), number_format))
        
        # Comments
        if self.file_extension in ['.py', '.rb', '.sh', '.otui', '.otml']:
            self.highlighting_rules.append((QRegularExpression(r'#.*'), comment_format))
        elif self.file_extension in ['.js', '.ts', '.java', '.cs', '.cpp', '.c', '.php', '.go', '.swift']:
            self.highlighting_rules.append((QRegularExpression(r'//.*'), comment_format))
        elif self.file_extension == '.lua':
            self.highlighting_rules.append((QRegularExpression(r'--.*'), comment_format))
        elif self.file_extension == '.sql':
            self.highlighting_rules.append((QRegularExpression(r'--.*'), comment_format))
        
        # Functions
        self.highlighting_rules.append((QRegularExpression(r'\b[A-Za-z]+[A-Za-z0-9_]*(?=\()'), function_format))
    
    def highlightBlock(self, text):
        for pattern, format_style in self.highlighting_rules:
            iterator = pattern.globalMatch(text)
            while iterator.hasNext():
                match = iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), format_style)

class CodeEditor(QTextEdit):
    def __init__(self, file_path=None):
        super().__init__()
        self.file_path = file_path
        self.current_encoding = 'utf-8'
        self.setFont(QFont("Consolas", 11))
        self.textChanged.connect(self.on_text_changed)        
        
        if file_path:
            self.load_file(file_path)
            ext = os.path.splitext(file_path)[1]
            
            file_size = os.path.getsize(file_path)
            max_size_for_highlighting = 1024 * 1024
            
            if file_size < max_size_for_highlighting:
                self.highlighter = SyntaxHighlighter(self.document(), ext)
            else:
                print(f"Large file ({file_size} bytes), syntax highlighting disabled")
   
    def on_text_changed(self):
        """Update color highlighting when text changes"""
        if hasattr(self, 'color_highlighting_enabled') and self.color_highlighting_enabled:
            # Use a timer to avoid updating on every keystroke
            if not hasattr(self, 'color_update_timer'):
                from PyQt6.QtCore import QTimer
                self.color_update_timer = QTimer()
                self.color_update_timer.setSingleShot(True)
                self.color_update_timer.timeout.connect(self.highlight_all_colors)
            
            self.color_update_timer.start(500)  # Update after 500ms of inactivity

    def mouseDoubleClickEvent(self, event):
        import re
        
        cursor = self.cursorForPosition(event.pos())
        click_pos = cursor.position()
        
        # Grab the entire line
        cursor.movePosition(QTextCursor.MoveOperation.StartOfLine)
        cursor.movePosition(QTextCursor.MoveOperation.EndOfLine, QTextCursor.MoveMode.KeepAnchor)
        line_text = cursor.selectedText()
        line_start = cursor.selectionStart()
        
        # Search for all colors in the line
        pattern = r'#[0-9A-Fa-f]{3,8}\b'
        
        for match in re.finditer(pattern, line_text):
            # Calculate absolute position of the color in the document
            color_start = line_start + match.start()
            color_end = line_start + match.end()
            
            # Check if the click was inside this color span
            if color_start <= click_pos <= color_end:
                color_code = match.group()
                
                # Select the color
                cursor.setPosition(color_start)
                cursor.setPosition(color_end, QTextCursor.MoveMode.KeepAnchor)
                
                print(f"Double click on color: '{color_code}'")  # DEBUG
                self.open_color_picker(cursor, color_code)
                return
        
        # If no color was found, fallback to default behavior
        print(f"No color at position {click_pos}")  # DEBUG
        super().mouseDoubleClickEvent(event)

    
    def is_color_code(self, text):
        import re
        # Aceitar formatos: #RGB, #RRGGBB, #RRGGBBAA
        pattern = r'^#[0-9A-Fa-f]{3}$|^#[0-9A-Fa-f]{6}$|^#[0-9A-Fa-f]{8}$'
        return bool(re.match(pattern, text))
    
    def open_color_picker(self, cursor, current_color):
        try:
            # Converter cor atual para QColor
            initial_color = QColor(current_color)
            
            # Open color dialog
            color = QColorDialog.getColor(
                initial_color, 
                self,
                "Select Color",
                QColorDialog.ColorDialogOption.ShowAlphaChannel
            )
            
            # If the user chose a color
            if color.isValid():
                # Convert to hexadecimal
                if color.alpha() < 255:
                    # Include alpha if not fully opaque
                    new_color = color.name(QColor.NameFormat.HexArgb)
                else:
                    # Default format #RRGGBB
                    new_color = color.name(QColor.NameFormat.HexRgb)
                
                # Replace selected text with new color
                cursor.insertText(new_color)
                
                # Show temporary color preview in background
                self.show_color_preview(cursor, new_color)
                
        except Exception as e:
            print(f"Error opening color picker: {e}")
    
    def show_color_preview(self, cursor, color_code):
        # Create format with background color
        format_preview = QTextCharFormat()
        format_preview.setBackground(QColor(color_code))
        
        # If the color is very dark, use white text
        qcolor = QColor(color_code)
        brightness = (qcolor.red() * 299 + qcolor.green() * 587 + qcolor.blue() * 114) / 1000
        if brightness < 128:
            format_preview.setForeground(QColor("#FFFFFF"))
        else:
            format_preview.setForeground(QColor("#000000"))
        
        # Apply the format temporarily
        cursor.setPosition(cursor.position() - len(color_code))
        cursor.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor, len(color_code))
        cursor.mergeCharFormat(format_preview)
    
    def keyPressEvent(self, event):
        # Ctrl+F to search
        if event.key() == Qt.Key.Key_F and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.show_find_dialog()
            return
        
        # Ctrl+D to duplicate line
        elif event.key() == Qt.Key.Key_D and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.duplicate_line()
            return
        
        # Ctrl+/ to comment/uncomment line
        elif event.key() == Qt.Key.Key_Slash and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.toggle_comment()
            return
        
        # Fallback to default behavior
        super().keyPressEvent(event)
              
    def highlight_all_colors(self):

        # Remove previous highlights
        cursor = QTextCursor(self.document())
        cursor.select(QTextCursor.SelectionType.Document)
        default_format = QTextCharFormat()
        cursor.setCharFormat(default_format)
        
        # Find all color codes
        text = self.toPlainText()
        pattern = r'#[0-9A-Fa-f]{3,8}\b'
        
        extra_selections = []
        
        for match in re.finditer(pattern, text):
            if len(match.group()) in [4, 7, 9]:  # #RGB, #RRGGBB, #RRGGBBAA
                color_code = match.group()
                
                # Create cursor for this position
                cursor = QTextCursor(self.document())
                cursor.setPosition(match.start())
                cursor.setPosition(match.end(), QTextCursor.MoveMode.KeepAnchor)
                
                # Create extra selection with background color
                selection = QTextEdit.ExtraSelection()
                selection.cursor = cursor
                
                # Format with background color
                color_format = QTextCharFormat()
                qcolor = QColor(color_code)
                color_format.setBackground(qcolor)
                
                # Adjust text color based on brightness
                brightness = (qcolor.red() * 299 + qcolor.green() * 587 + qcolor.blue() * 114) / 1000
                if brightness < 128:
                    color_format.setForeground(QColor("#FFFFFF"))
                else:
                    color_format.setForeground(QColor("#000000"))
                
                selection.format = color_format
                extra_selections.append(selection)
        
        self.setExtraSelections(extra_selections)
             
    def show_find_dialog(self):
        # Check if there is already an open window
        if not hasattr(self, 'find_dialog') or not self.find_dialog.isVisible():
            self.find_dialog = FindReplaceDialog(self)
            
            # If text is selected, use it as initial search
            cursor = self.textCursor()
            if cursor.hasSelection():
                selected_text = cursor.selectedText()
                if '\u2029' not in selected_text:  # If not multi-line
                    self.find_dialog.find_input.setText(selected_text)
        
        self.find_dialog.show()
        self.find_dialog.raise_()
        self.find_dialog.activateWindow()

    def duplicate_line(self):
        cursor = self.textCursor()
        
        if cursor.hasSelection():
            selected_text = cursor.selectedText()
            # selectedText uses Unicode U+2029 for line breaks
            selected_text = selected_text.replace('\u2029', '\n')
            

            cursor.clearSelection()
            cursor.movePosition(QTextCursor.MoveOperation.EndOfLine)
            cursor.insertText('\n' + selected_text)
        else:
            # Duplicate current line
            cursor.movePosition(QTextCursor.MoveOperation.StartOfLine)
            cursor.movePosition(QTextCursor.MoveOperation.EndOfLine, QTextCursor.MoveMode.KeepAnchor)
            line_text = cursor.selectedText()
            
            # Insert duplicated line below
            cursor.movePosition(QTextCursor.MoveOperation.EndOfLine)
            cursor.insertText('\n' + line_text)
        
        self.setTextCursor(cursor)
    
    def toggle_comment(self):
        cursor = self.textCursor()
        
        file_ext = os.path.splitext(self.file_path)[1] if self.file_path else ''
        
        comment_symbols = {
            '.py': '#',
            '.rb': '#',
            '.sh': '#',
            '.js': '//',
            '.ts': '//',
            '.java': '//',
            '.cs': '//',
            '.cpp': '//',
            '.c': '//',
            '.php': '//',
            '.go': '//',
            '.swift': '//',
            '.lua': '--',
            '.sql': '--',
            '.otui': '//',  
            '.otml': '#'          
        }
        
        comment_symbol = comment_symbols.get(file_ext, '#')
        
        if cursor.hasSelection():
            start = cursor.selectionStart()
            end = cursor.selectionEnd()
            
            cursor.setPosition(start)
            cursor.movePosition(QTextCursor.MoveOperation.StartOfLine)
            
            lines_to_process = []
            while cursor.position() < end:
                cursor.movePosition(QTextCursor.MoveOperation.StartOfLine)
                cursor.movePosition(QTextCursor.MoveOperation.EndOfLine, QTextCursor.MoveMode.KeepAnchor)
                line_text = cursor.selectedText()
                lines_to_process.append((cursor.position(), line_text))
                
                if not cursor.movePosition(QTextCursor.MoveOperation.Down):
                    break
            

            all_commented = all(line.strip().startswith(comment_symbol) for _, line in lines_to_process if line.strip())
            
            for pos, line_text in reversed(lines_to_process):
                cursor.setPosition(pos - len(line_text))
                cursor.movePosition(QTextCursor.MoveOperation.EndOfLine, QTextCursor.MoveMode.KeepAnchor)
                
                if all_commented:
                    # Uncomment
                    new_text = line_text.replace(comment_symbol + ' ', '', 1).replace(comment_symbol, '', 1)
                else:
                    # Comment
                    new_text = comment_symbol + ' ' + line_text
                
                cursor.insertText(new_text)
        else:
            # Comment/uncomment single line
            cursor.movePosition(QTextCursor.MoveOperation.StartOfLine)
            cursor.movePosition(QTextCursor.MoveOperation.EndOfLine, QTextCursor.MoveMode.KeepAnchor)
            line_text = cursor.selectedText()
            
            if line_text.strip().startswith(comment_symbol):
                # Uncomment
                new_text = line_text.replace(comment_symbol + ' ', '', 1).replace(comment_symbol, '', 1)
            else:
                # Comment
                new_text = comment_symbol + ' ' + line_text
            
            cursor.insertText(new_text)
        
        self.setTextCursor(cursor)
    
    def detect_encoding(self, file_path):
        try:

            with open(file_path, 'rb') as f:
                raw_data = f.read(10240)  # Limit to 10KB
            
            # If the file is tiny, use everything
            if len(raw_data) == 0:
                return 'utf-8', 1.0
            
            result = chardet.detect(raw_data)
            detected_encoding = result['encoding']
            confidence = result['confidence']
            
            # Normalize encoding names
            if detected_encoding:
                detected_encoding = detected_encoding.lower()
                if 'iso-8859' in detected_encoding or 'latin' in detected_encoding:
                    detected_encoding = 'latin-1'  # ANSI
                elif 'utf-8' in detected_encoding:
                    detected_encoding = 'utf-8'
                elif 'windows-1252' in detected_encoding or 'cp1252' in detected_encoding:
                    detected_encoding = 'cp1252'  # ANSI Windows
                elif 'ascii' in detected_encoding:
                    detected_encoding = 'utf-8'  # ASCII is compatible with UTF-8
            
            # If confidence is too low, default to UTF-8
            if confidence < 0.7:
                detected_encoding = 'utf-8'
            
            return detected_encoding, confidence
        except Exception as e:
            print(f"Error detecting encoding: {e}")
            return 'utf-8', 0.0
                  
    def load_file(self, file_path, encoding=None):

        try:

            file_size = os.path.getsize(file_path)
            
            if not encoding:
                detected_encoding, confidence = self.detect_encoding(file_path)
                encoding = detected_encoding if detected_encoding else 'utf-8'
            
            self.current_encoding = encoding
            

            if file_size > 5 * 1024 * 1024:  # 5MB
                reply = QMessageBox.question(
                    None, 
                    'Large File', 
                    f'The file is {file_size / (1024*1024):.1f}MB. It may take time to load. Continue?',
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.No:
                    return False
            
            # Load file
            with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                content = f.read()
            
            # Desabilitar updates durante carregamento de texto grande
            self.setUpdatesEnabled(False)
            self.setPlainText(content)
            self.setUpdatesEnabled(True)
            
            self.file_path = file_path
            return True
            
        except Exception as e:
            # Fallback to UTF-8
            try:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                
                self.setUpdatesEnabled(False)
                self.setPlainText(content)
                self.setUpdatesEnabled(True)
                
                self.file_path = file_path
                self.current_encoding = 'utf-8'
                return True
            except Exception as e2:
                QMessageBox.critical(None, "Error", f"Error opening file: {str(e2)}")
                return False
               
        except Exception as e:
            # Fallback to UTF-8 on error
            try:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                self.setPlainText(content)
                self.file_path = file_path
                self.current_encoding = 'utf-8'
                return True
            except Exception as e2:
                QMessageBox.critical(None, "Error", f"Error opening file: {str(e2)}")
                return False

    
    def save_file(self, encoding=None):

        if not self.file_path:
            return self.save_file_as(encoding)
        
        if not encoding:
            encoding = self.current_encoding
        
        try:
            # Criar backup .bak antes de salvar
            if os.path.exists(self.file_path):
                try:
                    backup_path = self.file_path + ".bak"
                    shutil.copy2(self.file_path, backup_path)
                except Exception as backup_error:
                    # Não impedir o salvamento se o backup falhar, apenas informar no console
                    print(f"Falha ao criar backup .bak de '{self.file_path}': {backup_error}")
            with open(self.file_path, 'w', encoding=encoding, errors='replace') as f:
                f.write(self.toPlainText())
            self.current_encoding = encoding
            return True
        except Exception as e:
            QMessageBox.critical(None, "Error", f"Error saving file: {str(e)}")
            return False
    
    def save_file_as(self, encoding=None):
        file_path, _ = QFileDialog.getSaveFileName(None, 
        "Save As", 
        "All Files  (*)"
        )
        if file_path:
            self.file_path = file_path
            return self.save_file(encoding)
        return False
         
    def reload_with_encoding(self, encoding):
        """Reload the file with a different encoding"""
        if self.file_path:
            self.load_file(self.file_path, encoding)

class FindReplaceDialog(QWidget):

    def __init__(self, editor, parent=None):
        super().__init__(parent)
        self.editor = editor
        self.last_match_position = -1
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("Find and Replace")
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
        self.setGeometry(300, 300, 500, 250)
        
        layout = QVBoxLayout(self)
        
        # Find group
        find_group = QWidget()
        find_layout = QVBoxLayout(find_group)
        
        find_label = QLabel("Find:")
        find_layout.addWidget(find_label)
        
        find_input_layout = QHBoxLayout()
        self.find_input = QLineEdit()
        self.find_input.setPlaceholderText("Enter the text to find...")
        self.find_input.returnPressed.connect(self.find_next)
        find_input_layout.addWidget(self.find_input)
        find_layout.addLayout(find_input_layout)
        
        # Search options
        options_layout = QHBoxLayout()
        self.case_sensitive_check = QCheckBox("Match case")
        self.whole_word_check = QCheckBox("Whole word")
        options_layout.addWidget(self.case_sensitive_check)
        options_layout.addWidget(self.whole_word_check)
        find_layout.addLayout(options_layout)
        
        # Search buttons
        find_buttons_layout = QHBoxLayout()
        self.find_prev_btn = QPushButton("Previous")
        self.find_prev_btn.clicked.connect(self.find_previous)
        self.find_next_btn = QPushButton("Next")
        self.find_next_btn.clicked.connect(self.find_next)
        self.highlight_all_btn = QPushButton("Highlight All")
        self.highlight_all_btn.clicked.connect(self.highlight_all)
        
        find_buttons_layout.addWidget(self.find_prev_btn)
        find_buttons_layout.addWidget(self.find_next_btn)
        find_buttons_layout.addWidget(self.highlight_all_btn)
        find_layout.addLayout(find_buttons_layout)
        
        layout.addWidget(find_group)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)
        
        # Replace group
        replace_group = QWidget()
        replace_layout = QVBoxLayout(replace_group)
        
        replace_label = QLabel("Replace with:")
        replace_layout.addWidget(replace_label)
        
        self.replace_input = QLineEdit()
        self.replace_input.setPlaceholderText("Enter replacement text...")
        replace_layout.addWidget(self.replace_input)
        
        # Replace buttons
        replace_buttons_layout = QHBoxLayout()
        self.replace_btn = QPushButton("Replace")
        self.replace_btn.clicked.connect(self.replace_current)
        self.replace_all_btn = QPushButton("Replace All")
        self.replace_all_btn.clicked.connect(self.replace_all)
        
        replace_buttons_layout.addWidget(self.replace_btn)
        replace_buttons_layout.addWidget(self.replace_all_btn)
        replace_layout.addLayout(replace_buttons_layout)
        
        layout.addWidget(replace_group)
        
        # Status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #888; padding: 5px;")
        layout.addWidget(self.status_label)
        
        # Close button
        close_layout = QHBoxLayout()
        close_layout.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        close_layout.addWidget(close_btn)
        layout.addLayout(close_layout)
    
    def get_search_flags(self):
        flags = QTextDocument.FindFlag(0)
        
        if self.case_sensitive_check.isChecked():
            flags |= QTextDocument.FindFlag.FindCaseSensitively
        
        if self.whole_word_check.isChecked():
            flags |= QTextDocument.FindFlag.FindWholeWords
        
        return flags
    
    def find_next(self):
        search_text = self.find_input.text()
        if not search_text:
            self.status_label.setText("Enter text to find")
            return
        
        cursor = self.editor.textCursor()
        flags = self.get_search_flags()
        
        # Search from the current position
        found_cursor = self.editor.document().find(search_text, cursor, flags)
        
        if found_cursor.isNull():
            # If not found, search from start
            found_cursor = self.editor.document().find(search_text, 0, flags)
            
            if found_cursor.isNull():
                self.status_label.setText("No occurrences found")
                return
            else:
                self.status_label.setText("Wrapped to start of document")
        else:
            self.status_label.setText("Found")
        
        # Select the found text
        self.editor.setTextCursor(found_cursor)
        self.editor.ensureCursorVisible()
    
    def find_previous(self):
        search_text = self.find_input.text()
        if not search_text:
            self.status_label.setText("Enter text to find")
            return
        
        cursor = self.editor.textCursor()
        flags = self.get_search_flags()
        flags |= QTextDocument.FindFlag.FindBackward
        
        # Search backwards
        found_cursor = self.editor.document().find(search_text, cursor, flags)
        
        if found_cursor.isNull():
            # If not found, search from end
            cursor.movePosition(QTextCursor.MoveOperation.End)
            found_cursor = self.editor.document().find(search_text, cursor, flags)
            
            if found_cursor.isNull():
                self.status_label.setText("No occurrences found")
                return
            else:
                self.status_label.setText("Wrapped to end of document")
        else:
            self.status_label.setText("Found")
        
        # Select the found text
        self.editor.setTextCursor(found_cursor)
        self.editor.ensureCursorVisible()
    
    def highlight_all(self):
        search_text = self.find_input.text()
        if not search_text:
            self.status_label.setText("Enter text to find")
            return
            
        # Remove previous highlights
        cursor = self.editor.textCursor()
        cursor.select(QTextCursor.SelectionType.Document)
        
        # Create highlight format
        highlight_format = QTextCharFormat()
        highlight_format.setBackground(QColor("#6A5ACD"))
        
        # Find and highlight all
        extra_selections = []
        flags = self.get_search_flags()
        
        cursor = self.editor.document().find(search_text, 0, flags)
        count = 0
        
        while not cursor.isNull():
            selection = QTextEdit.ExtraSelection()
            selection.cursor = cursor
            selection.format = highlight_format
            extra_selections.append(selection)
            count += 1
            
            cursor = self.editor.document().find(search_text, cursor, flags)
        
        self.editor.setExtraSelections(extra_selections)
        self.status_label.setText(f"{count} occurrence(s) found")
    
    def replace_current(self):
        cursor = self.editor.textCursor()
        
        if cursor.hasSelection():
            search_text = self.find_input.text()
            selected_text = cursor.selectedText()
            
            # Check if the selected text matches the search
            matches = False
            if self.case_sensitive_check.isChecked():
                matches = selected_text == search_text
            else:
                matches = selected_text.lower() == search_text.lower()
            
            if matches:
                replace_text = self.replace_input.text()
                cursor.insertText(replace_text)
                self.status_label.setText("Replaced")
                
                # Find next
                self.find_next()
            else:
                self.status_label.setText("Select an occurrence first")
        else:
            self.status_label.setText("Select an occurrence first")
            self.find_next()
    
    def replace_all(self):
        search_text = self.find_input.text()
        replace_text = self.replace_input.text()
        
        if not search_text:
            self.status_label.setText("Enter text to find")
            return
        
        # Confirm action
        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self,
            'Confirm Replacement',
            f'Do you want to replace every occurrence of "{search_text}" with "{replace_text}"?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Perform replacements
        cursor = QTextCursor(self.editor.document())
        cursor.beginEditBlock()
        
        flags = self.get_search_flags()
        count = 0
        
        search_cursor = self.editor.document().find(search_text, 0, flags)
        
        while not search_cursor.isNull():
            search_cursor.insertText(replace_text)
            count += 1
            search_cursor = self.editor.document().find(search_text, search_cursor, flags)
        
        cursor.endEditBlock()
        
        self.status_label.setText(f"{count} occurrence(s) replaced")
    
    def showEvent(self, event):
        """When showing the window, focus on the search field"""
        super().showEvent(event)
        self.find_input.setFocus()
        self.find_input.selectAll()
    
    def keyPressEvent(self, event):
        """Detect Esc to close"""
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Project AI")
        self.setGeometry(100, 100, 1600, 900)
        
        # Default working folder
        self.working_directory = os.getcwd()
        
        # Widget central com splitter
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal horizontal
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Main splitter (3 panes)
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # File explorer (left)
        self.file_explorer = self.create_file_explorer()
        
        # Tab widget for multiple files (center)
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.update_encoding_selector)
        
        # AI chat (right)
        self.ai_chat = AIChatWidget(self)
        self.ai_chat.setMaximumWidth(400)  # Set max chat width
        self.ai_chat.setMinimumWidth(250)       
        
        # Adicionar widgets ao splitter
        self.main_splitter.addWidget(self.file_explorer)
        self.main_splitter.addWidget(self.tabs)
        self.main_splitter.addWidget(self.ai_chat)
              
        # Set proportions (20% explorer, 50% editor, 30% chat)
        self.main_splitter.setSizes([250, 1000, 100])
        
        main_layout.addWidget(self.main_splitter)
        
        # Criar menus
        self.create_menus()
        
        # Criar toolbar
        self.create_toolbar()
        
        # Status bar
        self.statusBar().showMessage("Ready")
        
        # Open an initial empty tab
        self.new_file()
        
        
    def toggle_color_highlighting(self):
        current_editor = self.tabs.currentWidget()
        if current_editor and isinstance(current_editor, CodeEditor):
            if hasattr(current_editor, 'color_highlighting_enabled'):
                current_editor.color_highlighting_enabled = not current_editor.color_highlighting_enabled
            else:
                current_editor.color_highlighting_enabled = True
            
            if current_editor.color_highlighting_enabled:
                current_editor.highlight_all_colors()
                self.statusBar().showMessage("Destaque de cores ATIVADO")
            else:
                current_editor.setExtraSelections([])
                self.statusBar().showMessage("Destaque de cores DESATIVADO")
                
                
    def show_compare_dialog(self):
        dialog = DiffViewerDialog(self)
        
        # Se há 2 ou mais abas abertas, perguntar se quer comparar abas abertas
        if self.tabs.count() >= 2:
            reply = QMessageBox.question(
                self,
                'Comparar Abas',
                'Deseja comparar duas abas abertas?\n\n'
                'Clique "Yes" para escolher abas abertas\n'
                'Clique "No" para selecionar arquivos do disco',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # Mostrar lista de abas para selecionar
                left_tab = self.select_tab_for_compare("Selecione a aba ORIGINAL")
                if left_tab is not None:
                    right_tab = self.select_tab_for_compare("Selecione a aba MODIFICADA")
                    if right_tab is not None:
                        left_editor = self.tabs.widget(left_tab)
                        right_editor = self.tabs.widget(right_tab)
                        
                        dialog.set_files_from_tabs(
                            left_editor.toPlainText(),
                            self.tabs.tabText(left_tab),
                            right_editor.toPlainText(),
                            self.tabs.tabText(right_tab)
                        )
        
        dialog.exec()

    def select_tab_for_compare(self, title):
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.setGeometry(400, 300, 400, 300)
        
        layout = QVBoxLayout(dialog)
        
        label = QLabel(f"{title}:")
        layout.addWidget(label)
        
        list_widget = QListWidget()
        for i in range(self.tabs.count()):
            list_widget.addItem(self.tabs.tabText(i))
        layout.addWidget(list_widget)
        
        button_layout = QHBoxLayout()
        ok_btn = QPushButton("OK")
        cancel_btn = QPushButton("Cancelar")
        
        ok_btn.clicked.connect(dialog.accept)
        cancel_btn.clicked.connect(dialog.reject)
        
        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return list_widget.currentRow()
        return None
                             
    def create_file_explorer(self):
        explorer_widget = QWidget()
        explorer_layout = QVBoxLayout(explorer_widget)
        explorer_layout.setContentsMargins(5, 5, 5, 5)
        
        # Title label
        title_label = QLabel("Workspace")
        title_label.setStyleSheet("font-weight: bold; padding: 7px;")
        explorer_layout.addWidget(title_label)
        

        folder_button_layout = QVBoxLayout()
        
        select_folder_btn = QAction("Select Folder", self)
        select_folder_btn.triggered.connect(self.select_working_folder)
        
        from PyQt6.QtWidgets import QPushButton
        select_btn = QPushButton("Select Folder")
        select_btn.clicked.connect(self.select_working_folder)
        folder_button_layout.addWidget(select_btn)
        
        explorer_layout.addLayout(folder_button_layout)
        
        # Tree view for files
        self.file_tree = QTreeView()
        self.file_model = QFileSystemModel()
        self.file_model.setRootPath(QDir.rootPath())
        
        # File filters
        filters = [
            "*.py", "*.js", "*.ts", "*.java", "*.cs", "*.cpp", "*.cc", "*.cxx",
            "*.c", "*.h", "*.php", "*.rb", "*.go", "*.swift", "*.html", "*.htm",
            "*.css", "*.sql", "*.sh", "*.txt", "*.xml", "*.lua", "*.otui", "*.otml"
        ]
        self.file_model.setNameFilters(filters)
        self.file_model.setNameFilterDisables(False)
        
        self.file_tree.setModel(self.file_model)
        self.file_tree.setRootIndex(self.file_model.index(self.working_directory))
        
        self.file_tree.setColumnWidth(0, 200)
        self.file_tree.hideColumn(1)  # Esconder tamanho
        self.file_tree.hideColumn(2)  # Esconder tipo
        self.file_tree.hideColumn(3)  # Esconder data
        
        # Double-click to open file
        self.file_tree.doubleClicked.connect(self.open_file_from_explorer)
        
        explorer_layout.addWidget(self.file_tree)
        
        # Label with current path
        self.current_path_label = QLabel(f"Current path: {self.working_directory}")
        self.current_path_label.setWordWrap(True)
        self.current_path_label.setStyleSheet("font-size: 9px; color: #888; padding: 5px;")
        explorer_layout.addWidget(self.current_path_label)
        
        return explorer_widget
        
    def show_find_replace(self):
        current_editor = self.tabs.currentWidget()
        if current_editor and isinstance(current_editor, CodeEditor):
            current_editor.show_find_dialog()
        
    
    def select_working_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Working Folder",
            self.working_directory
        )
        
        if folder:
            self.working_directory = folder
            self.file_tree.setRootIndex(self.file_model.index(folder))
            self.current_path_label.setText(f"Current path: {folder}")
            self.statusBar().showMessage(f"Working folder: {folder}")
  
    def open_file_from_explorer(self, index):
        file_path = self.file_model.filePath(index)
        

        if os.path.isfile(file_path):
 
            for i in range(self.tabs.count()):
                editor = self.tabs.widget(i)
                if hasattr(editor, 'file_path') and editor.file_path == file_path:
                    self.tabs.setCurrentIndex(i)
                    self.statusBar().showMessage(f"File already open: {os.path.basename(file_path)}")
                    return
            
            # Open new file
            editor = CodeEditor(file_path)
            file_name = os.path.basename(file_path)
            index = self.tabs.addTab(editor, file_name)
            self.tabs.setCurrentIndex(index)
            
            detected_enc = editor.current_encoding.upper()
            self.statusBar().showMessage(f"File: {file_name} | Encoding: {detected_enc}")
       
    def create_menus(self):
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        new_action = QAction("New", self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self.new_file)
        file_menu.addAction(new_action)
        
        open_action = QAction("Open", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)
        
        # Open folder
        open_folder_action = QAction("Open Folder", self)
        open_folder_action.setShortcut("Ctrl+Shift+O")
        open_folder_action.triggered.connect(self.select_working_folder)
        file_menu.addAction(open_folder_action)
        
        save_action = QAction("Save", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self.save_file)
        file_menu.addAction(save_action)
        
        save_as_action = QAction("Save As", self)
        save_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        save_as_action.triggered.connect(self.save_file_as)
        file_menu.addAction(save_as_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit menu
        edit_menu = menubar.addMenu("Edit")
        
        undo_action = QAction("Undo", self)
        undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        undo_action.triggered.connect(self.undo)
        edit_menu.addAction(undo_action)
        
        redo_action = QAction("Redo", self)
        redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        redo_action.triggered.connect(self.redo)
        edit_menu.addAction(redo_action)
        
        edit_menu.addSeparator()
        
        # Find and replace
        find_action = QAction("Find and Replace", self)
        find_action.setShortcut("Ctrl+F")
        find_action.triggered.connect(self.show_find_replace)
        edit_menu.addAction(find_action)
        
        edit_menu.addSeparator()

        duplicate_action = QAction("Duplicate Line", self)
        duplicate_action.setShortcut("Ctrl+D")
        duplicate_action.triggered.connect(self.duplicate_current_line)
        edit_menu.addAction(duplicate_action)
        
        # Comment/Uncomment
        comment_action = QAction("Comment/Uncomment", self)
        comment_action.setShortcut("Ctrl+/")
        comment_action.triggered.connect(self.toggle_comment_line)
        edit_menu.addAction(comment_action)        
          
        # View menu
        view_menu = menubar.addMenu("View")
        
        toggle_explorer_action = QAction("Show/Hide Explorer", self)
        toggle_explorer_action.setShortcut("Ctrl+B")
        toggle_explorer_action.triggered.connect(self.toggle_file_explorer)
        view_menu.addAction(toggle_explorer_action)
        
        toggle_chat_action = QAction("Show/Hide AI Chat", self)
        toggle_chat_action.setShortcut("Ctrl+Shift+A")
        toggle_chat_action.triggered.connect(self.toggle_ai_chat)
        view_menu.addAction(toggle_chat_action)
        
        edit_menu.addSeparator()       
        # Color highlight
        highlight_colors_action = QAction("Highlight Color Codes", self)
        highlight_colors_action.setShortcut("Ctrl+Shift+C")
        highlight_colors_action.triggered.connect(self.toggle_color_highlighting)
        view_menu.addAction(highlight_colors_action)


     


        tools_menu = menubar.addMenu("Tools")

        check_file_action = QAction("Verificar Arquivo Atual", self)
        check_file_action.setShortcut("F5")
        check_file_action.triggered.connect(self.check_current_file_syntax)
        tools_menu.addAction(check_file_action)

        check_project_action = QAction("Verificar Projeto", self)
        check_project_action.setShortcut("Shift+F5")
        check_project_action.triggered.connect(self.check_project_syntax)
        tools_menu.addAction(check_project_action) 

        tools_menu.addSeparator()
        
        #Comparar arquivos
        compare_action = QAction("Comparar Arquivos/Abas", self)
        compare_action.setShortcut("Ctrl+Shift+D")
        compare_action.triggered.connect(self.show_compare_dialog)
        tools_menu.addAction(compare_action)   
        

    def duplicate_current_line(self):
        """Duplica linha no editor atual"""
        current_editor = self.tabs.currentWidget()
        if current_editor and isinstance(current_editor, CodeEditor):
            current_editor.duplicate_line()

    def toggle_comment_line(self):
        current_editor = self.tabs.currentWidget()
        if current_editor and isinstance(current_editor, CodeEditor):
            current_editor.toggle_comment()



    def toggle_file_explorer(self):
        explorer = self.main_splitter.widget(0)
        if explorer.isVisible():
            explorer.hide()
        else:
            explorer.show()

    def toggle_ai_chat(self):
        """Mostra ou oculta o chat de IA"""
        chat = self.main_splitter.widget(2)
        if chat.isVisible():
            chat.hide()
        else:
            chat.show()

    def check_current_file_syntax(self):
        current_editor = self.tabs.currentWidget()
        if not isinstance(current_editor, CodeEditor) or not current_editor.file_path:
            QMessageBox.information(self, "Verificar arquivo", "Nenhum arquivo salvo está aberto para verificação.")
            return

        file_path = current_editor.file_path
        ext = os.path.splitext(file_path)[1].lower()
        if ext != ".py":
            QMessageBox.information(self, "Verificar arquivo", "A verificação automática está disponível apenas para arquivos Python (.py).")
            return

        results = self.run_python_syntax_check([file_path])
        self.show_syntax_results_dialog(results, title="Verificação do arquivo atual")

    def check_project_syntax(self):
        if not self.working_directory:
            QMessageBox.information(self, "Verificar projeto", "Selecione primeiro uma pasta de trabalho em Arquivo > Abrir Pasta.")
            return

        python_files = []
        for root, dirs, files in os.walk(self.working_directory):
            for name in files:
                if name.lower().endswith(".py"):
                    python_files.append(os.path.join(root, name))

        if not python_files:
            QMessageBox.information(self, "Verificar projeto", "Nenhum arquivo Python (.py) encontrado na pasta selecionada.")
            return

        results = self.run_python_syntax_check(python_files)
        self.show_syntax_results_dialog(results, title="Verificação de todo o projeto")

    def run_python_syntax_check(self, file_paths):
        report_lines = []
        python_exec = sys.executable or "python"

        for path in file_paths:
            rel_path = os.path.relpath(path, self.working_directory) if self.working_directory else path
            try:
                completed = subprocess.run(
                    [python_exec, "-m", "py_compile", path],
                    capture_output=True,
                    text=True
                )
                if completed.returncode == 0:
                    report_lines.append(f"[OK] {rel_path}")
                else:
                    stderr = completed.stderr.strip()
                    if not stderr:
                        stderr = "Erro desconhecido ao compilar."
                    report_lines.append(f"\n[ERRO] {rel_path}\n{stderr}\n")
            except Exception as e:
                report_lines.append(f"\n[ERRO] {rel_path}\nFalha ao executar verificação: {e}\n")

        return "\n".join(report_lines)

    def show_syntax_results_dialog(self, results_text, title="Resultados da verificação"):
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.resize(900, 600)

        layout = QVBoxLayout(dialog)

        info_label = QLabel("Arquivos verificados e possíveis erros encontrados. "
                            "Erros aparecem em destaque abaixo de cada arquivo.")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        text_edit = QPlainTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setPlainText(results_text or "Nenhum resultado para exibir.")
        layout.addWidget(text_edit)

        close_button = QPushButton("Fechar")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button)

        dialog.exec()
 
    def create_toolbar(self):
        toolbar = QToolBar()
        self.addToolBar(toolbar)
        
        new_action = QAction("New", self)
        new_action.triggered.connect(self.new_file)
        toolbar.addAction(new_action)
        
        open_action = QAction("Open", self)
        open_action.triggered.connect(self.open_file)
        toolbar.addAction(open_action)
        
        save_action = QAction("Save", self)
        save_action.triggered.connect(self.save_file)
        toolbar.addAction(save_action)
        
        toolbar.addSeparator()
        
        # Seletor de encoding
        encoding_label = QLabel(" Encoding: ")
        toolbar.addWidget(encoding_label)
        
        self.encoding_combo = QComboBox()
        self.encoding_combo.addItems([
            "UTF-8",
            "ANSI (Latin-1)",
            "Windows-1252",
            "UTF-16",
            "ASCII"
        ])
        self.encoding_combo.currentTextChanged.connect(self.change_encoding)
        toolbar.addWidget(self.encoding_combo)
    
    def update_encoding_selector(self):
        current_editor = self.tabs.currentWidget()
        if current_editor and hasattr(current_editor, 'current_encoding'):
            encoding = current_editor.current_encoding
            
            # Mapear encoding para o combo box
            encoding_map = {
                'utf-8': 0,
                'latin-1': 1,
                'cp1252': 2,
                'utf-16': 3,
                'ascii': 4
            }
            
            index = encoding_map.get(encoding, 0)
            self.encoding_combo.blockSignals(True)
            self.encoding_combo.setCurrentIndex(index)
            self.encoding_combo.blockSignals(False)
            
            # Atualizar status bar
            self.statusBar().showMessage(f"Encoding: {encoding.upper()}")
    
    def change_encoding(self, text):
        current_editor = self.tabs.currentWidget()
        if not current_editor:
            return
        
        # Mapear texto do combo box para encoding Python
        encoding_map = {
            "UTF-8": "utf-8",
            "ANSI (Latin-1)": "latin-1",
            "Windows-1252": "cp1252",
            "UTF-16": "utf-16",
            "ASCII": "ascii"
        }
        
        encoding = encoding_map.get(text, "utf-8")
        
        if hasattr(current_editor, 'file_path') and current_editor.file_path:
            # Reload file with new encoding
            current_editor.reload_with_encoding(encoding)
            self.statusBar().showMessage(f"File reloaded with encoding: {encoding.upper()}")
        else:
            # Apenas mudar o encoding para salvar
            current_editor.current_encoding = encoding
            self.statusBar().showMessage(f"Encoding alterado para: {encoding.upper()}")
    
    def new_file(self):
        editor = CodeEditor()
        index = self.tabs.addTab(editor, "Untitled")
        self.tabs.setCurrentIndex(index)
    
    def open_file(self):
        file_paths, _ = QFileDialog.getOpenFileNames( 
            self, 
            "Open File", 
            "", 
            "All Files (*);;"\
            "Python (*.py);;"\
            "JavaScript (*.js);;"\
            "TypeScript (*.ts);;"\
            "Java (*.java);;"\
            "C# (*.cs);;"\
            "C++ (*.cpp *.cc *.cxx *.h);;"\
            "C (*.c *.h);;"\
            "PHP (*.php);;"\
            "Ruby (*.rb);;"\
            "Go (*.go);;"\
            "Swift (*.swift);;"\
            "HTML (*.html *.htm);;"\
            "CSS (*.css);;"\
            "SQL (*.sql);;"\
            "Shell (*.sh);;"\
            "Text (*.txt);;"\
            "XML (*.xml);;"\
            "Lua (*.lua);;"\
            "OTUI (*.otui);;"\
            "OTML (*.otml)"
        )
        
        for file_path in file_paths:
            if file_path:
                editor = CodeEditor(file_path)
                file_name = os.path.basename(file_path)
                index = self.tabs.addTab(editor, file_name)
                self.tabs.setCurrentIndex(index)
                
                # Mostrar encoding detectado
                detected_enc = editor.current_encoding.upper()
                self.statusBar().showMessage(f"File: {file_name} | Encoding: {detected_enc}")
  
    def save_file(self):
        current_editor = self.tabs.currentWidget()
        if current_editor and current_editor.save_file():
            file_name = os.path.basename(current_editor.file_path)
            self.tabs.setTabText(self.tabs.currentIndex(), file_name)
            self.statusBar().showMessage(f"File saved: {current_editor.file_path}")
    
    def save_file_as(self):
        current_editor = self.tabs.currentWidget()
        if current_editor and current_editor.save_file_as():
            file_name = os.path.basename(current_editor.file_path)
            self.tabs.setTabText(self.tabs.currentIndex(), file_name)
            self.statusBar().showMessage(f"File saved: {current_editor.file_path}")
    
    def close_tab(self, index):
        self.tabs.removeTab(index)
        if self.tabs.count() == 0:
            self.new_file()
    
    def undo(self):
        current_editor = self.tabs.currentWidget()
        if current_editor:
            current_editor.undo()
    
    def redo(self):
        current_editor = self.tabs.currentWidget()
        if current_editor:
            current_editor.redo()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Aplicar tema escuro
    app.setStyleSheet(qdarktheme.load_stylesheet())
    
    
    window = MainWindow()
    window.showMaximized()
    
    sys.exit(app.exec())
