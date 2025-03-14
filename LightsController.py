import asyncio
import time
#import threading
#import copy

import uasyncio as asyncio
import aioble
import bluetooth
import binascii

from config import *
import espinput.ledcontrols as leds
from espinput.input import write_led

# Simulation of lights for unable to connect
#import lightsimul.simul as simul

def manual_deep_copy(matrix):
    new_matrix = []
    for row in matrix:
        new_matrix.append(row.copy())
    return new_matrix

def manual_zfill(str, width):
    return '0' * (width - len(str)) + str

class LightsController:
    def __init__(self):
        self.address = BD_ADDR
        self.connection = None
        self.connected = False
        self.lastFrame = None

    # Establish connection to the lights
    # Must run with asyncio.run()
    async def connect(self, run_simul_on_fail=False):
        try:
            self.device = None

            # Start load animation on the LEDs
            loading_task = asyncio.create_task(leds.show_loading())

            async with aioble.scan(duration_ms=5000, interval_us=30000, window_us=30000, active=True) as scanner:
                async for result in scanner:
                    #print(result, result.name(), result.rssi, result.services())
                    if self.address.lower() in str(result):
                        self.device = result.device
                        break

            if self.device:
                try:
                    self.connection = await self.device.connect(timeout_ms=2000)
                    print("Connection successful")
                    self.connected = True  # Only set if connection is valid
                except asyncio.TimeoutError:
                    print("Timeout connecting to device")
                    self.connected = False
                    return False
            else:
                print("Device not found")
                self.connected = False
                return False
                
            # Write hex value to the characteristic
            try:
                service = await self.connection.service(bluetooth.UUID(SERVICE_UUID))
                if not service:
                    print("Service not found")
                    return False

                self.characteristic = await service.characteristic(bluetooth.UUID(CHAR_UUID))
                if not self.characteristic:
                    print("Characteristic not found")
                    return False
            except Exception as e:
                pass
            
            # Stop the loading animation
            await leds.interrupt_loading(loading_task)
            await leds.flash_twice() # signal connected
            write_led(1, 1)          # keep light on while connected
            return True

        except Exception as e:
            print("Unable to connect to lights. Continuing program execution...")
            self.connected = False

            # Stop the loading animation
            await leds.interrupt_loading(loading_task)

            # NOT NEEDED FOR ESP32 VERSION:
            # -------------------------------------------------------------------
            # When connection fails, run pygame simulation 
            #simul_thread = threading.Thread(target=simul.run_simul, daemon=True)
            #simul_thread.start()


    # Disconnect from the lights
    async def disconnect(self):
        await self.drawBlankFrame() # Draw blank frame before disconnect
        await self.connection.disconnect()
        print("Lights disconnected")
        await leds.power_down_anim()
        return

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
            #simul.grid = frame
            pass

        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f"Write time: {elapsed_time:.4f} seconds")

        self.lastFrame = manual_deep_copy(frame)

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
            return manual_deep_copy(currentFrame)

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
        numValueHex = manual_zfill(hex(numLed)[2:], 3)

        # craft hex code
        hexCode = "aad1030" + numValueHex
        hexCode += color + "bb"

        # Send write command to lights
        await self.__sendWriteCommand(hexCode)

    async def __sendWriteCommand(self, hexCode):
        # Don't try writing if not connected to the lights
        if self.connected == False:
            return

        successful = False

        while successful == False:
            try:
                value_bytes = binascii.unhexlify(hexCode)
                await self.characteristic.write(value_bytes)
                print(f"Sent: {hexCode}")
                successful = True
            except Exception as e:
                #print("Error sending write command. Continuing program execution...")
                #print(e)
                pass


'''
async def test_lights():
    # Create a LightsController object
    lights = LightsController()

    # Connect to the lights
    await lights.connect()
    await lights.drawPixelSingle(1, "2A")
    await lights.drawPixelSingle(40, "2A")
    await lights.drawPixelSingle(10, "2A")

# JUST FOR TESTING
if __name__ == "__main__":
    asyncio.run(test_lights())
'''