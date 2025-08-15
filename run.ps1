$frames = 90
$config = "C:\Users\lociuser\code\loci-microscopes\MMConfigs\SLIM\OpenScan-DualDet-PMTControl.cfg"
$coords = "D:\UserData\HelenWilson\20250814_HDIM\hdim_trial2\thirteenbeads_coverslip_water\locations_hdim_beads.csv"
$eom = 0.3
$pmtgain = 80
$resolution = 256
$save_path = "D:\UserData\HelenWilson\20250814_HDIM\hdim_trial2\thirteenbeads_coverslip_water\data"

uv run tiled_acquisition `
  --frames $frames `
  --config $config `
  $coords `
  --eom $eom `
  --pmtgain $pmtgain `
  --resolution $resolution `
  --save $save_path
