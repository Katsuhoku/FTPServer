import sys
import socket
from os.path import isfile

# Execution arguments order:
# py client.py <host> <port> <operation> <file path 1> <file path 2>
def main():
    if len(sys.argv) < 4:
        print('Usage error, execution must be:')
        print('py client.py <host IP> <port> <operation> <file path 1> <file path 2>')
        print('Where:')
        print('Host IP: The IP of the TFTP server')
        print('Port: The port of the server')
        print('Operation: One of four, -up for Upload, -dw for Donwload, -dl for Delete and -ls for List server files')
        print('File Path 1: Required by Upload (as Local file), Download and Delete (as Remote File)')
        print('File Path 2: Required by Upload (as Remote Filename, Optional), Download (as Local Filename, Optional)')
        return

    host = sys.argv[1]
    port = int(sys.argv[2])
    op = sys.argv[3][1:]

    # Connect to server
    try:
        print(f'Trying connection to {host}, {port}...')
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((host, port))
            print(f'Connected to {host}, {port}')

            # Does desired operation
            if op == 'up':
                if len(sys.argv) < 5:
                    print('Usage error, Upload operation requires:')
                    print('py client.py <host IP> <port> <operation> <Local Filename> <Remote Filename (Optional)>')
                else: upload(s)
            elif op == 'dw':
                if len(sys.argv) < 5:
                    print('Usage error, Download operation requires:')
                    print('py client.py <host IP> <port> <operation> <Remote Filename> <Local Filename (Optional)>')
                else: download(s)
            elif op == 'dl':
                if len(sys.argv) < 5:
                    print('Usage error, Delete operation requires:')
                    print('py client.py <host IP> <port> <operation> <Remote Filename>')
                else: delete(s)
            elif op == 'ls':
                listf(s)
            else:
                print('Error: Unknown operation. Please enter:')
                print('-up for Upload')
                print('-dw for Downlaod')
                print('-dl for Delete')
                print('-ls for List files')
    except ConnectionRefusedError:
        print('Error: Host Unreachable.')
    except Exception as e:
        print('Error: Unknown error.')
        print(e)

# Upload file to server
def upload(s):
    # Gets local filename and checks existence
    lfn = sys.argv[4]
    if not isfile(lfn):
        print(f'Error: Cannot find {lfn}.')
        return
    
    # File exists, send request for Upload
    s.send(b'up')
    try:
        rfn = sys.argv[5]
    except IndexError:
        rfn = lfn

    print(f'Requested: Upload file {lfn} as {rfn}.')
    print('Trying access to file...')

    # Sends filename for server
    s.send(rfn.encode('utf-8', 'replace'))

    # Reply (2)
    exists = s.recv(1).decode('utf-8', 'replace')
    print('Access granted! Processing...')
    if exists == 'y':
        print(f'File "{rfn}" already exists in server.')
        while True:
            replace = input('Replace? (y/n) > ')
            if replace == 'y' or replace == 'n':
                # Replacement answer (3)
                s.send(replace.encode('utf-8'))
                break
            print('(Expected "y" for replace, or "n" for cancel. Try again.)')
        if replace == 'n':
            print('Upload Aborted')
            return

    # Sending file data (4)
    with open(lfn, 'rb') as lf:
        print('Uploading...')
        data = lf.read(4096)
        while data:
            s.send(data)
            data = lf.read(4096)

    # Confirmation (5)
    reply = s.recv(3).decode('utf-8', 'replace')
    if reply == '100': print('File saved successfully on server.')
    else: print("Couldn't save file on server. Server reported error.")

# Downlaod file from server
def download(s):
    # Requests download
    s.send(b'dw')

    rfn = sys.argv[4]
    try:
        lfn = sys.argv[5]
    except IndexError:
        lfn = rfn
    
    print(f'Requested: Download file {rfn} as {lfn}.')
    print('Trying access to file...')

    # Sends requested filename to server (1)
    s.send(rfn.encode('utf-8', 'replace'))

    # Reply (2)
    exists = s.recv(1).decode('utf-8', 'replace')
    if exists == 'n':
        print(f'Cannot find {rfn} on server.')
        return
    
    # Checks file existence locally
    print('Access granted! Processing...')
    if isfile(lfn):
        print(f'File {lfn} already exists locally.')
        while True:
            replace = input('Replace? (y/n) > ')
            if replace == 'y' or replace == 'n':
                # Replacement answer (3)
                s.send(replace.encode('utf-8'))
                break
            print('(Expected "y" for replace, or "n" for cancel. Try again.)')
        
        if replace == 'n':
            print('Download Aborted')
            return
    else: s.send(b'y')

    # New File (4)
    print('Downloading...')
    with open(lfn, 'wb') as lf:
        s.settimeout(5)
        try:
            data = s.recv(4096)
            while True:
                lf.write(data)
                data = s.recv(4096)
        except socket.timeout: pass
        s.settimeout(None)

    # Confirmation (5)
    s.send(b'100')
    print(f'Downloaded: {lfn}')

# Remove file on server
def delete(s):
    # Requests delete
    s.send(b'dl')

    rfn = sys.argv[4]
    print(f'Requested: Delete file {rfn}.')
    print('Trying access to file...')

    # Sends requested filename (1)
    s.send(rfn.encode('utf-8', 'replace'))

    # Reply (2)
    exists = s.recv(1).decode('utf-8', 'replace')
    if exists == 'n':
        print(f'Cannot find {rfn} on server.')
        return

    # File was found in server
    print('Access granted!')
    while True:
        remove = input('Are you sure to remove?\nThis action cannot be undone (y/n) > ')
        if remove == 'y' or remove == 'n':
            # Replacement answer (3)
            s.send(remove.encode('utf-8'))
            break
        print('(Expected "y" for replace, or "n" for cancel. Try again.)')
    if remove == 'n':
        print('Delete Aborted')
        return

    # Confirmation (4)
    reply = s.recv(3).decode('utf-8', 'replace')
    if reply == '100': print('File removed successfully from server.')
    else: print("Error: Couldn't remove file from server. Server reported error.")

# List files stored in server
def listf(s):
    # Requests list
    s.send(b'ls')

    print('Checking for files in server...')

    # Receiving file list (1)
    s.settimeout(3)
    buffer = b''
    try:
        while True:
            buffer += s.recv(4096)
    except socket.timeout: pass
    s.settimeout(None)

    # Confirmation (2)
    s.send(b'100')

    print('File list received:')
    print(buffer.decode('utf-8', 'replace'))



if __name__ == '__main__':
    main()