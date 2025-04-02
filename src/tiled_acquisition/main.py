import argparse
import csv
import os
import time
import numpy as np
from pymmcore_plus import CMMCorePlus
from pymmcore_plus.mda import MDAEngine
from useq import MDAEvent, MDASequence, TIntervalLoops


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("position_csv", help="CSV file containing X, Y, Z")
    parser.add_argument(
        "--frames",
        type=int,
        metavar="N",
        default=1,
        help="Number of frames to acquire at each position",
    )
    parser.add_argument(
        "--config", help="Micro-Manager hardware config file; default is Demo"
    )
    parser.add_argument(
        "--eom",
        type=float,
        metavar="V",
        default=0.0,
        help="Pockels Cell control voltage",
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
    return parser.parse_args()


def setup_hardware(args):
    # Set working directory to MICROMANAGER_PATH while loading devices so that
    # OpenScan can find its device modules.
    if "MICROMANAGER_PATH" not in os.environ:
        raise RuntimeError("Environment variable MICROMANAGER_PATH must be set")
    save_cwd = os.getcwd()
    os.chdir(os.environ["MICROMANAGER_PATH"])

    mmc = CMMCorePlus.instance()
    mmc.enableDebugLog(True)
    if args.config:
        mmc.loadSystemConfiguration(args.config)
    else:
        mmc.loadSystemConfiguration()

    os.chdir(save_cwd)

    if args.config:
        mmc.setConfig("Channels", "PhotonCounting Only")
        mmc.setConfig("FilterWheel", "457-50")
        mmc.setConfig("Lens", "20X 0.75 Nikon")
        mmc.setConfig("Resolution (pixels)", str(args.resolution))
        mmc.setProperty("NIDAQAO-Dev2/ao1", "Voltage", args.eom)
        mmc.setProperty("DCCModule2", "C3_GainHV", args.pmtgain)
        if args.no_sync_check:
            mmc.setConfig("FLIMCheckSync", "No")

    return mmc


def unaccumulate_images(images):
    return np.diff(images, axis=0, prepend=[np.zeros_like(images[0])])


def looks_like_pmt_shut_off(image):
    checked_portion = np.ravel(image)[-16384:]
    return np.all(checked_portion == 0)


def reset_pmt():
    pass  # TODO


def read_poslist(filename):
    with open(filename, newline="") as f:
        reader = csv.reader(f)
        xyzs = []
        for row in reader:
            xyz = tuple(float(v) for v in row)
            if len(xyz) != 3:
                raise ValueError(
                    f"Position CSV rows must contain X, Y, Z; found: {row}"
                )
            xyzs.append(xyz)
    return xyzs


# Custom acquisition engine to add PMT overload checking
class PMTCheckingEngine(MDAEngine):
    def exec_event(self, event: MDAEvent):
        # TODO Set FLIM filename
        result = super().exec_event(event)
        result = list(result)  # Originally a generator

        for image in unaccumulate_images([p.image for p in result]):
            if looks_like_pmt_shut_off(image):
                event = result[0].event
                print(
                    f"Resetting PMT at position {event.index['p']} at (x, y) = ({event.x_pos}, {event.y_pos})"
                )
                reset_pmt()
                break

        return result


def main():
    args = parse_args()

    mmc = setup_hardware(args)

    xyzs = read_poslist(args.position_csv)

    mda_sequence = MDASequence(
        stage_positions=xyzs,
        time_plan=TIntervalLoops(interval=0, loops=args.frames),
        axis_order="pt",
    )

    mmc.mda.set_engine(PMTCheckingEngine(mmc))
    mmc.mda.engine.use_hardware_sequencing = True

    try:
        if args.config:
            mmc.setConfig("PMT Power (HV)", "On")
        time.sleep(5.0)
        thd = mmc.run_mda(mda_sequence)
        thd.join()
    finally:
        print("Shutting down...")
        if args.config:
            mmc.setConfig("PMT Power (HV)", "Off")
        mmc.setShutterOpen(False)
