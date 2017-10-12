#-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
# ALMA Total Power Data Reduction Script
# Original ALMA calibration script modified by C. Herrera 12/01/2017
# Do not modify. This script is called by "ALMA-TP-pipeline-GalName.py".
# 
# Last modifications: 
# - 31.01.2017: read_source_coordinates
# - 01.02.2017: More than 1 line can be defined to be excluded for baseline corrections (bug fixed 21/03/2017)
# - 02.02.2017: Handle TOPO ALMA frame vs the given LSRK velocity for extraction of cube and baseline 
# - 27.03.2017: extract_jyperk. It was not working for Cycle 1 data.
# - 26.07.2017: add flag of 7m antennas (CM#)
# - 26.07.2017: correct spw Tsys value associated with the averaged spw science value 
#               (tsysmap[spws_scie[i]+1] = spws_tsys[i]-> tsysmap[spws_scie[i]+1] = spws_tsys[ddif.argmin()])
# - 26.07.2017: modified convert_vel2chan_line, because some asap files had mixed the IFs, 
#               having IFNO and IFID different.
# - 10.10.2017: handle imaging of 2 SGs of the same galaxy. 
#
# Still need to do:
# - Work on errors when files are not found, etc.
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

path_script = '../script/'       # Path to the script folder
path_raw    = '../raw/'          # Path to the raw folder
path_au     = '.'                # Path to the analysisUtils.py script

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
    
    if len(glob.glob(path_script+'PPR*.xml')) > 0:        
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
        os.system('cp -rf  ../raw/'+path_galaxy[4:-1]+'/calibration ../'+path_galaxy)
        os.system('cp -rf  ../raw/'+path_galaxy[4:-1]+'/raw         ../'+path_galaxy)
        os.system('cp -rf  ../raw/'+path_galaxy[4:-1]+'/script      ../'+path_galaxy)

#-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
#-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
# Data reduction steps
#-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
#
# Step 0
#*-*-*-*-*-*
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
    print "= Step 1 - Import ASDM data and split by antenna ="
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
            bdfflags=False, 
            process_caldevice=False, 
            with_pointing_correction=True)
    
    # Transfer specific flags (BDF flags) from the ADSM to the MS file
    os.system(os.environ['CASAPATH'].split()[0]+'/bin/bdflags2MS -f "COR DELA INT MIS SIG SYN TFB WVR ZER" '+filename0+' '+filename)
    
    # Check for known issue, CSV-2555: Inconsistency in FIELD_ID, SOURCE_ID and Spw_ID in single dish data
    es.fixForCSV2555(filename)   
    
    # 1.2 Listobs
    print "1.2 Creating listobs for MS file"
    outname = filename+'.listobs'
    os.system('rm -rf obs_lists/'+outname)
    listobs(vis = filename,
        listfile = 'obs_lists/'+outname)
    
    if doplots == True: 
        aU.getTPSampling(vis = filename, 
        showplot = True, 
        plotfile = 'plots/'+filename+'.sampling.png')
    
    # 1.3 A priori flagging: e.g., mount is off source, calibration device is not in correct position, power levels are not optimized, WCA not loaded...
    print "1.3 Applying a priori flagging, check plots/"+filename+".flagcmd.png plot to see these flags."
    flagcmd(vis = filename,
        inpmode = 'table',
        useapplied = True,
        action = 'plot',
        plotfile = 'plots/'+filename+'.flagcmd.png')
    
    flagcmd(vis = filename,
        inpmode = 'table',
        useapplied = True,
        action = 'apply')

    # If there are, flag 7m antennas
    vec_ants   = read_ants_names(filename)
    ants_7m = [s for s in vec_ants if "CM" in s]
    if len(ants_7m) > 0: 
        str_ants = ', '.join(ants_7m)
        flagdata(vis = filename,
                 mode = 'manual',
                 antenna = str_ants,
                 action = 'apply')

    # 1.4 Split by antenna 
    print "1.4 Splitting the file by antennas"
    fin = '.asap'

    vec_ants_t  = read_ants_names(filename)
    vec_ants    = [s for s in vec_ants_t if any(xs in s for xs in ['PM','DV'])]
    for ant in vec_ants :
        os.system('rm -Rf '+filename+'.'+ant+fin)
    
    sdsave(infile = filename, 
        splitant = True, 
        outfile = filename+fin, 
        overwrite = True)
    
    #1.5 sdlist
    print "1.5 Create sdlist for each splitted file."
    for ant in vec_ants:
        os.system('rm -Rf obs_lists/'+filename+'.'+ant+'.asap.sdlist')
        sdlist(infile = filename+'.'+ant+'.asap',
            outfile = 'obs_lists/'+filename+'.'+ant+'.asap.sdlist')
    

