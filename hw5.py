#!/usr/bin/env python
import math
from urllib2 import Request, urlopen, URLError
import urllib
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import Element
from xml.etree.ElementTree import SubElement
import cv2
import numpy as np
import sys

# CONSTANTS
API_KEY = 'AlfZl5Bjb08aGyCb2S-7cFyMx0f3SMNifV3d09xAjzWD8SQx03H8NB1-0NIgeH8q'
TREE_TAG = '{http://schemas.microsoft.com/search/local/ws/rest/v1}'
MIN_LAT = -85.05112878
MAX_LAT = 85.05112878
MIN_LON = -180
MAX_LON = 180

def clip(n, minn, maxn):
   return min(max(n, minn), maxn)

def makeRequest((lat1, lon1), (lat2, lon2)):
   """ returns api response from 2 latitudes and longitudes """
   # request = Request('http://dev.virtualearth.net/REST/V1/Imagery/Metadata/Aerial/40.714550167322159,-74.007124900817871?zl=15&output=xml&key=AlfZl5Bjb08aGyCb2S-7cFyMx0f3SMNifV3d09xAjzWD8SQx03H8NB1-0NIgeH8q')
   
   headers = {
   'output' : 'xml', #XML output
   'key' : API_KEY, #API KEY
   'pp' : str(lat1)+','+str(lon1)+';;T',
   'ma' : str(lat1)+','+str(lon1)+','+str(lat2)+','+str(lon2) #Box area
   }
   reqUrl = 'http://dev.virtualearth.net/REST/V1/Imagery/Metadata/Aerial?'
   try:
      params = urllib.urlencode(headers)
      response = urlopen(reqUrl + params)
      res = response.read()

      # save response
      # text_file = open(str(lat1)+"-"+str(lat2)+".txt", 'w+')
      # text_file.write(res)
      # text_file.close()

      return res

   except URLError, e:
      print 'No map... Got error code:', e

def readRequest(filename):
   f = open(filename, 'r')
   return f.read()

def parseXML(xml):
   """ returns tuple of image url and highest zoom level """
   tree = ET.ElementTree(ET.fromstring(xml))
   imageUrl = tree.find(TREE_TAG+'ResourceSets/'+TREE_TAG+'ResourceSet/'+TREE_TAG+'Resources/'+TREE_TAG+'ImageryMetadata/'+TREE_TAG+'ImageUrl')
   zoomMax = tree.find(TREE_TAG+'ResourceSets/'+TREE_TAG+'ResourceSet/'+TREE_TAG+'Resources/'+TREE_TAG+'ImageryMetadata/'+TREE_TAG+'ZoomMax')
   return (imageUrl.text, zoomMax.text)

def fixURL(url, subdomain, quadkey):
   """ returns maptile url with specified subdomain and quadkey """
   url = url.replace("{subdomain}", subdomain)
   url = url.replace("{quadkey}", quadkey)
   # print "getting image from url: " + url
   return url

def getImage(url, name):
   """ downloads image from url and save as name"""
   resp = urllib.urlopen(url)
   image = np.asarray(bytearray(resp.read()), dtype="uint8")
   image = cv2.imdecode(image, cv2.IMREAD_COLOR)
   # urllib.urlretrieve(url, str(name))
   # print "saved as " + name
   return image

def getPixel((lat, lon), level):
   """ returns the pixel coordinate from latitude, longitude, and highest zom level """
   sinLat = math.sin(lat*math.pi/180)
   latitude = clip(lat, MIN_LAT, MAX_LAT)
   longitude = clip(lon, MIN_LON, MAX_LON)

   x = (longitude + 180) / 360
   sinLat = math.sin(latitude * math.pi / 180)
   y = 0.5 - math.log((1 + sinLat) / (1 -sinLat)) / (4 * math.pi)

   mapSize = 256 << int(level)
   pixelX = clip(x * mapSize + 0.5, 0, mapSize - 1)
   pixelY = clip(y * mapSize + 0.5, 0, mapSize - 1)

   # print "pixel: (" + str(int(pixelX)) + "," + str(int(pixelY)) + ")"
   return (int(pixelX), int(pixelY))

def getTile((pixelX, pixelY)):
   """ returns the tile coordinate from pixel coordinate """
   tileX = math.floor(pixelX/256)
   tileY = math.floor(pixelY/256)

   # print "tile: (" + str(int(tileX)) + "," + str(int(tileY)) + ")"
   return (int(tileX), int(tileY))

def getQuadkey((tileX, tileY), level):
   """ returns the quadkey from tile coordinate and highest zoom level """
   formatType = '0'+str(level)+'b'
   # lists
   listX = [int(x) for x in str(format(tileX, formatType))]
   listY = [int(x) for x in str(format(tileY, formatType))]
   # interleave lists
   listYX = [x for t in zip(listY, listX) for x in t]
   # read as base 4
   string = ''
   for i, j in zip(listYX[0::2], listYX[1::2]):
      string+=(str((i<<1)+j))
   return string

