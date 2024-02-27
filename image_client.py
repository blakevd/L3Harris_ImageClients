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

        frame = [0] * 768
        # Temperature range in Celsius (adjust according to your application)
        min_temperature = 34  # Minimum temperature in Celsius (setting for human detection)
        max_temperature = 39  # Maximum temperature in Celsius (setting for human detection)

        # Grayscale intensity range
        min_intensity = 0  # Corresponding to min_temperature
        max_intensity = 255  # Corresponding to max_temperature

        while True:
            try:
                mlx.getFrame(frame)
            except ValueError:
                # these happen, no biggie - retry
                continue

            # Convert frame data into a PIL Image
            img = Image.new('L', (32, 24))  # Create a new grayscale image
            pixels = img.load()  # Create pixel map
            for h in range(24):
                for w in range(32):
                    # Scale the temperature value to the range [0, 1]
                    temperature = (frame[h*32 + w] - min_temperature) / (max_temperature - min_temperature)
                    # Map the temperature value to the grayscale intensity range [0, 255]
                    intensity = int(temperature * (max_intensity - min_intensity) + min_intensity)
                    # Ensure the intensity value is within the valid range [0, 255]
                    intensity = max(0, min(intensity, 255))
                    pixels[w, h] = intensity

            # Generate file name
            file_name = os.path.join("data", f"frame_{time.time()}.png")

            # Save the image as a PNG file
            img.save(file_name, format='PNG')

            for image_data in read_images_from_folder(image_file_path): 
                serial_data = image_data.SerializeToString()
                logging.info(f"Image Type: {type(serial_data)} \nData: {serial_data}")
                type_url = f"ImageData"
                anypb_msg = any_pb2.Any(value=serial_data, type_url=type_url)
                
                request = generic_pb2.protobuf_insert_request(
                    keyspace="imageKeyspace",
                    protobufs=[anypb_msg] 
                )
                logging.info(f"\nWorking Type: {type(request)} \nRequest: {request}")
                response = stub.Insert(request)

            # Clear out the folder after processing
            for filename in os.listdir(image_file_path):
                file_path = os.path.join(image_file_path, filename)
                if os.path.isfile(file_path):
                    os.remove(file_path)



if __name__ == '__main__':
    # Use argparse to handle command-line arguments
    parser = argparse.ArgumentParser(description='Image gRPC Client')
    parser.add_argument('image_file_path', help='Path to the images')
    parser.add_argument('--address', default='localhost', help='Address of the gRPC server')
    parser.add_argument('--port', type=int, default=50051, help='Port number for the gRPC server')

    args = parser.parse_args()

    # Runs the program with the provided arguments
    run(args.image_file_path, server_address=args.address, server_port=args.port)
