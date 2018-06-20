import firebase_admin
from firebase_admin import credentials
from firebase_admin import db


cred = credentials.Certificate('/home/sparsh/Projects/FirebasePython/firebase_credentials.json')
default_app = firebase_admin.initialize_app(cred , {'databaseURL' : 'https://throughputcalc.firebaseio.com'})

ref = db.reference('NSIT')

print ref.get()
