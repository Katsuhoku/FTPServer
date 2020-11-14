import socket
import threading
from os.path import isfile
from os import remove

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
    def download(self, conn):
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
            return False
        self.deletedLock.release()

        # File send (III)
        if isfile(self.filename):
            # Reply (2)
            conn.send(b'y')
            # If exists, asks for sending (3)
            send = conn.recv(1).decode('utf-8', 'replace')
            if send == 'n': return False
            
            # Sending file data (4)
            with open(self.filename, 'rb') as f:
                print('Sending...')
                data = f.read(1024)
                while data:
                    conn.send(data)
                    data = f.read(1024)

                # Confirmation
                reply = conn.recv(3).decode('utf-8', 'replace')
                if reply == '100': print('File transfered succesfully')
                else: print("Error: Couldn't transfer the file.")
        else: conn.send(b'n') # Reply (2)

        # Resource liberation (IV)
        self.readersLock.acquire()
        self.readersCount -= 1
        if self.readersCount == 0: self.writersLock.release()
        self.readersLock.release()

        return True

    # Receives file info from client and stores it
    def upload(self, conn):
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
            if replace == 'n': return False
        else: conn.send(b'n') # Reply (2)

        # Data receving (IV)
        self.server.aquireFileSystem()
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
        print(f'Uploaded: {self.filename}')
        self.server.releaseFileSystem()

        # Resource liberation (V)
        self.deletedLock.acquire()
        self.deleted = False
        self.deletedLock.release()
        self.writersLock.release()

        return True
    
    # Removes a file from server
    # If there's no threads waiting in upload(), also removes this resource from server list
    def delete(self, conn):
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
            if remove == 'n': return False
        else: conn.send(b'n')

        # Delete file permanently (IV)
        self.server.aquireFileSystem()
        remove(self.filename)
        self.server.releaseFileSystem()

        # Confirmation (4)
        conn.send(b'100')
        print(f'Removed: {self.filename}')

        # Removing resource from server (V)
        self.uploadLock.acquire()
        if self.uploadCount == 0: self.server.removeResource(self)
        self.uploadLock.release()

        # Resource liberation (VI)
        self.writersLock.release()

        return True