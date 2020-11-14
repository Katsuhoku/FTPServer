import socket
import threading
import systhreads
import ResourceFile

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

    # Método principal    
    def start(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((HOST, PORT))
            
            try:
                # Server remains available
                while True:
                    s.listen()
                    conn, addr = s.accept()

                    # Handles the new connection
                    print('Connected by', addr)
                    op = conn.recv(1).decode('utf-8', 'replace')
                    if op == 'up': # Upload
                        systhreads.UploadThread(conn, self).start()
                    elif op == 'dw': # Download
                        systhreads.DownloadThread(conn, self).start()
                    elif op == 'dl': # Delete
                        systhreads.DeleteThread(conn, self).start()
                    elif op == 'rn': # Rename
                        pass
                    elif op == 'ls': # List
                        pass
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

    # Bloqua el sistema de archivos
    def acquireFileSystem(self):
        self.fileSystemLock.acquire()

    # Libera el sistema de Archivos
    def releaseFileSystem(self):
        self.fileSystemLock.release()

    # Incrementa el contador de hilos de listado (listCount)
    # Equivalente a un proceso de lectura (entre los procesos List y Delete)
    def listEnter(self):
        self.listLock.acquire()
        self.listCount += 1
        if self.listCount == 1: self.fileSystemLock.acquire()
        self.listLock.release()

    # Decrementa el contador de hilos de listado (listCount)
    def listExit(self):
        self.listLock.acquire()
        self.listCount -= 1
        if self.listCount == 0: self.fileSystemLock.release()
        self.listLock.release()
