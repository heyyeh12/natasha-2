#!/usr/bin/env python
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

with open("pointcloud1.fuse") as f:
	data = f.read()

data = data.split('\n')

x = [row.split(' ')[0] for row in data]
y = [row.split(' ')[1] for row in data]
z = [row.split(' ')[2] for row in data]

xint = map(float, x)
yint = map(float, y)
zint = map(float, z)

fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')
ax.scatter(xint[0:10], yint[0:10], zint[0:10], c='r', marker='o')

plt.show()