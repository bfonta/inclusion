# coding: utf-8

_all_ = [ 'test_trigger_gains' ]

import os
import sys
parent_dir = os.path.abspath(__file__ + 2 * '/..')
sys.path.insert(0, parent_dir)

import json
import argparse
from inclusion.utils import utils
import numpy as np
from collections import defaultdict as dd
import hist
from hist.intervals import clopper_pearson_interval as clop
import pickle

import bokeh
from bokeh.plotting import figure, output_file, save
from bokeh.models import Whisker
from bokeh.layouts import gridplot
#from bokeh.io import export_svg

tau = '\u03C4'
mu  = '\u03BC'
pm  = '\u00B1'
ditau = tau+tau

def get_outname(sample, channel, regcuts, ptcuts, met_turnon, bigtau):
    utils.create_single_dir('data')

    name = sample + '_' + channel + '_'
    name += '_'.join((*regcuts, 'ptcuts', *[str(x) for x in ptcuts], 'turnon', str(met_turnon)))
    if bigtau:
        name += '_BIGTAU'
    name += '.pkl'

    s = 'data/regions_{}'.format(name)
    return s

def pp(chn):
    if chn == "tautau":
        return ditau
    elif chn == "etau":
        return "e" + tau
    elif chn == "mutau":
        return mu + tau

def rec_dd():
    return dd(rec_dd)

def set_fig(fig, legend=True):
    fig.output_backend = 'svg'
    fig.toolbar.logo = None
    # if legend:
    #     fig.legend.click_policy='hide'
    #     fig.legend.location = 'top_left'
    #     fig.legend.label_text_font_size = '8pt'
    fig.min_border_bottom = 5
    fig.xaxis.visible = True
    fig.title.align = "left"
    fig.title.text_font_size = "15px"
    fig.xaxis.axis_label_text_font_style = "bold"
    fig.yaxis.axis_label_text_font_style = "bold"
    fig.xaxis.axis_label_text_font_size = "13px"
    fig.yaxis.axis_label_text_font_size = "13px"

