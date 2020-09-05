#-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
# ALMA Total Power Data Reduction Script: Hack for importing cycle 7 ALMA data.
# 
# Original ALMA calibration script modified by C. Herrera 12/01/2017
# This version modified by C. Faesi 2020/09/05
# Do not modify.
# NOTE: must be run in casa 5.1 or later!
# 
# Last modifications: 
# 
# To do:
#   remove unnecessary functions (ie most of them...)
#
#-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*

# Import libraries
import os              # operating system
import re              # regular expression
import numpy as np     # Support for large, multi-dimensional arrays and matrices
import sys             # System-specific parameters and functions
import scipy.constants # Physical constants
import glob            # Pathnames matching a specified pattern
import imp

#---------------------------------------------------------------------
path_script = '../script/'       # Path to the script folder
path_raw    = '../raw/'          # Path to the raw folder
path_au     = '.'                # Path to the analysisUtils.py script
path_dataproduct = '../data/'     # Path to data products.
#---------------------------------------------------------------------

# Global variables
c_light = scipy.constants.c/1000   # Speed of light in km/s 
pi      = scipy.constants.pi

# Import ALMA Analysis Utils
try:
    dd = imp.find_module('analysisUtils')
    found = True
except ImportError:
    found = False
    if os.path.exists(path_au+'/analysis_scripts') == True:
        sys.path.append(path_au+'/analysis_scripts')
        import analysisUtils as aU
        es = aU.stuffForScienceDataReduction()
        print "> Specific tasks for ALMA data reduction are loaded\n"
    else:
        print "==========================================================="
        print " Specific tasks for ALMA data reduction were not found!"
        print " You can download the ALMA Analysis Utils tools from "
        print " the github (analysis_script folder) or from "
        print " ftp://ftp.cv.nrao.edu/pub/casaguides/analysis_scripts.tar"
        print "===========================================================\n"

# Check if data was calibrated with the pipeline 
def checkpipeline():
    
    if len(glob.glob(path_script+'*.xml')) > 0:        
        print "> Data was reduced by ALMA/JAO using an automatized pipeline "
        print "> Setting the variable 'pipeline' to True\n"
        return True
    else:
        print "> Data was reduced by ALMA/JAO using scripts "
        print "> Setting the variable 'pipeline' to False\n"
        return False

# Creating CASA tools
def createCasaTool(mytool):
    
    if (type(casac.Quantity) != type):  # casa 4.x
        myt = mytool()
    else:  # casa 3.x
        myt = mytool.create()
    return(myt)

# Retrieve name of the column
def getDataColumnName(inputms):
    
    mytb = createCasaTool(tbtool)
    mytb.open(inputms)
    colnames = mytb.colnames()
    if 'FLOAT_DATA' in colnames:
        data_query= 'FLOAT_DATA'
    else:
        data_query = 'DATA'
    mytb.close()
    return(data_query)

# by ALMA
def scaleAutocorr(vis, scale=1., antenna='', spw='', field='', scan=''):
    
    if os.path.exists(vis) == False:
        print "Could not find MS."
        return
    if os.path.exists(vis+'/table.dat') == False:
        print "No table.dat. This does not appear to be an MS."
        return
    
    mymsmd = createCasaTool(msmdtool)
    mytb = createCasaTool(tbtool)
    
    conditions = ["ANTENNA1==ANTENNA2"]
    
    mymsmd.open(vis)
    
    if antenna != '':
        if not isinstance(antenna, (list, tuple)):
            antenna = [antenna]
        antennaids = []
        for i in antenna:
            if re.match("^[0-9]+$", str(i)): # digits only: antenna ID
                antennaids.append(int(i))
            else: # otherwise: antenna name
                antennaids.append(mymsmd.antennaids(i)[0])
        conditions.append("ANTENNA1 in %s" % str(antennaids))
    if spw != '':
        if not isinstance(spw, (list, tuple)): 
            spw = [spw]
        datadescids = []
        for i in spw:
            datadescids.append(mymsmd.datadescids(spw=int(i))[0])
        conditions.append("DATA_DESC_ID in %s" % str(datadescids))
    if field != '':
        if not isinstance(field, (list, tuple)):
            field = [field]
        fieldids = []
        for i in field:
            if re.match("^[0-9]+$", str(i)): # digits only: field ID
                fieldids.append(int(i))
            else: # otherwise: field name
                fieldids.append(mymsmd.fieldsforname(i)[0])
        conditions.append("FIELD_ID in %s" % str(fieldids))
    if scan != '':
        if not isinstance(scan, (list, tuple)):
            scan = [scan]
        scannumbers = [int(i) for i in scan]
        conditions.append("SCAN_NUMBER in %s" % str(scannumbers))
    
    mymsmd.close()
    
    datacolumn = getDataColumnName(vis)
    
    print "Multiplying %s to the dataset %s column %s." % \
        (str(scale), vis, datacolumn)
    print "The selection criteria are '%s'." % (" && ".join(conditions))
    
    mytb.open(vis, nomodify=False)
    subtb = mytb.query(" && ".join(conditions))
    try:
        data = subtb.getcol(datacolumn)
        print "Dimension of the selected data: %s" % str(data.shape)
        subtb.putcol(datacolumn, data*scale)
    except:
        print "An error occurred upon reading/writing the data."
    finally:
        print "Closing the table."
        mytb.flush()
        subtb.close()
        mytb.close()

