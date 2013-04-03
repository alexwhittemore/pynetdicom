#
# Copyright (c) 2012 Patrice Munger
# This file is part of pynetdicom, released under a modified MIT license.
#    See the file license.txt included with this distribution, also
#    available at http://pynetdicom.googlecode.com
#
import dsutils
from DIMSEparameters import *
import DIMSEprovider
import ACSEprovider
import time

class Status(object):
    def __init__(self, Type, Description, CodeRange):
        self.Type = Type
        self.Description = Description
        self.CodeRange = CodeRange

    def __int__(self):
        return self.CodeRange[0]

    def __repr__(self):
        return self.Type+' '+self.Description


class ServiceClass(object):   
    def __init__(self):
        pass

    def Code2Status(self, code):
        for dd in dir(self):
            getattr(self,dd).__class__
            obj = getattr(self,dd)
            if obj.__class__ == Status:
                if code in obj.CodeRange:
                    return obj
        # unknown status ...
        return None


class VerificationServiceClass(ServiceClass):

    Success = Status(
        'Success',
        '',
        xrange(0x0000,0x0000+1)
        )

    def __init__(self):
        ServiceClass.__init__(self)


    def SCU(self, id):
        cecho = C_ECHO_ServiceParameters()
        cecho.MessageID = id
        cecho.AffectedSOPClassUID = self.UID

        self.DIMSE.Send(cecho, self.pcid, self.maxpdulength)

        ans, id = self.DIMSE.Receive(Wait=True)
        return  self.Code2Status(ans.Status)

    
    def SCP(self, msg):
        rsp = C_ECHO_ServiceParameters()
        rsp.MessageIDBeingRespondedTo = msg.MessageID.value
        rsp.Status = 0
                
        # send response
        try:
            self.AE.OnReceiveEcho(self)
        except:
            print "There was an exception on OnReceiveEcho callback"
        self.DIMSE.Send(rsp, self.pcid, self.ACSE.MaxPDULength)



class StorageServiceClass(ServiceClass):

    OutOfResources = Status(
        'Failure',
        'Refused: Out of resources',
        xrange(0xA700,0xA7FF+1)
        )
    DataSetDoesNotMatchSOPClassFailure = Status(
        'Failure',
        'Error: Data Set does not match SOP Class',
        xrange(0xA900,0xA9FF+1)
        )
    CannotUnderstand = Status(
        'Failure',
        'Error: Cannot understand',
        xrange(0xC000, 0xCFFF+1)
        )
    CoercionOfDataElements = Status(
        'Warning',
        'Coercion of Data Elements',
        xrange(0xB000,0xB000+1)
        )
    DataSetDoesNotMatchSOPClassWarning = Status(
        'Warning',
        'Data Set does not match SOP Class',
        xrange(0xB007,0xB007+1)
        )
    ElementDiscarted = Status(
        'Warning',
        'Element Discarted',
        xrange(0xB006,0xB006+1)
        )
    Success = Status(
        'Success',
        '',
        xrange(0x0000,0x0000+1)
        )

    
    def SCU(self, dataset, msgid):
        # build C-STORE primitive
        csto = C_STORE_ServiceParameters()
        csto.MessageID = msgid
        csto.AffectedSOPClassUID = dataset.SOPClassUID
        csto.AffectedSOPInstanceUID = dataset.SOPInstanceUID
        csto.Priority = 0x0002
        csto.DataSet = dsutils.encode(dataset, 
                                      self.transfersyntax.is_implicit_VR, 
                                      self.transfersyntax.is_little_endian)
        # send cstore request
        self.DIMSE.Send(csto, self.pcid, self.maxpdulength)

        # wait for c-store response
        ans, id = self.DIMSE.Receive(Wait=True)
        return self.Code2Status(ans.Status.value)


    def __init__(self):
        ServiceClass.__init__(self)

    def SCP(self, msg):
        status = None
        print self.transfersyntax.is_implicit_VR
        try:
            DS = dsutils.decode(msg.DataSet, 
                                self.transfersyntax.is_implicit_VR, 
                                self.transfersyntax.is_little_endian)
        except:
            status = self.CannotUnderstand
        # make response
        rsp = C_STORE_ServiceParameters()
        rsp.MessageIDBeingRespondedTo = msg.MessageID
        rsp.AffectedSOPInstanceUID = msg.AffectedSOPInstanceUID
        rsp.AffectedSOPClassUID = msg.AffectedSOPClassUID
        # callback
        if not status:
            try:
                status = self.AE.OnReceiveStore(self, DS)
            except:
                raise
                print "There was an exception in OnReceiveStore callback"
                status = self.CannotUnderstand
        rsp.Status = int(status)
        print "Status: %s" % status
        # send response
        self.DIMSE.Send(rsp, self.pcid, self.ACSE.MaxPDULength)
        


