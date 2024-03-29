# coding: utf-8

_all_ = [ 'processing', 'processing_outputs' ]

import os
import sys
parent_dir = os.path.abspath(__file__ + 3 * '/..')
sys.path.insert(0, parent_dir)

import inclusion
from inclusion.config import main
from inclusion.utils import utils
from inclusion.condor.job_writer import JobWriter

import re
import argparse

def produce_trigger_outputs_sample(args, sample, ext):
    """
    Produces all outputs of the submitTriggerEff task.
    Limitation: As soon as one file is not produced, luigi
    reruns everything.
    """
    assert(ext in ('root', 'txt'))
    extension = '.' + ext
    t = []
    exp = re.compile('.+output(_[0-9]{1,5}).root')

    inputs, _ = utils.get_root_inputs(sample, args.indir)

    folder = os.path.join( args.outdir, proc )
    for inp in inputs:
        number = exp.search(inp)
        proc_folder = os.path.dirname(inp).split('/')[-1]
        basename = args.tprefix + '_' + proc_folder + number.group(1)
        basename += args.subtag + extension
        t.append( os.path.join(folder, basename) )
    return t
    
@utils.set_pure_input_namespace
def produce_trigger_outputs(args, ext='root'):
    """
    Produces all outputs of the submitTriggerEff task.
    Limitation: As soon as one file is not produced, luigi
    reruns everything.
    """
    tdata, tmc = ([] for _ in range(2))
    for proc in args.data_vals:
        tdata.extend( produce_trigger_outputs_sample(args, proc, ext) )
    for proc in args.mc_vals:
        tmc.extend( produce_trigger_outputs_sample(args, proc, ext) )
    return tdata, tmc

@utils.set_pure_input_namespace
def processing_outputs(args):
    if args.mode == 'histos':
        name = 'Histos'
    elif args.mode == 'counts':
        name = 'Counts'
    else:
        raise ValueError('Mode {} is not supported.'.format(args.mode))

    _data_tup = tuple((k,v) for k,v in zip(args.data_keys,args.data_vals))
    _mc_tup = tuple((k,v) for k,v in zip(args.mc_keys,args.mc_vals))

    data_folders = [ name + '_' + v for v in args.data_vals ]
    mc_folders   = [ name + '_' + v for v in args.mc_vals ]
    job_opt = dict(localdir=args.localdir, tag=args.tag)
    return ( JobWriter.define_output( data_folders=data_folders, **job_opt),
             JobWriter.define_output( data_folders=mc_folders,   **job_opt),
             _data_tup, _mc_tup )

@utils.set_pure_input_namespace
def processing(args):
    outs_data, outs_mc, _data_procs, _mc_procs = processing_outputs(args)
    # unite Data and MC lists
    outs_job    = outs_data[0] + outs_mc[0]
    outs_submit = outs_data[1] + outs_mc[1]
    outs_check  = outs_data[2] + outs_mc[2]
    outs_log    = outs_data[3] + outs_mc[3]
    _all_processes = _data_procs + _mc_procs

    for i, (kproc, vproc) in enumerate(_all_processes):
        filelist, _ = utils.get_root_inputs(vproc, args.indir)
        
        #### Write shell executable (python scripts must be wrapped in shell files to run on HTCondor)
        pars = {'outdir'        : args.outdir,
                'dataset'       : kproc,
                'sample'        : vproc,
                'isdata'        : int(vproc in args.data_vals),
                'file'          : '${1}',
                'subtag'        : args.subtag,
                'channels'      : ' '.join(args.channels),
                'tprefix'       : args.tprefix,
                'year'          : args.year,
                'configuration' : args.configuration}
        script = ('produce_trig_histos.py' if args.mode == 'histos'
                  else 'produce_trig_counts.py')
        comm = utils.build_script_command(name=script, sep=' ', **pars)

        if args.mode == 'histos':
            pars1 = {'binedges_fname'   : args.binedges_filename,
                     'intersection_str' : args.intersection_str,
                     'variables'        : ' '.join(args.variables,),
                     'nocut_dummy_str'  : args.nocut_dummy_str}
            comm += utils.build_script_command(name=None, sep=' ', **pars1)

        jw = JobWriter()
        jw.write_shell(filename=outs_job[i], command=comm, localdir=args.localdir, machine=main.machine)
        jw.add_string('echo "Process {} done in mode {}."'.format(vproc,args.mode))

        #### Write submission file
        jw.write_condor(filename=outs_submit[i],
                        real_exec=utils.build_script_path(script),
                        shell_exec=outs_job[i],
                        outfile=outs_check[i],
                        logfile=outs_log[i],
                        queue=main.queue,
                        machine=main.machine)
        
        qlines = []
        for listname in filelist:
            qlines.append(' {}'.format( listname.replace('\n','') ))
        
        jw.write_queue( qvars=('filename',),
                        qlines=qlines )

# -- Parse options
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Command line parser')

    parser.add_argument('--binedges_dataset', required=True, help='in directory')
    parser.add_argument('--localdir', default=os.getcwd(), help='job out directory')
    parser.add_argument('--indir', required=True, help='in directory')
    parser.add_argument('--outdir', required=True, help='out directory')
    parser.add_argument('--tag', required=True, help='tag')
    parser.add_argument('--subtag', required=True, help='subtag')
    parser.add_argument('--tprefix', required=True, help='target prefix')
    parser.add_argument('--year', required=True, type=str,
                        choices=('2016', '2016APV', '2017', '2018'),
                        help='Data year: impact thresholds and selections.')
    parser.add_argument('--mc_processes', required=True, nargs='+', type=str,
                        help='list of MC process names')                
    parser.add_argument('--data_keys', required=True, nargs='+', type=str,
                        help='list of datasets')
    parser.add_argument('--data_vals', required=True, nargs='+', type=str,
                        help='list of datasets')
    parser.add_argument('--channels', required=True, nargs='+', type=str,
                        help='Select the channels over which the workflow will be run.' )
    parser.add_argument('--variables', required=True, nargs='+', type=str,
                        help='Select the variables over which the workflow will be run.' )
    parser.add_argument('--intersection_str', required=False, default=main.inters_str,
                        help='String used to represent set intersection between triggers.')
    parser.add_argument('--nocut_dummy_str', required=True,
                        help='Dummy string associated to trigger histograms were no cuts are applied.')
    parser.add_argument('--configuration', required=True,
                        help='Name of the configuration module to use.')
    args = parser.parse_args()

    submitTriggerEff( args )
