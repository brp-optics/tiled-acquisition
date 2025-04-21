$frames = 90
$config = "C:\Users\lociuser\code\loci-microscopes\MMConfigs\SLIM\OpenScan-DualDet-PMTControl.cfg"
$coords = "D:\UserData\HelenWilson\tile-coords\nras_1tissue_zcalc_0421_contd.csv"
$eom = 0.0
$pmtgain = 70
$resolution = 256
$save_path = "D:\UserData\HelenWilson\20250417_bigfovMN_slim\MN_nras_1tissue_0421_contd"

uv run tiled_acquisition `
  --frames $frames `
  --config $config `
  $coords `
  --eom $eom `
  --pmtgain $pmtgain `
  --resolution $resolution `
  --save $save_path
