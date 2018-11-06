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

try:
    os.environ['INSTALLPATH']
except KeyError as e:
    print('Did you remember to specify os.environ[\'INSTALLPATH\']?')
    raise e
    
# Load in the default LCLS libraries
import sys
sys.path.insert(0, os.environ['INSTALLPATH']+'/Libraries/LCLS')
from LCLSdefault import *

sys.path.insert(0, os.environ['INSTALLPATH']+'/Libraries/mattsTools')
from picklez import *

# Load in the get data library
from dataAnalysis import *

# Load in batch libraries
sys.path.insert(0, os.environ['INSTALLPATH']+'/Libraries/pythonBatchMagic')
from pythonBatchMagic import *

#################################################################################################
# Point data grabber
#################################################################################################

# code for individual nodes
def nodePointDataGrabber( eventMax=10, experiment='xppl2816', run=74, node=None, rank=None):
    '''
    Description: This function takes in a list of detector names, 
    specifies number of events, which experiment, and which run to look at
    
    Input:
        eventMax: Maximum number of events to read (integer)
            Default: 10
        experiment: Experiment name (string)
            Default: xppl2816
        run: Run number (integer)
            Default: 74
        node: Which node is the code running on
        rank: How many nodes is the batch job running across
    
    Output:
        None. Saves result to os.environ['OUTPUTPATH']+'/Batch/Output/nodePointDataGrabber%d' % node
    
    '''
    
    detDict = load_obj( os.environ['OUTPUTPATH']+'/Batch/Output/detDict' )

    print('Grabbing run %d from experiment %s') % (run , experiment)
    
    # Create a data source to grab data from
    ds = DataSource('exp=%s:run=%d' % (experiment , run) )
    
    # Generate detList from detDict
    detList = detDict.keys() 
    
    # Create empty dictionary to store names of detectors in
    detObjs = {name:'' for name in detList} 
    
    for name in detList:
        # gets name of detectors and stores in dictionary
        try:
            detObjs[name] = Detector( detDict[name]['name'] )
        except KeyError as e:
            detObjs[name] = None
    
    
    # Create empty dictionary to store
    detArrays = { name:np.zeros((eventMax,1)) for name in detList }
    
    # for each detector (named), use .sum(evt) to grab data stored
    # store that in the dictionary
    for nevent, evt in enumerate(ds.events()):
        if nevent == eventMax: break
            
        if np.mod( nevent,rank ) != node:
            continue
        
        # Always grab seconds, nanoseconds, fiducials to enable memorization
        seconds = getSeconds( evt )
        nanoseconds = getNanoseconds( evt )
        fiducials = getFiducials( evt )
        
        # Now grab user specified detectors
        for name in detList:
            getFunc = eval(detDict[name]['get-function'])
            detArrays[name][nevent] =  getFunc( evt, detObjs[name], 
                                                                     run=run, experiment=experiment, 
                                                                     seconds=seconds, nanoseconds=nanoseconds, fiducials=fiducials)
        
    save_obj( detArrays , os.environ['OUTPUTPATH']+'/Batch/Output/nodePointDataGrabber%d' % node )
    
    
    
