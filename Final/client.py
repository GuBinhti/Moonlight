import socket

def main():
    server_host = input("Enter server IP address (default=127.0.0.1): ").strip()
    if not server_host:
        server_host = "127.0.0.1"

    server_port_str = input("Enter server UDP port (default=50000): ").strip()
    if server_port_str:
        server_port = int(server_port_str)
    else:
        server_port = 50000

    print(f"Sending commands to {server_host}:{server_port} via UDP.\n"
          "Commands:\n"
          "  pt   -> plot moonrise/moonset times\n"
          "  pp   -> plot moon schedule phases\n"
          "  pang -> plot moon phase angles\n"
          "  pa X -> plot altitude for day X\n"
          "  q    -> quit simulation\n")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        while True:
            cmd = input("Enter command (or 'q' to quit server): ").strip()
            if not cmd:
                continue

            # Send command to server
            sock.sendto(cmd.encode(), (server_host, server_port))

            # If user typed "q", let's also exit client after sending
            if cmd.lower() == 'q':
                print("Exiting client.")
                break

            sock.settimeout(2.0)
            try:
                data, addr = sock.recvfrom(1024)
                print(f"[Server Response] {data.decode()}")
            except socket.timeout:
                print("[No response from server, continuing...]")

    finally:
        sock.close()

if __name__ == "__main__":
    main()
