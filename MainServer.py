import socket
import threading

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
                        pass
                    elif op == 'dw': # Download
                        pass
                    elif op == 'dl': # Delete
                        pass
                    elif op == 'rn': # Rename
                        pass
                    elif op == 'ls': # List
                        pass
            except:
                print("Error")

    # Provee el recurso para el archivo indicado en el parámetro. Si no existe, lo crea.
    # El método es sincronizado consigo mismo y con removeResource
    def getResource(self, filename):
        pass

    # Elimina el recuros que se especifica en el parámetro. El método es sincronizado
    # consigo mismo y con getResource
    def removeResource(self, resource):
        pass

    # Bloqua el sistema de archivos
    def acquireFileSystem(self):
        pass

    # Libera el sistema de Archivos
    def releaseFileSystem(self):
        pass

    # Incrementa el contador de hilos de listado (listCount)
    def listEnter(self):
        pass

    # Decrementa el contador de hilos de listado (listCount)
    def listExit(self):
        pass