# thread for submitted 
class batchPointDataGrabber (threading.Thread):
    def __init__(self, detDict, eventMax=10, experiment='xppl2816', runNumber=74, rank=1 ):
        threading.Thread.__init__(self)
        
        # Specify function parameters
        self.detDict = detDict
        self.eventMax = eventMax
        self.experiment = experiment
        self.runNumber = runNumber
        self.batchRank = rank
        
        # Specify batch job parameters
        self.RunType = 'mpirun python2'
        self.Nodes = 1
        self.Memory = 1000
        self.Queue = 'psnehq'
        self.OutputName = 'temp'
        
        # Save internally the batch job ids and run status
        self.subthreads = []
        self.status = 'Initialized'
        self.flag = None
        
        # Save the final output
        self.detArrays = None


    def run(self):
        self.status = 'Running'
        save_obj( self.detDict , os.environ['OUTPUTPATH']+'/Batch/Output/detDict' )
        
        for node in range(0,self.batchRank):
            try:
                os.remove( os.environ['OUTPUTPATH']+'/Batch/Output/nodePointDataGrabber%d.pkl' % node )
            except Exception:
                pass
        
        for node in range(self.batchRank):
            if self.flag == 'Stop requested':
                break
                
            batchJob = ['import os',
                        'os.environ[\'INSTALLPATH\']=\'%s\''% os.environ['INSTALLPATH'],
                        'os.environ[\'OUTPUTPATH\']=\'%s\'' % os.environ['OUTPUTPATH'],
                        'import sys',
                        'sys.path.insert(0, os.environ[\'INSTALLPATH\']+\'/Libraries/pythonBatchMagic\')',
                        'from lclsBatch import *',
                        'nodePointDataGrabber( eventMax=%d, experiment=\'%s\', run=%d, node=%d, rank=%d)' % (self.eventMax, self.experiment,self.runNumber,node,self.batchRank)]
            
            myBatchThread = batchThread( batchJob )
            myBatchThread.RunType = self.RunType
            myBatchThread.Nodes = self.Nodes
            myBatchThread.Memory = self.Memory
            myBatchThread.Queue = self.Queue
            myBatchThread.OutputName = self.OutputName+'%d' % node
            myBatchThread.start()
            self.subthreads.append( myBatchThread )
            
            time.sleep(5)
            
        
        forcedStop = False
        time.sleep(10)
        
        while self.checkStatus():
            if self.flag == 'Stop requested':
                [athread.requestStop() for athread in self.subthreads]
                forcedStop = True
                break
                
        if forcedStop:
            self.status = 'Stopped'
        else:
            self.status = 'Gathering'
            self.gather()
            self.status = 'Finished'
        
        
    def requestStop(self):
        self.flag = 'Stop requested'
        
    def checkStatus(self):
        if 'Running' in [athread.status for athread in self.subthreads]:
            return True
        elif 'Initialized' in [athread.status for athread in self.subthreads]:
            return True
        else:
            return False
        
    def gather(self):
        self.detArrays = load_obj( os.environ['OUTPUTPATH']+'/Batch/Output/nodePointDataGrabber%d' % 0 )
        for node in range(1,self.batchRank):
            detArrays0 = load_obj( os.environ['OUTPUTPATH']+'/Batch/Output/nodePointDataGrabber%d' % node )
            for key in self.detArrays.keys():
                self.detArrays[key] += detArrays0[key]
                
                              


#################################################################################################
# CSPAD grabber (mean and variance done in different batch jobs)
#################################################################################################                               
                
def batchMeanCSPAD(node, experiment = 'xppl2816', runNumber = 72):
    tagDict = load_obj( os.environ['OUTPUTPATH']+'/Batch/Output/tagDict-%d' % node )
    seconds, nanoseconds, fiducials = tagDict['seconds'], tagDict['nanoseconds'], tagDict['fiducials']
    
    ds = DataSource('exp=%s:run=%d:idx' % (experiment, runNumber))
    run = ds.runs().next()
    integratedCSPAD = np.zeros((32,185,388))
    count = 0
    for sec,nsec,fid in zip(reversed(seconds.astype(int)),reversed(nanoseconds.astype(int)),reversed(fiducials.astype(int))):
        et = EventTime(int((sec<<32)|nsec),fid)
        evt = run.event(et)
        currCSPAD = getCSPAD(evt, run=runNumber, experiment=experiment,
                             seconds=sec, nanoseconds=nsec, fiducials=fid)
        ipmIntensity = getIPM(evt,run=runNumber, experiment=experiment,
                              seconds=sec, nanoseconds=nsec, fiducials=fid)
        if currCSPAD is not None and ipmIntensity is not None:
                integratedCSPAD += currCSPAD / ipmIntensity
                count += 1
                
    cspadDict = { 'mean': integratedCSPAD/count , 'count': count }
    save_obj( cspadDict , os.environ['OUTPUTPATH']+'/Batch/Output/cspadDict-%d' % node )
    
