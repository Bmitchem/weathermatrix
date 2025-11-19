"""Minimal hardware diagnostic for the RGB matrix."""
import argparse
import time
import logging

from dotenv import load_dotenv

try:
    from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics
except ImportError as exc:  # pragma: no cover
    raise SystemExit("rgbmatrix not installed on this host") from exc


def parse_args():
    parser = argparse.ArgumentParser("Hardware diagnostic for RGB matrix")
    parser.add_argument("--led-rows", type=int, default=32)
    parser.add_argument("--led-cols", type=int, default=64)
    parser.add_argument("--led-chain", type=int, default=1)
    parser.add_argument("--led-parallel", type=int, default=1)
    parser.add_argument("--led-slowdown-gpio", type=int, default=2)
    parser.add_argument("--brightness", type=int, default=80)
    parser.add_argument("--font", default="fonts/7x13.bdf")
    parser.add_argument("--duration", type=int, default=30)
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def init_matrix(args):
    options = RGBMatrixOptions()
    options.rows = args.led_rows
    options.cols = args.led_cols
    options.chain_length = args.led_chain
    options.parallel = args.led_parallel
    options.gpio_slowdown = args.led_slowdown_gpio
    options.brightness = args.brightness
    return RGBMatrix(options=options)


def load_font(path):
    font = graphics.Font()
    font.LoadFont(path)
    return font


def main():
    args = parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)
    matrix = init_matrix(args)
    font = load_font(args.font)

    logging.info("Test 1: filling screen red for 2 seconds")
    matrix.Fill(255, 0, 0)
    time.sleep(2)

    logging.info("Test 2: filling screen green for 2 seconds")
    matrix.Fill(0, 255, 0)
    time.sleep(2)

    logging.info("Test 3: drawing white grid")
    matrix.Clear()
    color = graphics.Color(255, 255, 255)
    for x in range(0, args.led_cols * args.led_chain, 4):
        matrix.SetPixel(x, 0, 255, 255, 255)
        matrix.SetPixel(x, args.led_rows - 1, 255, 255, 255)
    for y in range(0, args.led_rows, 4):
        matrix.SetPixel(0, y, 255, 255, 255)
        matrix.SetPixel(args.led_cols * args.led_chain - 1, y, 255, 255, 255)
    time.sleep(2)

    logging.info("Test 4: drawing text sample")
    matrix.Clear()
    messages = [
        "RGB MATRIX DIAG",
        f"rows={args.led_rows} cols={args.led_cols}",
        f"chain={args.led_chain} parallel={args.led_parallel}",
        time.strftime("%H:%M:%S"),
    ]
    y = font.baseline
    for msg in messages:
        graphics.DrawText(matrix, font, 2, y, color, msg)
        y += font.height + 2
    time.sleep(args.duration)

    matrix.Clear()
    logging.info("Diagnostics complete")


if __name__ == "__main__":
    load_dotenv()
    main()
