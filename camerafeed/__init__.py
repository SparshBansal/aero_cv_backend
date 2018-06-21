import configparser
import time
import sys

import cv2
import imutils
import grequests
import json

from camerafeed.peopletracker import PeopleTracker
from camerafeed.tripline import Tripline

import firebase_admin
from firebase_admin import credentials
from firebase_admin import db

import argparse
import imutils
from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtWidgets import QApplication,QDialog
from PyQt5.uic import loadUi

class CameraFeed(QDialog):
    # frame dimension (calculated below in go)
    _frame_width = 0
    _frame_height = 0

    # how many frames processed
    _frame = 0

    def __init__(self, source=0, crop_x1=0, crop_y1=0, crop_x2=500, crop_y2=500, max_width=640, b_and_w=False,
                 hog_win_stride=6, hog_padding=8, hog_scale=1.05, mog_enabled=False, people_options=None, lines=None,
                 font=cv2.FONT_HERSHEY_SIMPLEX, endpoint=None, pi=False, show_window=True, to_stdout=False,
                 save_first_frame=False, quit_after_first_frame=False):

        self.__dict__.update(locals())

        #Initializer for UI
        super(CameraFeed,self).__init__()
        loadUi('airlines.ui',self)
        self.image=None
        self.startButton.clicked.connect(self.start_webcam)
        self.stopButton.clicked.connect(self.stop_webcam)
        self.detectButton.setCheckable(True)
        self.detectButton.toggled.connect(self.detect_people)
        self.f_Enabled=False

        # setup firebase credentials
        # cred = credentials.Certificate('/Users/newuser/Documents/People Tracking/aero_cv_backend/firebase_credentials.json')
        # default_app = firebase_admin.initialize_app(cred , {'databaseURL' : 'https://throughputcalc.firebaseio.com'})
    
    def detect_people(self,status):
        if status:
            self.detectButton.setText('Stop Detection')
            self.f_Enabled = True
        else:
            self.detectButton.setText('Detect')
            self.f_Enabled = False    

    def start_webcam(self):
        # self.capture=cv2.VideoCapture('/home/zero/1.MP4')
        # self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT,281)
        # self.capture.set(cv2.CAP_PROP_FRAME_WIDTH,371)
        
        self.go()

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(5)

    def update_frame(self):

        # self.go()
        # feed in video
        if self.pi:

            for frame in self.camera.capture_continuous(self.rawCapture, format="bgr", use_video_port=True):

                image = frame.array
                self.process(image)
                self.rawCapture.truncate(0)

                if self.quit_after_first_frame or cv2.waitKey(1) & 0xFF == ord('q'):
                    break
        else:

            if self.camera.isOpened():

                rval, frame = self.camera.read()
                self.origFrame  = frame
                self.process(frame)

        # ret,self.image = self.camera.read()
        # self.image=cv2.flip(self.image,1)

        # if(self.f_Enabled):
        #     detected_image = self.detection_algo(self.image)
        #     self.displayImage(detected_image,1)
        # else:
        #     self.displayImage(self.image,1)

    def stop_webcam(self):
        self.camera.release()
        cv2.destroyAllWindows()
        # self.timer.stop();

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


    def go_config(self, config_path=None):

        # load config
        config = configparser.ConfigParser()
        config.read(config_path)

        # remote host settings
        self.endpoint = config.get('host', 'endpoint', fallback=None)

        cred = credentials.Certificate(config.get('host', 'firebase_credentials_path'))
        default_app = firebase_admin.initialize_app(cred , {'databaseURL' : 'https://throughputcalc.firebaseio.com'})


        # platform
        self.pi = config.getboolean('platform', 'pi')
        self.to_stdout = config.getboolean('platform', 'to_stdout')
        self.show_window = config.getboolean('platform', 'show_window')
        self.save_first_frame = config.getboolean('platform', 'save_first_frame')
        self.quit_after_first_frame = config.getboolean('platform', 'quit_after_first_frame')

        # video source settings
        self.crop_x1 = config.getint('video_source', 'frame_x1')
        self.crop_y1 = config.getint('video_source', 'frame_y1')
        self.crop_x2 = config.getint('video_source', 'frame_x2')
        self.crop_y2 = config.getint('video_source', 'frame_y2')
        self.max_width = config.getint('video_source', 'max_width')
        self.b_and_w = config.getboolean('video_source', 'b_and_w')

        # hog settings
        self.hog_win_stride = config.getint('hog', 'win_stride')
        self.hog_padding = config.getint('hog', 'padding')
        self.hog_scale = config.getfloat('hog', 'scale')

        # mog settings
        self.mog_enabled = config.getboolean('mog', 'enabled')
        if self.mog_enabled:
            self.mogbg = cv2.createBackgroundSubtractorMOG2()

        # setup lines
        lines = []
        total_lines = config.getint('triplines', 'total_lines')

        for idx in range(total_lines):
            key = 'line%d' % (idx + 1)
            start = eval(config.get('triplines', '%s_start' % key))
            end = eval(config.get('triplines', '%s_end' % key))
            buffer = config.getint('triplines', '%s_buffer' % key, fallback=10)
            direction_1 = config.get('triplines', '%s_direction_1' % key, fallback='Up')
            direction_2 = config.get('triplines', '%s_direction_2' % key, fallback='Down')
            line = Tripline(point_1=start, point_2=end, buffer_size=buffer, direction_1=direction_1,
                            direction_2=direction_2)
            lines.append(line)

        self.lines = lines
        self.source = config.get('video_source', 'source')
        self.people_options = dict(config.items('person'))

        # self.go()

    def go(self):

        # setup HUD
        self.last_time = time.time()

        # opencv 3.x bug??
        cv2.ocl.setUseOpenCL(False)

        # people tracking
        self.finder = PeopleTracker(people_options=self.people_options)

        # STARTS HERE
        # connect to camera
        if self.pi:

            from picamera.array import PiRGBArray
            from picamera import PiCamera

            self.camera = PiCamera()
            self.camera.resolution = (640, 480)
            self.camera.framerate = 20

            self.rawCapture = PiRGBArray(self.camera, size=(640, 480))

            time.sleep(1)  # let camera warm up

        else:
            self.camera = cv2.VideoCapture(self.source)

        # setup detectors
        self.hog = cv2.HOGDescriptor()
        self.hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

        # setup throughput info
        self.ptime = time.time()
        self.pcount = 0

        # # feed in video
        # if self.pi:

        #     for frame in self.camera.capture_continuous(self.rawCapture, format="bgr", use_video_port=True):

        #         image = frame.array
        #         self.process(image)
        #         self.rawCapture.truncate(0)

        #         if self.quit_after_first_frame or cv2.waitKey(1) & 0xFF == ord('q'):
        #             break
        # else:

        #     if self.camera.isOpened():

        #         rval, frame = self.camera.read()
        #         self.origFrame  = frame
        #         self.process(frame)

        #         # if self.quit_after_first_frame or cv2.waitKey(1) & 0xFF == ord('q'):
        #         #     break

    def process(self, frame):

        if self.b_and_w:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        frame = self.crop_and_resize(frame)

        print_frame_size = self._frame_height == 0

        self._frame_height = frame.shape[0]
        self._frame_width = frame.shape[1]

        if print_frame_size and not self.to_stdout:
            print('resized video to %dx%d' % (self._frame_width, self._frame_height))

        frame = self.apply_mog(frame)
        frame = self.handle_the_people(frame)
        frame = self.render_hud(frame)

        # ret,image = self.camera.read()
        # self.image=cv2.flip(self.image,1)



        if(self.f_Enabled):
            self.displayImage(frame,1)
        else:
            self.displayImage(self.origFrame,1)

        # if self.show_window:
        #     cv2.imshow('Camerafeed', frame)

        if self.to_stdout:
            sys.stdout.write(frame.tostring())
            # string = "".join(map(chr, frame.tostring()))
            # sys.stdout.write(string)

        if self.save_first_frame and self._frame == 0:
            cv2.imwrite('first_frame.png', frame)

    # help us crop/resize frames as they come in
    def crop_and_resize(self, frame):

        frame = frame[self.crop_y1:self.crop_y2, self.crop_x1:self.crop_x2]
        frame = imutils.resize(frame, width=min(self.max_width, frame.shape[1]))

        return frame

    # apply background subtraction if needed
    def apply_mog(self, frame):
        if self.mog_enabled:
            mask = self.mogbg.apply(frame)
            frame = cv2.bitwise_and(frame, frame, mask=mask)

        return frame

    # all the data that overlays the video
    def render_hud(self, frame):
        this_time = time.time()
        diff = this_time - self.last_time
        fps = 1 / diff
        message = 'FPS: %d' % fps
        # print(message)

        cv2.putText(frame, message, (10, self._frame_height - 20), self.font, 0.5, (255, 255, 255), 2)

        self.last_time = time.time()

        return frame

    def handle_the_people(self, frame):

        (rects, weight) = self.hog.detectMultiScale(frame, winStride=(self.hog_win_stride, self.hog_win_stride),
                                                    padding=(self.hog_padding, self.hog_padding), scale=self.hog_scale)

        people = self.finder.people(rects)
        
        if ( len(people) != self.pcount ):
            if ( abs( self.pcount - len(people) ) > 3 ):
                print "People Count  :  " , len(people)
                ref = db.reference('NSIT').child('Jet Airways').child('carrier').child('1').update({
                    'counterCount' : len(people)
                    })
                self.pcount = len(people)

        # draw triplines
        for line in self.lines:
            for person in people:
                if line.handle_collision(person) == 1:
                    self.new_collision(person)

            frame = line.draw(frame)

        for person in people:
            frame = person.draw(frame)
            person.colliding = False

        return frame

    def new_collision(self, person):

        if self.endpoint is not None:
            post = {
                'name': person.name,
                'meta': json.dumps(person.meta),
                'date': time.time()
            }

            request = grequests.post(self.endpoint, data=post)
            grequests.map([request])

        if not self.to_stdout:
            # compute throughput now
            # ctime = time.time()
            # throughput = ctime - self.ptime
            # self.ptime = ctime
            ctime = self.camera.get(cv2.CAP_PROP_POS_MSEC)/1000
            print("Collision recorded at "+str(ctime)+"s")
            throughput = ctime - self.ptime
            self.ptime  = ctime
            

            if ( throughput >= 5 and person.meta['line-0']=="north" ):
                # push the data to the server
                print("Throughput update %d" % (throughput))
                ref = db.reference('NSIT').child('Jet Airways').child('carrier').child('1').update({
                    'throughput' : throughput
                    })
            
            print("NEW COLLISION %s HEADING %s" % (person.name, person.meta['line-0']))

# if( __name__=='____init____'):
#     app=QApplication(sys.argv)
#     widget=airlines()
#     widget.setWindowTitle('Airlines GUI')
#     widget.show()
#     sys.exit(app.exec_())