def main(args):
    channels = args.channels
    linear_x = [k for k in range(1,len(args.masses)+1)]
    edges_x  = [k-0.5 for k in range(1,len(args.masses)+1)] + [len(args.masses)+0.5]
    ptcuts = {chn: utils.get_ptcuts(chn, args.year) for chn in args.channels}

    nevents, errors = dd(lambda: dd(dict)), dd(lambda: dd(dict))
    ratios, eratios = dd(lambda: dd(dict)), dd(lambda: dd(dict))

    for adir in main_dir:
        dRstr = str(args.deltaR).replace('.', 'p')
        if len(args.channels) == 1:
            output_name = os.path.join(base_dir, 'trigger_gains_{}_{}_DR{}'.format(args.channels[0],
                                                                                        args.year, dRstr))
        elif len(args.channels) == 2:
            output_name = os.path.join(base_dir, 'trigger_gains_{}_{}_{}_DR{}'.format(*args.channels[:2],
                                                                                           args.year, dRstr))
        elif len(args.channels) == 3:
            output_name = os.path.join(base_dir, 'trigger_gains_all_{}_DR{}'.format(args.year, dRstr))
        if args.bigtau:
            output_name += "_BIGTAU"
        output_name += ".html"
        output_file(output_name)
        print('Saving file {}.'.format(output_name))

        for chn in channels:
            md = adir[chn]
            in_base = os.path.join(base_dir, md)

            nevents[md][chn]['base'], nevents[md][chn]['met'],  nevents[md][chn]['tau'] = [], [], []
            ratios[md][chn]['two'], ratios[md][chn]['met'], ratios[md][chn]['tau'] = [], [], []
            eratios[md][chn]['two'], eratios[md][chn]['met'], eratios[md][chn]['tau'] = [], [], []
            errors[md][chn] = []
              
            for mass in args.masses:
                outname = get_outname(mass, chn, [str(x) for x in args.region_cuts],
                                      [str(x) for x in ptcuts[chn]], str(args.met_turnon),
                                      args.bigtau)

                with open(outname, "rb") as f:
                    ahistos = pickle.load(f)

                    # all regions summed
                    sum_base_tot = round(ahistos["Base"]["legacy"]["baseline"].values().sum() +
                                         ahistos["Base"]["tau"]["baseline"].values().sum() +
                                         ahistos["Base"]["met"]["baseline"].values().sum())
                    
                    # legacy region
                    l1 = lambda x : round(x["legacy"]["baseline"].values().sum(), 2)
                    sum_base     = l1(ahistos["Base"])
                    sum_vbf      = l1(ahistos["VBF"])
                    sum_met      = l1(ahistos["NoBaseMET"])
                    sum_only_tau = l1(ahistos["NoBaseNoMETTau"])
                    sum_tau      = l1(ahistos["NoBaseTau"])
                    sum_basekin  = l1(ahistos["LegacyKin"])
                    w2_basekin   = ahistos["METKin"]["legacy"]["baseline"].variances().sum()
                    
                    # MET region
                    l2 = lambda x : round(x["met"]["baseline"].values().sum(), 2)
                    sum_metkin = l2(ahistos["METKin"])
                    w2_metkin = ahistos["METKin"]["met"]["baseline"].variances().sum()
                    
                    # Single Tau region
                    l3 = lambda x : round(x["tau"]["baseline"].values().sum(), 2)
                    sum_taukin = l3(ahistos["TauKin"])
                    w2_taukin = ahistos["TauKin"]["tau"]["baseline"].variances().sum()

                    # hypothetical VBF region
                    sum_vbfkin   = l2(ahistos["VBFKin"]) + l3(ahistos["VBFKin"])

                    nevents[md][chn]['base'].append(sum_basekin)
                    nevents[md][chn]['met'].append(sum_basekin + sum_metkin)
                    nevents[md][chn]['tau'].append(sum_basekin + sum_metkin + sum_taukin)

                    rat_met_num = sum_basekin + sum_metkin
                    rat_met_all = rat_met_num / sum_base_tot

                    rat_tau_num = sum_basekin + sum_taukin
                    rat_tau_all = rat_tau_num / sum_base_tot

                    rat_all_num = sum_basekin + sum_taukin + sum_metkin
                    rat_all = rat_all_num / sum_base_tot
                    
                    ratios[md][chn]['met'].append(rat_met_all)
                    ratios[md][chn]['tau'].append(rat_tau_all)
                    ratios[md][chn]['two'].append(rat_all)

                    e_metkin = np.sqrt(w2_metkin)
                    e_taukin = np.sqrt(w2_taukin)
                    e_basekin = np.sqrt(w2_basekin)

                    e_tau_num = np.sqrt(w2_taukin + w2_basekin)
                    e_met_num = np.sqrt(w2_metkin + w2_basekin)
                    e_all_num = np.sqrt(w2_metkin + w2_taukin + w2_basekin)

                    eratios[md][chn]['tau'].append(rat_tau_all * np.sqrt(e_tau_num**2/rat_tau_num**2 + 1/sum_base_tot))
                    eratios[md][chn]['met'].append(rat_met_all * np.sqrt(e_met_num**2/rat_met_num**2 + 1/sum_base_tot))
                    eratios[md][chn]['two'].append(rat_all * np.sqrt(e_all_num**2/rat_all_num**2 + 1/sum_base_tot))
                    errors[md][chn].append(e_all_num)

    json_name = 'data_' + chn + '_'
    json_name += ('bigtau' if args.bigtau else 'standard') + '.json'
    with open(json_name, 'w', encoding='utf-8') as json_obj:
        json_data = {"vals": {chn: nevents[adir[chn]][chn]['tau'] for chn in channels}}
        json_data.update({"errs": {chn: errors[adir[chn]][chn] for chn in channels}})
        json.dump(json_data, json_obj, ensure_ascii=False, indent=4)

    opt_points = dict(size=8)
    opt_line = dict(width=1.5)
    colors = ('green', 'blue', 'red', 'brown')
    styles = ('solid', 'dashed', 'dotdash')
    legends = {'base': 'Legacy',
               'met': 'MET', 'tau': 'Single Tau',
               'two': 'MET + Single Tau', 'vbf': 'VBF'}
     
    x_str = [str(k) for k in args.masses]
    xticks = linear_x[:]
    yticks = [x for x in range(0,110,5)]
    shift_one = {'met': [-0.15, 0., 0.15],  'tau': [-0.20, -0.05, 0.1],
                 'vbf': [-0.10, 0.05, 0.20]}
    shift_both = {'met': [-0.15, 0., 0.15], 'two': [-0.20, -0.05, 0.1]}
    shift_kin = {'met': [-0.09, 0., 0.15],  'tau': [0.03, -0.05, 0.1],
                 'two': [-0.03, 0.05, 0.20], 'vbf': [0.09, 0.1, 0.25]}
     
    for adir in main_dir:
        p_opt = dict(width=800, height=400, x_axis_label='x', y_axis_label='y')
        p1 = figure(title='Event number (' + pp(channels[0]) + ')', y_axis_type="linear", **p_opt)
        p2 = figure(title='Acceptance Gain (' + pp(channels[0]) + ')', **p_opt) if len(channels)==1 else figure(**p_opt)

        p1.yaxis.axis_label = 'Weighted number of events'
        p2.yaxis.axis_label = 'Trigger acceptance gain (w.r.t. trigger baseline) [%]'
        pics = (p1, p2)
        for p in pics:
            set_fig(p)

        for ichn,chn in enumerate(channels):
            md = adir[chn]
            
            p1.quad(top=nevents[md][chn]["base"], bottom=0,
                    left=edges_x[:-1], right=edges_x[1:],
                    legend_label=legends["base"]+(' ('+pp(chn)+')' if len(channels)>1 else ''),
                    fill_color="dodgerblue", line_color="black")
            p1.quad(top=nevents[md][chn]["met"], bottom=nevents[md][chn]["base"],
                    left=edges_x[:-1], right=edges_x[1:],
                    legend_label=legends["met"]+(' ('+pp(chn)+')' if len(channels)>1 else ''),
                    fill_color="green", line_color="black")
            p1.quad(top=nevents[md][chn]["tau"], bottom=nevents[md][chn]["met"],
                    left=edges_x[:-1], right=edges_x[1:],
                    legend_label=legends["tau"]+(' ('+pp(chn)+')' if len(channels)>1 else ''),
                    fill_color="red", line_color="black")

            for itd,td in enumerate(('met', 'tau', 'two')):
                p2.circle([x+shift_kin[td][ichn] for x in linear_x],
                          [(x-1)*100. for x in ratios[md][chn][td]],
                          color=colors[itd], fill_alpha=1., **opt_points)
                p2.line([x+shift_kin[td][ichn] for x in linear_x],
                        [(x-1)*100. for x in ratios[md][chn][td]],
                        color=colors[itd], line_dash=styles[ichn],
                        legend_label=legends[td]+(' ('+pp(chn)+')' if len(channels)>1 else ''), **opt_line)
                p2.multi_line(
                    [(x+shift_kin[td][ichn],x+shift_kin[td][ichn]) for x in linear_x], 
                    [((y-1)*100-(x*50.),(y-1)*100+(x*50.)) for x,y in zip(eratios[md][chn][td],ratios[md][chn][td])],
                    color=colors[itd], **opt_line)

        p1.legend.location = 'top_right'
        p2.legend.location = 'top_left'
        for p in pics:
            p.xaxis[0].ticker = xticks
            p.xgrid[0].ticker = xticks
            p.xgrid.grid_line_alpha = 0.2
            p.xgrid.grid_line_color = 'black'
            # p.yaxis[0].ticker = yticks
            # p.ygrid[0].ticker = yticks
            p.ygrid.grid_line_alpha = 0.2
            p.ygrid.grid_line_color = 'black'
             
            p.xaxis.axis_label = "m(X) [GeV]"
         
            p.xaxis.major_label_overrides = dict(zip(linear_x,x_str))
     
            p.legend.click_policy='hide'        
     
            p.output_backend = 'svg'
            #export_svg(p, filename='line_graph.svg')
         
        g = gridplot([[p] for p in pics])
        save(g, title=md)

