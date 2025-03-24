import argparse
import csv
import time
from pymmcore_plus import CMMCorePlus
from pymmcore_plus.mda import MDAEngine
from useq import MDAEvent, MDASequence, TIntervalLoops

parser = argparse.ArgumentParser()
parser.add_argument("position_csv", help="CSV file containing X, Y, Z")
parser.add_argument(
    "--nframes",
    type=int,
    metavar="N",
    default=1,
    help="Number of frames to acquire at each position",
)
parser.add_argument(
    "--config", help="Micro-Manager hardware config file; default is Demo"
)
parser.add_argument(
    "--eom", type=float, metavar="V", default=0.0, help="Pockels Cell control voltage"
)
parser.add_argument(
    "--pmtgain",
    type=float,
    metavar="PERCENT",
    default=70.0,
    help="PMT gain setting for DCC",
)
parser.add_argument(
    "--resolution",
    type=int,
    metavar="PIXELS",
    default=256,
    choices=(256, 512, 1024),
    help="Scan resolution",
)
parser.add_argument(
    "--no-sync-check", action="store_true", help="Disable check for SYNC signal"
)
args = parser.parse_args()

# Create the core instance.
mmc = CMMCorePlus.instance()
mmc.enableDebugLog(True)
if args.config:
    print("Loading config...")
    input("Press enter")
    mmc.loadSystemConfiguration(args.config)
    print("Loaded config")
else:
    mmc.loadSystemConfiguration()

if args.config:
    mmc.setConfig("Chennels", "PhotonCounting Only")
    mmc.setConfig("FilterWheel", "457-50")
    mmc.setConfig("Lens", "20X 0.75 Nikon")
    mmc.setConfig("Resolution (pixels)", args.resolution)
    mmc.setConfig("Pockels Cell (V)", args.eom)
    mmc.setConfig("PMT Gain (HV)", args.pmtgain)
    if args.no_sync_check:
        mmc.setConfig("FLIMCheckSync", "No")

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


# Custom acquisition engine to add PMT overload checking
class PMTCheckingEngine(MDAEngine):
    def exec_event(self, event: MDAEvent):
        # TODO Set FLIM filename
        result = super().exec_event(event)
        # TODO Check result image and detect overload
        return result


mmc.mda.set_engine(PMTCheckingEngine(mmc))
mmc.mda.engine.use_hardware_sequencing = True

# Run it!
try:
    if args.config:
        mmc.setConfig("PMT Power (HV)", "On")
    time.sleep(5.0)
    mmc.run_mda(mda_sequence)
finally:
    if args.config:
        mmc.setConfig("PMT Power (HV)", "Off")
    mmc.setShutterOpen(False)
