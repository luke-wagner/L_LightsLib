import asyncio
from bleak import BleakClient
import time
import threading
import copy

from config import *

# Simulation of lights for unable to connect
import lightsimul.simul as simul

class LightsController:
    def __init__(self):
        self.address = BD_ADDR
        self.client = BleakClient(self.address)
        self.connected = False
        #asyncio.run(self.connect())
        self.lastFrame = None

    # Establish connection to the lights
    # Must run with asyncio.run()
    async def connect(self, run_simul_on_fail=False):
        try:
            await self.client.connect()
            print("Connection successful...")
            self.connected = True
        except:
            print("Unable to connect to lights. Continuing program execution...")
            self.connected = False   
            # When connection fails, run pygame simulation     
            simul_thread = threading.Thread(target=simul.run_simul, daemon=True)
            simul_thread.start()

    # Disconnect from the lights
    async def disconnect(self):
        await self.client.disconnect()

    # Draws new frame with reference to the old frame, draws each pixel individually
    async def drawFrame(self, frame):
        difference = self.__computeDifference(frame, self.lastFrame)
        tasks = []

        width = len(difference)
        height = len(difference[0])

        start_time = time.time()

        if self.connected == True:
            for i in range(width):
                for j in range(height):
                    if difference[i][j] != '  ':
                        numLed = i * 20 + j
                        tasks.append(self.__drawPixelSingle(numLed, difference[i][j]))

            await asyncio.gather(*tasks)
        else:
            simul.grid = frame

        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f"Write time: {elapsed_time:.4f} seconds")

        self.lastFrame = copy.deepcopy(frame)

    '''
    # Draws completely new frame, each bulb is re-initialized. Uses L2CAP procedures
    async def drawFrameComplete(self, frame):
        tasks = []
        width = len(frame)
        height = len(frame[0])
        start_time = time.time()

        if self.connected == True:
            for i in range(width):
                for j in range(height):
                    if frame[i][j] != '  ':
                        numLed = i * 20 + j
                        tasks.append(self.__drawPixelSingle(numLed, frame[i][j]))

            await asyncio.gather(*tasks)
        else:
            simul.grid = frame

        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f"Write time: {elapsed_time:.4f} seconds")
    '''
    
    async def drawBlankFrame(self):
        await self.__sendWriteCommand("aad00400646403bb")
        
    # Get the difference between the two matrices, return the new matrix
    def __computeDifference(self, currentFrame, previousFrame):
        if previousFrame == None:
            return copy.deepcopy(currentFrame)

        difference = []     # this will be a matrix

        width = len(currentFrame)
        height = len(currentFrame[0])

        for i in range(width):
            newCol = []

            for j in range(height):
                currentVal = currentFrame[i][j]
                previousVal = previousFrame[i][j]

                if currentVal != previousVal:
                    if currentVal == '  ' and previousVal != '  ':
                        newCol.append('FE')
                    else:
                        newCol.append(currentVal)
                else:
                    newCol.append('  ')
            
            difference.append(newCol)
        
        return difference
    
    # Draw the specified color at led # = numLed
    async def __drawPixelSingle(self, numLed, color):
        numValueHex = hex(numLed)[2:].zfill(3)

        # craft hex code
        hexCode = "aad1030" + numValueHex
        hexCode += color + "bb"

        # Send write command to lights
        await self.__sendWriteCommand(hexCode)

    async def __sendWriteCommand(self, hexCode):
        # This is the uuid of the device to write to
        characteristic_uuid = CHAR_UUID

        # Don't try writing if not connected to the lights
        if self.connected == False:
            return

        try:
            await self.client.write_gatt_char(characteristic_uuid, bytes.fromhex(hexCode), response=False)
        except:
            print("Error sending write command. Continuing program execution...")
