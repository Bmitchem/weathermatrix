"""Diagnostic tools for debugging matrix display issues without visual access."""
import logging
from typing import Optional, List, Tuple
from matrix_canvas import FakeMatrixCanvas, MatrixCanvas


class DiagnosticCanvas(MatrixCanvas):
    """Canvas wrapper that logs all drawing operations for debugging."""
    
    def __init__(self, wrapped_canvas: MatrixCanvas):
        """
        Wrap a canvas to log all operations.
        
        Args:
            wrapped_canvas: The actual canvas to wrap
        """
        self._wrapped = wrapped_canvas
        self._operations: List[dict] = []
        self._pixel_log: List[Tuple[int, int, int, int, int]] = []  # (x, y, r, g, b)
    
    @property
    def width(self) -> int:
        return self._wrapped.width
    
    @property
    def height(self) -> int:
        return self._wrapped.height
    
    def clear(self) -> None:
        import time
        self._operations.append({"op": "clear", "timestamp": time.time()})
        logging.debug("DiagnosticCanvas: Clear() called")
        self._wrapped.clear()
    
    def set_pixel(self, x: int, y: int, r: int, g: int, b: int) -> None:
        self._pixel_log.append((x, y, r, g, b))
        if len(self._pixel_log) % 100 == 0:  # Log every 100th pixel to avoid spam
            logging.debug(f"DiagnosticCanvas: SetPixel({x}, {y}, {r}, {g}, {b}) - total pixels set: {len(self._pixel_log)}")
        self._wrapped.set_pixel(x, y, r, g, b)
    
    def fill(self, r: int, g: int, b: int) -> None:
        self._operations.append({"op": "fill", "r": r, "g": g, "b": b})
        logging.info(f"DiagnosticCanvas: Fill({r}, {g}, {b}) called")
        self._wrapped.fill(r, g, b)
    
    def get_operation_count(self) -> int:
        """Get total number of operations logged."""
        return len(self._operations)
    
    def get_pixel_count(self) -> int:
        """Get total number of pixels set."""
        return len(self._pixel_log)
    
    def get_recent_pixels(self, count: int = 50) -> List[Tuple[int, int, int, int, int]]:
        """Get the most recently set pixels."""
        return self._pixel_log[-count:]
    
    def get_pixel_summary(self) -> dict:
        """Get summary statistics about pixels set."""
        if not self._pixel_log:
            return {"total": 0, "unique_positions": 0, "color_range": None}
        
        unique_positions = len(set((x, y) for x, y, _, _, _ in self._pixel_log))
        all_r = [r for _, _, r, _, _ in self._pixel_log]
        all_g = [g for _, _, _, g, _ in self._pixel_log]
        all_b = [b for _, _, _, _, b in self._pixel_log]
        
        return {
            "total": len(self._pixel_log),
            "unique_positions": unique_positions,
            "color_range": {
                "r": (min(all_r), max(all_r)),
                "g": (min(all_g), max(all_g)),
                "b": (min(all_b), max(all_b))
            }
        }


def capture_frame_buffer_snapshot(canvas, filename: Optional[str] = None) -> dict:
    """
    Capture a snapshot of the current frame buffer state.
    
    Args:
        canvas: Canvas to capture (works with FakeMatrixCanvas)
        filename: Optional filename to save snapshot
        
    Returns:
        Dictionary with frame buffer information
    """
    snapshot = {
        "width": canvas.width,
        "height": canvas.height,
        "pixels": {}
    }
    
    if isinstance(canvas, FakeMatrixCanvas):
        # Capture all pixel values
        for y in range(canvas.height):
            for x in range(canvas.width):
                r, g, b = canvas.get_pixel(x, y)
                if r != 0 or g != 0 or b != 0:  # Only store non-black pixels
                    snapshot["pixels"][f"{x},{y}"] = (r, g, b)
        
        # Calculate statistics
        total_pixels = canvas.width * canvas.height
        non_black_pixels = len(snapshot["pixels"])
        snapshot["statistics"] = {
            "total_pixels": total_pixels,
            "non_black_pixels": non_black_pixels,
            "black_pixels": total_pixels - non_black_pixels,
            "fill_percentage": (non_black_pixels / total_pixels) * 100
        }
        
        if filename:
            # Save as text file
            with open(filename, 'w') as f:
                f.write(f"Frame Buffer Snapshot\n")
                f.write(f"Dimensions: {canvas.width}x{canvas.height}\n")
                f.write(f"Non-black pixels: {non_black_pixels}/{total_pixels}\n")
                f.write(f"Fill percentage: {snapshot['statistics']['fill_percentage']:.2f}%\n\n")
                f.write("Non-black pixels:\n")
                for pos, color in sorted(snapshot["pixels"].items()):
                    f.write(f"  {pos}: RGB{color}\n")
    
    return snapshot


