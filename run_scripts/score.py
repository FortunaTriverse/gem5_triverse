import os
import re
import shutil
import sys
from concurrent.futures import ProcessPoolExecutor

########### overall instructions numbers for each bench function
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
    "h264ref_foreman-baseline":"532409908080",
    "h264ref_foreman_main":"461268364405",
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

########### reference time to calculate spec score
########### score = test_time / ref_time
########### test time is added with each function in bench
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

########### 
pres = []
bench_time = {}
l2_accesses = {}
l2_hits = {}
pf_useds = {}
pf_unuseds = {}
pf_misseds = {}
dram_reads = {}
dram_writes = {}
l3_accesses = {}
meta_access = {}

input_folder = sys.argv[1]
output_folder = sys.argv[2]

path = os.getcwd()
stats_path = path + f'/{input_folder}'
csv_path = path + f'/{output_folder}'
test_prefetchers = os.listdir(stats_path)
functions = []
print('test function include:')
for key,value in insts.items():
    functions.append(key)
    print(key,end=',')
print('\n')

benchs = []
print('test benchs include:')
for key,value in ref_times.items():
    benchs.append(key)
    print(key,end=',')
print('\n')

all_results = []


####################################################################
########### grep the original data from stats.txt and accumulation
def grep(result_file_path):
  #initial
  time      = 0
  samples   = 0
  l2_access = 0
  l2_hit    = 0
  pf_used   = 0
  pf_unused = 0
  pf_missed = 0
  dramreads  = 0
  dramwrites = 0
  l3s        = 0
  metas      = 0

  f = open(result_file_path,'r')
  print(result_file_path)
  for line in f.readlines():
    if 'simSeconds' in line:
      sims = float(re.findall(r'(\d+.?\d*)',line)[-1])
      if sims < 1:
        time += sims
        samples += 1 
    elif 'l2cache.overallAccesses::total' in line:
      l2_access += int(re.findall(r'(\d+)',line)[-1])
    elif 'system.cpu.l2cache.overallHits::total' in line:
      l2_hit += int(re.findall(r'(\d+)',line)[-1])
    elif 'l2cache.prefetcher.pfUseful' in line:
      pf_used += int(re.findall(r'(\d+)',line)[-1])
    elif 'l2cache.prefetcher.pfUnused' in line:
      pf_unused += int(re.findall(r'(\d+)',line)[-1])
    elif 'l2cache.demandMisses::switch_cpus_1.data' in line:
      pf_missed += int(re.findall(r'(\d+)',line)[-1])
    elif 'bytesRead::total' in line:
      dramreads += int(re.findall(r'(\d+)',line)[-1])
    elif 'bytesWritten::tot' in line:
      dramwrites += int(re.findall(r'(\d+)',line)[-1])
    elif 'l3.overallAccesses::total' in line:
      l3s += int(re.findall(r'(\d+)',line)[-1])
    elif 'l2cache.prefetcher.metadataAccess' in line:
      metas += int(re.findall(r'(\d+)',line)[-1])
  f.close()
  return  time,samples,l2_access,l2_hit,pf_used,pf_unused,pf_missed,dramreads,dramwrites,l3s,metas


###########################################################################
####################### compute a bench function's overall test time
####################### without config combation, only one type in a folder
def get_time(prefetcher,function,time_path,files,prefetcher_stats_path):
    file_path    = prefetcher_stats_path + f'/{file}'
    time,samples,l2_access,l2_hit,pf_used,pf_unused,pf_missed,dramreads,dramwrites,l3s,metas = grep(file_path)
    instructions = int(insts[function])
    copies = instructions / (samples * 5000000)
    test_time = time * copies   

    f = open(time_path,'a')
    data = f'{prefetcher},{instructions},{samples},{copies},{time},{test_time},{l2_access},{l2_hit},{pf_used},{pf_unused},{pf_missed}\n'
    f.write(data)
    f.close()

    return test_time,l2_access,l2_hit,pf_used,pf_unused,pf_missed,dramreads,dramwrites,l3s,metas