if __name__ == '__main__':
    desc = "Produce plots of trigger gain VS resonance mass.\n"
    desc += "Uses the output of test_trigger_regions.py."
    desc += "When running on many channels, one should keep in mind each channel has different pT cuts."
    desc += "This might imply moving sub-folders (produced by the previous script) around."
    parser = argparse.ArgumentParser(description=desc, formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument('--masses', required=True, nargs='+', type=str,
                        help='Resonance mass')
    parser.add_argument('--channels', required=True, nargs='+', type=str, 
                        choices=('etau', 'mutau', 'tautau'),
                        help='Select the channel over which the workflow will be run.' )
    parser.add_argument('--year', required=True, type=str, choices=('2016', '2017', '2018'),
                        help='Select the year over which the workflow will be run.' )
    parser.add_argument('--deltaR', type=float, default=0.5, help='DeltaR between the two leptons.')
    parser.add_argument('--bigtau', action='store_true',
                        help='Consider a larger single tau region, reducing the ditau one.')
    parser.add_argument('--met_turnon', required=False, type=str,  default=180,
                        help='MET trigger turnon cut [GeV].' )
    parser.add_argument('--region_cuts', required=False, type=float, nargs=2, default=(190., 190.),
                        help='High/low regions pT1 and pT2 selection cuts [GeV].' )

    args = utils.parse_args(parser)

    base_dir = '/eos/home-b/bfontana/www/TriggerScaleFactors/'
    main_dir = [{"etau":   "Region_Spin2_190_190_PT_33_25_35_DR_{}_TURNON_200_190".format(args.deltaR),
                 "mutau":  "Region_Spin2_190_190_PT_25_21_32_DR_{}_TURNON_200_190".format(args.deltaR),
                 "tautau": "Region_Spin2_190_190_PT_40_40_DR_{}_TURNON_200_190".format(args.deltaR)},
                ]
    
    main(args)
