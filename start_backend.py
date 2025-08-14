import subprocess
import sys
import os
from pathlib import Path

def start_backend():
    """Запуск GFP CoreX бэкенда"""
    
    # Путь к виртуальному окружению
    venv_path = Path("D:/PROJECTS/Python/SELF/GFP CoreX/venv/Scripts/python.exe")
    
    # Проверяем существование файла
    if not venv_path.exists():
        print(f"❌ Ошибка: Python не найден по пути {venv_path}")
        return False
    
    try:
        print("🚀 Запуск GFP CoreX бэкенда...")
        print(f"📁 Путь к Python: {venv_path}")
        
        # Запускаем процесс
        process = subprocess.Popen([
            str(venv_path),
            "-m", "src.gfpcorex.main"
        ], 
        cwd="D:/PROJECTS/Python/SELF/GFP CoreX",
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