#-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
# Step 2  Generate Tsys and apply flagging 
#-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*

def gen_tsys_and_flag(filename,spws_info,pipeline,doplots=False):
    
    print "========================================================"
    print " Step 2  Generate Tsys and apply flagging"
    print "========================================================"
    
    if checkdir(os.getcwd(),path_galaxy) == False:  os.chdir('../'+path_galaxy+'calibration')
    if os.path.isdir("plots/") == False:     os.system('mkdir plots')       # folder containing all plots
    
    # 2.1 Generation of the Tsys cal table
    print " 2.1 Generating Tsys calibration table"
    
    os.system('rm -Rf '+filename+'.tsys')
    gencal(vis = filename, caltable = filename+'.tsys', caltype = 'tsys')
    
    # 2.2 Create png plots of CASA Tsys and bandpass solution
    print " 2.2 Create plots of Tsys and bandpass solution"
    #os.system('rm -rf plots/'+filename+'.tsys.plots.overlayTime/'+filename+'.tsys')
    
    if doplots == True:
        os.system('rm -Rf plots/'+filename+'.tsys.plots.overlayTime/'+filename+'.tsys')
        plotbandpass(caltable=filename+'.tsys', 
                     overlay='time',
                     xaxis='freq', yaxis='amp', 
                     subplot=22, 
                     buildpdf=False, 
                     interactive=False,
                     showatm=True,
                     pwv='auto',
                     chanrange='92.1875%',
                     showfdm=True,
                     field='', 
                     figfile='plots/'+filename+'.tsys.plots.overlayTime/'+filename+'.tsys')
        
        # Create png plots for Tsys per source with antennas
        es.checkCalTable(filename+'.tsys', msName=filename, interactive=False)
	os.system('rm -rf plots/'+filename+'.tsys.plots') 
        os.system('mv '+filename+'.tsys.plots  plots/.') 
    
    # 2.3 Do initial flagging 
    print "2.3 Initial flagging, reading flags in file file_flags.py. You can modify this file to add more flags"    
    extract_flagging(filename,pipeline)    # Extract flags from original ALMA calibration script (sdflag entries)
    if os.path.exists('../script/file_flags.py'): execfile('../script/file_flags.py')
    
    
    # 2.4 Create Tsys map 
    print "2.4 Creating Tsysmaps" 
    # Read spws and frquencies for science and tsys
    spws_scie,spws_tsys,freq_rep_scie,freq_rep_tsys = spws_info[0:4]
    
    from recipes.almahelpers import tsysspwmap
    tsysmap = tsysspwmap(vis = filename, tsystable = filename+'.tsys', trim = False)
    
    print "Spectral windows for science are: ",spws_scie,freq_rep_scie
    print "Spectral windows for tsys are   : ",spws_tsys,freq_rep_tsys
    print "Original map between science and tsys spws: (they should have the same frequency)"
    for i in range(len(spws_scie)): print spws_scie[i],tsysmap[spws_scie[i]]
    
    tsysmap = get_tsysmap(tsysmap,spws_scie,spws_tsys,freq_rep_scie,freq_rep_tsys)
    
    spwmap = {}
    for i in spws_scie:
        if not tsysmap[i] in spwmap.keys():
            spwmap[tsysmap[i]] = []
        spwmap[tsysmap[i]].append(i)
    
    return spwmap

