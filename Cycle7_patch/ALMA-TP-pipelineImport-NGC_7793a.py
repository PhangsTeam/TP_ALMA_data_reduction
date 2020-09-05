# This script carries out the importasdm step of the TP pipeline (step 1.1). This is only needed for Cycle 7 or later ALMA data. For a given galaxy, run this script first using CASA 5.1 or later, then the usual ALMA-TP-pipeline-NGC_xxx.py script in CASA 4.7.
# output: an .ms file for each EB in the raw directory
#
# created 2020/09/04 C. Faesi
# modifications:
#
#

# NOTE: be sure to use correct CASA version! (5.x +)
# note that this is NGC 7793 subblock 1 (NGC7793_a_06_TP)
# enter the name of the project/SGOUS/GOUS/MOUS/ where the project directory should be at the same level as the imaging directory
path_galaxy = "tmp/2018.A.00062.S/science_goal.uid___A001_X1458_X132/group.uid___A001_X1458_X133/member.uid___A001_X1458_X136/"

doplots    = True  # not used, but needs to be set
# EBs to exclude:
EBexclude      = []
# example format:
#  EBexclude      = ['uid___A002_Xc8b2b0_X66f0','uid___A002_Xc8b2b0_X5e65']

execfile('ALMA-TP-importCycle7.py')   
