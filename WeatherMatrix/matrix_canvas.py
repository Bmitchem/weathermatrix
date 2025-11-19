"""Canvas abstraction for matrix display - allows swapping real hardware with test backends."""
from abc import ABC, abstractmethod
from typing import Tuple, Optional, TYPE_CHECKING

# Try to import PIL for image output
try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    # Create a dummy type for type hints when PIL is not available
    if TYPE_CHECKING:
        from PIL import Image
    else:
        Image = None


class MatrixCanvas(ABC):
    """Abstract canvas interface for drawing on the LED matrix."""
    
    @property
    @abstractmethod
    def width(self) -> int:
        """Get canvas width in pixels."""
        pass
    
    @property
    @abstractmethod
    def height(self) -> int:
        """Get canvas height in pixels."""
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """Clear the entire canvas (set all pixels to black)."""
        pass
    
    @abstractmethod
    def set_pixel(self, x: int, y: int, r: int, g: int, b: int) -> None:
        """
        Set a single pixel to the given RGB color.
        
        Args:
            x: X coordinate (0-based)
            y: Y coordinate (0-based)
            r: Red component (0-255)
            g: Green component (0-255)
            b: Blue component (0-255)
        """
        pass
    
    @abstractmethod
    def fill(self, r: int, g: int, b: int) -> None:
        """
        Fill the entire canvas with the given RGB color.
        
        Args:
            r: Red component (0-255)
            g: Green component (0-255)
            b: Blue component (0-255)
        """
        pass


class RealMatrixCanvas(MatrixCanvas):
    """Canvas implementation using the actual RGB matrix hardware."""
    
    def __init__(self, matrix):
        """
        Initialize with an RGBMatrix instance.
        
        Args:
            matrix: RGBMatrix instance from rgbmatrix library
        """
        self._matrix = matrix
    
    @property
    def width(self) -> int:
        return self._matrix.width
    
    @property
    def height(self) -> int:
        return self._matrix.height
    
    def clear(self) -> None:
        self._matrix.Clear()
    
    def set_pixel(self, x: int, y: int, r: int, g: int, b: int) -> None:
        self._matrix.SetPixel(x, y, r, g, b)
    
    def fill(self, r: int, g: int, b: int) -> None:
        self._matrix.Fill(r, g, b)


class FakeMatrixCanvas(MatrixCanvas):
    """
    Fake canvas implementation for testing - stores pixels in memory.
    
    Useful for unit tests and development without hardware.
    """
    
    def __init__(self, width: int = 64, height: int = 32):
        """
        Initialize fake canvas.
        
        Args:
            width: Canvas width in pixels
            height: Canvas height in pixels
        """
        self._width = width
        self._height = height
        # Store pixels as list of lists: pixels[y][x] = (r, g, b)
        self._pixels = [[(0, 0, 0) for _ in range(width)] for _ in range(height)]
    
    @property
    def width(self) -> int:
        return self._width
    
    @property
    def height(self) -> int:
        return self._height
    
    def clear(self) -> None:
        self._pixels = [[(0, 0, 0) for _ in range(self._width)] 
                        for _ in range(self._height)]
    
    def set_pixel(self, x: int, y: int, r: int, g: int, b: int) -> None:
        if 0 <= x < self._width and 0 <= y < self._height:
            self._pixels[y][x] = (r, g, b)
    
    def fill(self, r: int, g: int, b: int) -> None:
        self._pixels = [[(r, g, b) for _ in range(self._width)] 
                        for _ in range(self._height)]
    
    def get_pixel(self, x: int, y: int) -> Tuple[int, int, int]:
        """
        Get pixel color at given coordinates (for testing).
        
        Args:
            x: X coordinate
            y: Y coordinate
            
        Returns:
            Tuple of (r, g, b) values
        """
        if 0 <= x < self._width and 0 <= y < self._height:
            return self._pixels[y][x]
        return (0, 0, 0)
    
    def to_ascii(self, chars: str = " .:-=+*#%@") -> str:
        """
        Convert canvas to ASCII art representation (for testing/debugging).
        
        Args:
            chars: Characters to use for different brightness levels
            
        Returns:
            Multi-line string representation
        """
        lines = []
        for row in self._pixels:
            line = ""
            for r, g, b in row:
                # Convert RGB to grayscale brightness
                brightness = int(0.299 * r + 0.587 * g + 0.114 * b)
                # Map to character
                char_idx = min(int(brightness / 256.0 * len(chars)), len(chars) - 1)
                line += chars[char_idx]
            lines.append(line)
        return "\n".join(lines)
    
    def draw_text(self, x: int, y: int, text: str, r: int, g: int, b: int, font_size: int = 8):
        """
        Simple text rendering for fake canvas - draws text as pixels.
        
        This is a very basic implementation that draws text using simple patterns.
        For better results, use PILCanvas backend.
        
        Args:
            x: X position
            y: Y position  
            text: Text to draw
            r: Red component
            g: Green component
            b: Blue component
            font_size: Font size (not really used, kept for compatibility)
        """
        # Very simple text rendering - just draw colored pixels for each character
        # This is just a placeholder - real text would need bitmap font rendering
        char_width = 6
        char_height = 8
        
        for i, char in enumerate(text):
            char_x = x + (i * char_width)
            # Draw a simple pattern for visibility (just a few pixels per char)
            if 0 <= char_x < self._width and 0 <= y < self._height:
                # Draw a simple "block" pattern
                for py in range(min(char_height, self._height - y)):
                    for px in range(min(char_width, self._width - char_x)):
                        if px < char_width - 1 and py < char_height - 1:
                            self.set_pixel(char_x + px, y + py, r, g, b)