# Create vector with antenna names
def read_ants_names(filename):
    
    mytb = createCasaTool(tbtool)
    mytb.open(filename + '/ANTENNA')
    vec_ants = mytb.getcol('NAME')
    mytb.close()
    
    return vec_ants

# Correct the Tsysmap (useful for old data)
def get_tsysmap(tsysmap,spws_scie,spws_tsys,freq_rep_scie,freq_rep_tsys):
    
    for i in range(len(freq_rep_scie)): 
        diff = [abs(freq_rep_tsys[j] - freq_rep_scie[i]) for j in range(len(freq_rep_tsys))]
        ddif = np.array(diff)
        tsysmap[spws_scie[i]]   = spws_tsys[ddif.argmin()]
        tsysmap[spws_scie[i]+1] = spws_tsys[ddif.argmin()]
    print "Final map used for the observations: (they should have the same frequency)"
    for i in range(len(spws_scie)): print spws_scie[i],tsysmap[spws_scie[i]]
    return tsysmap

# Read spw information (source and Tsys)
def read_spw(filename,source):
    
    # Tsys spws (index)
    mytb = createCasaTool(tbtool)
    mytb.open(filename + '/SYSCAL')
    
    spwstsys  = mytb.getcol('SPECTRAL_WINDOW_ID')
    spws_tsys = np.unique(spwstsys).tolist()
    mytb.close()
    
    # Science spws (index)
    mytb.open(filename + '/SOURCE') 
    names  = mytb.getcol('NAME')
    numli  = mytb.getcol('NUM_LINES')
    ss     = np.where((names == source) & (numli ==  1))
    spws_scie      = [int(mytb.getcol('SPECTRAL_WINDOW_ID',startrow=i,nrow=1))    for i in ss[0]]
    rest_freq_scie = [float(mytb.getcol('REST_FREQUENCY',startrow=i,nrow=1)) for i in ss[0]]
    mytb.close()
    mytb.open(filename + '/SPECTRAL_WINDOW')
    names          = mytb.getcol('NAME')
    rest_freq_scie = [rest_freq_scie[i] for i in range(len(spws_scie)) if "FULL_RES" in names[spws_scie[i]]]
    spws_scie      = [spw for spw in spws_scie if "FULL_RES" in names[spw]]
    spws_scie      = aU.getScienceSpws(filename)
    spws_scie      = spws_scie.split(",")
    spws_scie = [int(i) for i in spws_scie]

    # Read number of channels, frequency at channel zero and compute representative frequency
    freq_zero_scie  = range(len(spws_scie))
    chan_width_scie = range(len(spws_scie))
    num_chan_scie   = range(len(spws_scie))
    freq_rep_scie   = range(len(spws_scie))
    for i in range(len(spws_scie)):
        freq_zero_scie[i]  = float(mytb.getcol('REF_FREQUENCY',startrow=spws_scie[i],nrow=1))
        chan_width_scie[i] = float(mytb.getcol('CHAN_WIDTH',startrow=spws_scie[i],nrow=1)[0])
        num_chan_scie[i]   = float(mytb.getcol('NUM_CHAN',startrow=spws_scie[i],nrow=1))
        freq_rep_scie[i]   = (num_chan_scie[i]/2*chan_width_scie[i]+freq_zero_scie[i])/1e6
    freq_zero_tsys  = range(len(spws_tsys))
    chan_width_tsys = range(len(spws_tsys))
    num_chan_tsys   = range(len(spws_tsys))
    freq_rep_tsys   = range(len(spws_tsys))
    for i in range(len(spws_tsys)):
        freq_zero_tsys[i]  = float(mytb.getcol('REF_FREQUENCY',startrow=spws_tsys[i],nrow=1))
        chan_width_tsys[i] = float(mytb.getcol('CHAN_WIDTH',startrow=spws_tsys[i],nrow=1)[0])
        num_chan_tsys[i]   = float(mytb.getcol('NUM_CHAN',startrow=spws_tsys[i],nrow=1))
        freq_rep_tsys[i]   =  (num_chan_tsys[i]/2*chan_width_tsys[i]+freq_zero_tsys[i])/1e6
    mytb.close()
    
    return spws_scie,spws_tsys,freq_rep_scie,freq_rep_tsys,chan_width_scie,num_chan_scie

