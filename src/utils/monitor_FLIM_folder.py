import time
import pathlib
from zulip_channel_updator import warn_zulip_user

total_images=1870
time_per_image = 90 #sec
sleep_time = time_per_image * 1.5  # sec

folder = r'D:\UserData\HelenWilson\20250417_bigfovMN_slim\MN_nras_1tissue_0417'

def _get_number_of_files(folder=folder):
    return len(list(pathlib.Path(folder).glob('*.sdt')))

message = f"monitoring {folder}"
warn_zulip_user(message)

for i in range(90*total_images):

    nfiles = _get_number_of_files()
    time.sleep(sleep_time)
    nfiles_now = _get_number_of_files()
    print(nfiles,nfiles_now)
    if nfiles_now>nfiles:
        pass
    else:
        percent_completion = nfiles_now*100.0/(total_images)
        message = f"NO NEW FILES at {nfiles_now} completed {percent_completion:.2f}%"
        warn_zulip_user(message)

message = "done monitoring"
warn_zulip_user(message)
