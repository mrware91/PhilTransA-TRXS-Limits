from IPython.display import Audio
from IPython.display import clear_output

import os
import shlex, subprocess
import threading
import time
import re
import pickle

try:
    os.environ['OUTPUTPATH']
except KeyError as e:
    print('Did you remember to specify os.environ[\'OUTPUTPATH\']?')
    raise e
    
    BATCHDIR = os.environ['OUTPUTPATH'] + '/Batch'
        
#################################################################################################
# Batch job terminal commands
#################################################################################################

def unixCMD( cmd ):
    cmd='ssh psana \'%s\'' % cmd
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, executable='/bin/bash')
    (stdoutdata, stderrdata) = process.communicate()
    return stdoutdata, stderrdata

def bjobs():
    cmd='ssh psana \'bjobs\''
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, executable='/bin/bash')
    (stdoutdata, stderrdata) = process.communicate()
    return stdoutdata, stderrdata

def bkill( jobid = None , killAll = False ):
    cmd = ''
    if jobid is not None:
        cmd='ssh psana \'bkill %s\'' % jobid
    if killAll:
        cmd='ssh psana \'bkill 0\'' 
        
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, executable='/bin/bash')
    (stdoutdata, stderrdata) = process.communicate()
    return stdoutdata, stderrdata

def checkActive(jobid):
    stdoutdata, stderrdata = bjobs()
    return ( jobid in stdoutdata )

def extractJobId(batchOutput):
    m = re.search('<\d\d\d\d\d\d>', batchOutput)
    return m.group(0)[1:-1]    
        

#################################################################################################
# Submit batch job function
#################################################################################################

def SubmitBatchJob(Job,RunType='mpirun python2',Nodes=32,Memory=7000,Queue='psnehprioq',OutputName='temp'):
    
    # Make output directories if they do not exist
    if not os.path.isdir(os.environ['OUTPUTPATH']+'/Batch'):
        os.mkdir(os.environ['OUTPUTPATH']+'/Batch')
        
    if not os.path.isdir(os.environ['OUTPUTPATH']+'/Batch/Output'):
        os.mkdir(os.environ['OUTPUTPATH']+'/Batch/Output')
        
    if not os.path.isdir(os.environ['OUTPUTPATH']+'/Batch/Python'):
        os.mkdir(os.environ['OUTPUTPATH']+'/Batch/Python')
    
    # Specify output directory
    OutputTo=os.environ['OUTPUTPATH']+'/Batch/Output/'+OutputName+'.out'
    BatchFileName=os.environ['OUTPUTPATH']+'/Batch/Python/'+'%s.py'%OutputName
 
    print "Deleting the old output file ..."
    process = subprocess.Popen(shlex.split("rm %s" % OutputTo), stdout=subprocess.PIPE)
    output, error = process.communicate()
    print "Output: " + str(output)
    print "Error: " + str(error)    


    # Generate executable python file
    bfile = open(BatchFileName, 'w')
    for line in Job:
        bfile.write("%s \n" % line)
    bfile.close()
    
    # Execute batch command
    BatchCommand="ssh psana \'bsub -n %d -R \"rusage[mem=%d]\" -q %s -o %s /reg/neh/home/mrware/TRXS/Libraries/pythonBatchMagic/BatchWrapper.sh %s %s\'" % \
                                        (Nodes,Memory,Queue,OutputTo,RunType,BatchFileName)  
    
#     print(BatchCommand)
    
    print "Submitting: "+BatchCommand
    process = subprocess.Popen(BatchCommand, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, executable='/bin/bash')
    output, error = process.communicate()
    
    nerror = 0
    errorMax = 10
    while "ssh_exchange_identification" in error:
        print "Submitting again: "+BatchCommand
        process = subprocess.Popen(BatchCommand, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, executable='/bin/bash')
        output, error = process.communicate()
        nerror += 1
        if nerror > errorMax:
            print("Too many rejections")
            break
        
    
    print "Output: " + str(output)
    print "Error: " + str(error)    
    
    return extractJobId( str(output) )
    

#################################################################################################
# Threading for batch jobs
#################################################################################################    

class batchThread (threading.Thread):
    def __init__(self, Job):
        threading.Thread.__init__(self)
        
        # Specify job and batch job parameters
        self.Job = Job
        self.RunType = 'mpirun python2'
        self.Nodes = 1
        self.Memory = 7000
        self.Queue = 'psnehq'
        self.OutputName = 'temp'
        
        # Save internally the batch job id and run status
        self.jobid = None
        self.status = 'Initialized'
        self.flag = None


    def run(self):
        self.status = 'Running'
        
        self.jobid = SubmitBatchJob(self.Job ,
                                   RunType=self.RunType,
                                   Nodes=self.Nodes,
                                   Memory=self.Memory,
                                   Queue=self.Queue,
                                   OutputName=self.OutputName)
        
        forcedStop = False
        time.sleep(10)
        
        while checkActive( self.jobid ):
            if self.flag == 'Stop requested':
                bkill( jobid = self.jobid )
                forcedStop = True
                break
                
        if forcedStop:
            self.status = 'Stopped'
        else:
            self.status = 'Finished'
        
        
    def requestStop(self):
        self.flag = 'Stop requested'
    

    
# #################################################################################################
# # Sample use of batch job function
# #################################################################################################

# def MakePointData(Run,Experiment=None,Queue='psnehq'):
#     if Experiment is None:
#         Experiment="None"
        
#     Job=["import os",
#          "CodeDir=os.environ[\'CodeDir\']",
#          "print CodeDir",
#          "import sys",
#          "sys.path.insert(0, \'%s/Python\'%CodeDir)",
#          "from LCLS import *",
#          "GetPointData(RunNumber=%d,ExperimentName=%s,MaxEvents=1e8,GatherInterval=1e9,ConfigName=\'mrware\')" % (Run,Experiment)]
    
#     SubmitBatchJob(Job,
#                    RunType='mpirun python2',
#                    Nodes=16,
#                    Memory=1000,
#                    Queue=Queue,
#                    OutputName='Pointdata-%d' % Run)
    
#     print "Point data request has been submitted to batch queue. You may use %bjobs to watch for when your job completes."
    
# #################################################################################################
# # Sample use of batch job function leveraging rank and size of job
# #################################################################################################

# def MakePointDataPart(Rank,Size,Run,Experiment=None,Queue='psnehq'):
#     if Experiment is None:
#         Experiment="None"
        
#     Job=["import os",
#          "CodeDir=os.environ[\'CodeDir\']",
#          "print CodeDir",
#          "import sys",
#          "sys.path.insert(0, \'%s/Python\'%CodeDir)",
#          "from LCLS import *",
#          "GetPointDataPart(Rank=%d,Size=%d,RunNumber=%d,ExperimentName=%s,MaxEvents=1e8,GatherInterval=1e9,ConfigName=\'mrware\')" % (Rank,Size,Run,Experiment)]
    
#     SubmitBatchJob(Job,
#                    RunType='python2',
#                    Nodes=1,
#                    Memory=1000,
#                    Queue=Queue,
#                    OutputName='Pointdata-%d-%d' % (Rank,Run))
    
#     print "Point data request has been submitted to batch queue. You may use %bjobs to watch for when your job completes."   