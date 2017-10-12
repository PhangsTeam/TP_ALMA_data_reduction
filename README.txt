# TP_ALMA_data_reduction
New version of the phangs_scripts_TP_ALMA repository, using an updated directory tree

Scripts for Total Power (TP) ALMA data reduction and imaging.

###########################################################################

Basics: How does it work?
-------------------------

The ALMA total power reduction executes the follwing steps:
  1: import_and_split_ant - Import data to MS and split by antenna    (adsm   -> asap)
  2: gen_tsys_and_flag    - Generate tsys cables and apply flags      (create .tsys and swpmap)
  3: counts2kelvin        - Calibration of Tsys and convert data to K (asap   -> asap.2)
  4: extract_cube         - Extract cube with line                    (asap.2 -> asap.3)
  5: baseline             - Baseline correction                       (asap.3 -> asap.4)
  6: concat_ants          - Concatenate all antennas                  (asap.4 -> ms.5 -> cal.jy)
  7: imaging              - Imaging and fix the header                (cal.jy -> image)
  8: export_fits          - Export image and weight to a fits file    (image  -> fits)


To do this, the sources are spread in three files:

  - analysis_scripts
    ALMA provided folder that contains useful tools to be used during the
    TP ALMA data reduction. You should not modify any of the scripts in
    this folder.

  - ALMA-TP-tools.py
    Script which contains the generic procedures for total power data
    reduction and imaging. You should not modify this script.

  - ALMA-TP-pipeline-GalaxyName.py
    Galaxy specific scripts that encode our own data reduction. This script
    uses the two previous code source.

###########################################################################

Additional information about the TP calibration process
-------------------------------------------------------

1. For some observations (galaxies: NGC 1087, NGC 1385, NGC 1300, NGC 1433,
   NGC 1566) there was an atmospheric line in the bandpass that could not
   be automatically reduced in CASA. In these cases, only a zero order
   baseline was subtracted. After executing all steps from 1 to 8, we went
   to GILDAS\CLASS to make a 2nd round of baseline subtraction
   piecewise. If required, the GILDAS\CLASS scripts can be shared.

2. The ALMA TP data can originally be reduced by JAO or any of the ARC
   nodes using scripts or by an automatized pipeline. Depending on who does
   the data reduction, our scripts should have slightly different behaviors
   to apply the flagging and to convert from Kelvin to Jansky per beam.

   FLAGGING: 

   - For all data, an apriori flagging is applied during step 1
     (import_and_split_ant, see above). This includes flags such as: mount
     off source, calibration device is not in correct position, power
     levels are not optimized, WCA not loaded.
     
   - In addition, other flags can be applied during step 2
     (gen_tsys_and_flag, see above) :

       + For data previously reduced with scripts, the ALMA data reducer
	 may have added additional flags that are stored in the
	 scriptForSDCalibration.py script in the "script" folder.
	 For pipeline reduced data, no flag will be applied.

       + If you whish to add additional flags, you need to create a file 
       	 describing the flags to be done using the "sdflag" task under the 
	 name "scripts_TP/flags_folder/fileflagGalNam.py". For instance:
         > cat fileflagNGC_4535.py
	 sdflag(infile = 'uid___A002_Xb1d975_X2260.ms.PM02.asap',
  	    		  mode = 'manual',
  			  scan = '11,12',
  			  overwrite = True)


   JYPERK: 

   - For script reduced data, the information about the conversion from Kelvin
     to Jansky is stored in the scriptForSDCalibration.py scripts in the
     "script" folder.

   - For the pipeline reduced data, the same information is stored in a file
     called jyperk.csv in the calibration folder.

   - The ALMA-TP-tool.py script will check if the data was reduced by the 
     pipeline or not and will look for this information accordingly.

###########################################################################

What you have to do for galaxy NGC_1672
----------------------------------------