class QueryRetrieveServiceClass(ServiceClass):
    pass


class QueryRetrieveFindSOPClass(QueryRetrieveServiceClass):
    OutOfResources = Status(
        'Failure',
        'Refused: Out of resources',
        xrange(0xA700,0xA700+1)
        )
    IdentifierDoesNotMatchSOPClass = Status(
        'Failure',
        'Identifier does not match SOP Class',
        xrange(0xA900,0xA900+1)
        )
    UnableToProcess = Status(
        'Failure',
        'Unable to process',
        xrange(0xC000, 0xCFFF+1)
        )
    MatchingTerminatedDueToCancelRequest = Status(
        'Cancel',
        'Matching terminated due to Cancel request',
        xrange(0xFE00, 0xFE00+1)
        )
    Success = Status(
        'Success',
        'Matching is complete - No final Identifier is supplied',
        xrange(0x0000,0x0000+1)
        )
    Pending = Status(
        'Pending',
        'Matches are continuing - Current Match is supplied \
and any Optional Keys were supported in the same manner as Required Keys',
        xrange(0xFF00,0xFF00+1)
        )
    PendingWarning = Status(
        'Pending',
        'Matches are continuing - Warning that one or more Optional \
Keys were not supported for existence and/or matching for this identifier',
        xrange(0xFF01,0xFF01+1)
        )



    def SCU(self, ds, msgid):
        # build C-FIND primitive
        cfind = C_FIND_ServiceParameters()
        cfind.MessageID = msgid
        cfind.AffectedSOPClassUID = self.UID
        cfind.Priority = 0x0002
        cfind.Identifier = dsutils.encode(ds, 
                                          self.transfersyntax.is_implicit_VR, 
                                          self.transfersyntax.is_little_endian)

        # send c-find request
        self.DIMSE.Send(cfind, self.pcid, self.maxpdulength)
        while 1:
            time.sleep(0.001)
            # wait for c-find responses
            ans, id = self.DIMSE.Receive(Wait=False)
            if not ans: continue
            d = dsutils.decode(ans.Identifier, self.transfersyntax.is_implicit_VR, self.transfersyntax.is_little_endian)
            try:
                status = self.Code2Status(ans.Status.value)
            except:
                status = None
            if status != None and status.Type <> 'Pending':
                break
            yield status, d
        yield status, d


    def SCP(self, msg):
        ds = dsutils.decode(msg.Identifier, self.transfersyntax.is_implicit_VR, self.transfersyntax.is_little_endian)

        # make response
        rsp = C_FIND_ServiceParameters()
        rsp.MessageIDBeingRespondedTo = msg.MessageID
        rsp.AffectedSOPClassUID = msg.AffectedSOPClassUID
        
        gen = self.AE.OnReceiveFind(self, ds)
        try:
            while 1:
                time.sleep(0.001)
                IdentifierDS, status = gen.next()
                rsp.Status = int(status)
                rsp.Identifier = dsutils.encode(IdentifierDS, 
                                                self.transfersyntax.is_implicit_VR, 
                                                self.transfersyntax.is_little_endian)
                # send response
                self.DIMSE.Send(rsp, self.pcid, self.ACSE.MaxPDULength)
        except StopIteration:
            # send final response
            rsp = C_FIND_ServiceParameters()
            rsp.MessageIDBeingRespondedTo = msg.MessageID
            rsp.AffectedSOPClassUID = msg.AffectedSOPClassUID
            rsp.Status = int(self.Success)
            self.DIMSE.Send(rsp, self.pcid, self.ACSE.MaxPDULength)

        