# Get information of the source velocity
def read_vel_source(filename,source):
    
    mytb  = createCasaTool(tbtool)
    mytb.open(filename + '/SOURCE')
    names = mytb.getcol('NAME')
    numli = mytb.getcol('NUM_LINES')
    ss    = np.where((names == source) & (numli ==  1))[0]
    vel_source = float(mytb.getcol('SYSVEL',startrow=ss[0],nrow=1))/1e3
    vel_frame = mytb.getcolkeywords('SYSVEL')['MEASINFO']['Ref']
    print "Frame of source velocity  is: "+vel_frame
    mytb.close()
    
    return vel_source

# SPW where the requested line is located
def get_spw_line(vel_source,freq_rest,spws_info):
    
    #science spws
    spws_scie,spws_tsys,freq_rep_scie,freq_rep_tsys,chan_width_scie,num_chan_scie  = spws_info
    
    found = False
    for i in range(len(spws_scie)):
        freq_ini = (freq_rep_scie[i]-num_chan_scie[i]/2*chan_width_scie[i]*1e-6)/(1-vel_source/c_light)  # initial frequency in spw -> still to be check since observations are in TOPO
        freq_fin = (freq_rep_scie[i]+num_chan_scie[i]/2*chan_width_scie[i]*1e-6)/(1-vel_source/c_light)  # final frequency in spw -> still to be check since observations are in TOPO
        if freq_rest > min(freq_ini,freq_fin) and freq_rest < max(freq_ini,freq_fin): 
            found = True
            return spws_scie[i]
    if found == False: 
        print "** Requested line with rest frequency "+str(freq_rest/1e3)+" GHz is not on the data **"
        return False

# Extract flagging from original data reduction file.
def extract_flagging(filename,pipeline):

    os.system('rm '+path_script+'file_flags.py')
    file_flag    = open(path_script+'file_flags.py', 'w')
    fileflagread = ori_path+'/flags_folder/'+flag_file

    if pipeline == True: 
 	if os.path.exists(fileflagread) == False:        
	    print "No flagging will be done. If you want to flag something, please create a file "
            print "with the specific flags using the task sdflag."	
            print "Example: "
            print "sdflag(infile = 'uid___A002_X9998b8_X5d5.ms.PM04.asap',"
            print "  mode = 'manual',"
            print "  spw = '19:0~119;3960~4079,21:0~500;3960~4079',"
            print "  overwrite = True)"
            print " Save it as fileflagNAMEGAL.py in the flags_folder"
        else:
            print "Reading file "+fileflagread+" for flagging"
            with open(fileflagread) as f: lines_f = f.readlines()
            for i in range(len(lines_f)): file_flag.write(lines_f[i])
            print "Flags saved in "+path_script+"file_flags.py"
    else:  
        file_script = path_script+filename+'.scriptForSDCalibration.py'  
        with open(file_script) as f: lines_f = f.readlines()
        with open(file_script) as f:
            for i, line in enumerate(f):
                ll = i
                if "sdflag(infile" in line: 
                    ss = line.index("sdflag(i")
                    while len(lines_f[ll].split()) != 0: 
                        file_flag.write((lines_f[ll])[ss:len(lines_f[ll])]) 
                        ll = ll+1
        if os.path.exists(fileflagread) == True:
            print "Reading file "+fileflagread+" for flagging"
            with open(fileflagread) as f: lines_f = f.readlines()
            for i in range(len(lines_f)): file_flag.write(lines_f[i])
        
        print "Flags saved in script/file_flags.py"
    file_flag.close()

