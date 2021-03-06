import os
import sys
import time 
import cv2
import numpy as np

from argparse import ArgumentParser
import logging as log

from face_detection import FaceDetectionModel
from facial_landmarks_detection import FacialLandmarksDetectionModel
from gaze_estimation import GazeEstimationModel
from head_pose_estimation import HeadPoseEstimationModel
from mouse_controller import MouseController
from input_feeder import InputFeeder


def build_argparser():
    '''
    Parse command line arguments.

    :return: command line arguments
    '''
    parser = ArgumentParser()
    
    parser.add_argument("-f", "--face_detection_model", required=True, type=str,
                        help="Path to an .xml file with Face Detection model.")
    parser.add_argument("-fl", "--facial_landmark_model", required=True, type=str,
                        help="Path to an .xml file with Facial Landmark Detection model.")
    parser.add_argument("-hp", "--head_pose_model", required=True, type=str,
                        help="Path to an .xml file with Head Pose Estimation model.")
    parser.add_argument("-g", "--gaze_estimation_model", required=True, type=str,
                        help="Path to an .xml file with Gaze Estimation model.")
                        
    parser.add_argument("-i", "--input", required=True, type=str,
                        help="Path to image or video file or CAM")
                        
    parser.add_argument("-l", "--cpu_extension", required=False, type=str,
                        default=None,
                        help="MKLDNN (CPU)-targeted custom layers."
                             "Absolute path to a shared library with the"
                             "kernels impl.")
                             
    parser.add_argument("-pt", "--prob_threshold", required=False, type=float,
                        default=0.6,
                        help="Probability threshold for detection fitering.")
                        
    parser.add_argument("-d", "--device", type=str, default="CPU",
                        help="Specify the target device to infer on: "
                             "CPU, GPU, FPGA or MYRIAD is acceptable. Sample "
                             "will look for a suitable plugin for device "
                             "specified (CPU by default)")
    
    return parser



def main():

    # Grab command line args
    args = build_argparser().parse_args()
    
    inputFilePath = args.input
    inputFeeder = None
    
    if args.input =="CAM":
            inputFeeder = InputFeeder("cam")
    else:
        if not os.path.isfile(args.input):
            log.info("Unable to find specified video file")
            sys.exit(1)
        inputFeeder = InputFeeder("video",args.input)
    
    modelPathDict = {'FaceDetectionModel':args.face_detection_model, 'FacialLandmarksDetectionModel':args.facial_landmark_model, 
    'GazeEstimationModel':args.gaze_estimation_model, 'HeadPoseEstimationModel':args.head_pose_model}
    
    for fileNameKey in modelPathDict.keys():
        if not os.path.isfile(modelPathDict[fileNameKey]):
            log.info("Unable to find specified "+fileNameKey+" xml file")
            sys.exit(1)
            
    fdm = FaceDetectionModel(modelPathDict['FaceDetectionModel'], args.device, args.cpu_extension)
    fldm = FacialLandmarksDetectionModel(modelPathDict['FacialLandmarksDetectionModel'], args.device, args.cpu_extension)
    gem = GazeEstimationModel(modelPathDict['GazeEstimationModel'], args.device, args.cpu_extension)
    hpem = HeadPoseEstimationModel(modelPathDict['HeadPoseEstimationModel'], args.device, args.cpu_extension)
    
    mc = MouseController('medium','fast')
    
    inputFeeder.load_data()
    fdm.load_model()
    fldm.load_model()
    hpem.load_model()
    gem.load_model()
    
    frame_count = 0
    for ret, frame in inputFeeder.next_batch():
        if not ret:
            break
        frame_count+=1
        if frame_count%5==0:
            cv2.imshow('video',cv2.resize(frame,(500,500)))
    
        key = cv2.waitKey(60)
        croppedFace, face_coords = fdm.predict(frame.copy(), args.prob_threshold)
        if type(croppedFace)==int:
            log.info("Unable to detect the face.")
            if key==27:
                break
            continue
        
        hp_out = hpem.predict(croppedFace.copy())
        
        left_eye, right_eye, eye_coords = fldm.predict(croppedFace.copy())
        
        new_mouse_coord, gaze_vector = gem.predict(left_eye, right_eye, hp_out)
        
        '''
        if (not len(previewFlags)==0):
            preview_frame = frame.copy()
            if 'fd' in previewFlags:
                #cv2.rectangle(preview_frame, (face_coords[0], face_coords[1]), (face_coords[2], face_coords[3]), (255,0,0), 3)
                preview_frame = croppedFace
            if 'fld' in previewFlags:
                cv2.rectangle(croppedFace, (eye_coords[0][0]-10, eye_coords[0][1]-10), (eye_coords[0][2]+10, eye_coords[0][3]+10), (0,255,0), 3)
                cv2.rectangle(croppedFace, (eye_coords[1][0]-10, eye_coords[1][1]-10), (eye_coords[1][2]+10, eye_coords[1][3]+10), (0,255,0), 3)
                #preview_frame[face_coords[1]:face_coords[3], face_coords[0]:face_coords[2]] = croppedFace
                
            if 'hp' in previewFlags:
                cv2.putText(preview_frame, "Pose Angles: yaw:{:.2f} | pitch:{:.2f} | roll:{:.2f}".format(hp_out[0],hp_out[1],hp_out[2]), (10, 20), cv2.FONT_HERSHEY_COMPLEX, 0.25, (0, 255, 0), 1)
            if 'ge' in previewFlags:
                x, y, w = int(gaze_vector[0]*12), int(gaze_vector[1]*12), 160
                le =cv2.line(left_eye.copy(), (x-w, y-w), (x+w, y+w), (255,0,255), 2)
                cv2.line(le, (x-w, y+w), (x+w, y-w), (255,0,255), 2)
                re = cv2.line(right_eye.copy(), (x-w, y-w), (x+w, y+w), (255,0,255), 2)
                cv2.line(re, (x-w, y+w), (x+w, y-w), (255,0,255), 2)
                croppedFace[eye_coords[0][1]:eye_coords[0][3],eye_coords[0][0]:eye_coords[0][2]] = le
                croppedFace[eye_coords[1][1]:eye_coords[1][3],eye_coords[1][0]:eye_coords[1][2]] = re
                #preview_frame[face_coords[1]:face_coords[3], face_coords[0]:face_coords[2]] = croppedFace
                
            cv2.imshow("visualization",cv2.resize(preview_frame,(500,500)))
        '''
        if frame_count%5==0:
            mc.move(new_mouse_coord[0],new_mouse_coord[1])    
        if key==27:
                break
    log.info("VideoStream ended...")
    cv2.destroyAllWindows()
    inputFeeder.close()
     
    

if __name__ == '__main__':
    main() 
 