#-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
# Step 3  From counts to Kelvin
#-*-*-*-*-*-*-*-*-*-*
def counts2kelvin(filename,ant,spwmap,spws_info,doplots=False):
    
    print "=================================="
    print "= Step 3 - From counts to Kelvin ="
    print "=================================="
    
    if checkdir(os.getcwd(),path_galaxy) == False:  os.chdir('../'+path_galaxy+'calibration')
    if os.path.isdir("plots/") == False:     os.system('mkdir plots')       # folder containing all plots
    
    # Get string with needed spws to apply Tsys
    spws_scie_str,spws_tsys_str,spws_all_str = str_spw_apply_tsys(spws_info)
        
    print "3.1 Converting data into Kelvin Ta* = Tsys * (ON-OFF)/OFF"
    fin    = '.asap'  
    finout = '.asap.2'
    
    filename_in  = filename+'.'+ant+fin
    filename_out = filename+'.'+ant+finout
    
    os.system('rm -Rf '+filename_out)
    sdcal2(infile = filename_in,
            calmode = 'ps,tsys,apply',
            spw = spws_all_str,
            tsysspw = spws_tsys_str,
            spwmap = spwmap,
            outfile = filename_out,
            overwrite = True)
    
    if doplots == True: es.SDcheckSpectra(filename_out, spwIds=spws_scie_str, interactive=False)
    
    print "3.2 Applying non-linearity correction factor if data were obtained before the 2015-10-01"  
    
    apply_nl = check_date_nonlinearity(filename)
    if apply_nl == True:
        sdscale(infile = filename_out,
                outfile = filename_out,
                factor = 1.25,
                overwrite=True)


#-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
# Step 4  Extract the cube including the line
#-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
def extract_cube(filename,source,ant,freq_rest,vel_source,spws_info,vel_cube,doplots=False):
    
    print "========================================================="
    print "= Step 4 - Extracting cube including the requested line ="
    print "========================================================="
    
    if checkdir(os.getcwd(),path_galaxy) == False:  os.chdir('../'+path_galaxy+'calibration')
    if os.path.isdir("plots/") == False:     os.system('mkdir plots')       # folder containing all plots
    if os.path.isdir("obs_lists/") == False: os.system('mkdir obs_lists')   # folder containing all observation lists (i.e., listobs, sdlist)
    
    # Defining extensions
    fin    = '.asap.2'
    finout = '.asap.3'
    
    filename_in  = filename+'.'+ant+fin
    filename_out = filename+'.'+ant+finout
    
    # Plotting the line
    if doplots == True: 
        os.system('rm -Rf plots/'+filename+'.'+ant+fin+'.spec.png')
        print "4.1 Plotting each spw for each antenna"
        sdplot(infile=filename+'.'+ant+fin,plottype='spectra', specunit='channel', timeaverage=True,stack='p',outfile='plots/'+filename+'.'+ant+fin+'.spec.png')
    
    # Get the spw where the requested line is located
    spw_line = get_spw_line(vel_source,freq_rest,spws_info)
    
    print "Velocity of the source: ",vel_source," km/s. The line emission is in the SPW ",spw_line
    
    # Get the string of the channels to be extracted from the original cube
    coords = read_source_coordinates(filename,source)
    chan1_cube,chan2_cube = convert_vel2chan(filename,freq_rest,vel_cube,spw_line,vel_source,spws_info,coords)
    spw_extr = str(spw_line)+":"+str(chan1_cube)+"~"+str(chan2_cube)
    
    print "4.2 Extracting a cube with the line"
    
    os.system('rm -Rf '+filename_out)
    sdsave(infile=filename_in,
           field=source,
           spw=spw_extr,
           outfile=filename_out)
    
    os.system('rm -Rf obs_list/'+filename_out+'.list')
    sdlist(infile=filename_out,
           outfile='obs_list/'+filename_out+'.list') 
    
    if doplots == True: 
        print "4.3 Plotting the line averaged in time"    
        sdplot(infile=filename_out,
               plottype='spectra', 
               specunit='km/s', 
               restfreq=str(freq_rest)+'MHz',
               timeaverage=True, 
               stack='p',
               polaverage=True)

#-*-*-*-*-*-*-*-*-*-*-*-*-*-*
# Step 5 Baseline correction
#-*-*-*-*-*-*-*-*-*-*

