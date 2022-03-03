###### DOCSTRING ####################################################
# Submits all the jobs required to obtain the trigger scale factors
# Run example:
####################################################################

import sys
sys.path.append("..")

import os
import argparse
import ROOT

from utils import utils

@utils.setPureInputNamespace
def writeHTCondorUnionWeightsCalculatorFiles_outputs(args):
    """
    Outputs are guaranteed to have the same length.
    Returns all separate paths to avoid code duplication.
    """
    outSubmDir = 'submission'
    jobDir = os.path.join(args.localdir, 'jobs', args.tag, outSubmDir)
    os.system('mkdir -p {}'.format(jobDir))
    outCheckDir = 'outputs'
    checkDir = os.path.join(args.localdir, 'jobs', args.tag, outCheckDir)
    os.system('mkdir -p {}'.format(checkDir))

    name = 'jobDiscriminator_{}.{}'
    check_name = 'UnionWeightsCalculator_C$(Cluster)P$(Process).o'

    jobFiles = [ os.path.join(jobDir, name.format(chn, 'sh'))
                 for chn in args.channels ]

    submFiles = [ os.path.join(jobDir, name.format(chn, 'condor'))
                 for chn in args.channels ]

    checkFiles = [ os.path.join(checkDir, check_name)
                   for chn in args.channels ]

    return jobFiles, submFiles, checkFiles

@utils.setPureInputNamespace
def writeHTCondorUnionWeightsCalculatorFiles(args):
    script = os.path.join(args.localdir, 'scripts')
    script = os.path.join(script, 'runUnionWeightsCalculator.py')
    prog = 'python3 {}'.format(script)

    jobs, subs, checks = writeHTCondorUnionWeightsCalculatorFiles_outputs(args)

    #### Write shell executable (python scripts must be wrapped in shell files to run on HTCondor)
    command =  ( ( '{prog} --indir {indir} --outdir {outdir} --channel ${{1}} --triggers {triggers} --tag {tag} --subtag {subtag} --data_name {dataname} --mc_name {mcname} ' )
                 .format( prog=prog,
                          indir=args.indir, outdir=args.outdir,
                          tag=args.tag,
                          subtag=args.subtag,
                          triggers=' '.join(args.triggers,),
                          variables=' '.join(args.variables,),
                          dataname=args.data_name,
                          mcname=args.mc_name )
                )

    if args.debug:
        command += '--debug '
    command += '\n'

    # Technically one shell file would have been enough, but this solution is more flexible
    # for potential future changes, and is more readable when looking at the logs.
    for i in range(len(args.channels)):
        with open(jobs[i], 'w') as s:
            s.write('#!/bin/bash\n')
            s.write('export X509_USER_PROXY=~/.t3/proxy.cert\n')
            s.write('export EXTRA_CLING_ARGS=-O2\n')
            s.write('source /cvmfs/cms.cern.ch/cmsset_default.sh\n')
            s.write('cd {}/\n'.format(args.localdir))
            s.write('eval `scramv1 runtime -sh`\n')
            s.write(command)
            s.write('echo "Channel {} done."\n'.format(args.channels[i]))
        os.system('chmod u+rwx '+ jobs[i])

    #### Write submission file
    queue = 'short'
    for i,chn in enumerate(args.channels):
        with open(subs[i], 'w') as s:
            s.write('Universe = vanilla\n')
            s.write('Executable = {}\n'.format(jobs[i]))
            s.write('Arguments = $(channel) \n')
            s.write('input = /dev/null\n')
            s.write('output = {}\n'.format(checks[i]))
            s.write('error  = {}\n'.format(checks[i].replace('.o', '.e')))
            s.write('getenv = true\n')
            s.write('T3Queue = {}\n'.format(queue))
            s.write('WNTag=el7\n')
            s.write('+SingularityCmd = ""\n')
            s.write('include : /opt/exp_soft/cms/t3/t3queue |\n\n')
            s.write('queue channel from (\n')
            s.write('  {}\n'.format(chn))
            s.write(')\n')

    # os.system('condor_submit -name llrt3condor {}'.format(submFile))

# -- Parse options
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Command line parser')

    parser.add_argument('--localdir',         dest='localdir',         default=os.getcwd(),
                        help='out directory')
    parser.add_argument('--indir',      dest='indir',            required=True, help='in directory')
    parser.add_argument('--outdir',     dest='outdir',           required=True, help='out directory')
    parser.add_argument('--tag',        dest='tag',              required=True, help='tag')
    parser.add_argument('--subtag',           dest='subtag',           required=True, help='subtag')
    parser.add_argument('--data_name', dest='data_name', required=True, help='Data sample name')
    parser.add_argument('--mc_name', dest='mc_name', required=True, help='MC sample name')
    parser.add_argument('--channels',   dest='channels',         required=True, nargs='+', type=str,
                        help='Select the channels over which the workflow will be run.' )
    parser.add_argument('--triggers',         dest='triggers',         required=True, nargs='+', type=str,
                        help='Select the triggers over which the workflow will be run.' )
    parser.add_argument('--variables',        dest='variables',        required=True, nargs='+', type=str,
                        help='Select the variables over which the workflow will be run.' )
    parser.add_argument('--debug', action='store_true', help='debug verbosity')
    args = parser.parse_args()

    submitTriggerEff( args )