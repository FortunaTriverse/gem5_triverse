import os
import shutil
import re
import time

local_time=time.strftime("%Y%m%d",time.localtime())

insts = {
    'astar_biglakes':'311675635900',
    'astar_rivers':'658127490009', 
    "bwaves":"1650019284052",
    "bzip2_chicken":"181787412012", 
    "bzip2_combined":"359226782686",
    "bzip2_html":"735579475881",
    "bzip2_liberty":"305542263155",
    "bzip2_program":"572800534353",
    "bzip2_source":"452484478254",
    "cactusADM":"3371498924248",
    "calculix":"3617118277478",
    "dealII":"1647328019263",
    "gamess_cytosine":"1196555167074",
    "gamess_gradient":"969048020524",
    "gamess_triazolium":"3819388902476",
    "gcc_166":"80858843859",
    "gcc_200":"158923315859",
    "gcc_cpdecl":"101751393866",
    "gcc_expr":"113392762941",
    "gcc_expr2":"153836532176",
    "gcc_g23":"195905833025",
    "gcc_s04":"175174930998",
    "gcc_scilab":"61228852998",
    "gcc_typeck":"138382597912",
    "GemsFDTD":"1475323618742",
    "gobmk_13x13":"246211736511",
    "gobmk_nngs":"660150161467",
    "gobmk_score2":"324459463604",
    "gobmk_trevorc":"249707599485",
    "gobmk_trevord":"357616360147",
    "gromacs":"1444946367687",
    "h264ref_foreman.baseline":"532409908080",
    "h264ref_foreman.main":"461268364405",
    "h264ref_sss":"4208774912802",
    "hmmer_nph3":"1039149982959",
    "hmmer_retro":"2189472853380",
    "lbm":"971871862264",
    "leslie3d":"1848330864010",
    "libquantum":"1239675927956",
    "mcf":"280537105821",
    "milc":"706179141935",
    "namd":"1719281594949",
    "omnet":"565996607917",
    "perlbench_checkspam":"1130166175267",
    "perlbench_diffmail":"419765802378",
    "perlbench_splitmail":"690591078959",
    "povray":"943020595579",
    "sjeng":"2511336112644",
    "soplex_pds":"318007712641",
    "soplex_ref":"305553947195",
    "sphinx3":"3352652161622",
    "tonto":"2168485269198",
    "wrf":"2915368682622",
    "xalancbmk":"886287570264",
    "zeusmp":"1444408265569"
}

ref_times = {
    "bzip2": "9650",
    "perlbench": "9770",
    "namd": "8020",
    "omnet": "6250",
    "soplex": "8340",
    "leslie3d": "9400",
    "calculix": "8250",
    "gamess": "19580",
    "libquantum": "20720",
    "dealII": "11440",
    "bwaves": "13590",
    "xalancbmk": "6900",
    "hmmer": "9330",
    "tonto": "9840",
    "cactusADM": "11950",
    "specrand": "10",
    "gobmk": "10490",
    "wrf": "11170",
    "sphinx3": "19490",
    "GemsFDTD": "10610",
    "h264ref": "22130",
    "povray": "5320",
    "mcf": "9120",
    "sjeng": "12100",
    "zeusmp": "9100",
    "milc": "9180",
    "lbm": "13740",
    "gromacs": "7140",
    "astar": "7020",
    "gcc": "8050"
}


normal_prefetchers = ['ampm','bop','dcpt','imp','isb','sbooe','spp', \
                      'slim','stride','tagged','xsberti','xsbop', \
                      'xsopt','xsstream','triangelbloom']

personal_prefetchers = ['tkV10','tkV11','tkV12']

key_words = {'stride_mode':0,
             'dynamic_mode':0,
             'filter_size':64,
             'degree':512,
              'tu_entries':16,
              'tu_assoc':16,
              'ama_entries':196608,
              'ama_assoc':12,
              'amr_entries':262144,
              'amr_assoc':16,
              'am_replace':'RRIP',
              'sample_assoc':2,
              'sample_entries':512,
              'sample_replacement_policy':'LRURP',
              'reuse_entries':256,
              'reuse_assoc':2,
              'reuse_replace':'FIFORP',
              'second_assoc':2,
              'second_entries':64,
              'second_replace':'FIFORP',
              're_thre':40,
              'pre_threshold':60,
              'maxstride':64,
              'stride_degree':4,
              'inc_stride_thre':70,\
              'dec_stride_thre':40,
              'max_degree':8,
              'min_degree':0,
              'st_assoc':16,
              'st_entries':512,
              'st_replace':'FIFPRP'
}



path = os.getcwd()
gem5_path = os.path.dirname(path)
home_path = os.path.dirname(gem5_path)
results_path = home_path + '/test_results/stats_triangel'
time_path = home_path + f'/test_results/csv_triangel/time_{local_time}.csv'
perform_path = home_path + f'/test_results/csv_triangel/performance_{local_time}.csv'
fen_final_path = home_path + f'/test_results/csv_triangel/fen_final_{local_time}.csv'
final_path = home_path + f'/test_results/csv_triangel/final_{local_time}.csv'
config_path = home_path + f'/test_results/csv_triangel/config_{local_time}.csv'

