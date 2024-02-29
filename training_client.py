import sys
import grpc
import argparse
import os
from PIL import Image # This is Pillow from Ubuntu Dockerfile

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

def run(server_address='localhost', server_port=50051):
    # Connect to the gRPC server
    try:
        with grpc.insecure_channel(f'{server_address}:{server_port}') as channel:
            # Create a stub (client)
            stub = generic_pb2_grpc.DBGenericStub(channel)

            # request image data column
            # currently does not work because select query is bad
            for i in range(20):
                request = generic_pb2.protobuf_select_request(
                    keyspace='imagekeyspace',
                    table = 'imagedata',
                    column = 'identifier',
                    constraint = str(i)
                )
                response = stub.Select(request)
                
                # go through protobufs in the response
                for serial_msg in response.protobufs:
                    image_data = image_pb2.ImageData()
                    image_data.ParseFromString(serial_msg)
                    # print(f'Data: {image_data.data}, {image_data.identifier}')
                    frame = [float(j) for j in image_data.data.split(',')]
                    print(frame)
                
                #print(f'Server Response: {response}')
    except grpc.RpcError as e:
        print(f'Error communicating with gRPC server: {e}')
        print(f'Code: {e.code()}')
        print(f'Details: {e.details()}')
        print(f'Trailers: {e.trailing_metadata()}')

if __name__ == '__main__':
    # Use argparse to handle command-line arguments
    parser = argparse.ArgumentParser(description='Training gRPC Client')
    parser.add_argument('--address', default='localhost', help='Address of the gRPC server')
    parser.add_argument('--port', type=int, default=50051, help='Port number for the gRPC server')

    args = parser.parse_args()

    # Runs the program with the provided arguments
    run(server_address=args.address, server_port=args.port)