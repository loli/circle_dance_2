import sys

from note_dancer.visualization.base.receiver import AudioReceiver


def run():
    """Command-Line Audio Visualization using the AudioReceiver."""

    # Initialize the receiver from your new class
    rx = AudioReceiver(ip="127.0.0.1", port=5005)
    rx.bind()

    print("\n" + "=" * 60)
    print(" AUDIO ANALYZER CLI VISUALIZER ".center(60, "="))
    print("=" * 60 + "\n")

    try:
        while True:
            # Blocks until the next 76-byte packet arrives
            data = rx.wait_for_packet()

            if not data:
                continue

            # 1. Handle the Beat Trigger
            beat_marker = "[ BEAT ]" if data["is_beat"] > 0.5 else "        "

            # 2. Create Band Bars (L/M/H)
            # We scale the 0.0-1.0 value to a 10-character bar
            def make_bar(val):
                length = int(val * 10)
                return "[" + "#" * length + "-" * (10 - length) + "]"

            low_bar = make_bar(data["low"])
            mid_bar = make_bar(data["mid"])
            high_bar = make_bar(data["high"])

            # 3. Create Chroma (Notes) Visualization
            # Thresholding at 0.4 to keep the display clean
            chroma_viz = "".join(["#" if v > 0.4 else "." for v in data["notes"]])

            # 4. Format Output String
            # \r  = Go to start of line
            # \033[K = Clear everything from cursor to the right (ANSI Escape)
            output = (
                f"\r{beat_marker} | "
                f"BPM: {data['bpm']:>5.1f} | "
                f"L:{low_bar} M:{mid_bar} H:{high_bar} | "
                f"Flux: {data['flux']:>4.1f} | "
                f"Notes: [{chroma_viz}]\033[K"
            )

            sys.stdout.write(output)
            sys.stdout.flush()

            # Write to stdout and flush immediately for a smooth "live" feel
            sys.stdout.write("\r" + output)
            sys.stdout.flush()

    except KeyboardInterrupt:
        print("\n\nVisualizer stopped by user.")
    finally:
        rx.close()


if __name__ == "__main__":
    run()
