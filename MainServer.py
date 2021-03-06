# Benemérita Universidad Autónoma de Puebla
# Facultad de Ciencias de la Computación
# Programación Concurrente y Paralela
#
# Proyecto Final: Sistemas concurrentes, programación de un
# servidor FTP simple con gestión multiusuario concurrente.
#
# Arizmendi Ramírez Esiel Kevin, 201737811
# Coria Rios Marco Antonio, 201734576
# Ruiz Lozano Paulo César, 201727952
#
# Otoño 2020
# 27/Noviembre/2020

import sys
import errno
import socket
import threading
from datetime import datetime
from os import listdir, mkdir
from ResourceFile import ResourceFile
from os.path import isfile, isdir, join

# MainServer
# Clase principal. Gestiona las conexiones entrantes y las canaliza a sus respectivos
# hilos. Al recibir una conexión, solicita el tipo de operación, y luego el nombre
# del archivo (excepto si la operación es List) para generar el recurso correspondiente.
# Ejecuta en un nuevo hilo la función correspondiente del recurso a la operación
# solicitada.
#
# Provee semáforos y métodos para bloquear el acceso al sistema de archivos, y para
# obtener o generar los objetos recurso.
#
# Recurso: Objeto que representa y maneja el acceso a un archivo del sistema. Cada
# archivo se asocia con un y solo un recurso. Esto permite la ejecución concurrente
# de operaciones en diferentes recursos (salvo algunas excepciones)
class MainServer:
    def __init__(self,host=socket.gethostname(),port=42069):
        self.HOST = host
        self.PORT = port
        self.activeResourceList = [] # Lista de recursos arctivos
        self.listCount = 0 # Contador de hilos de operación List
        self.countID = 0 # Threads' ID counter

        self.fileSystemLock = threading.Lock() # Semáforo para bloquear el acceso al Sistema de Archivos
        self.listLock = threading.Lock() # Semáforo para el acceso a listCount
        self.resourceLock = threading.Lock() # Semáforo para el acceso a activeResourceList
        
        # Checa si existe el directorio
        if not isdir('./recv'):
            try:
                print(f'{datetime.now()} [Server] Creating directory ./recv for incoming files.')
                mkdir('./recv')
            except OSError as e:
                if e.errno != errno.EEXIST:
                    raise

        # Obtiene la lista de archivos en el sistema.
        self.files = [f for f in listdir('./recv') if isfile(join('./recv', f))]

    # Método principal, inicia el programa
    def start(self):
        # Creación del server socket. La cláusula 'with' maneja el socket y lo cierra
        # automáticamente al terminar
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as self.s:
            self.s.bind((self.HOST, self.PORT))# Crea un socket con esos parametros
            print(f'{datetime.now()} [Server] Service started on {self.HOST}, {self.PORT}. Ready to receive connections.')
            print('Press Enter to end process.')
            
            try:
                # Server remains available
                while True:
                    self.s.listen() # Escucha peticciones
                    conn, addr = self.s.accept() # Acepta una

                    # Handles the new connection
                    print(f'{datetime.now()} [Server] New connection received, connected by {addr}.')
                    self.countID += 1
                    op = conn.recv(2).decode('utf-8', 'replace')

                    # Si la operación es List, genera el nuevo hilo sin pedir más
                    # datos
                    if op == 'ls': # List
                        threading._start_new_thread(self.listf, (conn, addr, self.countID))
                        print(f'{datetime.now()} [Server] List Thread created.')
                    # Cualquier otra operación necesita primero el nombre del archivo
                    # deseado para generar el recurso.
                    else:
                        # Obtiene el nombre del archivo deseado (1)
                        name = conn.recv(1024).decode('utf-8', 'replace')
                        filename = f'recv/{name}'
                        # Busca y obtiene el recurso asociado al archivo
                        resource = self.getResource(filename)

                        # Starts a thread with the respective function for the desired
                        # operation
                        if op == 'up': # Upload
                            threading._start_new_thread(resource.upload, (conn, addr, self.countID))
                            print(f'{datetime.now()} [Server] Upload Thread created.')
                        elif op == 'dw': # Download
                            threading._start_new_thread(resource.download, (conn, addr, self.countID))
                            print(f'{datetime.now()} [Server] Download Thread created.')
                        elif op == 'dl': # Delete
                            threading._start_new_thread(resource.delete, (conn, addr, self.countID))
                            print(f'{datetime.now()} [Server] Delete Thread created.')
            except OSError:
                print(f'{datetime.now()} [Server] Service down by petition.')
            except Exception as e:
                print(f'{datetime.now()} [Server] Unknown Error. Service down.')
                print(e)

    # Provee el recurso para el archivo indicado en el parámetro. Si no existe, lo crea.
    # El método es sincronizado consigo mismo y con removeResource
    def getResource(self, filename):
        self.resourceLock.acquire()
        # Busca el recurso en la lista del servidor
        for resource in self.activeResourceList:
            if resource.filename == filename:
                # El recurso fue encontrado
                self.resourceLock.release()
                return resource
        
        # El recurso no fue encontrado, por lo que se crea uno nuevo asociándolo al
        # archivo solicitado
        resource = ResourceFile(filename, self)
        self.activeResourceList.append(resource)
        self.resourceLock.release()
        return resource


    # Elimina el recurso que se especifica en el parámetro de la lista del sistema.
    # El método es sincronizado consigo mismo y con getResource.
    def removeResource(self, resource):
        self.resourceLock.acquire()
        try:
            self.activeResourceList.remove(resource)
            self.resourceLock.release()
            return True
        except ValueError:
            self.resourceLock.release()
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
                print(f'{datetime.now()} [Server] Sending files list to client in {addr}.')
                conn.send(data)

            # Confirmation (2)
            reply = conn.recv(3).decode('utf-8', 'replace')
            if reply == '100': print(f"{datetime.now()} [Server] 100 List Successfull, sended file list to client in {addr}.")
            else: print(f"{datetime.now()} [Server] 404 List Failed, client in {addr} reported error.")

        self.listLock.acquire()
        self.listCount -= 1
        if self.listCount == 0: self.fileSystemLock.release()
        self.listLock.release()

    # Escucha de entrada para finalizar la ejecución del servidor
    # Se debe ejecutar en un hilo por separado, de tal forma que se mantenga escuchado
    # una entrada de teclado cualquiera. Esto permite que el servidor pueda detener
    # su ejecución incluso si se bloquea al esperar conexiones o datos del cliente.
    def listen_for_closing(self):
        while True:
            input()
            break
        self.s.close()

# Main
if __name__ == '__main__':
    print('Server Log:')
    try:
        PORT = int(sys.argv[1])
        server = MainServer(port=PORT)
    except :
        print(f'{datetime.now()} [Server] Port not specified. Using default port.')
        server = MainServer()

    # Ejecuta el hilo para la finalización de la ejecución
    threading._start_new_thread(server.listen_for_closing, ())
    # Ejecuta el servidor (no es un hilo aparte, la función se ejecuta sobre el
    # mismo hilo actual)
    server.start()