def coordToQuadkey((lat, lon), level):
   """ returns the quadkey from coordinate and highest level """
   pix = getPixel((lat, lon), int(level))
   tile = getTile(pix)
   quad = getQuadkey(tile, level)

   # print "quadkey: (" + str(int(pixelX)) + "," + str(int(pixelY)) + ")"
   return quad

def commonStart(sa, sb):
   """ returns the longest common substring from the beginning of sa and sb """
   def _iter():
     for a, b in zip(sa, sb):
         if a == b:
             yield a
         else:
             return

   return ''.join(_iter())

def fullRun(req, (lat1, lon1), (lat2, lon2), filename):
   """ gets tile image containing both coordinates """
   url, level = parseXML(req)
   
   # Find max zoom tile for each
   quad1 = coordToQuadkey((lat1, lon1), level)
   quad2 = coordToQuadkey((lat2, lon2), level)
   
   # Find largest common tile
   quad = commonStart(quad1, quad2)
   newLevel = len(quad)

   finalUrl = fixURL(url, 't0', quad)
   getImage(finalUrl, filename)

   # Get 4x higher resolution than highest containing tile
   nextUrl = fixURL(url, 't0', quad+str(0)+str(0))
   img0 = getImage(nextUrl, "0.jpg")
   nextUrl = fixURL(url, 't0', quad+str(0)+str(1))
   img1 = getImage(nextUrl, "0.jpg")
   nextUrl = fixURL(url, 't0', quad+str(0)+str(2))
   img2 = getImage(nextUrl, "0.jpg")
   nextUrl = fixURL(url, 't0', quad+str(0)+str(3))
   img3 = getImage(nextUrl, "0.jpg")
   full0 = np.concatenate((np.concatenate((img0,img1), axis=1), np.concatenate((img2, img3), axis=1)), axis=0)

   nextUrl = fixURL(url, 't0', quad+str(1)+str(0))
   img0 = getImage(nextUrl, "0.jpg")
   nextUrl = fixURL(url, 't0', quad+str(1)+str(1))
   img1 = getImage(nextUrl, "0.jpg")
   nextUrl = fixURL(url, 't0', quad+str(1)+str(2))
   img2 = getImage(nextUrl, "0.jpg")
   nextUrl = fixURL(url, 't0', quad+str(1)+str(3))
   img3 = getImage(nextUrl, "0.jpg")
   full1 = np.concatenate((np.concatenate((img0,img1), axis=1), np.concatenate((img2, img3), axis=1)), axis=0)

   nextUrl = fixURL(url, 't0', quad+str(2)+str(0))
   img0 = getImage(nextUrl, "0.jpg")
   nextUrl = fixURL(url, 't0', quad+str(2)+str(1))
   img1 = getImage(nextUrl, "0.jpg")
   nextUrl = fixURL(url, 't0', quad+str(2)+str(2))
   img2 = getImage(nextUrl, "0.jpg")
   nextUrl = fixURL(url, 't0', quad+str(2)+str(3))
   img3 = getImage(nextUrl, "0.jpg")
   full2 = np.concatenate((np.concatenate((img0,img1), axis=1), np.concatenate((img2, img3), axis=1)), axis=0)

   nextUrl = fixURL(url, 't0', quad+str(3)+str(0))
   img0 = getImage(nextUrl, "0.jpg")
   nextUrl = fixURL(url, 't0', quad+str(3)+str(1))
   img1 = getImage(nextUrl, "0.jpg")
   nextUrl = fixURL(url, 't0', quad+str(3)+str(2))
   img2 = getImage(nextUrl, "0.jpg")
   nextUrl = fixURL(url, 't0', quad+str(3)+str(3))
   img3 = getImage(nextUrl, "0.jpg")
   full3 = np.concatenate((np.concatenate((img0,img1), axis=1), np.concatenate((img2, img3), axis=1)), axis=0)

   full = np.concatenate((np.concatenate((full0,full1), axis=1), np.concatenate((full2, full3), axis=1)), axis=0)

   # cv2.imwrite('highres_'+filename, full)

   # Draw rectangle
   count = 4
 
   pix1 = getPixel((lat1, lon1), newLevel)
   tile1 = getTile(pix1)
   coord1 = ((pix1[0]-tile1[0]*256)*count, (pix1[1]-tile1[1]*256)*count)

   pix2 = getPixel((lat2, lon2), newLevel)
   tile2 = getTile(pix2)
   coord2 = ((pix2[0]-tile2[0]*256)*count, (pix2[1]-tile2[1]*256)*count)

   img = full #cv2.imread('highres_'+filename)

   # Cropped Image
   if (coord1[0] < coord2[0]):
      a = coord1[0]
      b = coord2[0]
   else:
      a = coord2[0]
      b = coord1[0]

   if (coord1[1] < coord2[1]):
      c = coord1[1]
      d = coord2[1]
   else:
      c = coord2[1]
      d = coord1[1]

   cropped = img[c:d, a:b]
   cv2.imwrite(filename, cropped)

   # Boxed Image
   # cv2.rectangle(img, coord1, coord2, (0, 0,  255), 1)
   # cv2.rectangle(img, (0, 127), (255, 127), (255, 255,  255), 1)
   # cv2.rectangle(img, (127, 0), (127, 255), (255, 255,  255), 1)
   # cv2.imwrite("boxed_"+filename, img)

   return url, level, quad1, quad2, quad, finalUrl, coord1, coord2

