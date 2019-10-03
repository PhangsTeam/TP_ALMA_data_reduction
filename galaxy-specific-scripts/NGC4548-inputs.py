#----------------------------------
# Defining paths and files
#-------------------------------

# use CASA version 4.7.2-el7
# NGC 4548 (NGC4548_a_06_TP)

path_galaxy = "tmp/2017.1.00886.L/science_goal.uid___A001_X12a3_X4f6/group.uid___A001_X12a3_X4f7/member.uid___A001_X12a3_X4fc/"
flag_file   = "NGC4548-flagfile.py"             # File containing additional flags

#----------------------------------1
# Parameters for data reduction:
#-------------------------------

doplots    = True                               # Do non-interactive. additional plots (plots will be saved in "calibration/plots" folder)
bl_order   = 1                                  # Order for the baseline fitting

source     = 'NGC4548'                         # Source name (without a/b/c)
freq_rest  =  230538.                           # Rest frequency of requested line in MHz (ex: "freq_rest  = 230538" for CO(2-1))
vel_cube   = '-14~986'                        # Range in velocity in km/s to extract the line cube. Set to a range of 1000 centered on the source_vel_kms below
vel_line   = '330~630'                       # Range in velocity in km/s to exclude the line emission from the baseline fit. Set to the central ~500 km/s around source_vel_kms set below. Verify by looking at a spectrum of the galaxy
                                                # You can add more than 1 line in the following format:  '-100~-50;20~30', where line 
                                                # emission is found between -100 and -50 km/s, and between 20 and 30 km/s. 

#----------------------------------
# Parameters for imaging:
#------------------------

phase_center   = 'J2000 12h35m26.4s +14d29m47s'  # Provide coordinate of phase center, otherwise set to "False" and coordinates will be read from the data
source_vel_kms = 486                        # Provide velocity of the source, otherwise set to "False" and coordinates will be read from the data
vwidth_kms     = 1000                            # width in velocity and velocity resolution in km/s
chan_dv_kms    = 2.5

freq_rest_im   = freq_rest/1e3                  # rest frequency in GHz for imaging
name_line      = 'CO21'                         # Name of the line, to be used for naming the files

# EBs to exclude: one obs of 21 Oct 2018 listed as semipass. Also another semipass in project tracker but only 7min, butnot included in data download
EBexclude      = ['uid___A002_Xd395f6_Xe8e6']

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