class QueryRetrieveGetSOPClass(QueryRetrieveServiceClass):

    OutOfResourcesNumberOfMatches = Status(
        'Failure',
        'Refused: Out of resources - Unable to calcultate number of matches',
        xrange(0xA701, 0xA701+1)
        )

    OutOfResourcesUnableToPerform = Status(
        'Failure',
        'Refused: Out of resources - Unable to perform sub-operations',
        xrange(0xA702, 0xA702+1)
        )

    IdentifierDoesNotMatchSOPClass = Status(
        'Failure',
        'Identifier does not match SOP Class',
        xrange(0xA900, 0xA900+1)
        )
    UnableToProcess  = Status(
        'Failure',
        'Unable to process',
        xrange(0xC000, 0xCFFF+1)
        )
    Cancel = Status(
        'Cancel',
        'Sub-operations terminated due to Cancel indication',
        xrange(0xFE00, 0xFE00+1)
        )
    Warning = Status(
        'Warning',
        'Sub-operations Complete - One or more Failures or Warnings',
        xrange(0xB000,0xB000+1)
        )
    Success = Status(
        'Success',
        'Sub-operations Complete - No Failure or Warnings',
        xrange(0x0000,0x0000+1)
        )
    Pending = Status(
        'Pending',
        'Sub-operations are continuing',
        xrange(0xFF00, 0xFF00+1)
        )


    def SCU(self, ds, msgid):
        # build C-GET primitive
        cget = C_GET_ServiceParameters()
        cget.MessageID = msgid
        cget.AffectedSOPClassUID = self.UID
        cget.Priority = 0x0002
        cget.Identifier = dsutils.encode(ds, 
                                         self.transfersyntax.is_implicit_VR, 
                                         self.transfersyntax.is_little_endian)

        # send c-get primitive
        self.DIMSE.Send(cget, self.pcid, self.maxpdulength)
        
        while 1:
            # receive c-store
            msg, id = self.DIMSE.Receive(Wait=True)
            if msg.__class__ == C_GET_ServiceParameters:
                if self.Code2Status(msg.Status.value).Type  == 'Pending':
                    # pending. intermediate C-GET response
                    pass
                else:
                    # last answer
                    break
            elif msg.__class__ == C_STORE_ServiceParameters:
                # send c-store response
                rsp = C_STORE_ServiceParameters()
                rsp.MessageIDBeingRespondedTo = msg.MessageID
                rsp.AffectedSOPInstanceUID = msg.AffectedSOPInstanceUID
                rsp.AffectedSOPClassUID = msg.AffectedSOPClassUID
                status = None
                try:
                    d = dsutils.decode(msg.DataSet, self.transfersyntax.is_implicit_VR, self.transfersyntax.is_little_endian)
                except:
                    # cannot understand
                    status = CannotUnderstand

                
                SOPClass = UID2SOPClass(d.SOPClassUID)
                status = self.AE.OnReceiveStore(SOPClass, d)
                rsp.Status = int(status)

                self.DIMSE.Send(rsp, id, self.maxpdulength)