def main():
   """ runs with test values """

   testA = (63.514382, 131.466770) # Russia
   testB = (40.921995, -121.658231) # California
   # req = readRequest(str(testA[0])+"-"+str(testB[0])+".txt")
   req = makeRequest(testA, testB)
   url, level, quad1, quad2, quad, finalUrl, coord1, coord2 = fullRun(req, testA, testB, "iCanSeeRussiaFromMyHouse.jpg")

   # req_1 = readRequest("29.7604-29.4.txt")
   test1a = (29.7604, -95.3698) # Houston
   test1b = (29.4000, -94.9339) # Texas City
   req_1 = makeRequest(test1a, test1b)
   url_1, level_1, quad1_1, quad2_1, quad_1, finalUrl_1, coord1_1, coord2_2 = fullRun(req_1, test1a, test1b, "HoustonToTexasCity.jpg")

   # req_2 = readRequest("42.0464-40.7127.txt")
   test2a = (42.0464, -87.6947) # Evanston
   test2b = (40.7127, -74.0059) # New York
   req_2 = makeRequest(test2a, test2b)
   url_2, level_2, quad1_2, quad2_2, quad_2, finalUrl_2, coord1_2, coord2_2 = fullRun(req_2, test2a, test2b, "EvanstonToNewYork.jpg")

   # req_3 = readRequest("41.8369-42.0464.txt")
   test3a = (41.8369, -87.6847) # Chicago
   test3b = (42.0464, -87.6947) # Evanston
   req_3 = makeRequest(test3a, test3b)
   url_3, level_3, quad1_3, quad2_3, quad_3, finalUrl_3, coord1_3, coord2_3 = fullRun(req_3, test3a, test3b, "ChicagoToEvanston.jpg")

   # req_4 = readRequest("42.0586-42.056717.txt")
   test4a = (42.058600, -87.674878) # NE Tech (Evanston campus)
   test4b = (42.056717, -87.676917) # SW Tech (Evanston campus)
   req_4 = makeRequest(test4a, test4b)
   url_4, level_4, quad1_4, quad2_4, quad_4, finalUrl_4, coord1_4, coord2_4 = fullRun(req_4, test4a, test4b, "Tech.jpg")

   return

if __name__ == "__main__":
   # run from command line version
   # ./hw5.py lat1 lon1 lat2 lon2 
   ########################
   # try:
   #    coord1 = (float(sys.argv[1]), float(sys.argv[2]))
   #    coord2 = (float(sys.argv[3]), float(sys.argv[4]))
   #    imgName = sys.argv[5]
   #    print "testing: " + str(coord1) + " to " + str(coord2)
   #    print "output directory: " + imgName
   # except:
   #    print "no coordinates specified, using default: (42.059585, -87.670606) to (42.049735, -87.681517) saved to NUcampus"
   #    coord1 = (42.059585, -87.670606) # NE Evanston campus
   #    coord2 = (42.049735, -87.681517) # SW Evanston campus
   #    imgName = "NUcampus"
   #    
   #    req = makeRequest(coord1, coord2)
   #    url, level, quad1, quad2, quad, finalUrl, coord1, coord2 = fullRun(req, testA, testB, str(imgName)+".jpg")
   

   # interactive version
   #######################
   done = 0

   while not done:
      lat1 = raw_input("Enter first latitude: ")
      lon1 = raw_input("Enter first longitude: ")
      lat2 = raw_input("Enter second latitude: ")
      lon2 = raw_input("Enter second longitude: ")
      imgName = raw_input("Enter image name: ")
      testA = (float(lat1), float(lon1))
      testB = (float(lat2), float(lon2))

      # API Request
      req = makeRequest(testA, testB)

      # Get Image
      url, level, quad1, quad2, quad, finalUrl, coord1, coord2 = fullRun(req, testA, testB, str(imgName)+".jpg")
      done = int(raw_input("Enter 1 if finished:"))