from datetime import datetime


class HexColorFormatter:
    """Форматтер с hex цветами для тегов"""
    
    @staticmethod
    def hex_to_ansi(hex_color: str) -> str:
        """Конвертирует hex цвет в ANSI escape code"""
        if not hex_color or not hex_color.startswith('#'):
            return ''
        
        try:
            hex_color = hex_color.lstrip('#')
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            
            ansi_color = 16 + (r // 51) * 36 + (g // 51) * 6 + (b // 51)
            return f'\033[38;5;{ansi_color}m'
        except (ValueError, IndexError):
            return ''
    
    def format(self, tag: str, hex_color: str, message: str) -> str:
        color_code = self.hex_to_ansi(hex_color) if hex_color else ''
        reset_code = '\033[0m' if color_code else ''
        
        formatted_time = datetime.fromtimestamp(datetime.now().timestamp()).strftime('%H:%M:%S')
        formatted = f"{color_code}[ {tag} ]{reset_code} {formatted_time} ~ {message}"
        
        return formatted
class GFPConsoleMessageStylizer:
    def __init__(self, tag, color):
        self.tag = tag
        self.color = color
        self.hex_formatter = HexColorFormatter()

    def log(self, message):
        msg = self.hex_formatter.format(self.tag, self.color, message)
        print(msg)

# Примеры использования:
if __name__ == "__main__":
    # Простое использование
    a  =GFPConsoleMessageStylizer(tag="a", color="#ff0000")
    a.log("Hello, World!")

    # Использование с цветом
    b = GFPConsoleMessageStylizer(tag="b", color="#66ff57")
    b.log("Hello, World!")

    # Использование с цветом и тегом
    c = GFPConsoleMessageStylizer(tag="c", color="#66f0ff")
    c.log("Hello, World!")