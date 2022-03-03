import os
import glob
import re
import numpy as np
import json
import argparse

import sys
sys.path.append( os.environ['PWD'] ) 
import ROOT
ROOT.gROOT.SetBatch(True)
from ROOT import TFile

from utils.utils import (
    generateTriggerCombinations,
    joinNameTriggerIntersection as joinNTC,
    loadBinning,
)

from luigi_conf import (
    _variables_unionweights,
)

def effExtractor(args, chn, dvars, nbins):
    """
    Extracts the efficiencies for data and MC to be used as scale factors: e_data / e_MC.
    Returns a dictionary with al efficiencies.
    """
    efficiencies_data, efficiencies_data_ehigh, efficiencies_data_elow = ({} for _ in range(3))
    efficiencies_MC, efficiencies_MC_ehigh, efficiencies_MC_elow = ({} for _ in range(3)) 
    
    triggercomb = generateTriggerCombinations(args.triggers)
    for tcomb in triggercomb:
        variables = dvars[ joinNTC(tcomb) ]
        assert(len(variables)==1)
        var = variables[0]
        
        inBaseName = ( 'trigSF_' + args.data_name + '_' + args.mc_name + '_' +
                       chn + '_' + var + '_' + joinNTC(tcomb) + args.subtag + '_CUTS*.root' )
        inName = os.path.join(args.indir, chn, var, inBaseName)
        inName = min( glob.glob(inName), key=len) #select the shortest string (NoCut)

        if len(inName) != 0:
            efficiencies_data[joinNTC(tcomb)] = []
            efficiencies_MC[joinNTC(tcomb)] = []
            
            inName = inName # same decision for all cuts
            inFile = TFile.Open(inName, 'READ')
            keyList = ROOT.TIter(inFile.GetListOfKeys())

            for key in keyList:
                print(key)
                
                cl = ROOT.gROOT.GetClass(key.GetClassName())
                if not cl.InheritsFrom("TGraph"):
                    continue
                h = key.ReadObj()

                assert(nbins[var][chn] == h.GetN())
                for datapoint in range(h.GetN()):
                    efficiencies_data[joinNTC(tcomb)].append( h.GetPointY(datapoint) )
                    efficiencies_data_elow[joinNTC(tcomb)].append( h.GetErrorYlow(datapoint) )
                    efficiencies_data_ehigh[joinNTC(tcomb)].append( h.GetErrorYhigh(datapoint) )

    return ( (efficiencies_data, efficiencies_data_ehigh, efficiencies_data_elow),
             (efficiencies_MC,   efficiencies_MC_ehigh,   efficiencies_MC_elow) )

def findBin(edges, value):
    """Find the bin id corresponding to one value, given the bin edges."""
    return np.digitize(value, edges)

def effCalculator(args, efficiencies, eventvars, channel, dvars, binedges):
    eff_data, eff_mc = (0 for _ in range(2))

    triggercomb = generateTriggerCombinations(args.triggers)
    for tcomb in triggercomb:
        variable = dvars[joinNTC(triggercomb)]
        assert len(dvars[joinNTC(triggercomb)]) == 1

        binid = findBin(binedges[variable][channel], 40.) #SHOULD DEPEND ON EVENTVARS
        # check for out-of-bounds
        assert binid!=0 and binid!=len(binedges[variable][channel])

        term_data = efficiencies[0][0][joinNTC(tcomb)][binid]
        term_mc   = efficiencies[1][0][joinNTC(tcomb)][binid]

        ###CHANGE!!!!!!!!!!!!!!!!!! this is a simplification
        if len(tcomb) > 3:
            continue


        if len(tcomb)%2==0:
            eff_data -= term_data
            ef_mc    -= term_mc
        else:
            eff_data += term_data
            eff_mc   += term_mc

    return effData, effMC

def runUnionWeightsCalculator_outputs(args, chn):
    return os.path.join(args.outdir, '{}_{}.root'.format(os.path.basename(__file__), chn))

def runUnionWeightsCalculator(args, chn):
    output = runUnionWeightsCalculator_outputs(args, chn)

    binedges, nbins = loadBinning(afile=args.binedges_filename, key=args.subtag,
                                  variables=args.variables, channels=[chn])

    json_fname = os.path.join( args.indir, 'variableImportanceDiscriminator_{}.json'.format(chn) )
    dvar = json.load(json_fname)

    efficiencies = effExtractor(args, chn, dvar, nbins)

    var1, var2 = _variables_unionweights
    var1_low, var1_high = binedges[var1][chn][0], binedges[var1][chn][-1]
    var2_low, var2_high = binedges[var2][chn][0], binedges[var2][chn][-1]

    def meanbins(m1,m2,nelem):
         arr = np.linspace(m1, m2, nelem)
         return (arr[:-1]+arr[1:])/2
     
    nbins_union = 20
    vars1 = meanbins(var1_low, var1_high, nbins_union+1)
    vars2 = meanbins(var2_low, var2_high, nbins_union+1)

    for iv1 in vars1:
        for iv2 in vars2:
            eventvars = (iv1, iv2)
            effData, effMC = effCalculator(args, efficiencies, eventvars,
                                           chn, dvar, binedges)
    print('CHECK!!!!! ', chn)
        
        # with open(outputs[i], 'w') as f:
        #     json.dump(orderedVars, f)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Choose the most significant variables to draw the efficiencies.')

    parser.add_argument('--indir',  help='Inputs directory',  required=True)
    parser.add_argument('--outdir', help='Outputs directory', required=True)
    parser.add_argument('--data_name', dest='data_name', required=True, help='Data sample name')
    parser.add_argument('--mc_name', dest='mc_name', required=True, help='MC sample name')
    parser.add_argument('--triggers', dest='triggers', nargs='+', type=str,
                        required=True, help='Triggers included in the workfow.')
    parser.add_argument('--channel', dest='channel', required=True,
                        help='Select the channels over which the workflow will be run.' )
    parser.add_argument('-t', '--tag', help='string to differentiate between different workflow runs', required=True)
    parser.add_argument('--subtag', dest='subtag', required=True, help='subtag')
    parser.add_argument('--debug', action='store_true', help='debug verbosity')
    args = parser.parse_args()

    runUnionWeightsCalculator(args, args.channel)