# Convert the given velocity to channels (using MS file)
def convert_vel2chan(filename,freq_rest,vel_cube,spw_line,vel_source,spws_info,coords):
    
    spws_scie,freq_rep_scie,chan_width_scie,num_chan_scie = spws_info[0],spws_info[2],spws_info[4],spws_info[5]
    freq_rep_line   = freq_rep_scie[np.where(np.array(spws_scie)    == spw_line)[0]]
    chan_width_line = (chan_width_scie[np.where(np.array(spws_scie) == spw_line)[0]])/1e6
    num_chan_line   = num_chan_scie[np.where(np.array(spws_scie)    == spw_line)[0]]
    
    vel1 = float((vel_cube.split('~'))[0])
    vel2 = float((vel_cube.split('~'))[1])
    freq1 = (1-vel1/c_light)*freq_rest
    freq2 = (1-vel2/c_light)*freq_rest
    
    ra  = coords.split()[1]
    ra  = ra.replace("h",":")
    ra  = ra.replace("m",":")
    dec = coords.split()[2]
    dec = dec.replace("d",":")
    dec = dec.replace("m",":")

    date = aU.getObservationStartDate(filename)
    date = (date.split()[0]).replace('-','/')+'/'+date.split()[1]
    
    freq1_topo = aU.lsrkToTopo(freq1,date,ra,dec)
    freq2_topo = aU.lsrkToTopo(freq2,date,ra,dec)
    
    freq_chan0  = freq_rep_line-(num_chan_line/2-0.5)*chan_width_line
    
    chan1 = int(round((freq1_topo-freq_chan0)/chan_width_line))
    chan2 = int(round((freq2_topo-freq_chan0)/chan_width_line))
    
    return min(chan1,chan2),max(chan1,chan2) 

# Convert the given velocity to channels (using ASAP file with unique spw)
def convert_vel2chan_line(filename_in,freq_rest,vel_line,spw_line,coords,date):
   
    vel1 = float((vel_line.split('~'))[0])
    vel2 = float((vel_line.split('~'))[1])
    
    freq1 = (1-vel1/c_light)*freq_rest
    freq2 = (1-vel2/c_light)*freq_rest
    
    ra  = coords.split()[1]
    ra  = ra.replace("h",":")
    ra  = ra.replace("m",":")
    dec = coords.split()[2]
    dec = dec.replace("d",":")
    dec = dec.replace("m",":")
    
    freq1_topo = aU.lsrkToTopo(freq1, date,ra,dec)
    freq2_topo = aU.lsrkToTopo(freq2, date,ra,dec)

    mytb  = createCasaTool(tbtool)
    mytb.open(filename_in)
    nchan = mytb.getkeyword('nChan')
    if_eq = mytb.getcol('FREQ_ID',startrow=1,nrow=1)
    bandw = mytb.getkeyword('Bandwidth')
    mytb.close()
    
    mytb.open(filename_in+'/FREQUENCIES')   
    freq_chanref = mytb.getcol('REFVAL',startrow=if_eq,nrow=1)/1e6
    chanref      = mytb.getcol('REFPIX',startrow=if_eq,nrow=1)
    chan_width   = mytb.getcol('INCREMENT',startrow=if_eq,nrow=1)/1e6
    mytb.close()
    
    freq_chan0 = freq_chanref-chanref*chan_width
    chan1 = int(round((freq1_topo-freq_chan0)/chan_width))
    chan2 = int(round((freq2_topo-freq_chan0)/chan_width))
    
    return min(chan1,chan2),max(chan1,chan2),nchan

# Create string with spw and channel for baseline correction 
def str_spw4baseline(filename_in,freq_rest,vel_line,spw_line,coords):
    
    filename = re.search('(.+?).ms',filename_in).group(0)
    
    date = aU.getObservationStartDate(filename)
    date = (date.split()[0]).replace('-','/')+'/'+date.split()[1]
    vel_line_s = vel_line.split(';')
    nlines = len(vel_line_s)
    channels_v = range(nlines*2)
    for i in range(nlines):
        vel_str = vel_line_s[i]
        chan1_line,chan2_line,nchan_line = convert_vel2chan_line(filename_in,freq_rest,vel_str,spw_line,coords,date)
        channels_v[2*i+1] = chan2_line
        channels_v[2*i]   = chan1_line
    channels_v.sort()
    # String to define spws for baseline correction
    spw_extr = str(spw_line)+":0~"+str(channels_v[0])+";"
    if nlines > 1:
        for i in range(nlines-1):
            spw_extr = spw_extr + str(channels_v[2*i+1])+"~"+ str(channels_v[2*i+2])+";"
    spw_extr = spw_extr + str(channels_v[-1])+"~"+str(max(channels_v[-1],nchan_line))
    
    return spw_extr

