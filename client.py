import sys
import socket
import argparse
from os.path import isfile

# Execution arguments order:
# py client.py <host> <port> <operation> <file path 1> <file path 2>
def main():
    argv = ParseArgs()# Resice parametros

    host = argv.host
    port = argv.port
    

    
    # Connect to server
    try:
        if argv.verbose:
            print(f'[+]Trying connection to {host}, {port}...')
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((host, port))
            print(f'[+]Connected to {host}, {port}')
            # Does desired operation
            if argv.upfile != None:
                upload(s,argv.upfile,argv.verbose)
            elif argv.dowloadFile != None:
                download(s,argv.dowloadFile,argv.verbose)
            elif argv.deleteFile != None:
                delete(s,argv.deleteFil,argv.verbose)
            elif argv.list:
                listf(s,argv.verbose)
    except ConnectionRefusedError:
        print('Error: Host Unreachable.')
    except Exception as e:
        print('Error: Unknown error.')
        print(e)

def ParseArgs():
    '''
    ParseArgs() recibe de la linea de comandos
    '''
    parser = argparse.ArgumentParser(description='Simple FTFP Client')
    group = parser.add_mutually_exclusive_group()

    parser.add_argument('host', 
                    help='The IP of the TFTP server')
    
    parser.add_argument('port', 
                    type=int,
                    help='The port of the server')

    group.add_argument('-up','--upload', 
                    action='store',
                    dest='upfile',
                    default=None,
                    help='for Upload')

    group.add_argument('-dw','--dowload', 
                    action='store',
                    dest='dowloadFile',
                    default=None,
                    help='for Donwload server file')

    group.add_argument('-dl','--delete', 
                    action='store',
                    dest='deleteFile',
                    default=None,
                    help='Delete a Server File')

    group.add_argument('-ls','--list', 
                    action='store_true',
                    dest='list',
                    default=False,
                    help='List server files')
    
    group.add_argument('-v','--verbose', 
                    action='store_true',
                    dest='verbose',
                    default=False,
                    help='List server files')

    #Lee los argumentos de la linea de comandos
    args = parser.parse_args()

    if args.verbose:
        print("[upfile]",args.upfile)
        print("[donwfile]",args.dowloadFile)
        print("[delfile]",args.deleteFile)
        print("[list]",args.list)
    
    return args

# Upload file to server
def upload(s,file, verbose=False):
    # Gets local filename and checks existence
    lfn = file
    if not isfile(lfn):
        print(f'[x]Error: Cannot find {lfn}.')
        return
    
    # File exists, send request for Upload
    s.send(b'up')
    try:
        rfn = sys.argv[5]
    except IndexError:
        rfn = lfn

    if verbose:
        print(f'[+]Requested: Upload file {lfn} as {rfn}.')
        print('[+]Trying access to file...')

    # Sends filename for server
    s.send(rfn.encode('utf-8', 'replace'))

    # Reply (2)
    exists = s.recv(1).decode('utf-8', 'replace')
    if verbose:
        print('[+]Access granted! Processing...')

    if exists == 'y':
        print(f'[-]File "{rfn}" already exists in server.')
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
    if reply == '100': 
        print('[+]File saved successfully on server.')
    else: 
        print("[-]Couldn't save file on server. Server reported error.")

# Downlaod file from server
def download(s,file,verbose=False):
    # Requests download
    s.send(b'dw')

    rfn = file
    try:
        lfn = sys.argv[5]
    except IndexError:
        lfn = rfn
    if verbose:
        print(f'[+]Requested: Download file {rfn} as {lfn}.')
        print('[+]Trying access to file...')

    # Sends requested filename to server (1)
    s.send(rfn.encode('utf-8', 'replace'))

    # Reply (2)
    exists = s.recv(1).decode('utf-8', 'replace')
    if exists == 'n':
        print(f'[-]Cannot find {rfn} on server.')
        return
    
    # Checks file existence locally
    if verbose:
        print('[+]Access granted! Processing...')
    if isfile(lfn):
        print(f'[-]File {lfn} already exists locally.')
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
    print('[+]Downloading...')
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
    print(f'[*]Downloaded: {lfn}')

# Remove file on server
def delete(s,file,verbose=False):
    # Requests delete
    s.send(b'dl')

    rfn = file
    if verbose:
        print(f'[+]Requested: Delete file {rfn}.')
        print('[+]]Trying access to file...')

    # Sends requested filename (1)
    s.send(rfn.encode('utf-8', 'replace'))

    # Reply (2)
    exists = s.recv(1).decode('utf-8', 'replace')
    if exists == 'n':
        print(f'[-]Cannot find {rfn} on server.')
        return

    # File was found in server
    if verbose:
        print('[+]Access granted!')
    while True:
        remove = input('Are you sure to remove?\nThis action cannot be undone (y/n)\n$ ')
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
    if reply == '100': 
        print('[+]File removed successfully from server.')
    else: 
        print("[-]Error: Couldn't remove file from server. Server reported error.")

# List files stored in server
def listf(s,verbose=False):
    # Requests list
    s.send(b'ls')
    if verbose:
        print('[+]Checking for files in server...')

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

    print('[+]File list received:')
    print(buffer.decode('utf-8', 'replace'))

if __name__ == '__main__':
    main()