def baseline(filename,source,ant,freq_rest,vel_source,spws_info,vel_line,bl_order):
    print "================================"
    print "= Step 5 - Baseline correction ="
    print "================================"
    
    if checkdir(os.getcwd(),path_galaxy) == False:  os.chdir('../'+path_galaxy+'calibration')
    if os.path.isdir("plots/") == False:     os.system('mkdir plots')       # folder containing all plots
    
    # Definition of extension
    fin    = '.asap.3'
    finout = '.asap.4'
    
    filename_in  = filename+'.'+ant+fin
    filename_out = filename+'.'+ant+finout
    
    # Extract the ID of the spw where the line is
    spw_line = get_spw_line(vel_source,freq_rest,spws_info)
    
    # Convert the velocity range in channels and get spw string for baseline fitting
    coords   = read_source_coordinates(filename,source)
    spw_extr = str_spw4baseline(filename_in,freq_rest,vel_line,spw_line,coords)
    
    # Subtracting the baseline
    os.system('rm -Rf '+filename_out)
    sdbaseline(infile = filename_in,
           spw = spw_extr,
           maskmode = 'list',
           blfunc = 'poly',
           order = bl_order,
           outfile = filename_out,
           overwrite = True)  
    
    if doplots == True:
        # PLotting the result from the baseline correction. Spectra avergarfed in time  
    	os.system('rm -Rf plots/'+filename_out+'_baseline_corrected.png')
        sdplot(infile=filename_out,
               plottype='spectra', 
               specunit='km/s', 
               restfreq=str(freq_rest)+'MHz', 
               timeaverage=True, 
               stack='p',
               outfile='plots/'+filename_out+'_baseline_corrected.png',
               polaverage=True)

    os.system('mv  *blparam.txt  obs_lists/')

#-*-*-*-*-*-*-*-*-*-*-*-*-*-*
# Step 6 Concatenate antennas
#-*-*-*-*-*-*-*-*-*-*
def concat_ants(filename,vec_ants,vel_source,freq_rest,spws_info,pipeline):
    
    print "========================================================"
    print "= Step 6 - Concatenate antennas and K to Jy conversion ="
    print "========================================================"
    
    if checkdir(os.getcwd(),path_galaxy) == False:  os.chdir('../'+path_galaxy+'calibration')
    
    # Defining extensions
    fin    = '.asap.4'
    finout = '.ms.5'
    
    # Extract the ID of the spw where the line is
    spw_line = get_spw_line(vel_source,freq_rest,spws_info)
    
    # Converting from ASAP to MS
    print "6.1 Converting from ASAP to MS"
    lis_fils = [f for f in os.listdir(".") if f.endswith(fin) and f.startswith(filename)]
    vec_As   = [lis_fils[i].split("ms.")[1].split(".asap")[0] for i in range(len(lis_fils))]
    
    for f in lis_fils : 
        filout = f.replace(fin,finout)
        os.system('rm -Rf '+filout)
        sdsave(infile = f,
            outfile = filout,
            outform='MS2')
    
    # Concatenation
    print "6.2 Concatenating antennas"
    lis_fils = [f for f in os.listdir(".") if f.endswith('.ms.5') and f.startswith(filename)]
    os.system('rm -Rf '+filename+'.cal')
    concat(vis = lis_fils,concatvis = filename+'.cal')
    
    # Convert the Science Target Units from Kelvin to Jansky   
    print " 6.3 Convert the Science Target Units from Kelvin to Jansky"
    jyperk = extract_jyperk(filename,pipeline)
    
    os.system('rm -Rf '+filename+'.cal.jy')
    os.system('cp -Rf '+filename+'.cal '+filename+'.cal.jy')
    
    for ant in vec_As:
        print ant,spw_line
        scaleAutocorr(vis=filename+'.cal.jy', scale=jyperk[ant][spw_line]['mean'], antenna=ant, spw=spw_line)
        
    # Rename line spw to spw=0
    print "6.4 Renaming spw of line, "+str(spw_line)+" to 0"
    fin = '.cal.jy'
    finout = '.cal.jy.tmp'
    
    split(vis=filename+fin,
         outputvis=filename+finout,
         datacolumn='all')
    
    os.system('rm -Rf '+filename+fin)
    os.system('mv '+filename+finout+' '+filename+fin)
    listobs(vis=filename+fin,listfile=filename+fin+'.listobs')