# Extract variable jyperk, used to convert from K to Jy.
def extract_jyperk(filename,pipeline):
    print "Extracting Jy per K conversion factor"
    if pipeline == True: 
        file_script = 'jyperk.csv'
        ant_arr = []
        spw_arr = []
        val_arr = []
        with open(file_script) as f: 
            for line in f:
                if filename in line:
                    line_arr = line.split(',')
                    ant_arr.append(line_arr[1])
                    spw_arr.append(int(line_arr[2]))
                    val_arr.append(line_arr[4][0:line_arr[4].index('\n')])       
        jyperk = {k: {e:{'mean':{}} for e in np.unique(spw_arr)} for k in np.unique(ant_arr)}
        for i in range(len(ant_arr)): jyperk[ant_arr[i]][spw_arr[i]]['mean']= float(val_arr[i])
        return jyperk
    else:  
        file_script = '../script/'+filename+'.scriptForSDCalibration.py'   
        vec_jyperk = ''
        with open(file_script) as f: lines_f = f.readlines()
        with open(file_script) as f:
            for i, line in enumerate(f):
                ll = i
                if "jyperk = " in line: 
                    ss = line.index("jyperk")
                    while len(lines_f[ll].split()) != 0: 
                        if ll == i+1: ss2 = lines_f[ll].index("{")
                        if ll == i: 
                            vec_jyperk = vec_jyperk+(lines_f[ll])[ss:len(lines_f[ll])]
                        else:
                            vec_jyperk = vec_jyperk+(lines_f[ll])[ss2:len(lines_f[ll])]
                        ll = ll+1
        kw = {}
        exec(vec_jyperk) in kw
        jyperk = kw['jyperk']
        return jyperk

# Read source coordinates
def read_source_coordinates(filename,source):
    
    coord_source = aU.getRADecForSource(filename,source)
    RA_h  = (coord_source.split(' ')[0]).split(':')[0]
    RA_m  = (coord_source.split(' ')[0]).split(':')[1]
    RA_s  = (coord_source.split(' ')[0]).split(':')[2]
    DEC_d = (coord_source.split(' ')[1]).split(':')[0]
    DEC_m = (coord_source.split(' ')[1]).split(':')[1] 
    DEC_s = (coord_source.split(' ')[1]).split(':')[2]
    coord = "J2000  "+str(RA_h)+"h"+str(RA_m)+"m"+str(RA_s[0:6])+" "+str(DEC_d)+"d"+str(DEC_m)+"m"+str(DEC_s)
    return coord

# Get source name
def get_sourcename(filename):
    
    mytb   = createCasaTool(msmdtool)
    mytb.open(filename)
    source = mytb.fieldnames()[mytb.fieldsforintent('OBSERVE_TARGET#ON_SOURCE')[0]]
    mytb.close()
    
    return source

# Create string of spws to apply the Tsys
def str_spw_apply_tsys(spws_info):
    #science spws
    spws_scie,spws_tsys,freq_rep_scie,freq_rep_tsys = spws_info[0:4]
    
    spws_all = spws_tsys+spws_scie
    spws_all.sort()
    spws_tsys_str = (str(spws_tsys))[1:len(str(spws_tsys))-1]
    spws_scie_str = (str(spws_scie))[1:len(str(spws_scie))-1]
    spws_all_str  = (str(spws_all))[1:len(str(spws_all))-1]
    
    return spws_scie_str,spws_tsys_str,spws_all_str

# Check date of observations to decide if the non-linearity correction should be applied or not.
def check_date_nonlinearity(filename):
    
    date_obs    = aU.getObservationStart(filename)/24/60/60.
    date_change = aU.dateStringToMJD('2015/10/01 00:00:00')
    
    if abs(date_obs-date_change) <= 1: print "Data obtained within 1 day of the change, be careful!"    
    if date_obs >= date_change: 
        print "Data obtained after 2015/10/01, non-linearity not applied"
        return False
    if date_obs < date_change:  
        print "Data obtained before 2015/10/01, non-linearity applied"
        return True

# Check if we are in the correct directory
def checkdir(currentdir,path_galaxy):
    
    if path_galaxy in currentdir:
        return True
    else:
        return False

