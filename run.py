#!/usr/bin/env python
from camerafeed import CameraFeed
from argparse import ArgumentParser
from PyQt5.QtWidgets import QApplication
import sys

# make dict from args
parser = ArgumentParser(description="Camerafeed")
parser.add_argument('--config_path', dest='config_path', default="settings.ini", help='path to settinsg.ini')
args = parser.parse_args()


app=QApplication(sys.argv)
widget=CameraFeed()
widget.go_config(config_path=args.config_path)
widget.setWindowTitle('Airlines GUI')
widget.show()
sys.exit(app.exec_())


# start app
# camerafeed = CameraFeed()
# camerafeed.go_config(config_path=args.config_path)



