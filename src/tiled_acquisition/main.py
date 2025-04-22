import argparse
import csv
import os
from pathlib import Path
import sys
import time
import numpy as np
from pymmcore_plus import CMMCorePlus
from pymmcore_plus.mda import MDAEngine
from pyometiff import OMETIFFWriter
from useq import MDAEvent, MDASequence, TIntervalLoops


def parse_args():
    parser = argparse.ArgumentParser(fromfile_prefix_chars="@")
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
    parser.add_argument("--save", metavar="DIRNAME", help="Destination to save images")
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
        mmc.setProperty(
            "OSc-LSM",
            "BH-TCSPC-FLIMFileSaving",
            ("Yes" if args.save is not None else "No"),
        )

    return mmc


def unaccumulate_images(images):
    return np.diff(images, axis=0, prepend=[np.zeros_like(images[0])])


def looks_like_pmt_shut_off(image):
    checked_portion = np.ravel(image)[-16384:]
    return np.all(checked_portion == 0)


def reset_pmt(args, mmc):
    if args.config:
        mmc.setConfig("PMT Power (HV)", "Off")
        mmc.setProperty("DCCModule2", "ClearOverloads", "Clear")
        time.sleep(0.1)
        mmc.setConfig("PMT Power (HV)", "On")
        time.sleep(5.0)


def make_sdt_prefix(args, number):
    return f"{args.save}/pos_{number:04d}"


def set_sdt_filename(mmc, prefix):
    mmc.setProperty("OSc-LSM", "BH-TCSPC-FLIMFileNamePrefix", prefix)
    
def create_tile_config(args,prefix,coords):

    filename = f"{prefix}"
    #print(f"filename: {filename.split("/")[1]}")
    #print(f"this is x y:{coords[0][1].x_pos} and {coords[0][1].y_pos}")
    tile_config_row = (f"{filename.split("/")[-1]}.tif; ; ({coords[0][1].x_pos},{coords[0][1].y_pos})")
    #print(tile_config_row)
    write_tile_config(args, tile_config_row,filename.split("/")[-1])
    return

def write_tile_config(args,tile_config_row,position):
    
    # FIXME: @Helen
    # - move this before acquisition
    # but need coords info from result for stage?

    if Path(f"{args.save}/tile_config.txt").exists() and position=='pos_0000':
        raise RuntimeError("Tile config file already exists")

    with open(f"{args.save}/tile_config.txt","a") as text_file:
        text_file.write(tile_config_row+ "\n")

def rename_sdt_files(args, prefix):
    if args.save is None:
        return
    extensions = ("spc", "sdt", "json")
    for ext in extensions:
        original = f"{prefix}_0000.{ext}"
        renamed = f"{prefix}.{ext}"
        os.rename(original, renamed)

#@Helen tiff save needs updating
def save_tiff_image_test(file,values):
    imvalues = []
    imgarray = [np.array(p.image) for p in values]
    imvalues = np.stack(imgarray)
    
    imvalues = np.array(imvalues)
    #print(f"this is imvalues: {imvalues.shape}")
    
    metadata_dict = {
        "PhysicalSizeX" : "0.7", #update
        "PhysicalSizeXUnit" : "µm",
        "PhysicalSizeY" : "0.7",    #update
        "PhysicalSizeYUnit" : "µm",
        "PhysicalSizeZ" : "0.0",
        "PhysicalSizeZUnit" : "µm",
        "Channels" : {
            "FLIM" : {
                "Name" : "FLIM740",
                "SamplesPerPixel": 90,
                "ExcitationWavelength": 740,
                "ExcitationWavelengthUnit": "nm"
            },
        }
    }

    # our data in npy format
    npy_array_data = np.uint8(imvalues)
    # a string describing the dimension ordering
    dimension_order = "TYX"
    
    writer = OMETIFFWriter(
        fpath=f"E:\\Code\\MM_bigfovacqusition\\tiffimages\\{file.split("/")[-1]}.tif",
        dimension_order=dimension_order,
        array=npy_array_data,
        metadata=metadata_dict,
        explicit_tiffdata=False)

    writer.write()

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
    def __init__(self, mmc, args):
        super().__init__(mmc)
        self.__args = args
        self.__event_counter = 0

    def exec_event(self, event: MDAEvent):
        sdt_prefix = make_sdt_prefix(self.__args, self.__event_counter)
        self.__event_counter += 1

        set_sdt_filename(self.mmcore, sdt_prefix)

        result = super().exec_event(event)
        result = list(result)  # Originally a generator

        rename_sdt_files(self.__args, sdt_prefix)
        create_tile_config(args, sdt_prefix,result)

        save_tiff_image_test(sdt_prefix,result)

        for image in unaccumulate_images([p.image for p in result]):
            if looks_like_pmt_shut_off(image):
                event = result[0].event
                print(
                    f"Resetting PMT at position {event.index['p']} at (x, y) = ({event.x_pos}, {event.y_pos})",
                    file=sys.stderr,
                )
                reset_pmt(self.__args, self.mmcore)
                break

        return result


def main():
    args = parse_args()

    if args.save is not None and Path(args.save).exists():
        print(f"The save directory {args.save} already exists", file=sys.stderr)
        sys.exit(1)
    if args.save is not None:
        os.mkdir(args.save)

    mmc = setup_hardware(args)

    xyzs = read_poslist(args.position_csv)

    mda_sequence = MDASequence(
        stage_positions=xyzs,
        time_plan=TIntervalLoops(interval=0, loops=args.frames),
        axis_order="pt",
    )

    mmc.mda.set_engine(PMTCheckingEngine(mmc, args))
    mmc.mda.engine.use_hardware_sequencing = True

    try:
        if args.config:
            mmc.setConfig("PMT Power (HV)", "On")
        time.sleep(5.0)
        thd = mmc.run_mda(mda_sequence)
        while thd.is_alive():
            try:
                thd.join(timeout=0.1)
            except:
                print("Canceling MDA due to exception", file=sys.stderr)
                mmc.mda.cancel()
                thd.join()
                raise
    finally:
        print("Shutting down...", file=sys.stderr)
        if args.config:
            mmc.setConfig("PMT Power (HV)", "Off")
        mmc.setShutterOpen(False)
