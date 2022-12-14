# Go-back-N-ARQ
Course Project for CSC573 - Fall 2022, at NCSU implementing Go-back-N automatic repeat request (ARQ) scheme

Author: Subramanian Venkataraman <svenka25@ncsu.edu>

---
Server.py - sets up reliable receiver to receive incoming file from client (we'll receive ProjTestFile.txt here, ~1.5MB) 
	Args - ServerFilename[server.py] server-port[default: 7735] testFileOutputName p[Probability Factor for loss]
	A copy of the file can be stored in the same directory where server.py executes to diff with incoming file and see if there's data loss.

Client.py - sets up reliable sender to send file to server (ProjTestFile.txt here ~1.5MB)