t = open(time_path,'w')
t_title = 'prefetcher,bench,samples,instructions,slice_numbers,slice_time,test_time\n'
t.write(t_title)
t.close()

p = open(perform_path,'w')
p_title = 'prefetcher,bench,samples,l2 accesses,l2_hit,pf_used,pf_unused,pf missed,l3_access,meta\n'
p.write(p_title)
p.close()

ff = open(fen_final_path,'w')
ff_title = 'prefetcher,bench,speedup,pf_accuracy,pf_coverage,l3_ratio,overhead\n'
ff.write(ff_title)
cc.close()


f = open(final_path,'w')
f_title = 'prefetcher,benchmark,score,SpeedUp,PF_accuracy,PF_coverage,L3_ratio,overhead\n'
f.write(f_title)
f.close()

c = open(config-path,'w')
c_title = 'prefetcher,stride_mode,dynamic_mode,filter_size,degree,tu_entries,tu_assoc,tu_replace,ama_entries,ama_assoc,amr_entries,amr_assoc,am_replace,sample_assoc,sample_entries,sample_replacement_policy,reuse_entries,reuse_assoc,reuse_replace,second_assoc,second_entries,second_replace,re_thre,pre_threshold,maxstride,stride_degree,inc_stride_thre,dec_stride_thre,max_degree,min_degree,st_assoc,st_entries,st_replace'
c.write(c_title)
c.close()


result_prefetchers = os.listdir(results_path)

def grep(result_file_path):
  #initial
  time = 0
  samples = 0
  l2_access = 0
  l2_hit = 0 
  pf_used = 0
  pf_unused = 0
  pf_missed = 0
  dram_reads = 0
  dram_writes = 0
  l3_accesses = 0
  meta = 0

  f = open(result_file_path,'r')
  for line in f.readlines():
    if 'simSeconds' in line:
      sims = float(re.findall(r'(\d+.?\d*)',line)[-1])
      if sims < 1:
        time += sims
      samples += 1
    elif 'l2cache.overallAccesses::total' in line:
      l2_a = int(re.findall(r'(\d+)',line)[-1])
      l2_access += l2_a
    elif 'system.cpu.l2cache.overallHits::total' in line:
      l2_h = int(re.findall(r'(\d+)',line)[-1])
      l2_hit += l2_h
    elif 'l2cache.prefetcher.pfUseful' in line:
      pf_u = int(re.findall(r'(\d+)',line)[-1])
      pf_used += pf_u
    elif 'l2cache.prefetcher.pfUnused' in line:
      pf_uu = int(re.findall(r'(\d+)',line)[-1])
      pf_unused += pf_uu
    elif 'l2cache.demandMisses::switch_cpus_1.data' in line:
      pf_m = int(re.findall(r'(\d+)',line)[-1])
      pf_missed += pf_m
    elif 'bytesRead::total' in line:
      dr_read = int(re.findall(r'(\d+)',line)[-1])
      dram_reads += dr_read
    elif 'bytesWritten::total' in line:
      dr_write = int(re.findall(r'(\d+)',line)[-1])
      dram_writes += dr_write
    elif 'l3.overallAccesses::total' in line:
      l3_acc = int(re.findall(r'(\d+)',line)[-1])
      l3_accesses += l3_acc
    elif 'l2cache.prefetcher.metadataAccesses' in line:
      me = int(re.findall(r'(\d+)',line)[-1])
      meta += me
  f.close()

  return  time,samples,l2_access,l2_hit,pf_used,pf_unused,pf_missed,dram_reads,dram_writes,l3_accesses,meta

def calculate(result_file_path):
  #grep the original data
  time,samples,l2_access,l2_hit,pf_used,pf_unused,pf_missed,dram_reads,dram_writes,l3_accesses,meta = grep(result_file_path)
  
  ###put it in results
  results={}
  results['time']=time
  results['samples']=samples
  results['l2_accrss']=l2_access
  results['l2_hit']=l2_hit
  results['pf_used']=pf_used
  results['pf_unused']=pf_unused
  results['pf_missed']=pf_missed
  results['dram_reads']=dram_reads
  results['dram_writes']=dram_writes
  results['l3_access']=l3_access
  results['meta']=meta

  
  


def caculate_score(bench)



for bench,ref_time in ref_times.items():
  print(f'************** {bench} ***************') 
  for result_prefetcher in result_prefetchers:
    prefetcher_configs = result_prefetcher.split('_')
    prefetcher = prefetcher_configs[0]
    p_bench = prefetcher_configs[-1]
    if p_bench == bench: 
      if prefetcher in normal_prefetchers:
        print(f'##### normal prefetcher {prefetcher}')
        




      elif prefetcher in personal_prefetchers:
        print(f'##### personal prefetcher {prefetcher}')

        txt_path = results_path + f'/{prefetcher}'
        tests = os.listdir(txt_path)
        for test in tests:
        
          file_path = txt_path + f'/{test}'
          configs = []
          if 'txt' in test and os.path.getsize(file_path):
            print(test)
            for key_word in key_words:
              if key_word in test:
                configs.append(key_word)

            time = gettime(path)
          #print(configs)
              


