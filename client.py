import sys
import socket
import threading
import time

segments = []
time_stamp = []
close_flag = False

def retFileDetails(filename, position):
    with open(filename, "rb") as f:
        f.seek(position, 0)
        data = f.read(1)
        new_position = f.tell()
        if new_position == position:
            end_file_flag = True
        else:
            end_file_flag = False
    return data, new_position, end_file_flag

def carry_around_add(a, b):
    c = a + b
    return (c & 0xffff) + (c >> 16)

def calculate_checksum(data):
    s = 0
    if len(data) % 2 != 0:
        data = data + b"0"
    for i in range(0, len(data), 2):
        checkSumData = data[i] + (data[i + 1] << 8)
        s = carry_around_add(s, checkSumData)
    return ~s & 0xffff

def create_segment(sequence_number, data):
    checksum = '{0:016b}'.format(calculate_checksum(data)).encode()
    data_indicator = b"0101010101010101"
    sequence_number = '{0:032b}'.format(sequence_number).encode()
    header = sequence_number + checksum + data_indicator
    segment = header + data
    return segment

def check_ack(ack):
    segment = segments[0]
    header = segment[:64]
    true_ack = header[:32]
    if ack == true_ack:
        return True
    else:
        return False


def get_sequence_number(segment):
    header = segment[:64]
    sequence_number = header[:32]
    sequence_number = int(sequence_number, 2)
    return sequence_number


def resend_segments(UDPClientSocket):
    global segments
    global time_stamp
    time_stamp = []
    for segment in segments:
        UDPClientSocket.sendto(segment, (server_host_name, server_port))
        # print("Retransmission sequence number = {}".format(get_sequence_number(segment)))
    time_stamp.append(time.time())


def sending_thread(UDPClientSocket, server_host_name, server_port, file_name, window_size, mss, condition):
    global segments
    global time_stamp
    global close_flag

    position = 0
    total_data = b""
    end_file_flag = False
    sequence_number = 0
    timeout_value = 0.2
    while end_file_flag is False:
        if len(segments) < window_size:
            while len(total_data) < mss and end_file_flag is False:
                data, position, end_file_flag = retFileDetails(file_name, position)
                total_data = total_data + data
            condition.acquire()
            segments.append(create_segment(sequence_number, total_data))
            condition.release()
            UDPClientSocket.sendto(segments[-1], (server_host_name, server_port))
            condition.acquire()
            if not time_stamp:
                time_stamp.append(time.time())
            condition.release()
            condition.acquire()
            if (time.time() - time_stamp[0]) > timeout_value:
                print("Timeout, sequence number = {}".format(get_sequence_number(segments[0])))
                resend_segments(UDPClientSocket)
            condition.release()
        else:
            # print("Window size exceeded")
            condition.acquire()
            condition.wait(min(0, (timeout_value - (time.time() - time_stamp[0]))))
            if (time.time() - time_stamp[0]) > timeout_value:
                print("Timeout, sequence number = {}".format(get_sequence_number(segments[0])))
                resend_segments(UDPClientSocket)
                condition.wait(timeout_value)
            condition.release()
        sequence_number = position
        total_data = b""

    while len(segments) != 0:
        condition.acquire()
        if len(segments) != 0:
            if (time.time() - time_stamp[0]) > timeout_value:
                print("Timeout, sequence number = {}".format(get_sequence_number(segments[0])))
                resend_segments(UDPClientSocket)
                condition.wait(timeout_value)
            condition.release()
    close_flag = True


def rdt_send(UDPClientSocket, condition):
    global segments
    global time_stamp
    # To ensure the sending thread sends first
    time.sleep(0.1)
    while not close_flag:
        # print("Receiving an ACK")
        data = UDPClientSocket.recvfrom(2048)[0]
        # print("Ack Received")
        ack = data[:32]
        ack_indicator = data[48:]
        true_ack_indicator = b"1010101010101010"
        if true_ack_indicator == ack_indicator:
            # Verified this is an ack packet
            if check_ack(ack):
                condition.acquire()
                segments.pop(0)
                time_stamp[0] = time.time()
                last_ack = ack
                condition.notify()
                condition.release()
                # To ensure control goes back to thread 1
                time.sleep(0.01)


if __name__ == "__main__":
    if len(sys.argv) != 6:
        print("Insufficient arguments entered in client. Usage:\npython client.py server-host-name server-port#[default: 7735] file-name N(window-size) MSS")
        exit()


    server_host_name = sys.argv[1]
    server_port = int(sys.argv[2])
    file_name = sys.argv[3]
    window_size = int(sys.argv[4])
    mss = int(sys.argv[5])
    UDPClientSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)

    condition = threading.Condition()
    sender_thread = threading.Thread(target=sending_thread,
                                     args=(UDPClientSocket, server_host_name, server_port, file_name, window_size, mss,
                                           condition))
    receiver_thread = threading.Thread(target=rdt_send, args=(UDPClientSocket, condition))
    t_one = time.time()
    sender_thread.start()
    receiver_thread.start()
    sender_thread.join()
    receiver_thread.join()
    print(time.time() - t_one)
    UDPClientSocket.close()