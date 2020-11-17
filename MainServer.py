import sys
import socket
import threading
from os import listdir
from datetime import datetime
from os.path import isfile, join
from ResourceFile import ResourceFile

# Clase principal. Gestiona las conexiones entrantes, y las canaliza a sus respectivos
# hilos. Provee métodos para bloquear el acceso al sistmea de archivos, y para gestionar
# los objetos recurso (crearlos, proveerlos y removerlos).
class MainServer:
    def __init__(self, port):
        self.HOST = socket.gethostname()
        self.PORT = port
        self.activeResourceList = [] # Lista de recursos activos
        self.listCount = 0 # Contador de hilos de listado
        self.countID = 0 # Threads' ID counter

        self.fileSystemLock = threading.Lock() # Semáforo para bloquear el acceso al FS
        self.listLock = threading.Lock() # Semáforo para el acceso a listCount
        self.resourceLock = threading.Lock() # Semáforo para el acceso a activeResourceList

         # Gets the file list in the received files directory
        self.files = [f for f in listdir('./recv') if isfile(join('./recv', f))]

    # Método principal    
    def start(self):
        print('Log:')
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as self.s:
            self.s.bind((self.HOST, self.PORT))
            print(f'{datetime.now()} Server started on {self.HOST}, {self.PORT}. Ready to receive connections')
            print('Press Enter to end process.')
            
            try:
                # Server remains available
                while True:
                    self.s.listen()
                    conn, addr = self.s.accept()

                    # Handles the new connection
                    print('Connected by', addr)
                    self.countID += 1
                    op = conn.recv(2).decode('utf-8', 'replace')

                    if op == 'ls': # List
                        threading._start_new_thread(self.listf, (conn, addr, self.countID))
                        print(f'{datetime.now()} List Thread created')
                    else:
                        # Obtains the desired file name and its resource (1)
                        name = conn.recv(1024).decode('utf-8', 'replace')
                        filename = f'recv/{name}'
                        resource = self.getResource(filename)

                        print(f'Working... {op}')

                        # Starts a thread with the respective function for the desired
                        # operation
                        if op == 'up': # Upload
                            threading._start_new_thread(resource.upload, (conn, addr, self.countID))
                            print(f'{datetime.now()} Upload Thread created')
                        elif op == 'dw': # Download
                            threading._start_new_thread(resource.download, (conn, addr, self.countID))
                            print(f'{datetime.now()} Download Thread created')
                        elif op == 'dl': # Delete
                            threading._start_new_thread(resource.delete, (conn, addr, self.countID))
                            print(f'{datetime.now()} Delete Thread created')
            except OSError:
                print(f'{datetime.now()} Server down by petition.')
            except Exception as e:
                print(f'{datetime.now()} Unknown Error.')
                print(e)

    # Provee el recurso para el archivo indicado en el parámetro. Si no existe, lo crea.
    # El método es sincronizado consigo mismo y con removeResource
    def getResource(self, filename):
        self.resourceLock.acquire()
        # Searchs resource
        print(f'Desired: {filename}')
        for resource in self.activeResourceList:
            if resource.filename == filename:
                print(f'Resource selection: {resource.filename}')
                self.resourceLock.release()
                return resource
        
        # If resource doesn't exist, creates it
        print('Did not exist, creating resource')
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
    def listf(self, conn, addr, ID):
        self.listLock.acquire()
        self.listCount += 1
        if self.listCount == 1: self.fileSystemLock.acquire()
        self.listLock.release()

        with conn:
            # Sends file list one by one (1)
            for f in self.files:
                data = str(f + '\n').encode('utf-8', 'replace')
                print('Sending...')
                conn.send(data)

            # Confirmation (2)
            reply = conn.recv(3).decode('utf-8', 'replace')
            if reply == '100': print(f"{datetime.now()}: 100 List Successfull, sended file list to client in {addr}")
            else: print(f"{datetime.now()}: 404 List Failed, client in {addr} reported error.")

        self.listLock.acquire()
        self.listCount -= 1
        if self.listCount == 0: self.fileSystemLock.release()
        self.listLock.release()

    def listen_for_closing(self):
        while True:
            input()
            break
        self.s.close()


if __name__ == '__main__':
    server = MainServer(int(sys.argv[1]))
    threading._start_new_thread(server.listen_for_closing, ())
    server.start()
