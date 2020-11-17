import os
import socket
import threading
from os.path import isfile
from datetime import datetime

# ResourceFile
# Clase que representa un único archivo almacenado en el sistema. Provee los métodos
# necesarios para gestionar todos los tipos de acceso al archivo de forma concurrente
# implementado el modelo de Lectores y Escritores, con prioridad a Lectores.
#
# Funciones Lector: download()
# Funciones Escritor: upload(), delete()
# Pese a ser Escritores, las operaciones upload() y delete() no son completamente
# iguales. Eliminar un archivo del sistema no implica que el recurso también deba ser
# eliminado. Al eliminar, otros hilos pueden estar esperando su lugar, ya sea para
# leer (download) o para escribir (upload, delete). Es por esto que se implementan
# otras variables comunes para dar estos avisos.
#
# El recurso será eliminado del sistema (al eliminar el archivo) únicamente cuando
# no queden hilos esperando para subir (upload) información. (Si se elimina el recurso
# podría generar inconsistencias, pues en el servidor se generaría otro recurso con
# diferentes semáforos para los nuevos hilos después de la eliminación)
#
# Al eliminar, el hilo debe avisar a los demás hilos de lectura (downlaod) y escritura
# (únicamente delete) que el archivo ha sido eliminado. Éstos deben, antes
# de buscar el archivo en el sistema, comprobar este aviso, evitando así intentar
# acceder a un archivo "inexistente".
class ResourceFile:
    def __init__(self, filename, server):
        self.filename = filename # Nombre del archivo asociado a este recurso
        self.server = server # Objeto del servidor

        self.readersCount = 0 # Contador de hilos de lectura ACTIVOS (leyendo o esperando)
        self.uploadCount = 0 # Contador de hilos de escritora upload ESPERANDO
        self.deleted = False # Bandera de eliminación
        self.readersLock = threading.Lock() # Semáforo para los lectores
        self.uploadLock = threading.Lock() # Semáforo para acceder a uploadCount
        self.deletedLock = threading.Lock() # Semáforo para acceder a la bandera deleted
        self.writersLock = threading.Lock() # Semáforo para los escritores

    # Download
    # Gestiona todo el proceso de descarga de un archivo con el cliente
    # Consta de los siguientes pasos:
    # (2) Confirmar la existencia del archivo en el servidor
    # (3) Confirmar con el usuario el envío del archivo
    # (4) Envíar el archivo
    # (5) Esperar la confirmación del cliente de la recepción del archivo
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
            # Primero verifica que el archivo no haya sido eliminado anteriormente por
            # un hilo delete()
            self.deletedLock.acquire()
            if self.deleted:
                self.deletedLock.release()
                conn.send(b'n') # Reply (2)
                print(f"{datetime.now()}: 201 Download Failed, {self.filename} doesn't exist")
            else:
                self.deletedLock.release()

                # File send (III)
                # Comprueba que el archivo exista en el servidor
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

    # Upload
    # Gestiona el proceso de la subida de un archivo al servidor.
    # Consta de los siguientes pasos:
    # (2) Confirmar la existencia del archivo en el servidor
    # (3) Si el archivo existe, confirmar la sobreescritura
    # (4) Recibir los datos del archivo
    # (5) Envíar una confirmación del archivo recibido
    def upload(self, conn, addr, ID):
        # Waiting resource announcement (I)
        # Incrementa el contador de hilos upload() en espera
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
                # Reply (2)
                conn.send(b'y')
                # Replace? (3)
                # Si el archivo existe, pregunta al cliente por sobreescribir
                replace = conn.recv(1).decode('utf-8', 'replace')
                if replace == 'n':
                    print(f"{datetime.now()}: 302 Upload Aborted, by client in {addr}")
            else: conn.send(b'n') # Reply (2)

            # Data receving (IV)
            # Si el archivo no existía, o existía y se confirmó la sobreescritura
            if exists and replace == 'y' or not exists:
                with open(self.filename, 'wb') as f:
                    conn.settimeout(5)
                    try:
                        # Recibe los datos del archivo (4)
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
                # Actualiza la lista de archivos en el servidor
                self.server.updateFileList()

        # Resource liberation (VI)
        self.deletedLock.acquire()
        self.deleted = False
        self.deletedLock.release()
        self.writersLock.release()
    
    # Remove
    # Gestiona el proceso de la eliminación de un archivo almacenado en el servidor
    # Consta de los siguientes pasos:
    # (2) Confirmar la existencia del archivo
    # (3) Si el archivo existe, confirmar con el usuario la eliminación (esta operación
    # no se puede revertir)
    # (4) Eliminar el archivo y confirmar al usuario la eliminación
    def delete(self, conn, addr, ID):
        # Resource Adquisition (I)
        self.writersLock.acquire()

        with conn:
            # File doesn't more exist (II)
            self.deletedLock.acquire()
            # If file was already deleted while wating, ends process
            # Si el archivo fue eliminado por un hilo delete() anterior, finaliza
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
                    # Pregunta al usuario por última vez si desea eliminar el archivo
                    remove = conn.recv(1).decode('utf-8', 'replace')
                    if remove == 'n':
                        print(f"{datetime.now()}: 303 Delete Aborted, by client in {addr}")
                    else:
                        # Delete file permanently (IV)
                        os.remove(self.filename)

                        # Confirmation (4)
                        conn.send(b'100')

                        # Removing resource from server (V)
                        # Elimina este recurso de la lista del servidor, solo si no
                        # quedan hilos upload() esperando.
                        self.uploadLock.acquire()
                        if self.uploadCount == 0: self.server.removeResource(self)
                        self.uploadLock.release()

                        # File list update (VI)
                        # Actualiza la lista de archivos en el servidor
                        self.server.updateFileList()
                        print(f"{datetime.now()}: 100 Delete Successfull, {self.filename} was succesfully deleted")
                else:
                    conn.send(b'n') # Reply (2)
                    print(f"{datetime.now()}: 201 Download Failed, {self.filename} doesn't exist")

        # Resource liberation (VII)
        self.writersLock.release()