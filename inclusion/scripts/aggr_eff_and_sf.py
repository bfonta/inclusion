# coding: utf-8

_all_ = [ 'aggregate_eff_and_sf' ]

import os
import sys
parent_dir = os.path.abspath(__file__ + 3 * '/..')
sys.path.insert(0, parent_dir)

import inclusion
from inclusion.utils import utils

import re
import argparse
import ctypes

import ROOT
ROOT.gROOT.SetBatch(True)
from ROOT import (
    TFile,
    TGraphAsymmErrors,
    TH1D,
    TH2D,
    )
from array import array

def convert_graph_to_hist(graph):
    """
    Converts 1D TGraphAsymmErrors to TH1D.
    TODO: support 2D graphs [3D histograms hopefully not...]
    The convertion is required due to ROOT's bad support of 2D objects:
    - TGraph2DAsymmErrors must have the same number of points in X and Y!
    - TGraph3DAsymmErrors does not exist
    - Histograms are the most flexible, although do not support asym errors.
    """
    n = graph.GetN()
    name = graph.GetName()

    # define x (bin centers)
    x = array('d')
    x.append((3.0 * graph.GetX()[0] - graph.GetX()[1]) / 2.0)
    for i in range(1,n):
        x.append((graph.GetX()[i-1] + graph.GetX()[i]) / 2.0)
    x.append((3.0 * graph.GetX()[n-1] - graph.GetX()[n-2]) / 2.0)
    histo = TH1D(name, name, n, x)

    # fill y values (counts)
    for i in range(n):
        histo.SetBinContent(i+1, graph.GetY()[i])
        # losing up/down asymmetric info...
        toterr = graph.GetErrorYhigh(i)+graph.GetErrorYlow(i)
        histo.SetBinError(i+1, toterr)

    return histo

def aggregate_eff_and_sf(indir, outdir, channel, subtag, prefix, variables, debug):
    extension = 'root'
    _outname = os.path.join(outdir, prefix + channel + '.' + extension)
    fout = ROOT.TFile.Open(_outname , 'RECREATE')
    
    var_re = '_(.+)_TRG_' # ?: match but do not capture
    trig_re = '(.+)_CUTS_'
    cuts_re = '(.+)'
    regex_str = ( '.*' + channel + var_re + trig_re +
                   cuts_re + args.subtag + '\.' + extension )
    regex = re.compile( regex_str )

    walk_path = os.path.join(indir, channel)
    for root, _, files in os.walk( walk_path ):
        for afile in files:
            if afile.endswith('.' + extension):
                print(os.path.join(root,afile))
                froot = ROOT.TFile.Open( os.path.join(root,afile), 'READ' )
                keyList = ROOT.TIter(froot.GetListOfKeys())
                fout.cd()
                for key in keyList:
                    h = key.ReadObj()
                    if ( not h.InheritsFrom(TGraphAsymmErrors.Class()) and
                         not h.InheritsFrom(TH2D.Class()) ):
                        mess = '\n - Dir: {}\n'.format(root)
                        mess += ' - File: {}\n'.format(afile)
                        mess += ' - Key: {}\n'.format(key)
                        raise ValueError(mess)

                    if h.InheritsFrom(TGraphAsymmErrors.Class()):
                        h = convert_graph_to_hist(h)

                    try:
                        var, trigger, cut = regex.match(afile).groups()
                    except AttributeError as e:
                        mess = '\nNo match! Regex: {}\n'.format(regex)
                        mess += 'Channel: {}\n'.format(channel)
                        mess += 'File: {}\n'.format(afile)
                        mess += 'Dir: {}\n'.format(root)
                        raise AttributeError(mess) from e
                    new_name = h.GetName() + '_VAR_' + var + '_TRG_' + trigger + '_CUT_' + cut

                    h.Write(new_name)
    print('File {} saved.'.format(_outname))
            
parser = argparse.ArgumentParser(description='Draw trigger scale factors')

parser.add_argument('--indir', help='Inputs directory', required=True)
parser.add_argument('--outdir', help='Output directory', required=True, )
parser.add_argument('--channel', dest='channel', required=True, type=str,
                    help='Select the channels over which the workflow will be run.' )
parser.add_argument('--file_prefix', help='ROOT file prefix', required=True)
parser.add_argument('--variables', dest='variables', required=True, type=str, nargs='+',
                    help='Select the variables over which the workflow will be run.' )
parser.add_argument('--subtag', dest='subtag', required=True, help='subtag')
parser.add_argument('--debug', action='store_true', help='debug verbosity')
args = utils.parse_args(parser)

aggregate_eff_and_sf(args.indir, args.outdir, args.channel, args.subtag,
                     args.file_prefix, args.variables, args.debug)