def batchVarianceCSPAD(node, experiment = 'xppl2816', runNumber = 72):
    tagDict = load_obj( os.environ['OUTPUTPATH']+'/Batch/Output/tagDict-%d' % node )
    seconds, nanoseconds, fiducials = tagDict['seconds'], tagDict['nanoseconds'], tagDict['fiducials']
    
    meanLoaded = False
    while not meanLoaded:
        time.sleep(1)
        try:
            mean = load_obj( os.environ['OUTPUTPATH']+'/Batch/Output/cspadDict-%d' % node )['mean']
            meanLoaded = True
        except Exception:
            pass
    
    ds = DataSource('exp=%s:run=%d:idx' % (experiment, runNumber))
    run = ds.runs().next()
    varianceCSPAD = np.zeros((32,185,388))
    count = 0
    for sec,nsec,fid in zip(reversed(seconds.astype(int)),reversed(nanoseconds.astype(int)),reversed(fiducials.astype(int))):
        et = EventTime(int((sec<<32)|nsec),fid)
        evt = run.event(et)
        currCSPAD = getCSPAD(evt, run=runNumber, experiment=experiment,
                              seconds=sec, nanoseconds=nsec, fiducials=fid)
        ipmIntensity = getIPM(evt, run=runNumber, experiment=experiment,
                              seconds=sec, nanoseconds=nsec, fiducials=fid)
        if currCSPAD is not None and ipmIntensity is not None:
            varianceCSPAD += (currCSPAD / ipmIntensity - mean)**2
            count += 1
            

                
    variance = varianceCSPAD/count 
    save_obj( variance , os.environ['OUTPUTPATH']+'/Batch/Output/variance-%d' % node )
    

# thread for submitted 
class batchCSPADGrabber (threading.Thread):
    def __init__(self, tagsList, experiment='xppl2816', runNumber=74):
        threading.Thread.__init__(self)
        
        # Specify function parameters
        self.tagsList = tagsList
        self.experiment = experiment
        self.runNumber = runNumber
        self.batchRank = len( tagsList )
        
        # Specify batch job parameters
        self.RunType = 'mpirun python2'
        self.Nodes = 1
        self.Memory = 7000
        self.Queue = 'psnehq'
        self.OutputName = 'temp'
        
        # Save internally the batch job ids and run status
        self.subthreads = []
        self.status = 'Initialized'
        self.flag = None
        
        # Save the final output
        NT = len( tagsList )
        self.CSPAD = np.zeros((32,185,388,NT))
        self.variance = np.zeros((32,185,388,NT))
        self.counts = np.zeros((NT,1))


    def run(self):
        self.status = 'Running'
        
        for node in range(self.batchRank):
            try:
                os.remove( os.environ['OUTPUTPATH']+'/Batch/Output/variance-%d.pkl' % node  % node )
            except Exception:
                pass
            
            try:
                os.remove( os.environ['OUTPUTPATH']+'/Batch/Output/cspadDict-%d.pkl' % node  )
            except Exception:
                pass
            
        for node in range(self.batchRank):
            if self.flag == 'Stop requested':
                break
                
            save_obj( self.tagsList[node] , os.environ['OUTPUTPATH']+'/Batch/Output/tagDict-%d' % node )
            
            # Submit CSPAD to batch
            batchJobC = ['import os',
                        'os.environ[\'INSTALLPATH\']=\'%s\''% os.environ['INSTALLPATH'],
                        'os.environ[\'OUTPUTPATH\']=\'%s\'' % os.environ['OUTPUTPATH'],
                        'import sys',
                        'sys.path.insert(0, os.environ[\'INSTALLPATH\']+\'/Libraries/pythonBatchMagic\')',
                        'from lclsBatch import *',
                        'batchMeanCSPAD( node=%d, experiment=\'%s\', runNumber=%d )' % (node, self.experiment,self.runNumber)]
            self.submitBatch( batchJobC , self.OutputName+'CSPAD-%d' % node )
            
            time.sleep(5)
            
            # Submit variance of CSPAD to batch
            batchJobV = ['import os',
                        'os.environ[\'INSTALLPATH\']=\'%s\''% os.environ['INSTALLPATH'],
                        'os.environ[\'OUTPUTPATH\']=\'%s\'' % os.environ['OUTPUTPATH'],
                        'import sys',
                        'sys.path.insert(0, os.environ[\'INSTALLPATH\']+\'/Libraries/pythonBatchMagic\')',
                        'from lclsBatch import *',
                        'batchVarianceCSPAD( node=%d, experiment=\'%s\', runNumber=%d )' % (node, self.experiment,self.runNumber)]
            self.submitBatch( batchJobV , self.OutputName+'variance-%d' % node )
            
            time.sleep(5)
            
        
        forcedStop = False
        time.sleep(10)
        
        while self.checkStatus():
            if self.flag == 'Stop requested':
                [athread.requestStop() for athread in self.subthreads]
                forcedStop = True
                break
                
        if forcedStop:
            self.status = 'Stopped'
        else:
            self.status = 'Gathering'
            self.gather()
            self.status = 'Finished'
        
    def submitBatch(self, job, outputName):
        myBatchThread = batchThread( job )
        myBatchThread.RunType = self.RunType
        myBatchThread.Nodes = self.Nodes
        myBatchThread.Memory = self.Memory
        myBatchThread.Queue = self.Queue
        myBatchThread.OutputName = outputName
        myBatchThread.start()
        self.subthreads.append( myBatchThread )        
        
    def requestStop(self):
        self.flag = 'Stop requested'
        
    def checkStatus(self):
        if 'Running' in [athread.status for athread in self.subthreads]:
            return True
        elif 'Initialized' in [athread.status for athread in self.subthreads]:
            return True
        else:
            return False
        
    def gather(self):
        for node in range(self.batchRank):
            CSPADdict = load_obj( os.environ['OUTPUTPATH']+'/Batch/Output/cspadDict-%d' % node )
            self.CSPAD[:,:,:,node] = CSPADdict['mean']
            self.counts[node] = CSPADdict['count']
            self.variance[:,:,:,node] = load_obj( os.environ['OUTPUTPATH']+'/Batch/Output/variance-%d' % node )
            
            
            

