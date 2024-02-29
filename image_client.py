import sys
import grpc
import argparse
import os
from PIL import Image # This is Pillow from Ubuntu Dockerfile
import board
import busio
import adafruit_mlx90640
import logging
import io
import time
import struct

logging.basicConfig(level=logging.INFO)

# Camera Setup
i2c = busio.I2C(board.SCL, board.SDA, frequency=400000)
mlx = adafruit_mlx90640.MLX90640(i2c)
print("MLX addr detected on I2C", [hex(i) for i in mlx.serial_number])


# if using higher refresh rates yields a 'too many retries' exception,
# try decreasing this value to work with certain pi/camera combinations
mlx.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_2_HZ

# Change directory to Routes so we can import the protobufs
current_directory = sys.path[0]
routes_directory = current_directory + '/common'
sys.path.insert(1, routes_directory)

from google.protobuf import any_pb2
import image_pb2
import image_pb2_grpc
import generic_pb2
import generic_pb2_grpc

def read_images_from_folder(image_file_path):
    for file_name in os.listdir(image_file_path):
        if file_name.endswith('.png'):
            image_path = os.path.join(image_file_path, file_name)
            with open(image_path, 'rb') as image_file:
                image_data = image_file.read()
                yield image_data

def run(image_file_path, server_address='localhost', server_port=50051):
    global counter
    counter = 1
    # Connect to the gRPC server
    with grpc.insecure_channel(f'{server_address}:{server_port}') as channel:
        # Create a stub (client)
        stub = generic_pb2_grpc.DBGenericStub(channel)

        while True:
            frame = [0] * 768
            try:
                mlx.getFrame(frame)
            except ValueError:
                # these happen, no biggie - retry
                continue

            # Create an instance of the ImageData message
            image_message = image_pb2.ImageData()
            image_message.identifier = counter
            counter += 1

            # add list of floats into long string and round the floats to save space
            image_message.data = stringify_float_list(round(frame, decimals=1), delimiter=',')

            # Serialize the ImageData message to bytes
            serialized_image = image_message.SerializeToString()

            # Create an Any message to hold the serialized ImageData message
            any_message = any_pb2.Any(value=serialized_image, type_url="ImageData")

            # Create a request to send to the server
            request = generic_pb2.protobuf_insert_request(
                keyspace="imageKeyspace",
                protobufs=[any_message]
            )

            # Send the request to the server
            response = stub.Insert(request)

            # Handle the response as needed
            print("Response:", response)

def stringify_float_list(float_list, delimiter=','):
    return delimiter.join(map(str, float_list))

# Deletes the entire table in the database
def dropTable(server_address='localhost', server_port=50051):
    # Connect to the gRPC server
    with grpc.insecure_channel(f'{server_address}:{server_port}') as channel:
        # Create a stub (client) for the generic service
        stub = generic_pb2_grpc.DBGenericStub(channel)

        # Create a delete request
        droptable_request = generic_pb2.protobuf_droptable_request(
            keyspace="imagekeyspace",
            table="imagedata"
        )

        # Send the delete request
        response = stub.DropTable(droptable_request)
        # Check if response.errs is not empty
        handle_errors(response.errs)

def handle_errors(errors):
    if errors != []:
        logging.info(f"Server Response: {errors}")

if __name__ == '__main__':
    # Use argparse to handle command-line arguments
    parser = argparse.ArgumentParser(description='Image gRPC Client')
    parser.add_argument('image_file_path', help='Path to the images')
    parser.add_argument('--address', default='localhost', help='Address of the gRPC server')
    parser.add_argument('--port', type=int, default=50051, help='Port number for the gRPC server')
    parser.add_argument('--action', choices=['run', 'deleteall'], help='Action to perform')

    args = parser.parse_args()

    if args.action == 'run':
        run(args.image_file_path, server_address=args.address, server_port=args.port)
    elif args.action == 'deleteall':
        dropTable(server_address=args.address, server_port=args.port)
    else:
        print("Invalid action. Please specify either 'run' or 'deleteall'.")
    