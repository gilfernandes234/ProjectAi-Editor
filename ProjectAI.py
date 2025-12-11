#  py -m pip install  --upgrade google-generativeai


import sys
import os
import qdarktheme  
import chardet
import re
import difflib

from PyQt6.QtGui import (QAction, QFont, QSyntaxHighlighter, QTextCharFormat, 
                        QColor, QKeySequence, QFileSystemModel, QTextCursor, QTextDocument)
                        
                   
                             
from PyQt6.QtCore import Qt, QRegularExpression, QDir, QThread, pyqtSignal


from PyQt6.QtWidgets import (QApplication, QMainWindow, QTextEdit, QFileDialog, 
                             QVBoxLayout, QWidget, QMenuBar, QMenu, QToolBar, 
                             QStatusBar, QMessageBox, QTabWidget, QComboBox, QLabel,
                             QTreeView, QSplitter, QPushButton, QLineEdit, 
                             QScrollArea, QFrame, QHBoxLayout, QCheckBox, QColorDialog, QDialog, QListWidget)


import google.generativeai as genai

class AIThread(QThread):
    """Thread para processar requisiÃ§Ãµes de IA sem travar a interface"""
    response_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, model, prompt):
        super().__init__()
        self.model = model
        self.prompt = prompt
    
    def run(self):
        try:
            response = self.model.generate_content(self.prompt)
            self.response_ready.emit(response.text)
        except Exception as e:
            self.error_occurred.emit(f"Erro: {str(e)}")