#################################################################################################
# CSPAD grabber (mean and variance done in different batch jobs)
#################################################################################################                               
                
def batchMeanVarCSPAD(node, experiment = 'xppl2816', runNumber = 72):
    tagDict = load_obj( os.environ['OUTPUTPATH']+'/Batch/Output/tagDict-%d' % node )
    seconds, nanoseconds, fiducials = tagDict['seconds'], tagDict['nanoseconds'], tagDict['fiducials']
    
    ds = DataSource('exp=%s:run=%d:idx' % (experiment, runNumber))
    run = ds.runs().next()
    integratedCSPAD = np.zeros((32,185,388))
    count = 0
    for sec,nsec,fid in zip(reversed(seconds.astype(int)),reversed(nanoseconds.astype(int)),reversed(fiducials.astype(int))):
        et = EventTime(int((sec<<32)|nsec),fid)
        evt = run.event(et)
        currCSPAD = getCSPAD(evt, run=runNumber, experiment=experiment,
                             seconds=sec, nanoseconds=nsec, fiducials=fid)
        ipmIntensity = getIPM(evt,run=runNumber, experiment=experiment,
                              seconds=sec, nanoseconds=nsec, fiducials=fid)
        if currCSPAD is not None and ipmIntensity is not None:
                integratedCSPAD += currCSPAD / ipmIntensity
                count += 1
                
#     save_obj( cspadDict , os.environ['OUTPUTPATH']+'/Batch/Output/cspadDict-%d' % node )
    
    mean = integratedCSPAD/count
    
    ds = DataSource('exp=%s:run=%d:idx' % (experiment, runNumber))
    run = ds.runs().next()
    varianceCSPAD = np.zeros((32,185,388))
    count = 0
    for sec,nsec,fid in zip(reversed(seconds.astype(int)),reversed(nanoseconds.astype(int)),reversed(fiducials.astype(int))):
        et = EventTime(int((sec<<32)|nsec),fid)
        evt = run.event(et)
        currCSPAD = getCSPAD(evt, run=runNumber, experiment=experiment,
                              seconds=sec, nanoseconds=nsec, fiducials=fid)
        ipmIntensity = getIPM(evt, run=runNumber, experiment=experiment,
                              seconds=sec, nanoseconds=nsec, fiducials=fid)
        if currCSPAD is not None and ipmIntensity is not None:
            varianceCSPAD += (currCSPAD / ipmIntensity - mean)**2
            count += 1
            

                
    variance = varianceCSPAD/count 
    cspadDict = { 'mean': integratedCSPAD/count , 'count': count , 'variance': variance }
    
    save_obj( cspadDict , os.environ['OUTPUTPATH']+'/Batch/Output/mean-var-%d' % node )
    

