import os
import socket
import threading
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
    def download(self, conn, addr, ID):
        print(f'{datetime.now()} Thread #{ID}: Preparing for download, trying to aquire resource...')
        # Resource adquisition (I)
        self.readersLock.acquire()
        self.readersCount += 1
        if self.readersCount == 1: self.writersLock.acquire()
        self.readersLock.release()

        print(f'{datetime.now()} Thread #{ID}: Resource Aquired.')

        with conn:
            # Checking file existence (II)
            self.deletedLock.acquire()
            if self.deleted:
                self.deletedLock.release()
                conn.send(b'n') # Reply (2)
                print(f"{datetime.now()}: 201 Download Failed, {self.filename} doesn't exist")
            else:
                self.deletedLock.release()

                # File send (III)
                if isfile(self.filename):
                    print(f'{datetime.now()} Thread #{ID}: File found. Waiting for confirmation to send...')
                    # Reply (2)
                    conn.send(b'y')
                    # If exists in client, asks for sending (3)
                    send = conn.recv(1).decode('utf-8', 'replace')
                    if send == 'n':
                        print(f"{datetime.now()}: 301 Download Aborted, by client in {addr}")
                    else:
                        # Sending file data (4)
                        print(f'{datetime.now()} Thread #{ID}: Download Confirmed.')
                        # Bug here...
                        with open(self.filename, 'rb') as f:
                            data = f.read(4096)
                            print(f'{datetime.now()} Thread #{ID}: Sending...')
                            while data:
                                conn.send(data)
                                data = f.read(4096)
                                print(f'{datetime.now()} Thread #{ID}: Sending...')

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
    def upload(self, conn, addr, ID):
        # Waiting resource announcement (I)
        self.uploadLock.acquire()
        self.uploadCount += 1
        self.uploadLock.release()

        # Resource adquisition (II)
        self.writersLock.acquire()
        self.uploadLock.acquire()
        self.uploadCount -= 1
        self.uploadLock.release()

        with conn:
            # Checking file existence (III)
            exists = isfile(self.filename)
            if exists:
                # Replu (2)
                conn.send(b'y')
                # Replace? (3)
                replace = conn.recv(1).decode('utf-8', 'replace')
                if replace == 'n':
                    print(f"{datetime.now()}: 302 Upload Aborted, by client in {addr}")
            else: conn.send(b'n') # Reply (2)

            # Data receving (IV)
            if exists and replace == 'y' or not exists:
                with open(self.filename, 'wb') as f:
                    conn.settimeout(5)
                    try:
                        data = conn.recv(4096)
                        while True:
                            f.write(data)
                            data = conn.recv(4096)
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
    def delete(self, conn, addr, ID):
        # Resource Adquisition (I)
        self.writersLock.acquire()

        with conn:
            # File doesn't more exist (II)
            self.deletedLock.acquire()
            # If file was already deleted while wating, ends process
            if self.deleted:
                self.deletedLock.release()
                conn.send(b'n') # Reply (2)
                print(f"{datetime.now()}: 201 Download Failed, {self.filename} doesn't exist")
            else:
                self.deleted = True
                self.deletedLock.release()

                # Checking file existence (III)
                if isfile(self.filename):
                    # Reply (2)
                    conn.send(b'y')
                    # Remove? (3)
                    remove = conn.recv(1).decode('utf-8', 'replace')
                    if remove == 'n':
                        print(f"{datetime.now()}: 303 Delete Aborted, by client in {addr}")
                    else:
                        # Delete file permanently (IV)
                        os.remove(self.filename)

                        # Confirmation (4)
                        conn.send(b'100')

                        # Removing resource from server (V)
                        # Prevents Upload threads to enter while is checking for already wating Uplaod threads
                        # in this resource
                        self.uploadLock.acquire()
                        if self.uploadCount == 0: self.server.removeResource(self)
                        self.uploadLock.release()

                        # File list update (VI)
                        self.server.updateFileList()
                        print(f"{datetime.now()}: 100 Delete Successfull, {self.filename} was succesfully deleted")
                else:
                    conn.send(b'n') # Reply (2)
                    print(f"{datetime.now()}: 201 Download Failed, {self.filename} doesn't exist")

        # Resource liberation (VII)
        self.writersLock.release()