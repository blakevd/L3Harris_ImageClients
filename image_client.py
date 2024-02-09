import sys
import grpc
import argparse
import os
from PIL import Image

# Change directory to Routes so we can import the protobufs
current_directory = sys.path[0]
routes_directory = current_directory + '/common'
sys.path.insert(1, routes_directory)

from google.protobuf import any_pb2
import image_pb2
import image_pb2_grpc
import generic_pb2
import generic_pb2_grpc

def get_value(value):
    try:
        return int(value)
    except ValueError:
        try:
            return float(value)
        except ValueError:
            return value

def read_images_from_folder(image_file_path):
    for file_name in os.listdir(image_file_path):
        if file_name.endswith('.png'):
            image_path = os.path.join(image_file_path, file_name)
            with open(image_path, 'rb') as image_file:
                image_data = image_file.read()
                yield image_pb2.ImageData(data=image_data)

def run(image_file_path, server_address='localhost', server_port=50051):
    # Connect to the gRPC server
    with grpc.insecure_channel(f'{server_address}:{server_port}') as channel:
        # Create a stub (client)
        stub = generic_pb2_grpc.DBGenericStub(channel)

        # Read and send data from the CSV file
        for image_data in read_images_from_folder(image_file_path): 
            serial_data = image_data.SerializeToString()
            type_url = f"ImageData" # this is needed if we define a package in the proto then it  would be the packagename.EmailData or packagename.email_pb2.EmailData
            anypb_msg = any_pb2.Any(value=serial_data, type_url=type_url)
            
            request = generic_pb2.protobuf_insert_request(
                keyspace="imageKeyspace",
                protobufs=[anypb_msg] 
            )
            response = stub.Insert(request)
            print(f"Server Response: {response.errs}")

if __name__ == '__main__':
    # Use argparse to handle command-line arguments
    parser = argparse.ArgumentParser(description='Image gRPC Client')
    parser.add_argument('image_file_path', help='Path to the images')
    parser.add_argument('--address', default='localhost', help='Address of the gRPC server')
    parser.add_argument('--port', type=int, default=50051, help='Port number for the gRPC server')

    args = parser.parse_args()

    # Runs the program with the provided arguments
    run(args.image_file_path, server_address=args.address, server_port=args.port)