#-*-*-*-*-*-*-*-*-*-*-*-*-*-*
# Step 7 - Imaging
#-*-*-*-*-*-*-*-*-*-*
def imaging(source,name_line,phcenter,vel_source,source_vel_kms,vwidth_kms,chan_dv_kms,freq_rest_im,doplots=False):
    
    print "===================="
    print "= Step 7 - Imaging ="
    print "===================="
    
    if checkdir(os.getcwd(),path_galaxy) == False:  os.chdir('../'+path_galaxy+'calibration')
    
    fwhmfactor = 1.13                               # Factor to estimate the ALMA theoretical beam 
    diameter   = 12                                 # Diameter of ALMA antennas in meters
    
    # Search for files already calibrated
    path = '.'
    Msnames = [f for f in os.listdir(path) if f.endswith('.cal.jy')]
    
    # If 2 SGs have to be imaged together, look for *cal.jy files for the second part of the galaxy 
    if 'path_galaxy2' in globals() and image_2gals == True : 
        path2 = ori_path+'/../'+path_galaxy2+'calibration/'
        Msnames2 = [path2+f for f in os.listdir(path2) if f.endswith('.cal.jy')]
        Msnames = Msnames+Msnames2
    
    # Definition of parameters for imaging
    xSampling,ySampling,maxsize = aU.getTPSampling(Msnames[0],showplot=False)
    
    # Read frequency
    msmd.open(Msnames[0])
    freq = msmd.meanfreq(0)
    msmd.close()
    
    # Coordinate of phasecenter read from the data or used as input
    if phcenter == False:
        coord_phase = read_source_coordinates(Msnames[0],source)
        print "Coordinate of phasecenter, read from the data: "
        print coord_phase
    else:
        print "Coordinate of phasecenter entered by the user: "
        coord_phase = phcenter
        print coord_phase
    
    # Source velocity for imaging, read from the data or used as input
    if source_vel_kms == False:
        source_vel_kms = vel_source
        print "Velocity of source used for imaging read from the data: "
        print source_vel_kms
    else:
        print "Velocity of source used for imaging entered by the user: "
        source_vel_kms = source_vel_kms 
        print source_vel_kms
    
    theorybeam = fwhmfactor*c_light*1e3/freq/diameter*180/pi*3600
    cell       = theorybeam/9.0
    if 'factorim' in globals():  
        imsize  = int(round(maxsize/cell)*factorim)
    else:
        imsize     = int(round(maxsize/cell)*1.5)
        
    start_vel      = source_vel_kms-vwidth_kms/2
    nchans_vel     = int(round(vwidth_kms/chan_dv_kms))
    
    os.system('rm -Rf ALMA_TP.'+source+'.'+name_line+'.image')
    
    print "Start imaging"
    print "Imaging from velocity "+str(start_vel)+", using "+str(nchans_vel)+" channels."
    print "rest frequency is "+str(freq_rest_im)+" GHz."
    sdimaging(infiles = Msnames,
        mode = 'velocity',
        nchan = nchans_vel,
        width = str(chan_dv_kms)+'km/s',
        start = str(start_vel)+'km/s',
        veltype  = "radio",
        outframe = 'LSRK',
        restfreq = str(freq_rest_im)+'GHz',
        gridfunction = 'SF',
        convsupport = 6,
        phasecenter = coord_phase,
        imsize = imsize,        
        cell = str(cell)+'arcsec',
        overwrite = True,
        outfile = 'ALMA_TP.'+source+'.'+name_line+'.image')
    
    print imsize
    # Correct the brightness unit in the image header  
    imhead(imagename = 'ALMA_TP.'+source+'.'+name_line+'.image',
        mode = 'put',
        hdkey = 'bunit',
        hdvalue = 'Jy/beam')
    
    # Add Restoring Beam Header Information to the Science Image    
    minor, major, fwhmsfBeam, sfbeam = aU.sfBeam(frequency=freq*1e-9,
        pixelsize=cell,
        convsupport=6,
        img=None, #to use Gaussian theorybeam
        stokes='both',
        xSamplingArcsec=xSampling,
        ySamplingArcsec=ySampling,
        fwhmfactor=fwhmfactor,
        diameter=diameter)
    
    ia.open('ALMA_TP.'+source+'.'+name_line+'.image')
    ia.setrestoringbeam(major = str(sfbeam)+'arcsec', minor = str(sfbeam)+'arcsec', pa = '0deg')
    ia.done()
    
    if doplots == True: viewer('ALMA_TP.'+source+'.'+name_line+'.image')


