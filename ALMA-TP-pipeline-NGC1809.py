#----------------------------------
# Defining paths and files
#-------------------------------

path_galaxy = "tmp/2017.1.00886.L/science_goal.uid___A001_X1284_X283b/group.uid___A001_X1284_X283c/member.uid___A001_X1284_X2843/"
flag_file   = "fileflagIC_1809.py"             # File containing additional flags 

#----------------------------------
# Parameters for data reduction:
#-------------------------------

doplots    = True                               # Do non-interactive. additional plots (plots will be saved in "calibration/plots" folder)
bl_order   = 1                                  # Order for the baseline fitting

source     = 'NGC1809'                          # Source name
freq_rest  =  230538.                           # Rest frequency of requested line in MHz (ex: "freq_rest  = 230538" for CO(2-1))
vel_cube   = '0~2500'                           # Range in velocity in km/s to extract the line cube.
vel_line   = '0~900;1100~1500;1700~2500'                        # Range in velocity in km/s to exclude the line emission from the baseline fit.
                                                # You can add more than 1 line in the following format:  '-100~-50;20~30', where line 
                                                # emission is found between -100 and -50 km/s, and between 20 and 30 km/s. 

#----------------------------------
# Parameters for imaging:
#------------------------

phase_center   = 'J2000 05h02m05.0s -69d34m06s' # Provide coordinate of phase center, otherwise set to "False" and coordinates will be read from the data
source_vel_kms = 1230                           # Provide velocity of the source, otherwise set to "False" and coordinates will be read from the data
vwidth_kms     = 1230                           # width in velocity and velocity resolution in km/s
chan_dv_kms    = 1.0

freq_rest_im   = freq_rest/1e3                  # rest frequency in GHz for imaging
name_line      = 'CO21_1kmsres'                 # Name of the line, to be used for naming the files
#wider: only imaging part is wider
#wider2: vel_cube is larger.

# Exclude these EBs, SEMIPASS

#-----------------------------------------------
# Steps of data reduction you want to perform:
#---------------------------------------------
do_step = [7,8]
#  1: import_and_split_ant - Import data to MS and split by antenna    (adsm   -> asap)
#  2: gen_tsys_and_flag    - Generate tsys cables and apply flags      (create .tsys and swpmap)
#  3: counts2kelvin        - Calibration of Tsys and convert data to K (asap   -> asap.2)
#  4: extract_cube         - Extract cube with line                    (asap.2 -> asap.3)
#  5: baseline             - Baseline correction                       (asap.3 -> asap.4)
#  6: concat_ants          - Concatenate all antennas                  (asap.4 -> ms.5 -> cal.jy)
#  7: imaging              - Imaging and fix the header                (cal.jy -> image)
#  8: export_fits          - Export image and weight to a fits file    (image  -> fits)

execfile('ALMA-TP-tools.py')                  # All procedures for data reduction

