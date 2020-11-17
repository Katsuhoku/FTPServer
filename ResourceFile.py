import socket
import threading
from os import remove
from os.path import isfile
from datetime import datetime

# Clase que representa un único archivo almacenado en el sistema. Provee los métodos
# necesarios para gestioanr todos los tipos de acceso ala rchivo de forma concurrente
# implementado el modelo de Lectores y Escritores, con prioridad a Lectores
class ResourceFile:
    def __init__(self, filename, server):
        self.filename = filename
        self.server = server

        self.readersCount = 0
        self.uploadCount = 0
        self.deleted = False
        self.readersLock = threading.Lock()
        self.uploadLock = threading.Lock()
        self.deletedLock = threading.Lock()
        self.writersLock = threading.Lock()

    # Sends file info to client
    def download(self, conn, addr):
        # Resource adquisition (I)
        self.readersLock.acquire()
        self.readersCount += 1
        if self.readersCount == 1: self.writersLock.acquire()
        self.readersLock.release()

        # Checking file existence (II)
        self.deletedLock.acquire()
        if self.deleted:
            self.deletedLock.release()
            conn.send(b'n') # Reply (2)
            print(f"{datetime.now()}: 201 Download Failed, {self.filename} doesn't exist")
            return
        self.deletedLock.release()

        # File send (III)
        if isfile(self.filename):
            # Reply (2)
            conn.send(b'y')
            # If exists, asks for sending (3)
            send = conn.recv(1).decode('utf-8', 'replace')
            if send == 'n':
                print(f"{datetime.now()}: 301 Download Aborted, by client in {addr}")
                return
            
            # Sending file data (4)
            with open(self.filename, 'rb') as f:
                print('Sending...')
                data = f.read(1024)
                while data:
                    conn.send(data)
                    data = f.read(1024)

                # Confirmation
                reply = conn.recv(3).decode('utf-8', 'replace')
                if reply == '100': print(f"{datetime.now()}: 100 Download Successfull, {self.filename} sended to client in {addr}")
                else: print(f"{datetime.now()}: 401 Download Failed, client in {addr} reported error.")
        else:
            conn.send(b'n') # Reply (2)
            print(f"{datetime.now()}: 201 Download Failed, {self.filename} doesn't exist")

        # Resource liberation (IV)
        self.readersLock.acquire()
        self.readersCount -= 1
        if self.readersCount == 0: self.writersLock.release()
        self.readersLock.release()

    # Receives file info from client and stores it
    def upload(self, conn, addr):
        # Waiting resource announcement (I)
        self.uploadLock.acquire()
        self.uploadCount += 1
        self.uploadLock.release()

        # Resource adquisition (II)
        self.writersLock.acquire()
        self.uploadLock.acquire()
        self.uploadCount -= 1
        self.uploadLock.release()

        # Checking file existence (III)
        if isfile(self.filename):
            # Replu (2)
            conn.send(b'y')
            # Replace? (3)
            replace = conn.recv(1).decode('utf-8', 'replace')
            if replace == 'n':
                print(f"{datetime.now()}: 302 Upload Aborted, by client in {addr}")
                return
        else: conn.send(b'n') # Reply (2)

        # Data receving (IV)
        with open(self.filename, 'wb') as f:
            conn.settimeout(5)
            try:
                data = conn.recv(1024)
                while True:
                    f.write(data)
                    data = conn.recv(1024)
            except socket.timeout: pass
            conn.settimeout(None)

        # Confirmation (5)
        conn.send(b'100')
        print(f"{datetime.now()}: 100 Upload Successfull, stored {self.filename} from client in {addr}")

        # File list update (V)
        self.server.updateFileList()

        # Resource liberation (VI)
        self.deletedLock.acquire()
        self.deleted = False
        self.deletedLock.release()
        self.writersLock.release()
    
    # Removes a file from server
    # If there's no threads waiting in upload(), also removes this resource from server list
    def delete(self, conn, addr):
        # File doesn't more exist (I)
        self.deletedLock.acquire()
        self.deleted = True
        self.deletedLock.release()

        # Resource Adquisition (II)
        self.writersLock.acquire()

        # Checking file existence (III)
        if isfile(self.filename):
            # Reply (2)
            conn.send(b'y')
            # Remove? (3)
            remove = conn.recv(1).decode('utf-8', 'replace')
            if remove == 'n':
                print(f"{datetime.now()}: 303 Delete Aborted, by client in {addr}")
                return
        else: conn.send(b'n')

        # Delete file permanently (IV)
        remove(self.filename)

        # Confirmation (4)
        conn.send(b'100')
        print(f"{datetime.now()}: 100 Upload Successfull, {self.filename} was succesfully deleted")

        # Removing resource from server (V)
        self.uploadLock.acquire()
        if self.uploadCount == 0: self.server.removeResource(self)
        self.uploadLock.release()

        # File list update (VI)
        self.server.updateFileList()

        # Resource liberation (VII)
        self.writersLock.release()