import argparse
import csv
import json
import numpy as np


def get_pos_array(poslist):
    return poslist["map"]["StagePositions"]["array"]


def get_xy_stage(poslist):
    return get_uniform_value(get_pos_array(poslist), lambda p: p["DefaultXYStage"]["scalar"])


def get_z_stage(poslist, allow_blank=False):
    return get_uniform_value(
        get_pos_array(poslist),
        lambda p: p["DefaultZStage"]["scalar"],
        blank_value="" if allow_blank else None,
    )


def get_uniform_value(array, value_getter, blank_value=None):
    values = set(value_getter(v) for v in array)
    if len(values) == 1:
        return tuple(values)[0]
    if blank_value is not None and len(values) == 2 and blank_value in values:
        values.remove(blank_value)
        return tuple(values)[0]
    raise ValueError(f"Non-uniform value: {list(values)}")


def find_xy_coord_of_pos(p, xy_stage):
    devposs = p["DevicePositions"]["array"]
    for devpos in devposs:
        if devpos["Device"]["scalar"] == xy_stage:
            xy = devpos["Position_um"]["array"]
            if len(xy) != 2:
                raise ValueError("XY position not 2D")
            return xy
    raise ValueError("Missing xy")


def find_z_coord_of_pos(p, z_stage, create_if_missing=False):
    devposs = p["DevicePositions"]["array"]
    for devpos in devposs:
        if devpos["Device"]["scalar"] == z_stage:
            z = devpos["Position_um"]["array"]
            if len(z) != 1:
                raise ValueError("Z position not scalar")
            return z
    if create_if_missing:
        devposs.append(
            {
                "Device": {"type": "STRING", "scalar": z_stage},
                "Position_um": {"type": "DOUBLE", "array": [None]},
            }
        )
        return devposs[-1]["Position_um"]["array"]
    raise ValueError("Missing z")


def get_xy_positions(poslist, xy_stage):
    ps = get_pos_array(poslist)
    coords = []
    for p in ps:
        xy = find_xy_coord_of_pos(p, xy_stage)
        coords.append((xy[0], xy[1]))
    return np.array(coords)


def get_xyz_positions(poslist, xy_stage, z_stage):
    ps = get_pos_array(poslist)
    coords = []
    for p in ps:
        try:
            xy, z = find_xy_coord_of_pos(p, xy_stage), find_z_coord_of_pos(p, z_stage)
        except ValueError as e:
            continue
        coords.append((xy[0], xy[1], z[0]))
    return np.array(coords)


def overwrite_pos_z_stage(p, z_stage):
    p["DefaultZStage"]["scalar"] = z_stage


def overwrite_z_coords(poslist, z_stage, z_coords):
    ps = get_pos_array(poslist)
    if len(z_coords) != len(ps):
        raise ValueError("Length mismatch")
    for p, new_z in zip(ps, z_coords):
        overwrite_pos_z_stage(p, z_stage)
        find_z_coord_of_pos(p, z_stage, create_if_missing=True)[0] = new_z


def check_safe_z_range(z_coords, z_min, z_max):
    if any(z < z_min or z > z_max for z in z_coords):
        raise ValueError(f"Z out of safe range of {z_min} to {z_max}")


def main():
    parser = argparse.ArgumentParser(
        description="Interpolate Z coordinates in a Micro-Manager position list"
    )
    parser.add_argument("input_filename")
    parser.add_argument("output_filename")
    parser.add_argument("--zmin", type=float, metavar="MICRONS", required=True)
    parser.add_argument("--zmax", type=float, metavar="MICRONS", required=True)
    parser.add_argument(
        "--csv", action="store_true", help="Write a CSV file instead of a position list"
    )
    args = parser.parse_args()

    z_min, z_max = args.zmin, args.zmax
    if z_min > z_max:
        raise ValueError(f"Invalid safe z range: {z_min} to {z_max}")

    with open(args.input_filename) as f:
        poslist = json.load(f)

    xy_stage = get_xy_stage(poslist)
    z_stage = get_z_stage(poslist, allow_blank=True)

    all_xys = get_xy_positions(poslist, xy_stage)
    xyzs = get_xyz_positions(poslist, xy_stage, z_stage)

    print("number of positions:", len(all_xys))
    print("number of positions with Z:", len(xyzs))

    x = xyzs[:, 0]
    y = xyzs[:, 1]
    z = xyzs[:, 2]

    A = np.column_stack((x, y, np.ones(len(x))))
    print("A:", A)
    print("z:", z)
    # Solve for the plane coefficients (a, b, c)
    coeffs, residuals, rank, s = np.linalg.lstsq(A, z)
    a, b, c = coeffs
    print("coefficients:", coeffs)
    print("residuals:", residuals)
    print("rank:", rank)
    print("s:", s)
    print()

    new_z = a * all_xys[:, 0] + b * all_xys[:, 1] + c
    print("Computed Zs:", new_z)
    print(f"Z range: {new_z.min()} to {new_z.max()}")

    check_safe_z_range(new_z, z_min, z_max)
    overwrite_z_coords(poslist, z_stage, new_z)

    if args.csv:
        with open(args.output_filename, "w", newline="") as f:
            xyzs = get_xyz_positions(poslist, xy_stage, z_stage)
            writer = csv.writer(f)
            for row in xyzs:
                writer.writerow(row)
    else:
        with open(args.output_filename, "w") as f:
            json.dump(poslist, f, indent=2)


if __name__ == "__main__":
    main()
