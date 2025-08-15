import argparse
import pandas as pd
import pathlib
import time
from rich.progress import Progress
import humanize
from rich import print as pprint
import datetime

def _get_number_of_files(folder, get_files=False):
    if get_files:
        return list(pathlib.Path(folder).glob('*.sdt'))
    else:
        return len(list(pathlib.Path(folder).glob('*.sdt')))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("folder")
    parser.add_argument("csvfile")
    parser.add_argument('frames')
    args = parser.parse_args()

    df = pd.read_csv(args.csvfile)
    total = len(df)
    count = _get_number_of_files(args.folder)
    files = _get_number_of_files(args.folder,True)
    oldest_file = min(files, key=lambda f: f.stat().st_ctime)    
    start_time = datetime.datetime.fromtimestamp(oldest_file.stat().st_ctime)
    start_str = start_time.strftime("%A, %B %d, %Y at %I:%M %p").lstrip("0")

    eta_per_frame = 105 #sec with saving time
    remaining = total - count
    eta_seconds = remaining * eta_per_frame

    now = datetime.datetime.now()
    now_str = now.strftime("%A, %B %d, %Y at %I:%M %p").lstrip("0")
    eta_str = f"{humanize.naturaldelta(eta_seconds)}"
    end_time = datetime.datetime.now() + datetime.timedelta(seconds=eta_seconds)
    end_str = f"{humanize.naturaldate(end_time)} at {end_time.strftime('%H:%M:%S')}"
    pprint(f"Current Time     : [blue]{now_str}[/blue]")
    pprint(f"Imaging Started  : [cyan]{start_str}[/cyan]")
    pprint(f"Run Estimate     : [bold green]{eta_str}[/bold green]")
    pprint(f"Finish Time      : [bold yellow]{end_str}[/bold yellow]")

    with Progress() as progress:
        task = progress.add_task("Waiting for files...", total=total)
        while True:
            count = _get_number_of_files(args.folder)
            progress.update(task, completed=count)
            if count >= total:
                break
            time.sleep(int(args.frames))

if __name__ == "__main__":
    main()