class QueryRetrieveMoveSOPClass(QueryRetrieveServiceClass):

    OutOfResourcesNumberOfMatches = Status(
        'Failure',
        'Refused: Out of resources - Unable to calcultate number of matches',
        xrange(0xA701, 0xA701+1)
        )

    OutOfResourcesUnableToPerform = Status(
        'Failure',
        'Refused: Out of resources - Unable to perform sub-operations',
        xrange(0xA702, 0xA702+1)
        )
    MoveDestinationUnknown = Status(
        'Failure',
        'Refused: Move destination unknown',
        xrange(0xA801, 0xA801+1)
    )
    IdentifierDoesNotMatchSOPClass = Status(
        'Failure',
        'Identifier does not match SOP Class',
        xrange(0xA900, 0xA900+1)
        )
    UnableToProcess  = Status(
        'Failure',
        'Unable to process',
        xrange(0xC000, 0xCFFF+1)
        )
    Cancel = Status(
        'Cancel',
        'Sub-operations terminated due to Cancel indication',
        xrange(0xFE00, 0xFE00+1)
        )
    Warning = Status(
        'Warning',
        'Sub-operations Complete - One or more Failures or Warnings',
        xrange(0xB000,0xB000+1)
        )
    Success = Status(
        'Success',
        'Sub-operations Complete - No Failure or Warnings',
        xrange(0x0000,0x0000+1)
        )
    Pending = Status(
        'Pending',
        'Sub-operations are continuing',
        xrange(0xFF00, 0xFF00+1)
        )


    def SCU(self, ds, destaet, msgid):
        # build C-FIND primitive
        cmove = C_MOVE_ServiceParameters()
        cmove.MessageID = msgid
        cmove.AffectedSOPClassUID = self.UID
        cmove.MoveDestination = destaet
        cmove.Priority = 0x0002
        cmove.Identifier = dsutils.encode(ds, self.transfersyntax.is_implicit_VR, self.transfersyntax.is_little_endian)

        # send c-find request
        self.DIMSE.Send(cmove, self.pcid, self.maxpdulength)

        while 1:
            # wait for c-move responses
            time.sleep(0.001)
            ans, id = self.DIMSE.Receive(Wait=False)
            if not ans: continue
            status = self.Code2Status(ans.Status.value).Type
            if status <> 'Pending':
                yield status
                break
            yield status




    def SCP(self, msg):
        ds = dsutils.decode(msg.Identifier, self.transfersyntax.is_implicit_VR, self.transfersyntax.is_little_endian)
        
        # make response
        rsp = C_MOVE_ServiceParameters()
        rsp.MessageIDBeingRespondedTo = msg.MessageID.value
        rsp.AffectedSOPClassUID = msg.AffectedSOPClassUID.value
        gen = self.AE.OnReceiveMove(self, ds, msg.MoveDestination.value)

        # first value returned by callback must be the complete remote AE specs
        remoteAE = gen.next()
        
        # request association to move destination
        ass = self.AE.RequestAssociation(remoteAE)
        nop = gen.next()
        print nop
        try:
            ncomp = 0
            nfailed = 0
            nwarning = 0
            ncompleted = 0
            while 1:
                DataSet = gen.next()
                # request an association with destination
                # send C-STORE
                s=str(UID2SOPClass(DataSet.SOPClassUID))
                ind = len(s)-s[::-1].find('.')
                obj = getattr(ass,s[ind:-2])
                status = obj.SCU(DataSet, ncompleted)
                if status.Type == 'Failed':
                     nfailed += 1
                if status.Type == 'Warning':
                    nwarning += 1
                rsp.Status =  int(self.Pending)
                rsp.NumberOfRemainingSubOperations = nop-ncompleted
                rsp.NumberOfCompletedSubOperations = ncompleted
                rsp.NumberOfFailedSubOperations = nfailed
                rsp.NumberOfWarningSubOperations = nwarning
                ncompleted += 1
                
                # send response
                self.DIMSE.Send(rsp, self.pcid, self.ACSE.MaxPDULength)
                print ncompleted
                
        except StopIteration:
            # send final response
            rsp = C_MOVE_ServiceParameters()
            rsp.MessageIDBeingRespondedTo = msg.MessageID.value
            rsp.AffectedSOPClassUID = msg.AffectedSOPClassUID.value
            rsp.NumberOfRemainingSubOperations = nop-ncompleted
            rsp.NumberOfCompletedSubOperations = ncompleted
            rsp.NumberOfFailedSubOperations = nfailed
            rsp.NumberOfWarningSubOperations = nwarning
            rsp.Status = int(self.Success)
            self.DIMSE.Send(rsp, self.pcid, self.ACSE.MaxPDULength)
            ass.Release(0)




# VERIFICATION SOP CLASSES
class VerificationSOPClass(VerificationServiceClass):
    UID = '1.2.840.10008.1.1'


# STORAGE SOP CLASSES
# Slowly adding everything from http://www.dicomlibrary.com/dicom/sop/
class StorageSOPClass(StorageServiceClass):
    pass

class MRImageStorageSOPClass(StorageSOPClass):
    UID = '1.2.840.10008.5.1.4.1.1.4'

class EnhancedMRImageStorageSOPClass(StorageSOPClass):
    UID = '1.2.840.10008.5.1.4.1.1.4.1'

class MRSpectroscopyStorageSOPClass(StorageSOPClass):
    UID = '1.2.840.10008.5.1.4.1.1.4.2'

class CTImageStorageSOPClass(StorageSOPClass):
    UID = '1.2.840.10008.5.1.4.1.1.2'

class PositronEmissionTomographyImageStorageSOPClass(StorageSOPClass):
    UID = '1.2.840.10008.5.1.4.1.1.128'

class CRImageStorageSOPClass(StorageSOPClass):
    UID = '1.2.840.10008.5.1.4.1.1.1'

class DigitalXRayImagePresentationStorageSOPClass(StorageSOPClass):
    UID = '1.2.840.10008.5.1.4.1.1.1.1'

class DigitalXRayImageProcessingStorageSOPClass(StorageSOPClass):
    UID = '1.2.840.10008.5.1.4.1.1.1.1.1'

class DigitalMammographyXRayImagePresentationStorageSOPClass(StorageSOPClass):
    UID = '1.2.840.10008.5.1.4.1.1.1.2'

