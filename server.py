import socket
import random
import sys

ack_no = 0
data_pkt_indicator = b"0101010101010101"
ack_pkt_indicator = b"1010101010101010"
zero_padding = '{0:016b}'.format(0).encode()

def write_file(data, name_file):
    with open("{}".format(name_file), mode="ab") as f:
        f.write(data)

def carry_around_add(a, b):
    c = a + b
    return (c & 0xffff) + (c >> 16)

def verify_checksum(checksum, data):
    s = 0
    if len(data) % 2 != 0:
        data = data + b"0"
    for i in range(0, len(data), 2):
        checkSumData = data[i] + (data[i + 1] << 8)
        s = carry_around_add(s, checkSumData)

    calculatedChecksum = ~s & 0xffff
    calculatedChecksum = '{0:016b}'.format(calculatedChecksum).encode()
    if checksum == calculatedChecksum:
        return True
    else:
        return False

def create_segment(ack):
    zero_padding = '{0:016b}'.format(0).encode()
    ack_indicator = b"1010101010101010"
    segment = ack + zero_padding + ack_indicator
    return segment

def check_probability(p):
    r = random.random()
    if r <= p:
        print("R {} less than P {}".format(r, p))
        return False
    else:
        return True

def receive_file(UDPServerSocket, probabilityFactor, fileName):
    global ack_no
    UDPServerSocket.settimeout(10)


    while 1:
        try:
            bytes_received = UDPServerSocket.recvfrom(2048)
            message = bytes_received[0]
            client_address = bytes_received[1]
            
            header = message[:64]
            data = message[64:]

            if header[48:64] == '1' * 16:
                break
            
            # Break through Header
            sequence_number = header[:32]
            checksum = header[32:48]
            data_indicator = header[48:]
            # First check if this is a data packet

            isValidDataPkt = 1 if data_indicator == data_pkt_indicator else 0
            validCheckSum = verify_checksum(checksum, data)

            if not check_probability(probabilityFactor):
                print("\nPacket Loss, sequence number = {}".format(int(sequence_number, 2)))
                continue

            if isValidDataPkt and validCheckSum:
                if ack_no == int(sequence_number, 2):
                    write_file(data, fileName)
                    ack_no += len(data)
                    ack_segment = create_segment(sequence_number)
                    UDPServerSocket.sendto(ack_segment, client_address)
                else:
                    print(
                        "\nPacket loss, sequence number = {}".format(ack_no))
            else:
                if not isValidDataPkt:
                    print("\nNot a valid data packet. Packet dropped!")
                if not validCheckSum:
                    print("\nChecksum error. Packet dropped!")
        except socket.timeout as err:
            print("\n Connection Gracefully closed due to no active data transfer {}".format(err))
            exit()

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Insufficient arguments entered in server. Usage:\npython server.py server-port[default:7735] file-name p")
        exit()

    serverPort = int(sys.argv[1])
    fileName = str(sys.argv[2])
    probabilityFactor = float(sys.argv[3])

    print("Server Port = ", serverPort)
    print("File Name = ", fileName)
    print("Probability = ", probabilityFactor)

    UDPServerSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    UDPServerSocket.bind(("0.0.0.0", serverPort))
    receive_file(UDPServerSocket, probabilityFactor, fileName)