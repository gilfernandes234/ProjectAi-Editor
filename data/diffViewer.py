import sys
import os
import shutil
import subprocess
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
                             QScrollArea, QFrame, QHBoxLayout, QCheckBox, QColorDialog,
                             QDialog, QListWidget, QPlainTextEdit)
                             
                             
class DiffViewerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Comparar Arquivos")
        self.setGeometry(100, 100, 1200, 700)
        self.showMaximized()       
        self.left_content = ""
        self.right_content = ""
        self.left_name = ""
        self.right_name = ""
        
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(5)  # Reduzir espaçamento entre widgets
        
        # ===== Seção de Seleção (compacta) =====
        selection_widget = QWidget()
        selection_widget.setMaximumHeight(120)  # LIMITAR altura da seção de seleção
        selection_layout = QHBoxLayout(selection_widget)
        
        # Seleção esquerda
        left_group = QVBoxLayout()
        left_label = QLabel("Arquivo Original:")
        self.left_file_label = QLabel("Nenhum arquivo selecionado")
        self.left_file_label.setStyleSheet("color: #888; font-size: 10px;")
        left_btn = QPushButton("Selecionar Arquivo Original")
        left_btn.clicked.connect(lambda: self.select_file('left'))
        left_group.addWidget(left_label)
        left_group.addWidget(self.left_file_label)
        left_group.addWidget(left_btn)
        
        # Seleção direita
        right_group = QVBoxLayout()
        right_label = QLabel("Arquivo Modificado:")
        self.right_file_label = QLabel("Nenhum arquivo selecionado")
        self.right_file_label.setStyleSheet("color: #888; font-size: 10px;")
        right_btn = QPushButton("Selecionar Arquivo Modificado")
        right_btn.clicked.connect(lambda: self.select_file('right'))
        right_group.addWidget(right_label)
        right_group.addWidget(self.right_file_label)
        right_group.addWidget(right_btn)
        
        selection_layout.addLayout(left_group)
        selection_layout.addLayout(right_group)
        layout.addWidget(selection_widget)
        
        # ===== Botão de comparar (compacto) =====
        compare_widget = QWidget()
        compare_widget.setMaximumHeight(50)  # LIMITAR altura
        compare_layout = QVBoxLayout(compare_widget)
        compare_layout.setContentsMargins(0, 0, 0, 0)
        
        compare_btn = QPushButton("Comparar")
        compare_btn.clicked.connect(self.compare_files)
        compare_btn.setStyleSheet("background-color: #0e639c; padding: 8px; font-weight: bold;")
        compare_layout.addWidget(compare_btn)
        layout.addWidget(compare_widget)
        
        # ===== Estatísticas (compacta) =====
        self.stats_label = QLabel("")
        self.stats_label.setStyleSheet("color: #888; padding: 5px;")
        self.stats_label.setMaximumHeight(30)  # LIMITAR altura
        layout.addWidget(self.stats_label)
        
        # ===== EDITORES (OCUPAM TODO O ESPAÇO RESTANTE) =====
        diff_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Editor esquerdo
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)
        
        self.left_title = QLabel("Original")
        self.left_title.setStyleSheet("background-color: #2d2d2d; padding: 8px; font-weight: bold; font-size: 13px;")
        self.left_title.setMaximumHeight(32)
        
        self.left_editor = QTextEdit()
        self.left_editor.setReadOnly(True)
        self.left_editor.setFont(QFont("Consolas", 10))
        self.left_editor.setStyleSheet("background-color: #1e1e1e;")
        
        left_layout.addWidget(self.left_title)
        left_layout.addWidget(self.left_editor)  # Vai ocupar todo espaço restante
        
        # Editor direito
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        
        self.right_title = QLabel("Modificado")
        self.right_title.setStyleSheet("background-color: #2d2d2d; padding: 8px; font-weight: bold; font-size: 13px;")
        self.right_title.setMaximumHeight(32)
        
        self.right_editor = QTextEdit()
        self.right_editor.setReadOnly(True)
        self.right_editor.setFont(QFont("Consolas", 10))
        self.right_editor.setStyleSheet("background-color: #1e1e1e;")
        
        right_layout.addWidget(self.right_title)
        right_layout.addWidget(self.right_editor)  # Vai ocupar todo espaço restante
        
        diff_splitter.addWidget(left_container)
        diff_splitter.addWidget(right_container)
        diff_splitter.setSizes([600, 600])
        
        # ADICIONAR com stretch=100 para ocupar MÁXIMO espaço
        layout.addWidget(diff_splitter, stretch=100)  # <-- IMPORTANTE
        
        # ===== Botão fechar (compacto) =====
        close_btn = QPushButton("Fechar")
        close_btn.clicked.connect(self.close)
        close_btn.setMaximumHeight(35)
        layout.addWidget(close_btn, stretch=0)  # <-- stretch=0 = não expandir

    def select_file(self, side):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            f"Selecionar Arquivo {'Original' if side == 'left' else 'Modificado'}",
            "",
            "Todos os Arquivos (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                file_name = os.path.basename(file_path)
                
                if side == 'left':
                    self.left_content = content
                    self.left_name = file_name
                    self.left_file_label.setText(file_path)
                else:
                    self.right_content = content
                    self.right_name = file_name
                    self.right_file_label.setText(file_path)
                    
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Erro ao ler arquivo: {str(e)}")
    
    def set_files_from_tabs(self, left_content, left_name, right_content, right_name):
        self.left_content = left_content
        self.left_name = left_name
        self.right_content = right_content
        self.right_name = right_name
        
        self.left_file_label.setText(f"Aba: {left_name}")
        self.right_file_label.setText(f"Aba: {right_name}")
        
        # Comparar automaticamente
        self.compare_files()
    
    def compare_files(self):
        if not self.left_content or not self.right_content:
            QMessageBox.warning(self, "Aviso", "Selecione ambos os arquivos para comparar")
            return
        
        # Atualizar títulos
        self.left_title.setText(f"Original: {self.left_name}")
        self.right_title.setText(f"Modificado: {self.right_name}")
        
        # Calcular diferenças
        left_lines = self.left_content.splitlines()
        right_lines = self.right_content.splitlines()
        
        differ = difflib.Differ()
        diff = list(differ.compare(left_lines, right_lines))
        
        # Contar alterações
        additions = sum(1 for line in diff if line.startswith('+ '))
        deletions = sum(1 for line in diff if line.startswith('- '))
        
        self.stats_label.setText(
            f"Adições: <span style='color: #4caf50;'>{additions}</span> | "
            f"Remoções: <span style='color: #f44336;'>{deletions}</span>"
        )
        
        # Renderizar diff com cores
        self.render_diff(left_lines, right_lines, diff)
    
    def render_diff(self, left_lines, right_lines, diff):
        left_html = []
        right_html = []
        
        left_idx = 0
        right_idx = 0
        
        for line in diff:
            if line.startswith('  '):  # Linha igual
                content = line[2:]
                left_html.append(f"<div style='padding: 2px;'>{self.escape_html(content)}</div>")
                right_html.append(f"<div style='padding: 2px;'>{self.escape_html(content)}</div>")
                left_idx += 1
                right_idx += 1
                
            elif line.startswith('- '):  # Linha removida (só no original)
                content = line[2:]
                left_html.append(
                    f"<div style='background-color: #4d1f1f; padding: 2px; border-left: 3px solid #f44336;'>"
                    f"{self.escape_html(content)}</div>"
                )
                right_html.append("<div style='padding: 2px; background-color: #2d2d2d;'>&nbsp;</div>")
                left_idx += 1
                
            elif line.startswith('+ '):  # Linha adicionada (só no modificado)
                content = line[2:]
                left_html.append("<div style='padding: 2px; background-color: #2d2d2d;'>&nbsp;</div>")
                right_html.append(
                    f"<div style='background-color: #1f4d1f; padding: 2px; border-left: 3px solid #4caf50;'>"
                    f"{self.escape_html(content)}</div>"
                )
                right_idx += 1
        
        # Aplicar HTML aos editores
        self.left_editor.setHtml(''.join(left_html))
        self.right_editor.setHtml(''.join(right_html))
        
        # Sincronizar scroll
        self.sync_scrollbars()
    
    def sync_scrollbars(self):
        left_scroll = self.left_editor.verticalScrollBar()
        right_scroll = self.right_editor.verticalScrollBar()
        
        left_scroll.valueChanged.connect(right_scroll.setValue)
        right_scroll.valueChanged.connect(left_scroll.setValue)
    
    def escape_html(self, text):
        return (text.replace('&', '&amp;')
                   .replace('<', '&lt;')
                   .replace('>', '&gt;')
                   .replace(' ', '&nbsp;'))