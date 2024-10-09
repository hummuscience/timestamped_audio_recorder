import sounddevice as sd
import soundfile as sf
from datetime import datetime, timezone
import argparse
import sys
from pathlib import Path
import queue
import time

# Function to convert datetime to formatted string
def dt_to_str(dt):
    """Converts a datetime object to a formatted string."""
    isoformat = "%Y-%m-%dT%H_%M_%S"
    dt_str = dt.strftime(isoformat)
    if dt.microsecond != 0:
        dt_str += ".{:06d}".format(dt.microsecond)
    if dt.tzinfo is not None and dt.utcoffset().total_seconds() == 0:
        dt_str += "Z"
    return dt_str

# Function to generate timestamped filename
def get_timestamped_filename(prefix, output_dir, use_utc=False):
    if use_utc:
        now = datetime.now(timezone.utc)
    else:
        now = datetime.now()
    timestamp_str = dt_to_str(now)
    filename = f"{prefix}_{timestamp_str}.wav"
    return output_dir / filename

# Callback function for streaming audio data
def audio_callback(indata, frames, time, status):
    if status:
        print(status, file=sys.stderr)
    q.put(indata.copy())

# Main function
def main():
    parser = argparse.ArgumentParser(description="Continuous Audio Recording Script")
    parser.add_argument('-d', '--duration', type=float, default=60, help='Duration of each recording chunk in seconds')
    parser.add_argument('-t', '--total-duration', type=float, help='Total duration of recording in seconds (default: runs indefinitely until cancelled)')
    parser.add_argument('-r', '--samplerate', type=int, default=44100, help='Sampling rate in Hz')
    parser.add_argument('-c', '--channels', type=int, default=2, help='Number of audio channels')
    parser.add_argument('--device', type=int, help='Device index for recording')
    parser.add_argument('--print-devices', action='store_true', help='Print list of audio devices and exit')
    parser.add_argument('--prefix', type=str, default='audio_recording', help='Custom prefix for the filename')
    parser.add_argument('--use-utc', action='store_true', help='Use UTC time for the filename timestamp (default is local time)')
    parser.add_argument('--output-dir', type=str, default='.', help='Output directory for the recording files')
    args = parser.parse_args()

    if args.print_devices:
        print("Available audio devices:")
        print(sd.query_devices())
        sys.exit(0)

    # Create output directory if it doesn't exist
    output_dir = Path(args.output_dir)
    if not output_dir.exists():
        output_dir.mkdir(parents=True, exist_ok=True)

    global q
    q = queue.Queue()

    try:
        with sd.InputStream(samplerate=args.samplerate, device=args.device,
                            channels=args.channels, callback=audio_callback):
            print('#' * 80)
            print('Recording... Press Ctrl+C to stop the recording.')
            print('#' * 80)

            start_time = time.time()
            elapsed_time = 0

            while True:
                print(f"Recording audio chunk for {args.duration} seconds...")
                if args.total_duration and elapsed_time >= args.total_duration:
                    print("Total recording duration reached. Exiting.")
                    break

                # Create a new chunk file
                filename = get_timestamped_filename(args.prefix, output_dir, use_utc=args.use_utc)

                # Write chunks for the specified duration
                with sf.SoundFile(filename, mode='x', samplerate=args.samplerate,
                                  channels=args.channels, subtype='PCM_16') as file:
                    chunk_start_time = time.time()
                    while time.time() - chunk_start_time < args.duration:
                        file.write(q.get())

                elapsed_time = time.time() - start_time

    except KeyboardInterrupt:
        print("\nRecording interrupted by user. Exiting.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
