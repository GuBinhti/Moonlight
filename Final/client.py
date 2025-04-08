import socket
import sys
import threading

def read_from_server(sock):
    #keep reading datra from server socket and print to client console

    try:
        while True:
            data = sock.recv(1024)
            if not data:
                break
            print(data.decode("utf-8"), end='')
    except ConnectionError:
        pass
    finally:
        print("\n[Client] Connection to the server closed.")

def main():
    host = '127.0.0.1'
    port = 12345

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, port))
        print(f"[Client] Connected to server at {host}:{port}")
    except Exception as e:
        print(f"[Client] Could not connect to {host}:{port} -> {e}")
        sys.exit(1)

    read_thread = threading.Thread(target=read_from_server, args=(sock,), daemon=True)
    read_thread.start()

    # read lines from the client and send toserver
    try:
        while True:
            line = sys.stdin.readline()
            if not line:
                break
            sock.sendall(line.encode("utf-8"))

            if line.strip().lower() == 'q':
                break
    except KeyboardInterrupt:
        pass
    finally:
        sock.close()
        read_thread.join()

if __name__ == "__main__":
    main()
