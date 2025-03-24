import argparse
import csv
from pymmcore_plus import CMMCorePlus
from useq import MDASequence, TIntervalLoops

parser = argparse.ArgumentParser()
parser.add_argument("position_csv", help="CSV file containing X, Y, Z")
parser.add_argument("--nframes", type=int, metavar="N", default=1,
                    help="Number of frames to acquire at each position")
args = parser.parse_args()

# Create the core instance.
mmc = CMMCorePlus.instance()  
mmc.loadSystemConfiguration()  

with open(args.position_csv, newline="") as f:
    reader = csv.reader(f)
    xyzs = []
    for row in reader:
        xyz = tuple(float(v) for v in row)
        if len(xyz) != 3:
            raise ValueError(f"Position CSV rows must contain X, Y, Z; found: {row}")
        xyzs.append(xyz)


# Create a super-simple sequence, with one event
mda_sequence = MDASequence(
    stage_positions=xyzs,
    time_plan=TIntervalLoops(interval=0, loops=args.nframes),
    axis_order="pt",
)

# Run it!
try:
    mmc.run_mda(mda_sequence)
finally:
    mmc.setShutterOpen(False)