##########################################################################################################################################################
####################### compute the performance index and put it set as the directory into the file
####################### SpeedUp  = test_score / ref_score     (equal to test_time / ref_time)
####################### Accuracy = pf_used / (pf_used+pf_unused)
####################### Coverage = 1-(pf_missed / nopf_pf_missed)
####################### dram_ratio = (dramreads + dramwrites) / (nopf_dramreads + nopf_dramwrites)
####################### l3_ratio = (l3_access + meta_access) /nopf_l3_access
####################### l3_energy = (64*l3_access + 64*meta_access) / (64*nopf_l3_access + 64*nopf_meta_access + 25*nopf_dramreads + 25*nopf_dramwrites)
####################### dram_energy = (25*dramreads + 25*dramwrites) / (64*nopf_l3_access + 64*nopf_meta_access + 25*nopf_dramreads + 25*nopf_dramwrites)
####################### total_energy = l3_energy + dram_energy
####################### All results are formatted in percentages to four decimal places
def process_score(pres,bench_time,l2_accesses,l2_hits,pf_useds,pf_unuseds,pf_misseds,dram_reads,dram_writes,l3_accesses,meta_accesses):
    print(f'\n\nready to go process score\n\n')
    i = 0
    
    ### summarize to be used for calculating the overall performance indicators
    total_score       = {}
    total_l2_access   = {}
    total_l2_hit      = {}    
    total_pf_used     = {}
    total_pf_unused   = {}
    total_pf_missed   = {}
    total_dramreads   = {}
    total_dramwrites  = {}
    total_l3_access   = {}
    total_meta_access = {}
    total_l2_score = 0
    total_total_score = 0
    
    ### count the calculation results to return to take_picture function
    l2_speedups    = {}
    accuracys      = {}
    coverages      = {}
    dram_ratios    = {}
    l3_ratios      = {}
    l3_energys     = {}
    dram_energys   = {}
    total_energys  = {}
    l2_hit_rates   = {}
  
    ### 
    for bench in benchs:
        print(bench)
        i += 1
        #print(bench)
        
        
        score_folder_path = csv_path + '/score'
        if not os.path.exists(score_folder_path):
          os.mkdir(score_folder_path) 
        score_path = score_folder_path + f'/score_{bench}.csv'  
        f = open(score_path,'w')
        title = 'prefetcher,score,L2speedup,pf_accuracy,pf_coverage,l2_hit_rate,test_time,ref_time,'
        title += 'dram_ratio,l3_ratio,l3_energy,dram_energy,total_energy\n'
        f.write(title)
        f.close()
         
        base_l2_key = f'NoPF-{bench}'
        l2_ref_score = (int(ref_times[bench])/int(bench_time[base_l2_key]))
        total_l2_score += l2_ref_score

        for pre in pres:
            print(pre)
            #print(pre,end=',')
            key = f'{pre}-{bench}'
            #print(key)
            if key in bench_time:
                test_time  = int(bench_time[key])
                ref_time   = int(ref_times[bench])
                score      = ref_time / test_time
                l2_speedup = score / l2_ref_score

                pf_used = pf_useds[key]
                pf_unused = pf_unuseds[key]
                if (pf_used+pf_unused) != 0:
                  pf_accuracy = round((pf_used / (pf_used+pf_unused))*100,4)
                else:
                  pf_accuracy = 0

                nopf_pf_missed = pf_misseds[f'NoPF-{bench}']
                pf_missed = pf_misseds[key]
                if nopf_pf_missed != 0:
                  pf_coverage = round((1-(pf_missed / nopf_pf_missed))*100,4)
                else:
                  pf_coverage = 0               

                l2_access = l2_accesses[key]
                l2_hit = l2_hits[key]
                if l2_access != 0:
                  l2_hit_rate = round((l2_hit / l2_access)*100,4)
                else:
                  l2_hit_rate = 0

                nopf_dramreads = dram_reads[f'NoPF-{bench}']
                nopf_dramwrites = dram_writes[f'NoPF-{bench}']
                dramreads = dram_reads[key]
                dramwrites = dram_writes[key]  
                if (nopf_dramreads + nopf_dramwrites) != 0:
                  dram_ratio = (dramreads + dramwrites) / (nopf_dramreads + nopf_dramwrites)
                else:
                  dram_ratio = 0  
                
                nopf_l3_access = l3_accesses[f'NoPF-{bench}']
                l3_access = l3_accesses[key]
                meta_access = meta_accesses[key]
                nopf_meta_access = meta_accesses[f'NoPF-{bench}']
                if (nopf_l3_access != 0):
                  l3_ratio = (l3_access + meta_access) /nopf_l3_access 
                else:
                  l3_ratio = 0
                
                if (nopf_dramreads + nopf_dramwrites) != 0:
                  l3_energy = (64*l3_access + 64*meta_access) / (64*nopf_l3_access + 64*nopf_meta_access + 25*nopf_dramreads + 25*nopf_dramwrites)
                  dram_energy = (25*dramreads + 25*dramwrites) / (64*nopf_l3_access + 64*nopf_meta_access + 25*nopf_dramreads + 25*nopf_dramwrites)
                  total_energy = l3_energy + dram_energy
                else:
                  l3_energy = 0
                  dram_energy = 0
                  total_energy = 0                 

                if pre not in total_score:
                    total_score[pre]        = score
                    total_pf_missed[pre]    = pf_missed
                    total_pf_used[pre]      = pf_used
                    total_pf_unused[pre]    = pf_unused
                    total_l2_access[pre]    = l2_access
                    total_l2_hit[pre]       = l2_hit
                    total_dramreads[pre]    = dramreads
                    total_dramwrites[pre]   = dramwrites
                    total_l3_access[pre]    = l3_access
                    total_meta_access[pre]  = meta_access
                else:
                    total_score[pre]       += score
                    total_pf_missed[pre]   += pf_missed
                    total_pf_used[pre]     += pf_used
                    total_pf_unused[pre]   += pf_unused
                    total_l2_access[pre]   += l2_access
                    total_l2_hit[pre]      += l2_hit
                    total_dramreads[pre]   += dramreads
                    total_dramwrites[pre]  += dramwrites
                    total_l3_access[pre]   += l3_access
                    total_meta_access[pre] += meta_access
                
                f = open(score_path,'a')
                data = f'{pre},{score},{l2_speedup},{pf_accuracy},{pf_coverage},{l2_hit_rate},{test_time},{ref_time},'
                data += f'{dram_ratio},{l3_ratio},{l3_energy},{dram_energy},{total_energy}\n'
                f.write(data)
                f.close()
                
                l2_speedups[key]    = l2_speedup
                accuracys[key]      = pf_accuracy
                coverages[key]      = pf_coverage
                l2_hit_rates[key]   = l2_hit_rate
                dram_ratios[key]    = dram_ratio
                l3_ratios[key]      = l3_ratio
                l3_energys[key]     = l3_energy
                dram_energys[key]   = dram_energy
                total_energys[key]  = total_energy
                
    total_score_path = score_folder_path + '/score_total.csv'
    f = open(total_score_path,'w')
    title = 'prefetcher,score,l2sppedup,totalspeedup,pf_accuracy,pf_coverage,l2_hit_rate,dram_ratio,l3_ratio,l3_energy,dram_energy,total_energy\n'
    f.write(title)
    f.close()

    for pre in pres:
        l2speedup = total_score[pre] / total_l2_score
        totalspeedup = total_score[pre] / total_total_score

        if (total_pf_used[pre]+total_pf_unused[pre]) != 0:
            totalpfaccuracy = round((total_pf_used[pre] / (total_pf_used[pre]+total_pf_unused[pre]))*100,4)
        else:
            totalpfaccuracy = 0
        if total_pf_missed['NoPF'] != 0:
            totalpfcoverage = round((1-(total_pf_missed[pre] / total_pf_missed['NoPF']))*100,4)
        else:
            totalpfcoverage = 0

        if total_l2_access[pre] != 0:
            totall2hitrate  = round((total_l2_hit[pre] / total_l2_access[pre])*100,4)
        else: 
            totall2hitrate  = 0

        if (total_dramreads['NoPF'] + total_dramwrites['NoPF']) != 0:
            total_dram_ratio = round((total_dramreads[pre] + total_dramwrites[pre]) / (total_dramreads['NoPF'] + total_dramwrites['NoPF'])*100,4)
        else:
            total_dram_ratio = 0
            
        if (total_l3_access['NoPF'] != 0):
            total_l3_ratio = round(((total_l3_access[pre] + total_meta_access[pre]) / total_l3_access['NoPF']) *100,4)
        else:
            total_l3_ratio = 0

        if (total_dramreads['NoPF'] + total_dramwrites['NoPF']) != 0:
            total_l3_energy = (64*total_l3_access[pre] + 64*total_meta_access[pre]) / (64*total_l3_access['NoPF'] + 64*total_meta_access['NoPF'] + 25*total_dramreads['NoPF'] + 25*total_dramwrites['NoPF'])
            total_dram_energy = (25*total_dramreads[pre] + 25*total_dramwrites[pre]) / (64*total_l3_access['NoPF'] + 64*total_meta_access['NoPF'] + 25*total_dramreads['NoPF'] + 25*total_dramwrites['NoPF'])
            total_total_energy = total_l3_energy + total_dram_energy
        else:
            total_l3_energy = 0
            total_dram_energy = 0
            total_total_energy = 0

        f = open(total_score_path,'a')
        score = total_score[pre] / i
        data = f'{pre},{score},{l2speedup},{totalpfaccuracy},{totalpfcoverage},{totall2hitrate},'
        data += f'{total_dram_ratio},{total_l3_ratio},{total_l3_energy},{total_dram_energy},{total_total_energy}\n'
        f.write(data)
        f.close()
        
        key = f'{pre}-total'
        l2_speedups[key]    = l2speedup
        accuracys[key]      = totalpfaccuracy
        coverages[key]      = totalpfcoverage
        l2_hit_rates[key]   = totall2hitrate
        dram_ratios[key]    = total_dram_ratio
        l3_ratios[key]      = total_l3_ratio
        l3_energys[key]     = total_l3_energy
        dram_energys[key]   = total_dram_energy
        total_energys[key]  = total_total_energy

    return l2_speedups,accuracys,coverages,l2_hit_rates,dram_ratios,l3_ratios,l3_energys,dram_energys,total_energys

