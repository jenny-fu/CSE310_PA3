from socket import *
import os
import sys
import struct
import time
import select
import binascii

ICMP_ECHO_REQUEST = 8

def checksum(string):
    csum = 0
    countTo = (len(string) // 2) * 2
    count = 0
    while count < countTo:
        thisVal = string[count+1] * 256 + string[count]
        csum = csum + thisVal
        csum = csum & 0xffffffff
        count = count + 2

    if countTo < len(string):
        csum = csum + string[len(string) - 1]
        csum = csum & 0xffffffff

    csum = (csum >> 16) + (csum & 0xffff)
    csum = csum + (csum >> 16)
    answer = ~csum
    answer = answer & 0xffff
    answer = answer >> 8 | (answer << 8 & 0xff00)
    return answer

rtt = []
totalPackets = 0
lostPackets = 0

# receive the structure ICMP_ECHO_REPLY and fetch the information you need, such as checksum, sequence number, time to live (TTL), etc
# returns delay
def receiveOnePing(mySocket, ID, timeout, destAddr):
    timeLeft = timeout
    while 1:
        startedSelect = time.time()
        whatReady = select.select([mySocket], [], [], timeLeft)
        howLongInSelect = (time.time() - startedSelect)
        print(whatReady[0])
        if whatReady[0] == []: # Timeout
            return "Request timed out."
        timeReceived = time.time()
        recPacket, addr = mySocket.recvfrom(1024) #IP packet

        #Fill in start

        #Fetch the ICMP header from the IP packet
        ##### Type and code must be set to 0.
        ##### The identifier and sequence number can be used by the client to determine which echo requests are associated with the echo replies
        ##### The data received in the echo request must be entirely included in the echo reply.

        header = recPacket[20:28]
        payloadSize = struct.calcsize("d") # 8
        payload = recPacket[28:36]
        # payload = recPacket[:payloadSize]
        fields = struct.unpack("bbHHh", header) #returns tuple
        payloadTime = struct.unpack("d", payload)[0] # "unpack requires buffer of 8 bytes" ?????
        type = fields[0]
        code = fields[1]
        checksum = fields[2]
        id = fields[3]
        seqnum = fields[4]
        if(ID != id or type != 0 or code != 0 or seqnum != 1):
            global lostPackets
            lostPackets = lostPackets + 1
            return None # assume ping is lost bc corrupted?
        else:
            global rtt
            delay = timeReceived - payloadTime
            rtt.append(delay)
            # print(time.asctime( time.localtime(payloadTime) ))
            # print(time.asctime( time.localtime(timeReceived) ))
            out = "DELAY: " + str(delay) + " seconds"
            return out

        #Fill in end

        timeLeft = timeLeft - howLongInSelect
        # return recPacket # Remove this or comment it out when you begin working.
        if timeLeft <= 0:
            lostPackets = lostPackets + 1
            return "Request timed out."

# study before completing receiveOnePing
def sendOnePing(mySocket, destAddr, ID):
    # Header is type (8), code (8), checksum (16), id (16), sequence (16)
    # Note that the numbers in parentheses are not values, but sizes in bits
    myChecksum = 0

    # Make a dummy header with a 0 checksum
    # struct -- Interpret strings as packed binary data
    header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, myChecksum, ID, 1)
    data = struct.pack("d", time.time())

    # Calculate the checksum on the data and the dummy header.
    myChecksum = checksum(header + data)

    # Get the right checksum, and put in the header
    if sys.platform == 'darwin':
        # Convert 16-bit integers from host to network byte order
        myChecksum = htons(myChecksum) & 0xffff
    else:
        myChecksum = htons(myChecksum)

    header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, myChecksum, ID, 1)
    packet = header + data

    mySocket.sendto(packet, (destAddr, 1)) # AF_INET address must be tuple, not str
    # Both LISTS and TUPLES consist of a number of objects
    # which can be referenced by their position number within the object.
    global totalPackets
    totalPackets = totalPackets + 1

def doOnePing(destAddr, timeout):
    icmp = getprotobyname("icmp")

    # SOCK_RAW is a powerful socket type. For more details: http://sockraw.org/papers/sock_raw
    mySocket = socket(AF_INET, SOCK_RAW, icmp)

    myID = os.getpid() & 0xFFFF # Return the current process i
    sendOnePing(mySocket, destAddr, myID)
    delay = receiveOnePing(mySocket, myID, timeout, destAddr)
    mySocket.close()
    return delay

def ping(host, timeout=1):
    # timeout=1 means: If one second goes by without a reply from the server,
    # the client assumes that either the client's ping or the server's pong is lost
    dest = gethostbyname(host)
    print("Pinging host: " + host + " at: " + dest + " using Python:")
    print("")

    global rtt
    global lostPackets
    global totalPackets

    # Send ping requests to a server separated by approximately one second
    while 1 :
        delay = doOnePing(dest, timeout)
        print(delay)
        print("MIN RTT: " + str(min(rtt)) + " seconds")
        print("MAX RTT: " + str(max(rtt)) + " seconds")

        lossRate = lostPackets / totalPackets
        average = 0
        for r in rtt:
            average = average + r
        average = average / len(rtt)

        print("AVERAGE RTT: " + str(average) + " seconds")
        print("LOSS RATE: " + str(lossRate) + "%")
        print("\n")
        time.sleep(1) # one second
    return delay

if __name__ == "__main__":
    host = sys.argv[1] if len(sys.argv) > 1 else 'localhost'
    ping(host)
