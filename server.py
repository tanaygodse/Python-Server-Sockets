import socket
import threading
import os
import mimetypes
import argparse


def handle_client_connection(client_socket, client_address, document_root, timeout):
    client_socket.settimeout(timeout)
    while True:
        try:
            request = client_socket.recv(1024).decode('utf-8')
            if not request:
                break

            # Parse HTTP request
            lines = request.split('\r\n')
            request_line = lines[0]
            parts = request_line.split()

            # Error Codes based on: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status
            if len(parts) < 3:
                send_response(client_socket, 400, 'Bad Request', 'HTTP/1.1')
                break

            method, path, http_version = parts
            if method != 'GET':
                send_response(client_socket, 501,
                              'Not Implemented', http_version)
                break

            # Handle default index.html
            if path == '/':
                path = '/index.html'

            # Construct full path
            file_path = os.path.join(document_root, path.lstrip('/'))
            file_path = os.path.normpath(file_path)
            # Check if file exists and is readable
            if not os.path.isfile(file_path):
                send_response(client_socket, 404, 'Not Found', http_version)
                break
            if not os.access(file_path, os.R_OK):
                send_response(client_socket, 403, 'Forbidden', http_version)
                break

            # Read file content
            with open(file_path, 'rb') as f:
                content = f.read()

            # Determine content type
            mime_type, _ = mimetypes.guess_type(file_path)
            if mime_type is None:
                mime_type = 'application/octet-stream'

            # Send successful 200 response with content
            send_response(client_socket, 200, content, http_version, mime_type)

            # For HTTP/1.0, close the connection after the response
            if http_version == 'HTTP/1.0':
                break

        except socket.timeout:
            break
        except Exception as e:
            print(f'Error handling request from {client_address}: {e}')
            break

    client_socket.close()


# Function to send a response (both success and error)
def send_response(client_socket, status_code, content, http_version, content_type=None):
    if status_code == 200:
        # Successful response
        response_headers = [
            f'{http_version} 200 OK',
            f'Content-Type: {content_type}',
            f'Content-Length: {len(content)}',
            'Connection: keep-alive' if http_version == 'HTTP/1.1' else 'Connection: close',
            '',
            ''
        ]
        response_headers = '\r\n'.join(response_headers)
        client_socket.sendall(response_headers.encode('utf-8') + content)
    else:
        # Error response
        response_body = f'<html><body><h1>{
            status_code} {content}</h1></body></html>'
        response_headers = [
            f'{http_version} {status_code} {content}',
            'Content-Type: text/html',
            f'Content-Length: {len(response_body)}',
            'Connection: close',
            '',
            ''
        ]
        response = '\r\n'.join(response_headers) + response_body
        client_socket.sendall(response.encode('utf-8'))


# Function to start the server
def start_server(port, document_root, timeout):
    # Ensure the document root exists
    if not os.path.isdir(document_root):
        os.makedirs(document_root)

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('0.0.0.0', port))
    server_socket.listen(5)
    print(f'Started Server at 0.0.0.0:{port}')
    print(f'Server listening on port {port}...')
    print('Ctrl + C to Stop the Server')

    try:
        while True:
            client_socket, client_address = server_socket.accept()
            print(f'Accepted connection from {client_address}')
            client_handler = threading.Thread(
                target=handle_client_connection,
                args=(client_socket, client_address, document_root, timeout)
            )
            client_handler.start()
    except KeyboardInterrupt:
        print('\nShutting down the server.')
    finally:
        server_socket.close()


# Main function to parse arguments and run the server
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Simple HTTP server")
    parser.add_argument('--port', type=int, default=8000,
                        help='Port to listen on (default: 8000)')
    parser.add_argument('--document_root', type=str, default=os.path.abspath('../www.sjsu.edu'),
                        help='Directory to serve files from (default: ../www.sjsu.edu)')
    parser.add_argument('--timeout', type=int, default=5,
                        help='Timeout for persistent connections in seconds (default: 5)')

    args = parser.parse_args()

    start_server(args.port, args.document_root, args.timeout)
