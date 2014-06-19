#!/usr/bin/env python3

import os, sys
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as colors

def error_colour_scale(max_val=4):
    norm = colors.Normalize(0, max_val, clip=True)
    cmap = colors.LinearSegmentedColormap.from_list('distance', ['green', 'yellow', 'red'])
    scal = cm.ScalarMappable(norm=norm, cmap=cmap)
    scal.set_array([])
    return scal

def height_colour_scale():
    norm = colors.Normalize(-3, 3, clip=True)
    # cmap = colors.LinearSegmentedColormap.from_list('distance', ['cyan', 'black'])
    scal = cm.ScalarMappable(norm=norm, cmap=cm.jet_r)
    scal.set_array([])
    return scal

def plot_hist(dists, out_file, max_dist=4, nbins=100):
    N, bins, patches = plt.hist(dists, bins=nbins)

    scal = error_colour_scale(max_val=max_dist)
    for distance, patch in zip(bins, patches):
        patch.set_color(scal.to_rgba(distance))
        
    plt.title('Histogram of error distances for generated 3D points')
    plt.ylabel('Number of points')
    plt.xlabel('Error distance / m')
    plt.xlim([0, max_dist])

    plt.text(0.95, 0.95, 
        "N points: {}\n".format(len(dists)) +
        "Min error: {:.3f} m\n".format(np.min(dists)) +
        "Mean error: {:.3f} m\n".format(np.mean(dists)) +
        "Max error: {:.3f} m".format(np.max(dists))
        ,
        verticalalignment='top', horizontalalignment='right',
        transform=plt.gca().transAxes,
        fontsize=15)

    plt.savefig(out_file)
    plt.clf()

def set_cloud_scales():
    plt.xlim([-30, 30])
    plt.ylim([-30, 30])
    plt.xlabel('X Position / m')
    plt.ylabel('Z Position / m')

def plot_cloud(x, y, z, out_file): 
    scal = height_colour_scale()
    plt.scatter(x, z, c=scal.to_rgba(y), marker='.', edgecolors='none')
    cbar = plt.colorbar(scal, label="Y Position / m")
    cbar.ax.invert_yaxis()
    plt.title('Generated point cloud relative to camera position')
    set_cloud_scales()
    plt.savefig(out_file)
    plt.clf()

def plot_error_cloud(x, z, dists, out_file, max_dist=4):
    scal = error_colour_scale(max_val=max_dist)
    plt.scatter(x, z, c=scal.to_rgba(dists), marker='.', edgecolors='none')
    cbar = plt.colorbar(scal, label="Error distance / m")
    plt.title('Error distances of generated point cloud')
    set_cloud_scales()
    plt.savefig(out_file)
    plt.clf()


def main():
    c2m_file = sys.argv[1]
    c2c_file = sys.argv[2]
    dist_dir = os.path.dirname(c2m_file)

    c2m_dat = np.loadtxt(c2m_file)
    c2c_dat = np.loadtxt(c2c_file)

    x, y, z, mesh_error = (c2m_dat[:,i] for i in range(4))
    cloud_error = c2c_dat[:,3]
    mesh_error = np.abs(mesh_error)
    cloud_error = np.abs(cloud_error)

    plot_cloud(x, y, z, os.path.join(dist_dir, 'cloud.png'))
    plot_hist(mesh_error, os.path.join(dist_dir, 'error_hist.png'))
    plot_error_cloud(x, z, mesh_error, os.path.join(dist_dir, 'error_cloud.png'))
    plot_hist(cloud_error, os.path.join(dist_dir, 'cloudref_error_hist.png'), max_dist=2, nbins=100)
    plot_error_cloud(x, z, cloud_error, os.path.join(dist_dir, 'cloudref_error_cloud.png'), max_dist=2)


if __name__ == "__main__":
    main()