############# similar like process_score, but use the performance metrics as the file name
def take_picture(pres,l2_speedups,accuracys,coverages,l2_hit_rates,dram_ratios,l3_ratios,l3_energys,dram_energys,total_energys):
  
  performances = [l2_speedups,accuracys,coverages,l2_hit_rates,dram_ratios,l3_ratios,l3_energys,dram_energys,total_energys]
  performances_names = ['l2_speedups','accuracys','coverages','l2_hit_rates','dram_ratios','l3_ratios','l3_energys','dram_energys','total_energys']
  result_folder_path = csv_path + '/result'
  if not os.path.exists(result_folder_path):
    os.mkdir(result_folder_path)
  
  for perf_dict,perf_name in zip(performances,performances_names):
    #print(perf_name)
    #print(perf_dict)
    result_path = result_folder_path + f'/result_{perf_name}.csv'
    f = open(result_path,'w')
    title = 'prefetcher,total,'
    
    for bench in benchs:
     title += f'{bench},'
    f.write(title + '\n')
    f.close()

    for pre in pres:
      a = open(result_path,'a')
      key = f'{pre}-total'
      value = perf_dict[key]
      #print(f'{pre},total:{value}',end=',')
      data = f'{pre},{value},'
      #print(f'*********************** {key}-{value} ******************************')
      #a.write(f'{pre},{value}')
      for bench in benchs:
        key = f'{pre}-{bench}'
        value = perf_dict[key]
        data += f'{value},'
        print(f'{bench}:{value}',end=',')
        #print(f'*********************** {key}-{value} ******************************')
        #a.write(f'{value},')
      a.write(data +'\n')
      #print('\n')
      #print(data+'\n')
      a.close()

