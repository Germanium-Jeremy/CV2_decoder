import cv2
from pyzbar.pyzbar import decode

img = cv2.imread("./qr2/code.jpg")
data = decode(img)
print(data[0].data.decode() if data else "No QR found")