class PILCanvas(MatrixCanvas):
    """
    PIL-based canvas for rendering to PNG images.
    
    Useful for testing and previewing without hardware.
    """
    
    def __init__(self, width: int = 64, height: int = 32, scale: int = 10):
        """
        Initialize PIL canvas.
        
        Args:
            width: Canvas width in pixels
            height: Canvas height in pixels
            scale: Scale factor for output image (makes it bigger for viewing)
        """
        if not PIL_AVAILABLE:
            raise ImportError("PIL/Pillow not available. Install with: pip install Pillow")
        
        self._width = width
        self._height = height
        self._scale = scale
        # Create PIL image (RGB mode)
        self._image = Image.new("RGB", (width, height), (0, 0, 0))
        self._draw = ImageDraw.Draw(self._image)
    
    @property
    def width(self) -> int:
        return self._width
    
    @property
    def height(self) -> int:
        return self._height
    
    def clear(self) -> None:
        self._image = Image.new("RGB", (self._width, self._height), (0, 0, 0))
        self._draw = ImageDraw.Draw(self._image)
    
    def set_pixel(self, x: int, y: int, r: int, g: int, b: int) -> None:
        if 0 <= x < self._width and 0 <= y < self._height:
            self._image.putpixel((x, y), (r, g, b))
    
    def fill(self, r: int, g: int, b: int) -> None:
        self._image = Image.new("RGB", (self._width, self._height), (r, g, b))
        self._draw = ImageDraw.Draw(self._image)
    
    def save(self, filename: str) -> None:
        """
        Save canvas to PNG file (scaled up for visibility).
        
        Args:
            filename: Output filename (e.g., "test.png")
        """
        if self._scale > 1:
            # Scale up image for better visibility
            scaled = self._image.resize(
                (self._width * self._scale, self._height * self._scale),
                Image.NEAREST  # Nearest neighbor for pixel art look
            )
            scaled.save(filename)
        else:
            self._image.save(filename)
    
    def get_image(self):
        """Get the PIL Image object (for advanced usage)."""
        return self._image
    
    def draw_text(self, x: int, y: int, text: str, r: int, g: int, b: int, font_size: int = 10):
        """
        Draw text on the canvas using PIL.
        
        Args:
            x: X position
            y: Y position
            text: Text to draw
            r: Red component
            g: Green component
            b: Blue component
            font_size: Font size in pixels
        """
        try:
            # Try to use a default font
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
        except (OSError, IOError):
            try:
                # Fallback to default font
                font = ImageFont.load_default()
            except:
                font = None
        
        self._draw.text((x, y), text, fill=(r, g, b), font=font)

