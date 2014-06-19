#!/usr/bin/env python3

import os, sys
import re
import numpy as np
import collections
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as colors
import matplotlib.gridspec as gridspec
from matplotlib.ticker import FuncFormatter 


def perf_of_impl(results_dir, plat, impl_name, pattern):
    if plat == 'intel':
        plat = 'x86'
        impl_name += '_intel'
    base_dir = os.path.join(results_dir, plat)
    perf = 0
    units = None
    try:
        with open(os.path.join(base_dir, impl_name, 'log')) as f:
            match_lines = [line for line in f if re.match(pattern + ":", line)]
            if (not len(match_lines)):
                raise FileNotFoundError
            vals_and_units = [line.split(':')[-1].split() for line in match_lines]
            if (vals_and_units[0][-1] == "s"):
                units = "s"
            vals = np.array([float(line[0]) for line in vals_and_units])
            mean = np.mean(vals)
            if (len(vals) > 5):
                dev = np.std(vals)
                perf = np.mean(vals[abs(vals - mean) < 2*dev])
            else:
                perf = mean
    except FileNotFoundError:
        pass
    return perf

def fpga_util_of_impl(base_dir, impl_name, pattern):
    util = 0
    try:
        with open(os.path.join(base_dir, impl_name, 'aoc', 'acl_quartus_report.txt')) as f:
            match_lines = [line for line in f if re.match(pattern + ":", line)]
            if (not len(match_lines)):
                raise FileNotFoundError
            line = match_lines[0]
            vals = line.split(':')[-1].split()
            numerator = int(vals[0].replace(',',''))
            denominator = 1
            try:
                if vals[1] == '/':
                    denominator = int(vals[2].replace(',',''))
            except:
                pass
            util = 100 * numerator / denominator
    except FileNotFoundError:
        pass
    # print('impl:', impl_name)
    # print('pattern:', pattern)
    # print('util:', util)
    return util

def get_impl_names(src_dir):
    tag_dir = os.path.join(src_dir, '.git', 'refs', 'tags')
    tags = os.listdir(tag_dir)
    tags.sort(key=lambda t: os.path.getmtime(os.path.join(tag_dir, t)))
    tags = tags + ["current"]
    # if (len(tags) > 15):
        # tags = tags[3:5] + tags[-19:]
    return tags

platform_props = {
    'x86': {
        'colour': 'b',
        'long_name': 'x86 (GPU OpenCL)'
    },
    'arm': {
        'colour': 'r'
    },
    'intel': {
        'colour': 'y',
        'long_name': 'x86 (Intel CPU OpenCL)'
    }
}

fpga_resource_types = collections.OrderedDict([
    ('Logic utilization', {
        'colour': 'b'
    }),
    ('M10K blocks', {
        'colour': 'g'
    }),
    ('DSP blocks', {
        'colour': 'r'
    }),
])