class DigitalMammographyXRayImageProcessingStorageSOPClass(StorageSOPClass):
    UID = '1.2.840.10008.5.1.4.1.1.1.2.1'

class DigitalIntraOralXRayImagePresentationStorageSOPClass(StorageSOPClass):
    UID = '1.2.840.10008.5.1.4.1.1.1.3'

class DigitalIntraOralXRayImageProcessingStorageSOPClass(StorageSOPClass):
    UID = '1.2.840.10008.5.1.4.1.1.1.3.1'

class EncapsulatedPDFStorageSOPClass(StorageSOPClass):
    UID = '1.2.840.10008.5.1.4.1.1.104.1'
    
class GrayscaleSoftcopyPresentationStateStorageSOPClass(StorageSOPClass):
    UID = '1.2.840.10008.5.1.4.1.1.11.1'
    
class ColorSoftcopyPresentationStateStorageSOPClass(StorageSOPClass):
    UID = '1.2.840.10008.5.1.4.1.1.11.2'

class PseudocolorSoftcopyPresentationStageStorageSOPClass(StorageSOPClass):
    UID = '1.2.840.10008.5.1.4.1.1.11.3'

class BlendingSoftcopyPresentationStateStorageSOPClass(StorageSOPClass):
    UID = '1.2.840.10008.5.1.4.1.1.11.4'

class XRayAngiographicImageStorageSOPClass(StorageSOPClass):
    UID = '1.2.840.10008.5.1.4.1.1.12.1'

class EnhancedXAImageStorageSOPClass(StorageSOPClass):
    UID = '1.2.840.10008.5.1.4.1.1.12.1.1'

class XRayRadiofluoroscopicImageStorageSOPClass(StorageSOPClass):
    UID = '1.2.840.10008.5.1.4.1.1.12.2'

class EnhancedXRFImageStorageSOPClass(StorageSOPClass):
    UID = '1.2.840.10008.5.1.4.1.1.12.2.1'

class EnhancedCTImageStorageSOPClass(StorageSOPClass):
    UID = '1.2.840.10008.5.1.4.1.1.2.1'

class NMImageStorageSOPClass(StorageSOPClass):
    UID = '1.2.840.10008.5.1.4.1.1.20'

class UltrasoundMultiframeImageStorageSOPClass(StorageSOPClass):
    UID = '1.2.840.10008.5.1.4.1.1.3.1'

class SCImageStorageSOPClass(StorageSOPClass):
    UID = '1.2.840.10008.5.1.4.1.1.7'

class MultiframeSingleBitSecondaryCaptureImageStorageSOPClass(StorageSOPClass):
    UID = '1.2.840.10008.5.1.4.1.1.7.1'

class MultiframeGrayscaleByteSecondaryCaptureImageStorageSOPClass(StorageSOPClass):
    UID = '1.2.840.10008.5.1.4.1.1.7.2'

class MultiframeGrayscaleWordSecondaryCaptureImageStorageSOPClass(StorageSOPClass):
    UID = '1.2.840.10008.5.1.4.1.1.7.3'

class MultiframeTrueColorSecondaryCaptureImageStorageSOPClass(StorageSOPClass):
    UID = '1.2.840.10008.5.1.4.1.1.7.4'

class RTImageStorageSOPClass(StorageSOPClass):
    UID = '1.2.840.10008.5.1.4.1.1.481.1'

class RTDoseStorageSOPClass(StorageSOPClass):
    UID = '1.2.840.10008.5.1.4.1.1.481.2'

class RTStructureSetStorageSOPClass(StorageSOPClass):
    UID = '1.2.840.10008.5.1.4.1.1.481.3'

class RTPlanStorageSOPClass(StorageSOPClass):
    UID = '1.2.840.10008.5.1.4.1.1.481.5'

class VLEndoscopicImageStorageSOPClass(StorageSOPClass):
    UID = '1.2.840.10008.5.1.4.1.1.77.1.1'

class VideoEndoscopicImageStorageSOPClass(StorageSOPClass):
    UID = '1.2.840.10008.5.1.4.1.1.77.1.1.1'

class VLMicroscopicImageStorageSOPClass(StorageSOPClass):
    UID = '1.2.840.10008.5.1.4.1.1.77.1.2'

class VideoMicroscopicImageStorageSOPClass(StorageSOPClass):
    UID = '1.2.840.10008.5.1.4.1.1.77.1.2.1'

class VLSlideCoordinatesMicroscopicImageStorageSOPClass(StorageSOPClass):
    UID = '1.2.840.10008.5.1.4.1.1.77.1.3'