######################## main ######################################
for function in functions:
    #print(function)
    
    ### create the time folder and file to store original data
    time_folder_path = csv_path + '/time'
    if not os.path.exists(time_folder_path):
      os.mkdir(time_folder_path)
    time_path = time_folder_path + f'/time_{function}.csv'
    f = open(time_path,'w')
    title = 'prefetcher,instructions,samples,copies,time,test_time,l2_access,l2_hit,pf_used,pf_unused,pf_missed,'
    title += 'dramreads,dramwrites,l3_access,meta_access,stride_mode,dynamic_mode,filter_size,stream_degree\n'
    f.write(title)
    f.close()
    
    
    for prefetcher in test_prefetchers:
        #print(prefetcher)
        prefetcher_stats_path = stats_path + f'/{prefetcher}'
        files = os.listdir(prefetcher_stats_path)
        for file in files:
          if function in file:
            #print(file)
            test_time,l2_access,l2_hit,pf_used,pf_unused,pf_missed,dramreads,dramwrites,l3s,metas = get_time(prefetcher,function,time_path,file,prefetcher_stats_path)
            if prefetcher not in pres:
              pres.append(prefetcher)
            for bench in benchs:
              if bench in function:
                key = f'{prefetcher}-{bench}'
                if not key in bench_time:
                  bench_time[key]  = test_time
                  l2_accesses[key] = l2_access
                  l2_hits[key]     = l2_hit
                  pf_useds[key]    = pf_used
                  pf_unuseds[key]  = pf_unused
                  pf_misseds[key]  = pf_missed
                  dram_reads[key]  = dramreads
                  dram_writes[key] = dramwrites
                  l3_accesses[key] = l3s
                  meta_access[key] = metas

                else:
                  bench_time[key]  += test_time
                  l2_accesses[key] += l2_access
                  l2_hits[key]     += l2_hit
                  pf_useds[key]    += pf_used
                  pf_unuseds[key]  += pf_unused
                  pf_misseds[key]  += pf_missed
                  dram_reads[key]  += dramreads
                  dram_writes[key] += dramwrites
                  l3_accesses[key] += l3s
                  meta_access[key] += metas

total_score_path = csv_path + '/score_total.csv'
l2_speedups,accuracys,coverages,l2_hit_rates,dram_ratios,l3_ratios,l3_energys,dram_energys,total_energys = process_score(pres,bench_time,l2_accesses,l2_hits,pf_useds,pf_unuseds,pf_misseds,dram_reads,dram_writes,l3_accesses,meta_access)
take_picture(pres,l2_speedups,accuracys,coverages,l2_hit_rates,dram_ratios,l3_ratios,l3_energys,dram_energys,total_energys)


             
            

