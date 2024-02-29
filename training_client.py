import sys
import grpc
import argparse
import os
from PIL import Image, ImageTk # This is Pillow from Ubuntu Dockerfile
import numpy as np
import tkinter as tk
import time

# Change directory to Routes so we can import the protobufs
current_directory = sys.path[0]
routes_directory = current_directory + '/common'
sys.path.insert(1, routes_directory)

# get grpc / proto definitions
from google.protobuf import any_pb2
import image_pb2
import image_pb2_grpc
import generic_pb2
import generic_pb2_grpc

def on_close():
    root.destroy()

# Create a Tkinter window
root = tk.Tk()
root.title("Thermal Image Viewer")
# Create a Tkinter Label to display the image
label = tk.Label(root)
label.pack()
root.protocol("WM_DELETE_WINDOW", on_close) # to help not break stuff

# very bad global counter for now to go through data
counter = 1

def run(server_address='localhost', server_port=50051):
    # Connect to the gRPC server
    try:
        with grpc.insecure_channel(f'{server_address}:{server_port}') as channel:
            # Create a stub (client)
            stub = generic_pb2_grpc.DBGenericStub(channel)

            global counter
            
            # just run select queries
            while True:
                request = generic_pb2.protobuf_select_request(
                    keyspace='imagekeyspace',
                    table = 'imagedata',
                    column = 'identifier',
                    constraint = str(counter)
                )
                response = stub.Select(request)
                if(response != ''):
                    # go through protobufs in the response
                    for serial_msg in response.protobufs:
                        image_data = image_pb2.ImageData() # conver to our proto class
                        image_data.ParseFromString(serial_msg) # can use these fields from proto image_data.data or image_data.identifier
                        
                        frame = [float(j) for j in image_data.data.split(',')]
                        
                        update_img(frame)
                        root.update_idletasks()
                        root.update()   
                        
                        counter += 1    
                        
                        # close if the window disappears
                        if not root.winfo_exists():
                            break      
                
                time.sleep(.2)
                #print(f'Server Response: {response}')
    except grpc.RpcError as e:
        print(f'Error communicating with gRPC server: {e}')
        print(f'Code: {e.code()}')
        print(f'Details: {e.details()}')
        print(f'Trailers: {e.trailing_metadata()}')

def update_img(frame):
    thermal_data = np.array(frame).reshape((24, 32))

    # Normalize the data to be in the range [0, 255] for displaying
    normalized_data = ((thermal_data - np.min(thermal_data)) / (np.max(thermal_data) - np.min(thermal_data)) * 255).astype('uint8')

    # Create a Pillow Image from the NumPy array
    thermal_image = Image.fromarray(normalized_data, mode='L')  # 'L' mode is for grayscale
    thermal_image = thermal_image.resize((600, 400))


    photo = ImageTk.PhotoImage(thermal_image)

    # Update the image displayed in the Tkinter Label
    label.configure(image=photo)
    label.image = photo  # Keep a reference to prevent garbage collection

if __name__ == '__main__':
    # Use argparse to handle command-line arguments
    parser = argparse.ArgumentParser(description='Training gRPC Client')
    parser.add_argument('--address', default='localhost', help='Address of the gRPC server')
    parser.add_argument('--port', type=int, default=50051, help='Port number for the gRPC server')

    args = parser.parse_args()

    # Runs the program with the provided arguments
    run(server_address=args.address, server_port=args.port)