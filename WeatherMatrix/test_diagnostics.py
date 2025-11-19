"""Test script to verify diagnostic tools work correctly."""
import logging
from matrix_canvas import FakeMatrixCanvas
from matrix_diagnostics import DiagnosticCanvas, capture_frame_buffer_snapshot, create_diagnostic_report

logging.basicConfig(level=logging.DEBUG)

# Create a fake canvas and wrap it with diagnostics
fake_canvas = FakeMatrixCanvas(128, 32)
diag_canvas = DiagnosticCanvas(fake_canvas)

# Perform some operations
diag_canvas.fill(255, 0, 0)  # Red fill
diag_canvas.set_pixel(64, 16, 0, 255, 0)  # Green pixel in center
diag_canvas.set_pixel(65, 16, 0, 255, 0)
diag_canvas.set_pixel(66, 16, 0, 255, 0)

# Capture snapshot
snapshot = capture_frame_buffer_snapshot(fake_canvas, "test_snapshot.txt")
print("\nSnapshot statistics:")
print(f"  Non-black pixels: {snapshot['statistics']['non_black_pixels']}")
print(f"  Fill percentage: {snapshot['statistics']['fill_percentage']:.2f}%")

# Create diagnostic report
report = create_diagnostic_report(diag_canvas, diag_canvas._operations, 1)
print("\nDiagnostic Report:")
print(report)

# Check pixel summary
summary = diag_canvas.get_pixel_summary()
print("\nPixel Summary:")
print(f"  Total pixels set: {summary['total']}")
print(f"  Unique positions: {summary['unique_positions']}")
print(f"  Color range: {summary['color_range']}")

print("\n✓ Diagnostic tools test complete!")