1. Getting scripts and setting the directory tree:

   - Download the zip file from the Github https://github.com/cnherrera/TP_ALMA_data_reduction/
     by clicking the Green bouton "Clone or download". 
     
   - Place the TP_ALMA_data_reduction-master.zip file you downloaded from the github in your 
     HOME PHANGS-data-reduction folder. Unzip it and change the name to "scripts_TP".
     
   - Create a "raw" file at the same level as the "script_TP" folder. We will work in the 
     following directory tree:
	 
          PHANGS-data-reduction
	  ├── products       ! Automatically created. Final fits files.
	  ├── tmp	     ! Automatically created. Temporal folder for data reduction.
	  ├── raw	     ! Original ALMA data.
	  │   ├── 2015.1.00925.S
	  │   │   ├── 2015.1.00925.S
	  │   │   │   ├── science_goal.uid___A001_X2fe_X2ba
	  │   │   │   ├── science_goal.uid___A001_X2fe_X2c4
	  │   │   │   ├── ...
	  │   │   │   └── science_goal.uid___A001_X2fe_X332
	  │   │   └── 2015.1.00925.S.readme.txt
	  │   └── 2015.1.00956.S
	  │       ├── 2015.1.00956.S
	  │       │   ├── science_goal.uid___A001_X2fb_X271
	  │       │   ├── science_goal.uid___A001_X2fb_X27b
	  │       │   ├── ...
	  │       │   └── science_goal.uid___A001_X2fb_X2df
	  │       └── 2015.1.00956.S.readme.txt
	  └── scripts_TP     ! Contains the TP scripts for data reduction.
	      ├── ALMA-TP-pipeline-NGC_1672.py
	      ├── ALMA-TP-pipeline-...
	      ├── ALMA-TP-tools.py
	      ├── analysis_scripts
	      └── flags_folder
	          ├── fileflagNGC_1672.py
	          └── ...

2. Getting the ALMA data:

     - Donwload from the ALMA Science Archive Query (http://almascience.nrao.edu./aq/) the files under the 
       Member OUS of the TP observations for a given ALMA project (i.e  the product and the raw files). 
       Do NOT download the "semipass" files. Place the tar files in the "raw" folder (see point 1).

     - Within the "raw" folder, untar the "product" file (uid..._001_of_001.tar) and the uid....asdm.sdm files. 
       They will be automatically placed in the standard ALMA directory tree. 
       Example for ALMA directory tree, under the raw folder, after untaring thes file for galaxy NGC_1672 
       in project 2015.1.00956.S:

       # ALMA Directory tree, under the "raw" folder 
	2015.1.00956.S
	└── 2015.1.00956.S
	    └── science_goal.uid___A001_X2fb_X271
		└── group.uid___A001_X2fb_X272
		    └── member.uid___A001_X2fb_X279
			├── calibration   
			├── log            
			├── product       
			├── qa           
			├── raw           
			├── script        
			└── README        

      If you wish, you can read the ALMA README file for comments from the
      ALMA data reducer and for further description of the folders.

3. Running the scripts

     - In the "scripts_TP" folder, untar the analysis_script.tar file included in the zipped file.
     
     - In the "scripts_TP" folder, modify the "ALMA-TP-pipeline-NGC_1672.py" if you wish to modify the 
       parameters used in the data reduction or imaging. State the step of the data reduction you
       want to perform. 

     - In the "scripts_TP" folder, start a CASA session and:
       CASA> execfile('ALMA-TP-pipeline-NGC_1672.py')

     - Two additional folders will be created at the same level as the scripts_TP folder, 
       products and tmp (see point 1 for directory tree):
       
       + PRODUCTS: It will contain the final fits files.

       + TMP: Temporal folder where the TP data reduction happens. Once you have
       	      finished the data reduction, you can delete this folder. Raw data
	      will be stored in the original ALMA folder.

	      The "tmp" folder is a replica of the original ALMA folder, where only 
	      the needed files are copied. Data reduction will be done here, specifically in 
	      the "calibration" folder (see directory tree in point 2). In the 
	      "calibration" folder, two additional folders will be created: "plots" 
	      and "obs_lists".
	           + PLOTS folder: This folder contains all plots created by the data 
		     	   	   reduction scripts. For instance, the Tsys and the 
				   baseline correction plots. Using such plots, you 
				   can judge the quality of the data.
		   + OBS_LISTS folder: This folder contains the observation lists of 
		     	       	       the data.


###########################################################################
