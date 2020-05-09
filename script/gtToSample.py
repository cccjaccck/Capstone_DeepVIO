#!/usr/bin/python
# -*- coding: utf-8 -*-
from PIL import Image
import os
import sys
#import errno
#from subprocess import call
import csv

        
def getClosestIndex(searchTime, searchStartIndex, timeList):
    foundIdx = 0
    for i in range(searchStartIndex, len(timeList)):
        if timeList[i] >= searchTime:
            foundIdx = i
            break
    
    return foundIdx

def _get_filenames_and_classes(dataset_dir):


    ## Get image list
    fileList = []
    with open(dataset_dir + '/left_images.txt') as data:
        count=0
        for line in data.readlines():
            row = line.strip().split(' ')
            if count==0:
                count+=1
                continue
            fileList.append(row)

    image_timeList=[]
    for i in range(len(fileList)):
        image_timeList.append(fileList[i][1])

    image_timeList = sorted(image_timeList, key=lambda x: float(x))

    ## Get original imu 
    myTime = []
    timeList = []
    count=0
    with open(dataset_dir + '/imu.txt') as data:
        for line in data.readlines():
            row = line.strip().split(' ')
            myTime.append(row)

    myTime = myTime[1:]

    for i in range(len(myTime)):
        timeList.append( float(myTime[i][1] ) )


    sampledRow = []
    searchStartIndex = 0
    for i in range(len(image_timeList)):
        searchTime = float(image_timeList[i])
        foundIdx = getClosestIndex(searchTime, searchStartIndex, timeList)
        searchStartIndex = foundIdx
        sampledRow.append(myTime[foundIdx])

    with open(dataset_dir + '/sampled.txt', 'w') as f:
        for i in range(len(image_timeList)):
            tmpStr = " ".join(sampledRow[i])
            f.write(tmpStr + '\n')
        
        
    
    return
                

def main():
    _get_filenames_and_classes('/home/ssy/workspace/myspace/VIONet/data'+'/indoor_forward/indoor_forward_3')

if __name__ == "__main__":
    main()
    
    
