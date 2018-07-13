#----------------------------------
# Defining paths and files
#-------------------------------

path_galaxy = "tmp/2017.1.00886.L/science_goal.uid___A001_X1284_X275f/group.uid___A001_X1284_X2760/member.uid___A001_X1284_X2767/" 
flag_file   = "fileflagNGC_4207.py"             # File containing additional flags 

#----------------------------------
# Parameters for data reduction:
#-------------------------------

doplots    = True                               # Do non-interactive. additional plots (plots will be saved in "calibration/plots" folder)
bl_order   = 1                                  # Order for the baseline fitting

source     = 'NGC4207'                          # Source name
freq_rest  =  230538.                           # Rest frequency of requested line in MHz (ex: "freq_rest  = 230538" for CO(2-1))
vel_cube   = '296~896'                          # Range in velocity in km/s to extract the line cube.
vel_line   = '480~715'                          # Range in velocity in km/s to exclude the line emission from the baseline fit.
                                                # You can add more than 1 line in the following format:  '-100~-50;20~30', where line 
                                                # emission is found between -100 and -50 km/s, and between 20 and 30 km/s. 

#----------------------------------
# Parameters for imaging:
#------------------------

phase_center   = 'J2000 12h15m30.5s +09d35m06s' # Provide coordinate of phase center, otherwise set to "False" and coordinates will be read from the data
source_vel_kms = 596                            # Provide velocity of the source, otherwise set to "False" and coordinates will be read from the data
vwidth_kms     = 500                            # width in velocity and velocity resolution in km/s
chan_dv_kms    = 2.5

freq_rest_im   = freq_rest/1e3                  # rest frequency in GHz for imaging
name_line      = 'CO21'                         # Name of the line, to be used for naming the files

# Exclude these EBs, SEMIPASS
#EBexclude      = ['uid___A002_Xc96f17_Xbdc7']
#-----------------------------------------------
# Steps of data reduction you want to perform:
#---------------------------------------------
do_step = [1,2,3,4,5,6,7,8]
#  1: import_and_split_ant - Import data to MS and split by antenna    (adsm   -> asap)
#  2: gen_tsys_and_flag    - Generate tsys cables and apply flags      (create .tsys and swpmap)
#  3: counts2kelvin        - Calibration of Tsys and convert data to K (asap   -> asap.2)
#  4: extract_cube         - Extract cube with line                    (asap.2 -> asap.3)
#  5: baseline             - Baseline correction                       (asap.3 -> asap.4)
#  6: concat_ants          - Concatenate all antennas                  (asap.4 -> ms.5 -> cal.jy)
#  7: imaging              - Imaging and fix the header                (cal.jy -> image)
#  8: export_fits          - Export image and weight to a fits file    (image  -> fits)

execfile('ALMA-TP-tools.py')                  # All procedures for data reduction