# thread for submitted 
class batchCSPADMVGrabber (threading.Thread):
    def __init__(self, tagsList, experiment='xppl2816', runNumber=74):
        threading.Thread.__init__(self)
        
        # Specify function parameters
        self.tagsList = tagsList
        self.experiment = experiment
        self.runNumber = runNumber
        self.batchRank = len( tagsList )
        
        # Specify batch job parameters
        self.RunType = 'mpirun python2'
        self.Nodes = 1
        self.Memory = 7000
        self.Queue = 'psnehq'
        self.OutputName = 'temp'
        
        # Save internally the batch job ids and run status
        self.subthreads = []
        self.status = 'Initialized'
        self.flag = None
        
        # Save the final output
        NT = len( tagsList )
        self.CSPAD = np.zeros((32,185,388,NT))
        self.variance = np.zeros((32,185,388,NT))
        self.counts = np.zeros((NT,1))


    def run(self):
        self.status = 'Running'
        
        for node in range(self.batchRank):
            try:
                os.remove( os.environ['OUTPUTPATH']+'/Batch/Output/mean-var-%d.pkl' % node  % node )
            except Exception:
                pass
            
        for node in range(self.batchRank):
            if self.flag == 'Stop requested':
                break
                
            save_obj( self.tagsList[node] , os.environ['OUTPUTPATH']+'/Batch/Output/tagDict-%d' % node )
            
            # Submit CSPAD to batch
            batchJobCV = ['import os',
                        'os.environ[\'INSTALLPATH\']=\'%s\''% os.environ['INSTALLPATH'],
                        'os.environ[\'OUTPUTPATH\']=\'%s\'' % os.environ['OUTPUTPATH'],
                        'import sys',
                        'sys.path.insert(0, os.environ[\'INSTALLPATH\']+\'/Libraries/pythonBatchMagic\')',
                        'from lclsBatch import *',
                        'batchMeanVarCSPAD( node=%d, experiment=\'%s\', runNumber=%d )' % (node, self.experiment,self.runNumber)]
            self.submitBatch( batchJobCV , self.OutputName+'CSPAD-%d' % node )
            
            time.sleep(1)
            
        
        forcedStop = False
        time.sleep(10)
        
        while self.checkStatus():
            if self.flag == 'Stop requested':
                [athread.requestStop() for athread in self.subthreads]
                forcedStop = True
                break
                
        if forcedStop:
            self.status = 'Stopped'
        else:
            self.status = 'Gathering'
            self.gather()
            self.status = 'Finished'
        
    def submitBatch(self, job, outputName):
        myBatchThread = batchThread( job )
        myBatchThread.RunType = self.RunType
        myBatchThread.Nodes = self.Nodes
        myBatchThread.Memory = self.Memory
        myBatchThread.Queue = self.Queue
        myBatchThread.OutputName = outputName
        myBatchThread.start()
        self.subthreads.append( myBatchThread )        
        
    def requestStop(self):
        self.flag = 'Stop requested'
        
    def checkStatus(self):
        if 'Running' in [athread.status for athread in self.subthreads]:
            return True
        elif 'Initialized' in [athread.status for athread in self.subthreads]:
            return True
        else:
            return False
        
    def gather(self):
        for node in range(self.batchRank):
            CSPADdict = load_obj( os.environ['OUTPUTPATH']+'/Batch/Output/mean-var-%d' % node )
            self.CSPAD[:,:,:,node] = CSPADdict['mean']
            self.counts[node] = CSPADdict['count']
            self.variance[:,:,:,node] = CSPADdict['variance']