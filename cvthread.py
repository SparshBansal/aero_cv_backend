from PyQt5.QtCore import QThread
import cv2

class CVThread ( QThread ):

    def __init__( self, camerafeed , onFrameProcessedSignal):
        self.camerafeed = camerafeed
        self.onFrameProcessedSignal = onFrameProcessedSignal

        QThread.__init__(self)

    def __del__():
        self.wait()


    def run( self ):
        # Initialize tracker info
        self.camerafeed.init_tracker()

        # Initialize camera source
        self.camera = cv2.VideoCapture(self.camerafeed.source)
        
        while( self.camera.isOpened() ):
            rval, frame = self.camera.read()
            pFrame = self.camerafeed.process(frame)
            self.onFrameProcessedSignal.emit(frame, pFrame, self.camerafeed.pcount, self.camerafeed.throughput)