class AIChatWidget(QWidget):
    """Widget de chat com IA"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.api_key = None
        self.model = None
        self.conversation_history = []
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # TÃ­tulo
        title_label = QLabel("Assistente de IA")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px; padding: 5px;")
        layout.addWidget(title_label)
        
        # Campo para API Key
        api_layout = QHBoxLayout()
        api_label = QLabel("API Key:")
        self.api_input = QLineEdit()
        self.api_input.setPlaceholderText("Cole sua chave do Google Gemini aqui")
        self.api_input.setEchoMode(QLineEdit.EchoMode.Password)
        connect_btn = QPushButton("Conectar")
        connect_btn.clicked.connect(self.connect_ai)
        api_layout.addWidget(api_label)
        api_layout.addWidget(self.api_input)
        api_layout.addWidget(connect_btn)
        layout.addLayout(api_layout)
        
        # NOVO: Checkbox para modo projeto
        project_mode_layout = QHBoxLayout()
        self.project_mode_checkbox = QCheckBox("Modo Projeto Completo")
        self.project_mode_checkbox.setToolTip("Inclui todos os arquivos .lua da pasta no contexto")
        project_mode_layout.addWidget(self.project_mode_checkbox)
        project_mode_layout.addStretch()
        layout.addLayout(project_mode_layout)
        
        # de conversa
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
        self.message_input.setPlaceholderText("Digite sua pergunta aqui... (Ctrl+Enter para enviar)")
        self.message_input.installEventFilter(self)
        
        send_btn = QPushButton("Enviar")
        send_btn.clicked.connect(self.send_message)
        send_btn.setMinimumHeight(60)
        
        input_layout.addWidget(self.message_input)
        input_layout.addWidget(send_btn)
        layout.addLayout(input_layout)
        
        # BotÃµes adicionais
        buttons_layout = QHBoxLayout()
        
        clear_btn = QPushButton("Limpar Chat")
        clear_btn.clicked.connect(self.clear_chat)

        code_btn = QPushButton("Explicar Seleção")
        code_btn.clicked.connect(self.explain_selected_code)

        context_btn = QPushButton("Analisar Arquivo")
        context_btn.clicked.connect(self.analyze_current_file)
        
        # NOVO: BotÃµes para projeto
        project_btn = QPushButton("Analisar Projeto")
        project_btn.clicked.connect(self.analyze_full_project)
        project_btn.setToolTip("Analisa todos os arquivos Lua da pasta")
        
        apply_btn = QPushButton("Aplicar Código")
        apply_btn.clicked.connect(self.apply_code_suggestion)
        apply_btn.setStyleSheet("background-color: #2d5016; color: white;")
        apply_btn.setToolTip("Aplica o Ãºltimo codigo sugerido pela IA")

        buttons_layout.addWidget(clear_btn)
        buttons_layout.addWidget(code_btn)
        buttons_layout.addWidget(context_btn)
        buttons_layout.addWidget(project_btn)
        buttons_layout.addWidget(apply_btn)
        layout.addLayout(buttons_layout)
        
        self.status_label = QLabel("Conecte na IA primeiro")
        self.status_label.setStyleSheet("color: #ff9800; padding: 5px;")
        layout.addWidget(self.status_label)
        
        # Armazenar Ãºltimo codigo sugerido
        self.last_code_suggestion = None
        self.last_file_suggestion = None
        
    def get_current_file_context(self, user_message):
        """ObtÃ©m o contexto do arquivo atual ou projeto completo"""
        try:
            main_window = self.window()
            if hasattr(main_window, 'tabs'):
                current_editor = main_window.tabs.currentWidget()
                
                if current_editor and isinstance(current_editor, CodeEditor):
                    context_parts = []
                    
                    # informacoes do arquivo atual
                    file_path = getattr(current_editor, 'file_path', None)
                    file_content = current_editor.toPlainText()
                    selected_text = current_editor.textCursor().selectedText()
                    
                    if file_path:
                        file_name = os.path.basename(file_path)
                        file_ext = os.path.splitext(file_path)[1]
                        context_parts.append(f"Arquivo atual: {file_name} ({file_ext})")
                    
                    # NOVO: Modo Projeto Completo
                    if self.project_mode_checkbox.isChecked() and hasattr(main_window, 'working_directory'):
                        context_parts.append(f"\nCONTEXTO DO PROJETO COMPLETO:\n")
                        project_files = self.scan_project_files(main_window.working_directory)
                        
                        for pfile in project_files[:10]:  # Limitar a 10 arquivos
                            try:
                                with open(pfile, 'r', encoding='utf-8', errors='ignore') as f:
                                    content = f.read()
                                    if len(content) > 500:
                                        content = content[:500] + "..."
                                    context_parts.append(f"\n--- {os.path.basename(pfile)} ---\n``````")
                            except:
                                pass
                    
         
                    if selected_text:
                        context_parts.append(f"\nCódigo selecionado:\n``````")
       
                    elif file_content and len(file_content.strip()) > 0:
                        if len(file_content) > 4000:
                            context_parts.append(f"\nconteúdo (primeiros 4000 chars):\n``````")
                        else:
                            context_parts.append(f"\nðŸ“„ conteudo completo:\n``````")
                    
 
                    context_parts.append(f"Pergunta: {user_message}")
                    context_parts.append("\n\IMPORTANTE: Se voce sugerir codigo, forneca APENAS o codigo completo pronto para substituir, sem explicacoes adicionais dentro do bloco de codigo.```")
                    context_parts.append("\nResponda em portugues.")
                    
                    if context_parts:
                        return "\n".join(context_parts)
        
        except Exception as e:
            print(f"Erro ao obter contexto: {e}")
        
        return user_message + "\n\nPor favor, responda em portugues."

    def scan_project_files(self, directory, extensions=['.lua', '.py', '.js']):
        """Escaneia arquivos do projeto"""
        project_files = []
        try:
            for root, dirs, files in os.walk(directory):
                # Ignorar pastas comuns
                dirs[:] = [d for d in dirs if d not in ['.git', 'node_modules', '__pycache__', '.vscode']]
                
                for file in files:
                    if any(file.endswith(ext) for ext in extensions):
                        project_files.append(os.path.join(root, file))
                        
                    if len(project_files) >= 15:  # Limitar total
                        break
                if len(project_files) >= 15:
                    break
        except Exception as e:
            print(f"Erro ao escanear projeto: {e}")
        
        return project_files
        


    def analyze_full_project(self):
        """Analisa o projeto completo"""
        main_window = self.window()
        if hasattr(main_window, 'working_directory'):
            self.project_mode_checkbox.setChecked(True)
            prompt = "Analise a estrutura completa deste projeto. Liste os principais arquivos, suas funcoes, e sugira melhorias ou otimizacoes que podem ser feitas."
            self.message_input.setPlainText(prompt)
            self.send_message()
        else:
            QMessageBox.information(self, "Info", "Selecione uma pasta de trabalho primeiro")
    
    def apply_code_suggestion(self):
        if not self.last_code_suggestion:
            QMessageBox.warning(self, "Aviso", "Nenhum codigo foi sugerido ainda")
            return
        
        main_window = self.window()
        if hasattr(main_window, 'tabs'):
            current_editor = main_window.tabs.currentWidget()
            if current_editor and isinstance(current_editor, CodeEditor):
                # Verificar se ha selecao
                cursor = current_editor.textCursor()
                if cursor.hasSelection():
                    reply = QMessageBox.question(
                        self, 
                        'Substituir selecao?', 
                        'Deseja substituir o texto selecionado pelo codigo sugerido?',
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )
                    if reply == QMessageBox.StandardButton.Yes:
                        cursor.insertText(self.last_code_suggestion)
                        self.chat_display.append("<b>Sistema:</b> codigo aplicado a selecao!<br><br>")
                else:
                    reply = QMessageBox.question(
                        self, 
                        'Substituir Arquivo?', 
                        'Deseja substituir TODO o conteudo do arquivo pelo codigo sugerido?',
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )
                    if reply == QMessageBox.StandardButton.Yes:
                        current_editor.setPlainText(self.last_code_suggestion)
                        self.chat_display.append("<b>Sistema:</b> codigo aplicado ao arquivo completo!<br><br>")
            else:
                QMessageBox.information(self, "Info", "Nenhum arquivo aberto")
    
    def eventFilter(self, obj, event):
        if obj == self.message_input and event.type() == event.Type.KeyPress:
            if event.key() == Qt.Key.Key_Return and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                self.send_message()
                return True
        return super().eventFilter(obj, event)
    
    def connect_ai(self):
        self.api_key = self.api_input.text().strip()
        
        if not self.api_key:
            QMessageBox.warning(self, "Aviso", "Por favor, insira uma API Key valida")
            return
        
        try:
            genai.configure(api_key=self.api_key)
            
            # Listar modelos disponiveis
            print("Modelos disponiveis:")
            available_model = None
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    print(f"- {m.name}")
                    if available_model is None:
                        available_model = m.name
            
            if not available_model:
                raise Exception("Nenhum modelo disponivel para generateContent")
            
            # Usar o primeiro modelo disponivel
            self.model = genai.GenerativeModel(available_model)
            self.status_label.setText(f"Conectado ao {available_model}")
            self.status_label.setStyleSheet("color: #4caf50; padding: 5px;")
            self.chat_display.append(f"<b>Sistema:</b> Conectado usando {available_model}! Como posso ajudar?<br><br>")
            
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao conectar: {str(e)}")
            self.status_label.setText(f"Erro: {str(e)}")
            self.status_label.setStyleSheet("color: #f44336; padding: 5px;")
    
    def send_message(self):
        """Envia mensagem para a IA"""
        if not self.model:
            QMessageBox.warning(self, "Aviso", "Conecte-se IA primeiro!")
            return
        
        message = self.message_input.toPlainText().strip()
        if not message:
            return
        
        # Adicionar mensagem do usuÃ¡rio ao chat
        self.chat_display.append(f"<b>Você:</b> {message}<br>")
        self.message_input.clear()
        
        # Desabilitar entrada enquanto processa
        self.message_input.setEnabled(False)
        self.status_label.setText("Processando...")
        self.status_label.setStyleSheet("color: #2196f3; padding: 5px;")
        
        # Obter contexto do arquivo atual
        context_prompt = self.get_current_file_context(message)
        
        # Criar thread para processar
        self.ai_thread = AIThread(self.model, context_prompt)
        self.ai_thread.response_ready.connect(self.display_response)
        self.ai_thread.error_occurred.connect(self.display_error)
        self.ai_thread.start()
    
    def get_current_file_context(self, user_message):
        """ObtÃ©m o contexto do arquivo atual aberto"""
        try:
            # Navegar atÃ© a MainWindow
            main_window = self.window()
            if hasattr(main_window, 'tabs'):
                current_editor = main_window.tabs.currentWidget()
                
                if current_editor and isinstance(current_editor, CodeEditor):
                    # Obter informacoes do arquivo
                    file_path = getattr(current_editor, 'file_path', None)
                    file_content = current_editor.toPlainText()
                    
                    # Verificar se ha texto selecionado
                    selected_text = current_editor.textCursor().selectedText()
                    
                    # Construir prompt com contexto
                    context_parts = []
                    
                    if file_path:
                        file_name = os.path.basename(file_path)
                        file_ext = os.path.splitext(file_path)[1]
                        context_parts.append(f"Estou trabalhando no arquivo: {file_name} ({file_ext})")
                    
                    # Se  selecao, focar nela
                    if selected_text:
                        context_parts.append(f"\codigo selecionado:\n``````")
                    # Senao, enviar o arquivo inteiro (limitado a 3000 caracteres)
                    elif file_content and len(file_content.strip()) > 0:
                        if len(file_content) > 3000:
                            context_parts.append(f"\conteudo do arquivo (primeiros 3000 caracteres):\n``````")
                        else:
                            context_parts.append(f"\conteudo completo do arquivo:\n``````")
                    
                    # Adicionar a pergunta do usuÃ¡rio
                    if context_parts:
                        full_prompt = "\n".join(context_parts) + f"\n\nMinha pergunta: {user_message}\n\nPor favor, responda em portugues."
                        return full_prompt
        
        except Exception as e:
            print(f"Erro ao obter contexto: {e}")
        
        # Se nao conseguir contexto, enviar apenas a mensagem
        return user_message + "\n\nPor favor, responda em portugues."
    
    def display_response(self, response):
        """Exibe resposta da IA com formataÃ§Ã£o"""
        # Converter Markdown para HTML
        formatted_response = self.markdown_to_html(response)
        
        self.chat_display.append(f"ðŸ¤– <b>IA:</b><br>{formatted_response}<br><br>")
        self.message_input.setEnabled(True)
        self.message_input.setFocus()
        self.status_label.setText("âœ… Pronto")
        self.status_label.setStyleSheet("color: #4caf50; padding: 5px;")

    def markdown_to_html(self, text):
        """Converte Markdown bÃ¡sico para HTML"""
        # Substituir quebras de linha duplas por paragrafos
        text = text.replace('\n\n', '</p><p>')
        

        
        # codigo inline (`)
        text = re.sub(r'`([^`]+)`', r'<code style="background-color: #2d2d2d; padding: 2px 5px; border-radius: 3px;">\1</code>', text)
        

        text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
        text = re.sub(r'__(.+?)__', r'<b>\1</b>', text)
        

        text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
        text = re.sub(r'_(.+?)_', r'<i>\1</i>', text)
        
        # cabecalho
        text = re.sub(r'^### (.+)$', r'<h3 style="color: #569CD6; margin-top: 10px;">\1</h3>', text, flags=re.MULTILINE)
        text = re.sub(r'^## (.+)$', r'<h2 style="color: #569CD6; margin-top: 10px;">\1</h2>', text, flags=re.MULTILINE)
        text = re.sub(r'^# (.+)$', r'<h1 style="color: #569CD6; margin-top: 10px;">\1</h1>', text, flags=re.MULTILINE)
        
        # Listas nao ordenadas
        text = re.sub(r'^\* (.+)$', r'<li>\1</li>', text, flags=re.MULTILINE)
        text = re.sub(r'^- (.+)$', r'<li>\1</li>', text, flags=re.MULTILINE)
        
        # Listas ordenadas
        text = re.sub(r'^\d+\. (.+)$', r'<li>\1</li>', text, flags=re.MULTILINE)
        
        # Envolver listas em <ul> ou <ol>
        text = re.sub(r'(<li>.*?</li>)(?=\n(?!<li>))', r'<ul>\1</ul>', text, flags=re.DOTALL)
        
        # Links [texto](url)
        text = re.sub(r'\[([^\]]+)\]\(([^\)]+)\)', r'<a href="\2" style="color: #4A9EFF;">\1</a>', text)
        
        # Quebras de linha simples
        text = text.replace('\n', '<br>')
        
        # Envolver em paragrafo
        text = f'<p>{text}</p>'
        
        return text

    
    def display_error(self, error):
        """Exibe erro"""
        self.chat_display.append(f"<b>Erro:</b> {error}<br><br>")
        self.message_input.setEnabled(True)
        self.status_label.setText("âŒ Erro na requisão")
        self.status_label.setStyleSheet("color: #f44336; padding: 5px;")
    
    def clear_chat(self):
        """Limpa o histÃ³rico do chat"""
        self.chat_display.clear()
        self.conversation_history = []
    
    def explain_selected_code(self):
        """Explica codigo selecionado no editor"""
        main_window = self.window()
        if hasattr(main_window, 'tabs'):
            current_editor = main_window.tabs.currentWidget()
            if current_editor and isinstance(current_editor, CodeEditor):
                selected_text = current_editor.textCursor().selectedText()
                if selected_text:
                    prompt = f"Explique este código em detalhes"
                    self.message_input.setPlainText(prompt)
                    self.send_message()
                else:
                    QMessageBox.information(self, "Info", "Selecione algum código primeiro")
    
    def analyze_current_file(self):
        """Analisa o arquivo atual completamente"""
        main_window = self.window()
        if hasattr(main_window, 'tabs'):
            current_editor = main_window.tabs.currentWidget()
            if current_editor and isinstance(current_editor, CodeEditor):
                file_path = getattr(current_editor, 'file_path', None)
                file_name = os.path.basename(file_path) if file_path else "arquivo atual"
                
                prompt = f"Analise este código completo e me dá um resumo detalhado do que ele faz, suas funções principais."
                self.message_input.setPlainText(prompt)
                self.send_message()
            else:
                QMessageBox.information(self, "Info", "Nenhum arquivo aberto")
            

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
            
            # IDs (começam com #)
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
        
        # Números
        self.highlighting_rules.append((QRegularExpression(r'\b\d+\b'), number_format))
        
        # Comentários
        if self.file_extension in ['.py', '.rb', '.sh', '.otui', '.otml']:
            self.highlighting_rules.append((QRegularExpression(r'#.*'), comment_format))
        elif self.file_extension in ['.js', '.ts', '.java', '.cs', '.cpp', '.c', '.php', '.go', '.swift']:
            self.highlighting_rules.append((QRegularExpression(r'//.*'), comment_format))
        elif self.file_extension == '.lua':
            self.highlighting_rules.append((QRegularExpression(r'--.*'), comment_format))
        elif self.file_extension == '.sql':
            self.highlighting_rules.append((QRegularExpression(r'--.*'), comment_format))
        
        # Funções
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
                print(f"Arquivo grande ({file_size} bytes), highlighting desabilitado")
   


    def on_text_changed(self):
        """Atualiza highlight de cores quando o texto muda"""
        if hasattr(self, 'color_highlighting_enabled') and self.color_highlighting_enabled:
            # Usar timer para não atualizar a cada tecla
            if not hasattr(self, 'color_update_timer'):
                from PyQt6.QtCore import QTimer
                self.color_update_timer = QTimer()
                self.color_update_timer.setSingleShot(True)
                self.color_update_timer.timeout.connect(self.highlight_all_colors)
            
            self.color_update_timer.start(500)  # Atualizar após 500ms de inatividade



#342433


    def mouseDoubleClickEvent(self, event):
        """Detecta duplo clique para abrir seletor de cores"""
        import re
        
        cursor = self.cursorForPosition(event.pos())
        click_pos = cursor.position()
        
        # Pegar toda a linha
        cursor.movePosition(QTextCursor.MoveOperation.StartOfLine)
        cursor.movePosition(QTextCursor.MoveOperation.EndOfLine, QTextCursor.MoveMode.KeepAnchor)
        line_text = cursor.selectedText()
        line_start = cursor.selectionStart()
        
        # Procurar todas as cores na linha
        pattern = r'#[0-9A-Fa-f]{3,8}\b'
        
        for match in re.finditer(pattern, line_text):
            # Calcular posição absoluta da cor no documento
            color_start = line_start + match.start()
            color_end = line_start + match.end()
            
            # Verificar se o clique foi dentro desta cor
            if color_start <= click_pos <= color_end:
                color_code = match.group()
                
                # Selecionar a cor
                cursor.setPosition(color_start)
                cursor.setPosition(color_end, QTextCursor.MoveMode.KeepAnchor)
                
                print(f"Duplo clique em cor: '{color_code}'")  # DEBUG
                self.open_color_picker(cursor, color_code)
                return
        
        # Se não encontrou cor, comportamento padrão
        print(f"Não é cor na posição {click_pos}")  # DEBUG
        super().mouseDoubleClickEvent(event)

    
    def is_color_code(self, text):
        """Verifica se o texto é um código de cor válido"""
        import re
        # Aceitar formatos: #RGB, #RRGGBB, #RRGGBBAA
        pattern = r'^#[0-9A-Fa-f]{3}$|^#[0-9A-Fa-f]{6}$|^#[0-9A-Fa-f]{8}$'
        return bool(re.match(pattern, text))
    
    def open_color_picker(self, cursor, current_color):
        """Abre o seletor de cores e substitui o código"""
        try:
            # Converter cor atual para QColor
            initial_color = QColor(current_color)
            
            # Abrir diálogo de cores
            color = QColorDialog.getColor(
                initial_color, 
                self,
                "Selecionar Cor",
                QColorDialog.ColorDialogOption.ShowAlphaChannel
            )
            
            # Se o usuário escolheu uma cor
            if color.isValid():
                # Converter para hexadecimal
                if color.alpha() < 255:
                    # Incluir alpha se não for 100% opaco
                    new_color = color.name(QColor.NameFormat.HexArgb)
                else:
                    # Formato padrão #RRGGBB
                    new_color = color.name(QColor.NameFormat.HexRgb)
                
                # Substituir o texto selecionado pela nova cor
                cursor.insertText(new_color)
                
                # Mostrar preview da cor no fundo temporariamente
                self.show_color_preview(cursor, new_color)
                
        except Exception as e:
            print(f"Erro ao abrir seletor de cores: {e}")
    
    def show_color_preview(self, cursor, color_code):
        """Mostra um preview temporário da cor no fundo do texto"""
        # Criar formato com a cor de fundo
        format_preview = QTextCharFormat()
        format_preview.setBackground(QColor(color_code))
        
        # Se a cor for muito escura, usar texto branco
        qcolor = QColor(color_code)
        brightness = (qcolor.red() * 299 + qcolor.green() * 587 + qcolor.blue() * 114) / 1000
        if brightness < 128:
            format_preview.setForeground(QColor("#FFFFFF"))
        else:
            format_preview.setForeground(QColor("#000000"))
        
        # Aplicar formato temporariamente
        cursor.setPosition(cursor.position() - len(color_code))
        cursor.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor, len(color_code))
        cursor.mergeCharFormat(format_preview)
    

    def keyPressEvent(self, event):
        """Detectar atalhos de teclado personalizados"""
        # Ctrl+F para buscar
        if event.key() == Qt.Key.Key_F and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.show_find_dialog()
            return
        
        # Ctrl+D para duplicar linha
        elif event.key() == Qt.Key.Key_D and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.duplicate_line()
            return
        
        # Ctrl+/ para comentar/descomentar linha
        elif event.key() == Qt.Key.Key_Slash and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.toggle_comment()
            return
        
        # Passar para o comportamento padrão
        super().keyPressEvent(event)
        
        
    def highlight_all_colors(self):
        """Destaca todas as cores hexadecimais no código"""
        import re
        
        # Remover highlights anteriores
        cursor = QTextCursor(self.document())
        cursor.select(QTextCursor.SelectionType.Document)
        default_format = QTextCharFormat()
        cursor.setCharFormat(default_format)
        
        # Buscar todos os códigos de cor
        text = self.toPlainText()
        pattern = r'#[0-9A-Fa-f]{3,8}\b'
        
        extra_selections = []
        
        for match in re.finditer(pattern, text):
            if len(match.group()) in [4, 7, 9]:  # #RGB, #RRGGBB, #RRGGBBAA
                color_code = match.group()
                
                # Criar cursor para esta posição
                cursor = QTextCursor(self.document())
                cursor.setPosition(match.start())
                cursor.setPosition(match.end(), QTextCursor.MoveMode.KeepAnchor)
                
                # Criar seleção extra com a cor de fundo
                selection = QTextEdit.ExtraSelection()
                selection.cursor = cursor
                
                # Formato com a cor de fundo
                color_format = QTextCharFormat()
                qcolor = QColor(color_code)
                color_format.setBackground(qcolor)
                
                # Ajustar cor do texto baseado no brilho
                brightness = (qcolor.red() * 299 + qcolor.green() * 587 + qcolor.blue() * 114) / 1000
                if brightness < 128:
                    color_format.setForeground(QColor("#FFFFFF"))
                else:
                    color_format.setForeground(QColor("#000000"))
                
                selection.format = color_format
                extra_selections.append(selection)
        
        self.setExtraSelections(extra_selections)
        
        

    def show_find_dialog(self):
        """Mostra o diálogo de busca e substituição"""
        # Verificar se já existe uma janela aberta
        if not hasattr(self, 'find_dialog') or not self.find_dialog.isVisible():
            self.find_dialog = FindReplaceDialog(self)
            
            # Se há texto selecionado, usar como busca inicial
            cursor = self.textCursor()
            if cursor.hasSelection():
                selected_text = cursor.selectedText()
                if '\u2029' not in selected_text:  # Se não é multi-linha
                    self.find_dialog.find_input.setText(selected_text)
        
        self.find_dialog.show()
        self.find_dialog.raise_()
        self.find_dialog.activateWindow()

   
    
    def duplicate_line(self):
        """Duplica a linha atual ou selecao"""
        cursor = self.textCursor()
        

        if cursor.hasSelection():
            selected_text = cursor.selectedText()
            # selectedText usa Unicode U+2029 para quebras de linha
            selected_text = selected_text.replace('\u2029', '\n')
            

            cursor.clearSelection()
            cursor.movePosition(QTextCursor.MoveOperation.EndOfLine)
            cursor.insertText('\n' + selected_text)
        else:
            # Duplicar linha atual
            cursor.movePosition(QTextCursor.MoveOperation.StartOfLine)
            cursor.movePosition(QTextCursor.MoveOperation.EndOfLine, QTextCursor.MoveMode.KeepAnchor)
            line_text = cursor.selectedText()
            
            # Inserir linha duplicada abaixo
            cursor.movePosition(QTextCursor.MoveOperation.EndOfLine)
            cursor.insertText('\n' + line_text)
        
        self.setTextCursor(cursor)
    
    def toggle_comment(self):
        """Comenta/descomenta a linha atual ou selecao"""
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
            '.otui': '//',  # NOVO
            '.otml': '#'   # NOVO            
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
                    # Descomentar
                    new_text = line_text.replace(comment_symbol + ' ', '', 1).replace(comment_symbol, '', 1)
                else:
                    # Comentar
                    new_text = comment_symbol + ' ' + line_text
                
                cursor.insertText(new_text)
        else:
            # Comentar/descomentar linha Ãºnica
            cursor.movePosition(QTextCursor.MoveOperation.StartOfLine)
            cursor.movePosition(QTextCursor.MoveOperation.EndOfLine, QTextCursor.MoveMode.KeepAnchor)
            line_text = cursor.selectedText()
            
            if line_text.strip().startswith(comment_symbol):
                # Descomentar
                new_text = line_text.replace(comment_symbol + ' ', '', 1).replace(comment_symbol, '', 1)
            else:
                # Comentar
                new_text = comment_symbol + ' ' + line_text
            
            cursor.insertText(new_text)
        
        self.setTextCursor(cursor)
    

    def detect_encoding(self, file_path):
        """Detecta automaticamente o encoding do arquivo"""
        try:

            with open(file_path, 'rb') as f:
                raw_data = f.read(10240)  # Limitar a 10KB
            
            # Se o arquivo for muito pequeno, usar tudo
            if len(raw_data) == 0:
                return 'utf-8', 1.0
            
            result = chardet.detect(raw_data)
            detected_encoding = result['encoding']
            confidence = result['confidence']
            
            # Normalizar nomes de encoding
            if detected_encoding:
                detected_encoding = detected_encoding.lower()
                if 'iso-8859' in detected_encoding or 'latin' in detected_encoding:
                    detected_encoding = 'latin-1'  # ANSI
                elif 'utf-8' in detected_encoding:
                    detected_encoding = 'utf-8'
                elif 'windows-1252' in detected_encoding or 'cp1252' in detected_encoding:
                    detected_encoding = 'cp1252'  # ANSI Windows
                elif 'ascii' in detected_encoding:
                    detected_encoding = 'utf-8'  # ASCII Ã© compatÃ­vel com UTF-8
            
            # Se confianÃ§a muito baixa, usar UTF-8 como padrÃ£o
            if confidence < 0.7:
                detected_encoding = 'utf-8'
            
            return detected_encoding, confidence
        except Exception as e:
            print(f"Erro ao detectar encoding: {e}")
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
                    'Arquivo Grande', 
                    f'O arquivo tem {file_size / (1024*1024):.1f}MB. Pode demorar para carregar. Continuar?',
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.No:
                    return False
            
            # Carregar arquivo
            with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                content = f.read()
            
            # Desabilitar updates durante carregamento de texto grande
            self.setUpdatesEnabled(False)
            self.setPlainText(content)
            self.setUpdatesEnabled(True)
            
            self.file_path = file_path
            return True
            
        except Exception as e:
            # Fallback para UTF-8
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
                QMessageBox.critical(None, "Erro", f"Erro ao abrir arquivo: {str(e2)}")
                return False

                
        except Exception as e:
            # Fallback para UTF-8 em caso de erro
            try:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                self.setPlainText(content)
                self.file_path = file_path
                self.current_encoding = 'utf-8'
                return True
            except Exception as e2:
                QMessageBox.critical(None, "Erro", f"Erro ao abrir arquivo: {str(e2)}")
                return False

    
    def save_file(self, encoding=None):

        if not self.file_path:
            return self.save_file_as(encoding)
        
        if not encoding:
            encoding = self.current_encoding
        
        try:
            with open(self.file_path, 'w', encoding=encoding, errors='replace') as f:
                f.write(self.toPlainText())
            self.current_encoding = encoding
            return True
        except Exception as e:
            QMessageBox.critical(None, "Erro", f"Erro ao salvar arquivo: {str(e)}")
            return False
    
    def save_file_as(self, encoding=None):
        file_path, _ = QFileDialog.getSaveFileName(None, "Salvar Como")
        if file_path:
            self.file_path = file_path
            return self.save_file(encoding)
        return False
    
    def reload_with_encoding(self, encoding):
        """Recarrega o arquivo com um encoding diferente"""
        if self.file_path:
            self.load_file(self.file_path, encoding)


class FindReplaceDialog(QWidget):
    """Diálogo de busca e substituição"""
    def __init__(self, editor, parent=None):
        super().__init__(parent)
        self.editor = editor
        self.last_match_position = -1
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("Localizar e Substituir")
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
        self.setGeometry(300, 300, 500, 250)
        
        layout = QVBoxLayout(self)
        
        # Grupo Localizar
        find_group = QWidget()
        find_layout = QVBoxLayout(find_group)
        
        find_label = QLabel("Localizar:")
        find_layout.addWidget(find_label)
        
        find_input_layout = QHBoxLayout()
        self.find_input = QLineEdit()
        self.find_input.setPlaceholderText("Digite o texto a localizar...")
        self.find_input.returnPressed.connect(self.find_next)
        find_input_layout.addWidget(self.find_input)
        find_layout.addLayout(find_input_layout)
        
        # Opções de busca
        options_layout = QHBoxLayout()
        self.case_sensitive_check = QCheckBox("Diferenciar maiúsculas/minúsculas")
        self.whole_word_check = QCheckBox("Palavra inteira")
        options_layout.addWidget(self.case_sensitive_check)
        options_layout.addWidget(self.whole_word_check)
        find_layout.addLayout(options_layout)
        
        # Botões de busca
        find_buttons_layout = QHBoxLayout()
        self.find_prev_btn = QPushButton("◄ Anterior")
        self.find_prev_btn.clicked.connect(self.find_previous)
        self.find_next_btn = QPushButton("Próximo ►")
        self.find_next_btn.clicked.connect(self.find_next)
        self.highlight_all_btn = QPushButton("🔍 Destacar Todas")
        self.highlight_all_btn.clicked.connect(self.highlight_all)
        
        find_buttons_layout.addWidget(self.find_prev_btn)
        find_buttons_layout.addWidget(self.find_next_btn)
        find_buttons_layout.addWidget(self.highlight_all_btn)
        find_layout.addLayout(find_buttons_layout)
        
        layout.addWidget(find_group)
        
        # Separador
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)
        
        # Grupo Substituir
        replace_group = QWidget()
        replace_layout = QVBoxLayout(replace_group)
        
        replace_label = QLabel("Substituir por:")
        replace_layout.addWidget(replace_label)
        
        self.replace_input = QLineEdit()
        self.replace_input.setPlaceholderText("Digite o texto de substituição...")
        replace_layout.addWidget(self.replace_input)
        
        # Botões de substituição
        replace_buttons_layout = QHBoxLayout()
        self.replace_btn = QPushButton("Substituir")
        self.replace_btn.clicked.connect(self.replace_current)
        self.replace_all_btn = QPushButton("Substituir Todas")
        self.replace_all_btn.clicked.connect(self.replace_all)
        
        replace_buttons_layout.addWidget(self.replace_btn)
        replace_buttons_layout.addWidget(self.replace_all_btn)
        replace_layout.addLayout(replace_buttons_layout)
        
        layout.addWidget(replace_group)
        
        # Label de status
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #888; padding: 5px;")
        layout.addWidget(self.status_label)
        
        # Botão Fechar
        close_layout = QHBoxLayout()
        close_layout.addStretch()
        close_btn = QPushButton("Fechar")
        close_btn.clicked.connect(self.close)
        close_layout.addWidget(close_btn)
        layout.addLayout(close_layout)
    
    def get_search_flags(self):
        """Retorna flags de busca baseado nas opções"""
        flags = QTextDocument.FindFlag(0)
        
        if self.case_sensitive_check.isChecked():
            flags |= QTextDocument.FindFlag.FindCaseSensitively
        
        if self.whole_word_check.isChecked():
            flags |= QTextDocument.FindFlag.FindWholeWords
        
        return flags
    
    def find_next(self):
        """Localiza próxima ocorrência"""
        search_text = self.find_input.text()
        if not search_text:
            self.status_label.setText("⚠️ Digite um texto para localizar")
            return
        
        cursor = self.editor.textCursor()
        flags = self.get_search_flags()
        
        # Buscar a partir da posição atual
        found_cursor = self.editor.document().find(search_text, cursor, flags)
        
        if found_cursor.isNull():
            # Se não encontrou, buscar do início
            found_cursor = self.editor.document().find(search_text, 0, flags)
            
            if found_cursor.isNull():
                self.status_label.setText("❌ Nenhuma ocorrência encontrada")
                return
            else:
                self.status_label.setText("🔄 Voltando ao início do documento")
        else:
            self.status_label.setText("✅ Encontrado")
        
        # Selecionar o texto encontrado
        self.editor.setTextCursor(found_cursor)
        self.editor.ensureCursorVisible()
    
    def find_previous(self):
        """Localiza ocorrência anterior"""
        search_text = self.find_input.text()
        if not search_text:
            self.status_label.setText("⚠️ Digite um texto para localizar")
            return
        
        cursor = self.editor.textCursor()
        flags = self.get_search_flags()
        flags |= QTextDocument.FindFlag.FindBackward
        
        # Buscar para trás
        found_cursor = self.editor.document().find(search_text, cursor, flags)
        
        if found_cursor.isNull():
            # Se não encontrou, buscar do final
            cursor.movePosition(QTextCursor.MoveOperation.End)
            found_cursor = self.editor.document().find(search_text, cursor, flags)
            
            if found_cursor.isNull():
                self.status_label.setText("❌ Nenhuma ocorrência encontrada")
                return
            else:
                self.status_label.setText("🔄 Voltando ao final do documento")
        else:
            self.status_label.setText("✅ Encontrado")
        
        # Selecionar o texto encontrado
        self.editor.setTextCursor(found_cursor)
        self.editor.ensureCursorVisible()
    
    def highlight_all(self):
        """Destaca todas as ocorrências"""
        search_text = self.find_input.text()
        if not search_text:
            self.status_label.setText("⚠️ Digite um texto para localizar")
            return
        
        # Remover highlights anteriores
        cursor = self.editor.textCursor()
        cursor.select(QTextCursor.SelectionType.Document)
        
        # Criar formato de highlight
        highlight_format = QTextCharFormat()
        highlight_format.setBackground(QColor("#6A5ACD"))
        
        # Buscar e destacar todas
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
        self.status_label.setText(f"✅ {count} ocorrência(s) encontrada(s)")
    
    def replace_current(self):
        """Substitui a ocorrência atual"""
        cursor = self.editor.textCursor()
        
        if cursor.hasSelection():
            search_text = self.find_input.text()
            selected_text = cursor.selectedText()
            
            # Verificar se o texto selecionado corresponde à busca
            matches = False
            if self.case_sensitive_check.isChecked():
                matches = selected_text == search_text
            else:
                matches = selected_text.lower() == search_text.lower()
            
            if matches:
                replace_text = self.replace_input.text()
                cursor.insertText(replace_text)
                self.status_label.setText("✅ Substituído")
                
                # Buscar próxima
                self.find_next()
            else:
                self.status_label.setText("⚠️ Selecione uma ocorrência primeiro")
        else:
            self.status_label.setText("⚠️ Selecione uma ocorrência primeiro")
            self.find_next()
    
    def replace_all(self):
        """Substitui todas as ocorrências"""
        search_text = self.find_input.text()
        replace_text = self.replace_input.text()
        
        if not search_text:
            self.status_label.setText("⚠️ Digite um texto para localizar")
            return
        
        # Confirmar ação
        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self,
            'Confirmar Substituição',
            f'Deseja substituir todas as ocorrências de "{search_text}" por "{replace_text}"?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Realizar substituições
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
        
        self.status_label.setText(f"✅ {count} ocorrência(s) substituída(s)")
    
    def showEvent(self, event):
        """Ao mostrar a janela, focar no campo de busca"""
        super().showEvent(event)
        self.find_input.setFocus()
        self.find_input.selectAll()
    
    def keyPressEvent(self, event):
        """Detectar Esc para fechar"""
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Project AI")
        self.setGeometry(100, 100, 1600, 900)
        
        # Pasta de trabalho padrÃ£o
        self.working_directory = os.getcwd()
        
        # Widget central com splitter
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal horizontal
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Splitter principal (3 painÃ©is)
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Explorador de arquivos (esquerda)
        self.file_explorer = self.create_file_explorer()
        
        # Tab Widget para mÃºltiplos arquivos (centro)
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.update_encoding_selector)
        
        # Chat IA (direita)
        self.ai_chat = AIChatWidget(self)
        self.ai_chat.setMaximumWidth(400)  # Define largura máxima do chat
        self.ai_chat.setMinimumWidth(250)       
        
        # Adicionar widgets ao splitter
        self.main_splitter.addWidget(self.file_explorer)
        self.main_splitter.addWidget(self.tabs)
        self.main_splitter.addWidget(self.ai_chat)
        
        
        # Definir proporÃ§Ãµes (20% explorador, 50% editor, 30% chat)
        self.main_splitter.setSizes([250, 1000, 100])
        
        main_layout.addWidget(self.main_splitter)
        
        # Criar menus
        self.create_menus()
        
        # Criar toolbar
        self.create_toolbar()
        
        # Status bar
        self.statusBar().showMessage("Pronto")
        
        # Abrir uma aba vazia inicial
        self.new_file()
        
        
    def toggle_color_highlighting(self):
        """Ativa/desativa destaque de códigos de cores"""
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
            
            

    def create_file_explorer(self):
        """Cria o explorador de arquivos lateral"""
        explorer_widget = QWidget()
        explorer_layout = QVBoxLayout(explorer_widget)
        explorer_layout.setContentsMargins(5, 5, 5, 5)
        
        # Label do tÃ­tulo
        title_label = QLabel("Workplace")
        title_label.setStyleSheet("font-weight: bold; padding: 7px;")
        explorer_layout.addWidget(title_label)
        

        folder_button_layout = QVBoxLayout()
        
        select_folder_btn = QAction("Selecionar Pasta", self)
        select_folder_btn.triggered.connect(self.select_working_folder)
        
        from PyQt6.QtWidgets import QPushButton
        select_btn = QPushButton("Selecionar Pasta")
        select_btn.clicked.connect(self.select_working_folder)
        folder_button_layout.addWidget(select_btn)
        
        explorer_layout.addLayout(folder_button_layout)
        
        # Tree View para arquivos
        self.file_tree = QTreeView()
        self.file_model = QFileSystemModel()
        self.file_model.setRootPath(QDir.rootPath())
        
        # Filtros de arquivo
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
        
        # Duplo clique para abrir arquivo
        self.file_tree.doubleClicked.connect(self.open_file_from_explorer)
        
        explorer_layout.addWidget(self.file_tree)
        
        # Label com caminho atual
        self.current_path_label = QLabel(f"ok“? {self.working_directory}")
        self.current_path_label.setWordWrap(True)
        self.current_path_label.setStyleSheet("font-size: 9px; color: #888; padding: 5px;")
        explorer_layout.addWidget(self.current_path_label)
        
        return explorer_widget
        
    def show_find_replace(self):
        """Mostra busca e substituição no editor atual"""
        current_editor = self.tabs.currentWidget()
        if current_editor and isinstance(current_editor, CodeEditor):
            current_editor.show_find_dialog()
        
    
    def select_working_folder(self):
        """Seleciona a pasta de trabalho"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Selecionar Pasta de Trabalho",
            self.working_directory
        )
        
        if folder:
            self.working_directory = folder
            self.file_tree.setRootIndex(self.file_model.index(folder))
            self.current_path_label.setText(f"ok“? {folder}")
            self.statusBar().showMessage(f"Pasta de trabalho: {folder}")
            
            
            
    
    def open_file_from_explorer(self, index):
        """Abre arquivo clicado no explorador"""
        file_path = self.file_model.filePath(index)
        

        if os.path.isfile(file_path):
 
            for i in range(self.tabs.count()):
                editor = self.tabs.widget(i)
                if hasattr(editor, 'file_path') and editor.file_path == file_path:
                    self.tabs.setCurrentIndex(i)
                    self.statusBar().showMessage(f"Arquivo já aberto: {os.path.basename(file_path)}")
                    return
            
            # Abrir novo arquivo
            editor = CodeEditor(file_path)
            file_name = os.path.basename(file_path)
            index = self.tabs.addTab(editor, file_name)
            self.tabs.setCurrentIndex(index)
            
            detected_enc = editor.current_encoding.upper()
            self.statusBar().showMessage(f"Arquivo: {file_name} | Encoding: {detected_enc}")
    
    
    def create_menus(self):
        menubar = self.menuBar()
        
        # Menu Arquivo
        file_menu = menubar.addMenu("Arquivo")
        
        new_action = QAction("Novo", self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self.new_file)
        file_menu.addAction(new_action)
        
        open_action = QAction("Abrir", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)
        
        # Abrir Pasta
        open_folder_action = QAction("Abrir Pasta", self)
        open_folder_action.setShortcut("Ctrl+Shift+O")
        open_folder_action.triggered.connect(self.select_working_folder)
        file_menu.addAction(open_folder_action)
        
        save_action = QAction("Salvar", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self.save_file)
        file_menu.addAction(save_action)
        
        save_as_action = QAction("Salvar Como", self)
        save_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        save_as_action.triggered.connect(self.save_file_as)
        file_menu.addAction(save_as_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Sair", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Menu Editar
        edit_menu = menubar.addMenu("Editar")
        
        undo_action = QAction("Desfazer", self)
        undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        undo_action.triggered.connect(self.undo)
        edit_menu.addAction(undo_action)
        
        redo_action = QAction("Refazer", self)
        redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        redo_action.triggered.connect(self.redo)
        edit_menu.addAction(redo_action)
        
        edit_menu.addSeparator()
        
        # NOVO: Localizar e Substituir
        find_action = QAction("Localizar e Substituir", self)
        find_action.setShortcut("Ctrl+F")
        find_action.triggered.connect(self.show_find_replace)
        edit_menu.addAction(find_action)
        
        edit_menu.addSeparator()

      
  
        duplicate_action = QAction("Duplicar Linha", self)
        duplicate_action.setShortcut("Ctrl+D")
        duplicate_action.triggered.connect(self.duplicate_current_line)
        edit_menu.addAction(duplicate_action)
        
        # NOVO: Comentar/Descomentar
        comment_action = QAction("Comentar/Descomentar", self)
        comment_action.setShortcut("Ctrl+/")
        comment_action.triggered.connect(self.toggle_comment_line)
        edit_menu.addAction(comment_action)        
        
        
        # Menu Visualizar - CRIAR ANTES DE USAR
        view_menu = menubar.addMenu("Visualizar")
        
        toggle_explorer_action = QAction("Mostrar/Ocultar Explorador", self)
        toggle_explorer_action.setShortcut("Ctrl+B")
        toggle_explorer_action.triggered.connect(self.toggle_file_explorer)
        view_menu.addAction(toggle_explorer_action)
        
        toggle_chat_action = QAction("Mostrar/Ocultar Chat IA", self)
        toggle_chat_action.setShortcut("Ctrl+Shift+A")
        toggle_chat_action.triggered.connect(self.toggle_ai_chat)
        view_menu.addAction(toggle_chat_action)
        
        edit_menu.addSeparator()       
        # NOVO: Highlight de cores
        highlight_colors_action = QAction("Destacar Códigos de Cores", self)
        highlight_colors_action.setShortcut("Ctrl+Shift+C")
        highlight_colors_action.triggered.connect(self.toggle_color_highlighting)
        view_menu.addAction(highlight_colors_action)     

    def duplicate_current_line(self):
        """Duplica linha no editor atual"""
        current_editor = self.tabs.currentWidget()
        if current_editor and isinstance(current_editor, CodeEditor):
            current_editor.duplicate_line()

    def toggle_comment_line(self):
        """Comenta/descomenta linha no editor atual"""
        current_editor = self.tabs.currentWidget()
        if current_editor and isinstance(current_editor, CodeEditor):
            current_editor.toggle_comment()



    def toggle_file_explorer(self):
        """Mostra ou oculta o explorador de arquivos"""
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
            
            
            



    
    def create_toolbar(self):
        toolbar = QToolBar()
        self.addToolBar(toolbar)
        
        new_action = QAction("Novo", self)
        new_action.triggered.connect(self.new_file)
        toolbar.addAction(new_action)
        
        open_action = QAction("Abrir", self)
        open_action.triggered.connect(self.open_file)
        toolbar.addAction(open_action)
        
        save_action = QAction("Salvar", self)
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
        """Atualiza o seletor de encoding baseado na aba atual"""
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
        """Muda o encoding do arquivo atual"""
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
            # Recarregar arquivo com novo encoding
            current_editor.reload_with_encoding(encoding)
            self.statusBar().showMessage(f"Arquivo recarregado com encoding: {encoding.upper()}")
        else:
            # Apenas mudar o encoding para salvar
            current_editor.current_encoding = encoding
            self.statusBar().showMessage(f"Encoding alterado para: {encoding.upper()}")
    
    def new_file(self):
        editor = CodeEditor()
        index = self.tabs.addTab(editor, "Sem Título")
        self.tabs.setCurrentIndex(index)
    
    def open_file(self):
        file_paths, _ = QFileDialog.getOpenFileNames( 
            self, 
            "Abrir Arquivo", 
            "", 
            "Todos os Arquivos (*);;"\
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
            "Texto (*.txt);;"\
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
                self.statusBar().showMessage(f"Arquivo: {file_name} | Encoding: {detected_enc}")

    
    def save_file(self):
        current_editor = self.tabs.currentWidget()
        if current_editor and current_editor.save_file():
            file_name = os.path.basename(current_editor.file_path)
            self.tabs.setTabText(self.tabs.currentIndex(), file_name)
            self.statusBar().showMessage(f"Arquivo salvo: {current_editor.file_path}")
    
    def save_file_as(self):
        current_editor = self.tabs.currentWidget()
        if current_editor and current_editor.save_file_as():
            file_name = os.path.basename(current_editor.file_path)
            self.tabs.setTabText(self.tabs.currentIndex(), file_name)
            self.statusBar().showMessage(f"Arquivo salvo: {current_editor.file_path}")
    
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
    window.show()
    
    sys.exit(app.exec())
