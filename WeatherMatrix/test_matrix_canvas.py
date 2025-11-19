"""Tests for matrix canvas abstraction."""
import pytest
from matrix_canvas import FakeMatrixCanvas, MatrixCanvas


def test_fake_canvas_creation():
    """Test creating fake canvas."""
    canvas = FakeMatrixCanvas(width=64, height=32)
    
    assert canvas.width == 64
    assert canvas.height == 32


def test_fake_canvas_set_pixel():
    """Test setting pixels on fake canvas."""
    canvas = FakeMatrixCanvas(width=64, height=32)
    
    canvas.set_pixel(10, 5, 255, 128, 64)
    
    pixel = canvas.get_pixel(10, 5)
    assert pixel == (255, 128, 64)


def test_fake_canvas_clear():
    """Test clearing fake canvas."""
    canvas = FakeMatrixCanvas(width=64, height=32)
    
    # Set some pixels
    canvas.set_pixel(10, 5, 255, 255, 255)
    canvas.set_pixel(20, 15, 128, 128, 128)
    
    # Clear
    canvas.clear()
    
    # All pixels should be black
    assert canvas.get_pixel(10, 5) == (0, 0, 0)
    assert canvas.get_pixel(20, 15) == (0, 0, 0)


def test_fake_canvas_fill():
    """Test filling fake canvas."""
    canvas = FakeMatrixCanvas(width=64, height=32)
    
    canvas.fill(100, 150, 200)
    
    # All pixels should be the fill color
    assert canvas.get_pixel(0, 0) == (100, 150, 200)
    assert canvas.get_pixel(63, 31) == (100, 150, 200)
    assert canvas.get_pixel(32, 16) == (100, 150, 200)


def test_fake_canvas_bounds():
    """Test that fake canvas respects bounds."""
    canvas = FakeMatrixCanvas(width=64, height=32)
    
    # Set pixel out of bounds
    canvas.set_pixel(100, 100, 255, 255, 255)
    
    # Should return black (default)
    assert canvas.get_pixel(100, 100) == (0, 0, 0)


def test_fake_canvas_to_ascii():
    """Test ASCII representation."""
    canvas = FakeMatrixCanvas(width=10, height=5)
    
    # Fill with white
    canvas.fill(255, 255, 255)
    
    ascii_repr = canvas.to_ascii()
    lines = ascii_repr.split("\n")
    
    assert len(lines) == 5
    # Should have some non-space characters (bright pixels)
    assert any(char != " " for line in lines for char in line)


def test_fake_canvas_to_ascii_black():
    """Test ASCII representation of black canvas."""
    canvas = FakeMatrixCanvas(width=10, height=5)
    
    # Canvas is already black
    ascii_repr = canvas.to_ascii()
    lines = ascii_repr.split("\n")
    
    assert len(lines) == 5
    # Should be mostly spaces or darkest character
    assert all(char in " ." for line in lines for char in line)