def checktmp():
    if os.path.isdir('../'+path_galaxy) == False:  
        print "Temporal folder does not exists. Creating it and copying raw data\n"
        os.system('mkdir -p ../'+path_galaxy)
        os.system('cp -rf  ../../../'+path_galaxy[4:-1]+'/calibration ../'+path_galaxy)
        os.system('cp -rf  ../../../'+path_galaxy[4:-1]+'/raw         ../'+path_galaxy)
        os.system('cp -rf  ../../../'+path_galaxy[4:-1]+'/script      ../'+path_galaxy)

#-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
#-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
# Data reduction steps
#-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
#
# Step 0
#*-*-*-*-*-*
def check_casa_version():
    version = cu.version_string()
    print "You are using " + version
    if (version < '5.1.0'):
        print "THIS PART OF THE PIPELINE MUST BE RUN IN CASA 5.x."
        print "PLEASE UPDATE IT BEFORE PROCEEDING."
    else:
        print "Your version of CASA will work for this step."

def check_exists(filename):
    print "Checking that the original ALMA data exists"
    filename_asdm = filename[0:filename.find('.ms')]+'.asdm.sdm'
    
    if os.path.exists(path_raw+filename_asdm) == True:
        return True
    else:
        print "** Original ALMA data "+filename_asdm +" does NOT exist: **"
        print "   Skipping file \n"
        return False

#*-*-*-*-*-*_*-*-*-*-*-*
# Step 1  Import data 
#*-*-*-*-*-*-*-*-*-*-*
def import_and_split_ant(filename,doplots=False):
    
    print "=================================================="
    print "= Step 1 - Import ASDM data ="
    print "=================================================="
    print os.getcwd()
    if checkdir(os.getcwd(),path_galaxy) == False:  os.chdir('../'+path_galaxy+'calibration')
    if os.path.isdir("plots/") == False:     os.system('mkdir plots')       # folder containing all plots
    if os.path.isdir("obs_lists/") == False: os.system('mkdir obs_lists')   # folder containing all observation lists (i.e., listobs, sdlist)
    
    filename0 = filename[0:filename.find('.ms')]
    os.system('cp -r '+path_raw+filename0+'.asdm.sdm '+filename0)

    if  os.path.isdir(filename+'.flagversions') == True: os.system('rm -rf '+filename+'.flagversions')
    
    # 1.1 Import of the ASDM
    print "1.1 Importing from ASDM to MS"
    if os.path.exists(filename) == False:
        importasdm(filename0, 
            asis='Antenna Station Receiver Source CalAtmosphere CalWVR CorrelatorMode SBSummary', 
            bdfflags=True, # CMF test 200904
            process_caldevice=False, 
            with_pointing_correction=True)
    
    # Transfer specific flags (BDF flags) from the ADSM to the MS file
#    os.system(os.environ['CASAPATH'].split()[0]+'/bin/bdflags2MS -f "COR DELA INT MIS SIG SYN TFB WVR ZER" '+filename0+' '+filename)
    
    


  


#-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
# Main body TP ALMA data reduction. 
#-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*

print "=================================="
print " Starting TP ALMA data reduction: cycle 7+ version for asdm import only "
print "==================================\n"

print "> You are executing the ALMA-TP-pipeline script from the directory: "
print os.getcwd() + "\n"

ori_path = os.getcwd()                      # Current directory

checktmp()                                  # check if the tmp folder exists. If not, do it and copy the data.

print "> Changing directory to "+path_galaxy+'calibration'+"\n"
os.chdir('../'+path_galaxy+'calibration')   # Working on the calibration folder of the current galaxy

os.system('tar -zxvf *auxproducts.tgz')     # untar the jyperk.csv file

pipeline = checkpipeline()                  # Pipeline reduced data (True or False)

# Defining Execution Blocks (EBS) names
EBsnames = [f for f in os.listdir(path_raw) if f.endswith('.asdm.sdm')]

if 'EBexclude' in globals(): 
   EBsnames = [s for s in EBsnames if s[0:-9] not in EBexclude]
# CMF: s[0:-9] indexing is for if EBexclude does not have the '.asdm.sdm' at the end

#if len(do_step) == 0: do_step = [1]

# import for each EB 
for EBs in EBsnames:
    
    if pipeline == False:
        EBs = EBs.replace('.ms.scriptForSDCalibration.py', '.asdm.sdm')      
    filename = 'u'+re.search('u(.+?).asdm.sdm', EBs).group(1)+'.ms'       
    file_exists = check_exists(filename)                             # Check weather the raw data exists
    if file_exists == True:
        import_and_split_ant(filename,doplots)      # Import and split data per antenna


print " Changing directory to "+ori_path+'\n'
os.chdir(ori_path) # run this manually if you ever need to start over
