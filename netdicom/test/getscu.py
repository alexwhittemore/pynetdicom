#
# Copyright (c) 2012 Patrice Munger
# This file is part of pynetdicom, released under a modified MIT license.
#    See the file license.txt included with this distribution, also
#    available at http://pynetdicom.googlecode.com
#


"""
GetSCU AE example.

This demonstrates a simple application entity that support the Patient Root
Get SOP Class as SCU. The example sets up a SCP provider listening
on port 2001 on localhost using the dcmqrscp command from the offis toolkit. 
"""

import sys
sys.path.append('..')
import time
from applicationentity import AE
from SOPclass import *
import dicom
from dcmqrscp import start_dcmqrscp
from dicom.dataset import Dataset

# first create a partner
start_dcmqrscp(server_port=2001, server_AET='AE1', populate=True)
for ii in range(20): print

# call back
def OnAssociateResponse(association):
    print "Association response received"

def OnReceiveStore(SOPClass, DS):
    print "Received C-STORE"
    print DS
    return 0
    
# create application entity
MyAE = AE('LocalAE', 9998, [PatientRootGetSOPClass, VerificationSOPClass],[RTPlanStorageSOPClass,
									   CTImageStorageSOPClass,
									   MRImageStorageSOPClass,
									   RTImageStorageSOPClass,
									   ])
MyAE.OnAssociateResponse = OnAssociateResponse
MyAE.OnReceiveStore = OnReceiveStore

# remote application entity
RemoteAE = {'Address':'localhost','Port':2001,'AET':'AE1'}

# create association with remote AE
print "Request association"
assoc = MyAE.RequestAssociation(RemoteAE)

        
# perform a DICOM ECHO
print "DICOM Echo ... ",
st = assoc.VerificationSOPClass.SCU(1)
print 'done with status "%s"' % st

# send dataset using RTPlanStorageSOPClass
print "DICOM GetSCU ... ",
d = Dataset()
d.PatientsName = '*'
d.QueryRetrieveLevel = "PATIENT"
st = assoc.PatientRootGetSOPClass.SCU(d, 1)
print 'done with status "%s"' % st


print "Release association"
assoc.Release(0)

# done
MyAE.Quit()