#-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
# Step 8 - Export fits file
#-*-*-*-*-*-*-*-*-*-*-*-*-*

def export_fits(name_line,source):    
    
    if os.path.isdir(ori_path+'/../products') == False:     
        os.system('mkdir '+ori_path+'/../products')       # folder containing all plots
    
    if checkdir(os.getcwd(),path_galaxy) == False:  os.chdir('../'+path_galaxy+'calibration')
    
    # Export to fits file
    os.system('rm -Rf  '+ori_path+'/../products/ALMA_TP.'+source+'.'+name_line+'.image.fits')
    os.system('rm -Rf  '+ori_path+'/../products/ALMA_TP.'+source+'.'+name_line+'.image.weight.fits')
    exportfits(imagename = 'ALMA_TP.'+source+'.'+name_line+'.image', 
               fitsimage = ori_path+'/../products/ALMA_TP.'+source+'.'+name_line+'.image.fits')
    exportfits(imagename = 'ALMA_TP.'+source+'.'+name_line+'.image.weight', 
               fitsimage = ori_path+'/../products/ALMA_TP.'+source+'.'+name_line+'.image.weight.fits')
    


#-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
# Main body TP ALMA data reduction. 
#-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*

print "=================================="
print " Starting TP ALMA data reduction  "
print "==================================\n"

print "> You are executing the ALMA-TP-pipeline script from the directory: "
print os.getcwd() + "\n"

ori_path = os.getcwd()                      # Current directory

checktmp()                                  # check if the tmp folder exists. If not, do it and copy the data.

print "> Changing directory to "+path_galaxy+'calibration'+"\n"
os.chdir('../'+path_galaxy+'calibration')   # Working on the calibration folder of the current galaxy

pipeline = checkpipeline()                  # Pipeline reduced data (True or False)

# Defining Execution Blocks (EBS) names
if pipeline == True: 
    EBsnames = [f for f in os.listdir(path_raw) if f.endswith('.asdm.sdm')]
else: 
    EBsnames = [f for f in os.listdir(path_script) if f.endswith('.scriptForSDCalibration.py')]

if len(do_step) == 0: do_step = [1,2,3,4,5,6,7,8]

if 'EBexclude' in globals(): 
   EBsnames = [s for s in EBsnames if s not in EBexclude]

# Do data reduction for each EB 
for EBs in EBsnames:
    
    if pipeline == False:
        EBs = EBs.replace('.ms.scriptForSDCalibration.py', '.asdm.sdm')      
    filename = 'u'+re.search('u(.+?).asdm.sdm', EBs).group(1)+'.ms'       
    file_exists = check_exists(filename)                             # Check weather the raw data exists
    if file_exists == True:
        if 1 in do_step: import_and_split_ant(filename,doplots)      # Import and split data per antenna
        vec_ants_t = read_ants_names(filename)                       # Read vector with name of all antennas
        vec_ants   = [s for s in vec_ants_t if any(xs in s for xs in ['PM','DV'])] # Get only 12m antennas.
        vel_source = read_vel_source(filename,source)                # Read source velocity
        spws_info  = read_spw(filename,source)                       # Read information of spws (science and Tsys)

        if 2 in do_step: spwmap = gen_tsys_and_flag(filename,spws_info,pipeline,doplots) 
        for ant in vec_ants: 
            if 3 in do_step: counts2kelvin(filename,ant,spwmap,spws_info,doplots)
            if 4 in do_step: extract_cube(filename,source,ant,freq_rest,vel_source,spws_info,vel_cube,doplots) 
            if 5 in do_step: baseline(filename,source,ant,freq_rest,vel_source,spws_info,vel_line,bl_order)   
        if 6 in do_step: concat_ants(filename,vec_ants,vel_source,freq_rest,spws_info,pipeline)  
                       
if 7 in do_step: imaging(source,name_line,phase_center,vel_source,source_vel_kms,vwidth_kms,chan_dv_kms,freq_rest_im,doplots)
if 8 in do_step: export_fits(name_line,source)


print " Changing directory to "+ori_path+'\n'
os.chdir(ori_path)
