import firebase_admin
from firebase_admin import credentials, firestore

db = None


def init_firebase():
    global db
    cred = credentials.Certificate("serviceAccountKey.json")
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("Firestore connection established.")
