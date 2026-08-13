import subprocess
import sys
import os
from pathlib import Path

def start_backend():
    """Запуск GFP CoreX бэкенда"""
    
    python_exe = sys.executable
    project_root = Path(__file__).parent.resolve()
    
    try:
        print("🚀 Запуск GFP CoreX бэкенда...")
        print(f"📁 Путь к Python: {python_exe}")
        
        # Запускаем процесс
        process = subprocess.Popen([
            python_exe,
            "-m", "src.gfpcorex.main"
        ], 
        cwd=str(project_root),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
        )
        
        print("✅ Бэкенд запущен!")
        print("🌐 Доступен по адресу: http://localhost:8000")
        print("📚 Документация: http://localhost:8000/docs")
        print("⏹️  Для остановки нажмите Ctrl+C")
        
        # Ждем завершения процесса
        process.wait()
        
    except Exception as e:
        print(f"❌ Ошибка запуска: {e}")
        return False
    
    return True

if __name__ == "__main__":
    start_backend() 