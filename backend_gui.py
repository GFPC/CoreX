import tkinter as tk
from tkinter import ttk, scrolledtext
import subprocess
import threading
import sys
from pathlib import Path
import webbrowser
from datetime import datetime
import signal
import os

class BrightBackendGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("GFP CoreX Backend Launcher")
        self.root.geometry("1100x750")
        self.root.configure(bg='#1a1a2e')
        
        # Переменные
        self.process = None
        self.is_running = False
        
        # Настройка стилей
        self.setup_styles()
        self.setup_ui()
        
        # Центрирование окна
        self.center_window()
    
    def setup_styles(self):
        """Настройка стилей для яркого дизайна"""
        style = ttk.Style()
        
        # Яркая тема
        style.theme_use('clam')
        
        # Настройка цветов
        style.configure('Dark.TFrame', background='#1a1a2e')
        style.configure('Dark.TLabel', background='#1a1a2e', foreground='#ffffff')
        style.configure('Title.TLabel', background='#1a1a2e', foreground='#ff6b6b', font=('Segoe UI', 20, 'bold'))
        style.configure('Status.TLabel', background='#1a1a2e', foreground='#ffffff', font=('Segoe UI', 11))
        style.configure('Info.TLabel', background='#1a1a2e', foreground='#a8e6cf', font=('Consolas', 9))
        
        # Стили для кнопок
        style.configure('Start.TButton', 
                       background='#4ecdc4', 
                       foreground='#000000',
                       font=('Segoe UI', 12, 'bold'),
                       padding=(25, 12))
        
        style.configure('Stop.TButton', 
                       background='#ff6b6b', 
                       foreground='#ffffff',
                       font=('Segoe UI', 12, 'bold'),
                       padding=(25, 12))
        
        style.configure('Link.TButton', 
                       background='#45b7d1', 
                       foreground='#ffffff',
                       font=('Segoe UI', 10),
                       padding=(15, 8))
        
        # Стили для фреймов
        style.configure('Card.TFrame', background='#16213e', relief='flat')
        style.configure('Log.TFrame', background='#0f3460')
    
    def center_window(self):
        """Центрирование окна на экране"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
    
    def setup_ui(self):
        """Настройка интерфейса"""
        
        # Главный контейнер
        main_container = ttk.Frame(self.root, style='Dark.TFrame', padding="25")
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Заголовок с градиентом
        header_frame = ttk.Frame(main_container, style='Dark.TFrame')
        header_frame.pack(fill=tk.X, pady=(0, 25))
        
        title_label = ttk.Label(header_frame, 
                               text="GFP CoreX Backend Launcher", 
                               style='Title.TLabel')
        title_label.pack()
        
        subtitle_label = ttk.Label(header_frame, 
                                  text="Production-ready Multi-Configuration FastAPI Backend", 
                                  style='Info.TLabel')
        subtitle_label.pack(pady=(8, 0))
        
        # Карточка с кнопками управления
        control_card = ttk.Frame(main_container, style='Card.TFrame', padding="25")
        control_card.pack(fill=tk.X, pady=(0, 25))
        
        # Кнопки управления
        button_frame = ttk.Frame(control_card, style='Card.TFrame')
        button_frame.pack()
        
        self.start_button = ttk.Button(button_frame, 
                                      text="START BACKEND", 
                                      style='Start.TButton',
                                      command=self.start_backend)
        self.start_button.pack(side=tk.LEFT, padx=(0, 15))
        
        self.stop_button = ttk.Button(button_frame, 
                                     text="STOP BACKEND", 
                                     style='Stop.TButton',
                                     command=self.stop_backend, 
                                     state="disabled")
        self.stop_button.pack(side=tk.LEFT)
        
        # Статус
        status_frame = ttk.Frame(control_card, style='Card.TFrame')
        status_frame.pack(pady=(20, 0))
        
        self.status_label = ttk.Label(status_frame, 
                                     text="Status: Stopped", 
                                     style='Status.TLabel')
        self.status_label.pack()
        
        # Карточка с быстрыми ссылками
        links_card = ttk.Frame(main_container, style='Card.TFrame', padding="25")
        links_card.pack(fill=tk.X, pady=(0, 25))
        
        links_label = ttk.Label(links_card, text="Quick Access Links", style='Status.TLabel')
        links_label.pack(pady=(0, 15))
        
        links_frame = ttk.Frame(links_card, style='Card.TFrame')
        links_frame.pack()
        
        # Кнопки быстрых ссылок
        ttk.Button(links_frame, text="Backend API", style='Link.TButton',
                  command=lambda: webbrowser.open('http://localhost:8000')).pack(side=tk.LEFT, padx=(0, 12))
        
        ttk.Button(links_frame, text="Swagger Docs", style='Link.TButton',
                  command=lambda: webbrowser.open('http://localhost:8000/docs')).pack(side=tk.LEFT, padx=(0, 12))
        
        ttk.Button(links_frame, text="ReDoc Docs", style='Link.TButton',
                  command=lambda: webbrowser.open('http://localhost:8000/redoc')).pack(side=tk.LEFT, padx=(0, 12))
        
        ttk.Button(links_frame, text="Health Check", style='Link.TButton',
                  command=lambda: webbrowser.open('http://localhost:8000/health')).pack(side=tk.LEFT)
        
        # Карточка с логами
        log_card = ttk.Frame(main_container, style='Card.TFrame', padding="25")
        log_card.pack(fill=tk.BOTH, expand=True)
        
        log_header = ttk.Frame(log_card, style='Card.TFrame')
        log_header.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(log_header, text="Live Backend Logs", style='Status.TLabel').pack(side=tk.LEFT)
        
        # Кнопки управления логами
        ttk.Button(log_header, text="Clear Logs", style='Link.TButton',
                  command=self.clear_logs).pack(side=tk.RIGHT)
        
        ttk.Button(log_header, text="Copy Logs", style='Link.TButton',
                  command=self.copy_logs).pack(side=tk.RIGHT, padx=(0, 12))
        
        # Текстовое поле для логов с поддержкой эмодзи
        log_frame = ttk.Frame(log_card, style='Log.TFrame')
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        # Используем tk.Text вместо scrolledtext для лучшей поддержки эмодзи
        self.log_text = tk.Text(
            log_frame, 
            height=18, 
            width=90,
            bg='#0f3460',
            fg='#a8e6cf',
            font=('Segoe UI', 10),  # Используем Segoe UI для поддержки эмодзи
            insertbackground='#ffffff',
            selectbackground='#4ecdc4',
            selectforeground='#000000',
            wrap=tk.WORD,
            padx=10,
            pady=10
        )
        
        # Добавляем скроллбар
        scrollbar = tk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        # Размещаем текст и скроллбар
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Статус бар
        self.status_bar = ttk.Label(main_container, 
                                   text="Ready to launch backend", 
                                   style='Info.TLabel')
        self.status_bar.pack(fill=tk.X, pady=(15, 0))
    
    def log_message(self, message):
        """Добавление сообщения в лог с временной меткой"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # НЕ заменяем эмодзи - оставляем как есть
        formatted_message = f"[{timestamp}] {message}\n"
        
        self.log_text.insert(tk.END, formatted_message)
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def clear_logs(self):
        """Очистка логов"""
        self.log_text.delete(1.0, tk.END)
        self.log_message("Logs cleared")
    
    def copy_logs(self):
        """Копирование логов в буфер обмена"""
        logs = self.log_text.get(1.0, tk.END)
        self.root.clipboard_clear()
        self.root.clipboard_append(logs)
        self.status_bar.config(text="Logs copied to clipboard")
    
    def start_backend(self):
        """Запуск бэкенда"""
        if self.is_running:
            return
        
        self.is_running = True
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.status_label.config(text="Status: Starting...")
        self.status_bar.config(text="Initializing backend...")
        
        # Запуск в отдельном потоке
        thread = threading.Thread(target=self._run_backend)
        thread.daemon = True
        thread.start()
    
    def _run_backend(self):
        """Запуск бэкенда в отдельном потоке"""
        try:
            venv_path = Path("D:/PROJECTS/Python/SELF/GFP CoreX/venv/Scripts/python.exe")
            
            if not venv_path.exists():
                self.log_message("❌ Ошибка: Python не найден!")
                return
            
            self.log_message("🚀 Запуск GFP CoreX бэкенда...")
            self.log_message(f"📁 Путь к Python: {venv_path}")
            
            # Запуск процесса
            self.process = subprocess.Popen([
                str(venv_path),
                "-m", "src.gfpcorex.main"
            ],
            cwd="D:/PROJECTS/Python/SELF/GFP CoreX",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
            )
            
            # Обновление статуса
            self.root.after(0, lambda: self.status_label.config(text="Status: Running"))
            self.root.after(0, lambda: self.status_bar.config(text="Backend is running"))
            self.log_message("✅ Бэкенд запущен успешно!")
            self.log_message("🌐 Доступен по адресу: http://localhost:8000")
            
            # Чтение вывода
            for line in iter(self.process.stdout.readline, ''):
                if line:
                    self.root.after(0, lambda l=line: self.log_message(l.strip()))
            
        except Exception as e:
            self.log_message(f"❌ Ошибка запуска: {e}")
        finally:
            self.is_running = False
            self.root.after(0, self._reset_ui)
    
    def stop_backend(self):
        """Остановка бэкенда"""
        if self.process and self.is_running:
            try:
                # Сначала пробуем graceful shutdown
                self.process.terminate()
                
                # Ждем 5 секунд для graceful shutdown
                self.process.wait(timeout=5)
                
            except subprocess.TimeoutExpired:
                # Если не остановился за 5 секунд, принудительно убиваем
                self.process.kill()
                self.process.wait()
            
            self.log_message("⏹️ Остановка бэкенда...")
            self.status_label.config(text="Status: Stopping...")
            self.status_bar.config(text="Stopping backend...")
            
            # Сбрасываем состояние
            self.is_running = False
            self.process = None
            
            # Обновляем UI
            self.root.after(1000, self._reset_ui)
    
    def _reset_ui(self):
        """Сброс интерфейса"""
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")
        self.status_label.config(text="Status: Stopped")
        self.status_bar.config(text="Backend stopped")
        self.log_message("🛑 Бэкенд остановлен")

def main():
    root = tk.Tk()
    app = BrightBackendGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main() 