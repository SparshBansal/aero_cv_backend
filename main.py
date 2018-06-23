import sys
import cv2
from imutils.object_detection import non_max_suppression
from imutils import paths
import numpy as np
import argparse
import imutils
from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtWidgets import QApplication,QDialog
from PyQt5.uic import loadUi

from camerafeed import CameraFeed
from argparse import ArgumentParser
from cvthread import CVThread


class airlines(QDialog):

    onFrameProcessedSignal = pyqtSignal('PyQt_PyObject', 'PyQt_PyObject',int , float)

    def __init__(self):
        super(airlines,self).__init__()
        loadUi('airlines.ui',self)
        self.image=None
        self.startButton.clicked.connect(self.start_webcam)
        self.stopButton.clicked.connect(self.stop_webcam)
        self.detectButton.setCheckable(True)
        self.detectButton.toggled.connect(self.detect_people)
        self.f_Enabled=False
        self.hog = cv2.HOGDescriptor()
        self.hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
        
        parser = ArgumentParser(description="Camerafeed")
        parser.add_argument('--config_path', dest='config_path', default="settings.ini", help='path to settinsg.ini')
        args = parser.parse_args()

        # Initialize Camerafeed module
        self.camerafeed = CameraFeed()
        self.camerafeed.setup_config(config_path=args.config_path)

        # Initialize signal
        self.onFrameProcessedSignal.connect(self.onFrameProcessed)
        

    def detect_people(self):
        if (self.f_Enabled):
            self.f_Enabled = False
        else:
            self.f_Enabled = True

    def start_webcam(self):
        self.mCvthread = CVThread(self.camerafeed, self.onFrameProcessedSignal)

        # start the background thread
        self.mCvthread.start()
    
        
    def onFrameProcessed( self, upFrame, pFrame , lCount , throughput):
        if self.f_Enabled:
            self.displayImage(pFrame)
            self.lcLabel.setText(str(lCount))
            self.tLabel.setText(str(throughput))
            avgt = lCount * throughput
            self.tLabel.setText(str(avgt))
            limit = self.ovLimit.text()
            if lCount > limit:
            	self.qStatusLabel.setStyleSheet('color: red')
                self.qStatusLabel.setText('Overflow')
            else:
            	self.qStatusLabel.setStyleSheet('color: white')
                self.qStatusLabel.setText('Normal')
        else:
            self.displayImage(upFrame)


    def stop_webcam(self):
        print "stopping background thread"

    def displayImage(self,img,window=1):
        qformat=QtGui.QImage.Format_Indexed8
        if len(img.shape)==3 :
            if img.shape[2]==4 :
                qformat=QtGui.QImage.Format_RGBA8888
            else:
                qformat=QtGui.QImage.Format_RGB888
        outImage = QtGui.QImage(img,img.shape[1],img.shape[0],img.strides[0],qformat)
        outImage = outImage.rgbSwapped()

        if window==1:
            self.imgLabel.setPixmap(QtGui.QPixmap.fromImage(outImage))
            self.imgLabel.setScaledContents(True)


if( __name__=='__main__'):

    app=QApplication(sys.argv)
    widget=airlines()
    widget.setWindowTitle('Airlines GUI')

    parser = ArgumentParser(description="Camerafeed")
    parser.add_argument('--config_path', dest='config_path', default="settings.ini", help='path to settinsg.ini')
    args = parser.parse_args()

    widget.show()
    sys.exit(app.exec_())
