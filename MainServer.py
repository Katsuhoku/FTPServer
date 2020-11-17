import socket
import threading
import ResourceFile
from os import listdir
from datetime import datetime
from os.path import isfile, join

# Clase principal. Gestiona las conexiones entrantes, y las canaliza a sus respectivos
# hilos. Provee métodos para bloquear el acceso al sistmea de archivos, y para gestionar
# los objetos recurso (crearlos, proveerlos y removerlos).
class MainServer:
    def __init__(self, port):
        self.HOST = socket.gethostname()
        self.PORT = port
        self.activeResourceList = [] # Lista de recursos activos
        self.listCount = 0 # Contador de hilos de listado

        self.fileSystemLock = threading.Lock() # Semáforo para bloquear el acceso al FS
        self.listLock = threading.Lock() # Semáforo para el acceso a listCount
        self.resourceLock = threading.Lock() # Semáforo para el acceso a activeResourceList

         # Gets the file list in the received files directory
        self.files = [f for f in listdir('./recv') if isfile(join('./recv', f))]

    # Método principal    
    def start(self):
        print('Log:')
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((HOST, PORT))
            print(f'{datetime.now()} Server started. Ready to receive connections')
            
            try:
                # Server remains available
                while True:
                    s.listen()
                    conn, addr = s.accept()

                    # Handles the new connection
                    print('Connected by', addr)
                    op = conn.recv(1).decode('utf-8', 'replace')

                    # Obtains the desired file name and its resource (1)
                    name = conn.recv(1024).decode('utf-u', 'replace')
                    filename = f'recv/{name}'
                    resource = self.getResource(filename)

                    # Starts a thread with the respective function for the desired
                    # operation
                    if op == 'up': # Upload
                        threading._start_new_thread(resource.upload, (conn, addr))
                    elif op == 'dw': # Download
                        threading._start_new_thread(resource.download, (conn, addr))
                    elif op == 'dl': # Delete
                        threading._start_new_thread(resource.delete, (conn, addr))
                    elif op == 'ls': # List
                        threading._start_new_thread(self.listf, (conn, addr))
            except:
                print("Error?")

    # Provee el recurso para el archivo indicado en el parámetro. Si no existe, lo crea.
    # El método es sincronizado consigo mismo y con removeResource
    def getResource(self, filename):
        self.resourceLock.acquire()
        # Searchs resource
        for resource in self.activeResourceList:
            if resource.filename == filename:
                self.resourceLock.release()
                return resource
        
        # If resource doesn't exist, creates it
        resource = ResourceFile(filename, self)
        self.activeResourceList.append(resource)
        self.resourceLock.release()
        return resource


    # Elimina el recuros que se especifica en el parámetro. El método es sincronizado
    # consigo mismo y con getResource
    def removeResource(self, resource):
        self.resourceLock.acquire()
        try:
            self.activeResourceList.remove(resource)
            self.resourceLock.release()
            return True
        except ValueError:
            self.resourceLock.release()
            print("Couldn't find the resource")
            return False

    # Bloqua el sistema de archivos y actualiza la lista de archivos en el sistema
    def updateFileList(self):
        self.fileSystemLock.acquire()
        self.files = [f for f in listdir('./recv') if isfile(join('./recv', f))]
        self.fileSystemLock.release()
        
    # Envía la lista de archivos en el sistema al cliente
    def listf(self, conn, addr):
        self.listLock.acquire()
        self.listCount += 1
        if self.listCount == 1: self.fileSystemLock.acquire()
        self.listLock.release()

        with conn:
            # Sends file list one by one (1)
            for f in self.files:
                brk = '\n'
                conn.send(f + brk)

            # Confirmation (2)
            reply = conn.recv(3).decode('utf-8', 'replace')
            if reply == '100': print(f"{datetime.now()}: 100 List Successfull, sended file list to client in {addr}")
            else: print(f"{datetime.now()}: 404 List Failed, client in {addr} reported error.")

        self.listLock.acquire()
        self.listCount -= 1
        if self.listCount == 0: self.fileSystemLock.release()
        self.listLock.release()
    


if __name__ == '__main__':
    server = MainServer()
    server.start()