def compare_frame_buffers(before: dict, after: dict) -> dict:
    """
    Compare two frame buffer snapshots to see what changed.
    
    Args:
        before: First snapshot
        after: Second snapshot
        
    Returns:
        Dictionary with comparison results
    """
    before_pixels = set(before.get("pixels", {}).keys())
    after_pixels = set(after.get("pixels", {}).keys())
    
    added = after_pixels - before_pixels
    removed = before_pixels - after_pixels
    changed = []
    
    common = before_pixels & after_pixels
    for pos in common:
        if before["pixels"][pos] != after["pixels"][pos]:
            changed.append(pos)
    
    return {
        "pixels_added": len(added),
        "pixels_removed": len(removed),
        "pixels_changed": len(changed),
        "added_positions": list(added)[:20],  # Limit output
        "removed_positions": list(removed)[:20],
        "changed_positions": changed[:20]
    }


def log_matrix_state(matrix, offscreen_canvas, frame_count: int):
    """
    Log comprehensive state information about the matrix and current frame.
    
    Args:
        matrix: RGBMatrix instance
        offscreen_canvas: Current offscreen canvas
        frame_count: Current frame number
    """
    logging.info(f"=== Matrix State (Frame {frame_count}) ===")
    logging.info(f"Matrix dimensions: {matrix.width}x{matrix.height}")
    
    if offscreen_canvas:
        logging.info(f"Offscreen canvas dimensions: {offscreen_canvas.width}x{offscreen_canvas.height}")
        logging.info(f"Offscreen canvas type: {type(offscreen_canvas)}")
        logging.info(f"Offscreen canvas brightness: {getattr(offscreen_canvas, 'brightness', 'N/A')}")
        logging.info(f"Offscreen canvas pwmBits: {getattr(offscreen_canvas, 'pwmBits', 'N/A')}")
    
    logging.info(f"Matrix brightness: {getattr(matrix, 'brightness', 'N/A')}")
    logging.info("=" * 50)


def create_diagnostic_report(
    canvas: MatrixCanvas,
    operations: List[dict],
    frame_count: int
) -> str:
    """
    Create a text report of diagnostic information.
    
    Args:
        canvas: Canvas to analyze
        operations: List of drawing operations
        frame_count: Current frame number
        
    Returns:
        Formatted diagnostic report string
    """
    report = []
    report.append("=" * 60)
    report.append(f"Diagnostic Report - Frame {frame_count}")
    report.append("=" * 60)
    report.append(f"Canvas: {canvas.width}x{canvas.height}")
    report.append(f"Total operations: {len(operations)}")
    
    if isinstance(canvas, FakeMatrixCanvas):
        snapshot = capture_frame_buffer_snapshot(canvas)
        stats = snapshot.get("statistics", {})
        report.append(f"Non-black pixels: {stats.get('non_black_pixels', 0)}")
        report.append(f"Fill percentage: {stats.get('fill_percentage', 0):.2f}%")
        
        # Show sample of non-black pixels
        pixels = snapshot.get("pixels", {})
        if pixels:
            report.append("\nSample non-black pixels:")
            for i, (pos, color) in enumerate(list(pixels.items())[:10]):
                report.append(f"  {pos}: RGB{color}")
    
    report.append("=" * 60)
    return "\n".join(report)