def main():
    use_outliers = True
    outlier_margin_frac = 0.1
    leg_side = None
    width_override = None
    outlierthresh_override = None

    src_dir = sys.argv[1]
    results_dir = sys.argv[2]

    if '/' in sys.argv[3]:
        spec_file = sys.argv[3]
        plat_specifier = spec_file.split('_')[-1]
        out_filename = os.path.basename(spec_file) + '.png'
        use_plat_outdir = False

        impl_names = []
        impl_labels = []

        with open(spec_file) as f:
            pattern = f.readline().rstrip()
            in_preamble = True

            for line in f:
                line = line.strip()

                if len(line):
                    words = line.split()
                    if line == '---':
                        in_preamble = False
                    else:
                        if in_preamble:
                            if words[0] == "outlier":
                                use_outliers = True if words[1] == "on" else False
                            if words[0] == "outliermargin":
                                outlier_margin_frac = float(words[1])
                            if words[0] == "legside":
                                leg_side = words[1].replace("_", " ")
                            if words[0] == "width":
                                width_override = float(words[1])
                            if words[0] == "outlierthresh":
                                outlierthresh_override = float(words[1])
                        else:
                            impl_names += [words[0]]
                            try:
                                impl_labels += [words[1].replace("_", " ")]
                            except IndexError:
                                impl_labels += [words[0]]

        out_basedir = sys.argv[4]

        
    else:
        plat_specifier = sys.argv[3]
        pattern = sys.argv[4]
        
        impl_names = get_impl_names(src_dir)
        impl_labels = impl_names
        out_filename = pattern.lower() + '.png'
        use_plat_outdir = True
        out_basedir = results_dir

    if plat_specifier == "both":
        platforms = ['x86', 'arm']
    elif plat_specifier == "intelandx86":
        platforms = ['x86', 'intel']
    else:
        platforms = [plat_specifier]

    impl_ind = np.arange(len(impl_names))
    fig = plt.figure()
    main_ax = fig.add_subplot(111)
    impl_width = 0.8
    bar_width = impl_width/len(platforms)

    if pattern == 'fpga_area':
        if platforms != ['arm']:
            return

        plat = platforms[0]
        plat_dir = os.path.join(results_dir, plat)
        bottom = np.zeros(len(impl_names))

        for resource in fpga_resource_types:
            utils = [fpga_util_of_impl(plat_dir, i, resource) for i in impl_names]
            plt.bar(impl_ind, utils, bar_width, color=fpga_resource_types[resource]["colour"], bottom=bottom)
            bottom += utils

        def my_formatter(x, pos=0): 
            return '{:.0f}%'.format(x) 

        plt.gca().yaxis.set_major_formatter(FuncFormatter(my_formatter)) 

        plt.legend(fpga_resource_types.keys(), loc=leg_side if leg_side else "lower left")
        plt.ylabel("Percentage of resource used")
        plt.title("FPGA Resource Utilisation of OpenCL Kernels")

    else:

        if "fps" in pattern.lower():
            use_outliers = False

        if (use_outliers):
            gs = gridspec.GridSpec(2, 1, height_ratios=[1,5])

            sub_ax1 = fig.add_subplot(gs[0], sharex=main_ax)
            sub_ax2 = fig.add_subplot(gs[1], sharex=main_ax)
            fig.subplots_adjust(hspace=0.1)

            d = .015 # how big to make the diagonal lines in axes coordinates
            r = 4
            # arguments to pass plot, just so we don't keep repeating them
            kwargs = dict(transform=sub_ax1.transAxes, color='k', clip_on=False)
            sub_ax1.plot((-d,+d),(-d*r,+d*r), **kwargs)      # top-left diagonal
            sub_ax1.plot((1-d,1+d),(-d*r,+d*r), **kwargs)    # top-right diagonal

            kwargs.update(transform=sub_ax2.transAxes)  # switch to the bottom axes
            sub_ax2.plot((-d,+d),(1-d,1+d), **kwargs)   # bottom-left diagonal
            sub_ax2.plot((1-d,1+d),(1-d,1+d), **kwargs) # bottom-right diagonal

        first_val = 0
        min_outlier = float('inf')
        max_outlier = 0

        for plat, bar_off in zip(platforms, np.arange(0, impl_width, bar_width)):
            speeds = np.array([perf_of_impl(results_dir, plat, i, pattern) for i in impl_names])

            label = platform_props[plat]["long_name"] if 'intel' in platforms else plat

            do_plot = lambda plt_obj: plt_obj.bar(impl_ind + bar_off, speeds, bar_width, color=platform_props[plat]["colour"], label=label)

            if (use_outliers):
                do_plot(sub_ax1)
                do_plot(sub_ax2)
                first_val = max(first_val, next(s for s in speeds if s!=0))
                max_outlier = max(max_outlier, np.max(speeds))
                top_margin = outlier_margin_frac * first_val
                bottom_margin = 0.1 * first_val
                outlier_thresh = outlierthresh_override if outlierthresh_override else first_val + bottom_margin
                outliers = speeds[speeds > outlier_thresh]
                if (len(outliers)):
                    min_outlier = min(min_outlier, np.min(outliers))
            else:
                do_plot(main_ax)

        if min_outlier == float('inf'):
            use_outliers = False

        if (use_outliers):
            sub_ax1.set_ylim(min_outlier - top_margin, max_outlier + top_margin)
            sub_ax2.set_ylim(0, outlier_thresh)

            main_ax.spines['top'].set_color('none')
            main_ax.spines['bottom'].set_color('none')
            main_ax.spines['left'].set_color('none')
            main_ax.spines['right'].set_color('none')
            main_ax.tick_params(labelcolor='w', top='off', bottom='off', left='off', right='off')

            sub_ax1.spines['bottom'].set_visible(False)
            sub_ax2.spines['top'].set_visible(False)
            sub_ax1.xaxis.tick_top()
            sub_ax1.tick_params(labeltop='off')
            sub_ax2.xaxis.tick_bottom()

            sub_ax1.locator_params(nbins=5)

        leg_ax = sub_ax1 if use_outliers else main_ax

        if "fps" in pattern.lower():
            leg_ax.legend(loc=leg_side if leg_side else "upper left")
            main_ax.set_ylabel("Execution speed / frames per second")
            main_ax.set_title("Performance comparison between implementations")
        else:
            leg_ax.legend(loc=leg_side if leg_side else "upper right")
            main_ax.set_ylabel("Execution time / seconds")
            main_ax.set_title("Comparison of " + pattern.title() + " between implementations")
            
    main_ax.set_xticks(impl_ind+impl_width/2)
    main_ax.set_xticklabels(impl_labels)
    plt.xlim([0, len(impl_names)])
    plt.xlabel("Implementation")

    if width_override:
        plt.gcf().set_size_inches(width_override,6)
    elif len(impl_names) > 10:
        plt.gcf().set_size_inches(len(impl_names)/2,6)

    out_dir = os.path.join(out_basedir, platforms[0]) if len(platforms) == 1 and use_plat_outdir else out_basedir

    plt.savefig(os.path.join(out_dir, out_filename))


if __name__ == "__main__":
    main()
