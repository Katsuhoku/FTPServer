import threading

class DownloadThread (threading.Thread):
    def __init__(self, conn, server):
        threading.Thread.__init__(self)
        self.conn = conn
        self.server = server

    def run(self):
        name = conn.recv(1024).decode('utf-u', 'replace')
        filename = f'recv/{name}'

        resource = self.server.getResource(filename)
        if resource.download(self.conn): print(f'Downloaded: {filename}')
        else: print("Error: Couldn't send " + filename + " to the client")


class UploadThread (threading.Thread):
    def __init__(self, conn, server):
        threading.Thread.__init__(self)
        self.conn = conn
        self.server = server

    def run(self):
        name = conn.recv(1024).decode('utf-8', 'replace')
        filename = f'recv/{name}'

        resource = self.server.getResource(filename)
        if resource.upload(self.conn): print(f'Uploaded: {filename}')
        else: print("Error: Couldn't receive the file")

class DeleteThread (threading.Thread):
    def __init__(self, conn, server):
        threading.Thread.__init__(self)
        self.conn = conn
        self.server = server

    def run(self):
        name = conn.recv(1024).decode('utf-8', 'replace')
        filename = f'recv/{name}'

        resource = self.server.getResource(filename)
        if resource.upload(self.conn): print(f'Deleted: {filename}')
        else: print(f"Error: Couldn't delete {filename}")