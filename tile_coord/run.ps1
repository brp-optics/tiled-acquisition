$zmin = 10494-5
$zmax = 10494+5
$input_file = "D:\UserData\HelenWilson\20250814_HDIM\hdim_trial2\thirteenbeads_coverslip_water\locations_hdim_beads.pos"
$output_file = "D:\UserData\HelenWilson\20250814_HDIM\hdim_trial2\thirteenbeads_coverslip_water\locations_hdim_beads.csv"

python interpolate-z-coords.py `
  --zmin $zmin `
  --zmax $zmax `
  --csv `
  $input_file `
  $output_file



# usage: interpolate-z-coords.py [-h] --zmin MICRONS --zmax MICRONS [--csv] input_filename output_filename
# interpolate-z-coords.py: error: the following arguments are required: input_filename, output_filename, --zmin, --zmax