class VLPhotographicImageStorageSOPClass(StorageSOPClass):
    UID = '1.2.840.10008.5.1.4.1.1.77.1.4'

class VideoPhotographicImageStorageSOPClass(StorageSOPClass):
    UID = '1.2.840.10008.5.1.4.1.1.77.1.4.1'

class OphthalmicPhotography8BitImageStorageSOPClass(StorageSOPClass):
    UID = '1.2.840.10008.5.1.4.1.1.77.1.5.1'

class OphthalmicPhotography16BitImageStorageSOPClass(StorageSOPClass):
    UID = '1.2.840.10008.5.1.4.1.1.77.1.5.2'

class StereometricRelationshipStorageSOPClass(StorageSOPClass):
    UID = '1.2.840.10008.5.1.4.1.1.77.1.5.3'

class UltrasoundImageStorageSOPClass(StorageSOPClass):
    UID = '1.2.840.10008.5.1.4.1.1.6.1'

class RawDataStorageSOPClass(StorageSOPClass):
    UID = '1.2.840.10008.5.1.4.1.1.66'

class SpatialRegistrationStorageSOPClass(StorageSOPClass):
    UID = '1.2.840.10008.5.1.4.1.1.66.1'

class SpatialFiducialsStorageSOPClass(StorageSOPClass):
    UID = '1.2.840.10008.5.1.4.1.1.66.2'

class DeformableSpatialRegistrationStorageSOPClass(StorageSOPClass):
    UID = '1.2.840.10008.5.1.4.1.1.66.3'

class SegmentationStorageSOPClass(StorageSOPClass):
    UID = '1.2.840.10008.5.1.4.1.1.66.4'

class RealWorldValueMappingStorageSOPClass(StorageSOPClass):
    UID = '1.2.840.10008.5.1.4.1.1.67'
    

# QUERY RETRIEVE SOP Classes
class QueryRetrieveSOPClass(QueryRetrieveServiceClass):
    pass

class PatientRootQueryRetrieveSOPClass(QueryRetrieveSOPClass):
    pass

class StudyRootQueryRetrieveSOPClass(QueryRetrieveSOPClass):
    pass
    
class PatientStudyOnlyQueryRetrieveSOPClass(QueryRetrieveSOPClass):
    pass

class PatientRootFindSOPClass(PatientRootQueryRetrieveSOPClass, QueryRetrieveFindSOPClass):
    UID = '1.2.840.10008.5.1.4.1.2.1.1'

class PatientRootMoveSOPClass(PatientRootQueryRetrieveSOPClass, QueryRetrieveMoveSOPClass):
    UID = '1.2.840.10008.5.1.4.1.2.1.2'

class PatientRootGetSOPClass(PatientRootQueryRetrieveSOPClass, QueryRetrieveGetSOPClass):
    UID = '1.2.840.10008.5.1.4.1.2.1.3'

class StudyRootFindSOPClass(StudyRootQueryRetrieveSOPClass, QueryRetrieveFindSOPClass):
    UID = '1.2.840.10008.5.1.4.1.2.2.1'

class StudyRootMoveSOPClass(StudyRootQueryRetrieveSOPClass, QueryRetrieveMoveSOPClass):
    UID = '1.2.840.10008.5.1.4.1.2.2.2'

class StudyRootGetSOPClass(StudyRootQueryRetrieveSOPClass, QueryRetrieveGetSOPClass):
    UID = '1.2.840.10008.5.1.4.1.2.2.3'

class PatientStudyOnlyFindSOPClass(PatientStudyOnlyQueryRetrieveSOPClass, QueryRetrieveFindSOPClass):
    UID = '1.2.840.10008.5.1.4.1.2.3.1'

class PatientStudyOnlyMoveSOPClass(PatientStudyOnlyQueryRetrieveSOPClass, QueryRetrieveMoveSOPClass):
    UID = '1.2.840.10008.5.1.4.1.2.3.2'

class PatientStudyOnlyGetSOPClass(PatientStudyOnlyQueryRetrieveSOPClass, QueryRetrieveGetSOPClass):
    UID = '1.2.840.10008.5.1.4.1.2.3.3'



d = dir()


def UID2SOPClass(UID):
    """Returns a SOPClass object from given UID"""

    for ss in d:
        if hasattr(eval(ss),'UID'):
            tmpuid = getattr(eval(ss),'UID')
            if tmpuid == UID:
                return eval(ss)
    return None

