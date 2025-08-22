import os
import re
import shutil

path = os.getcwd()
gem5_path = os.path.dirname(path)
spec_path = gem5_path + 'spec06_riscv'
bench_path = spec_path + '/benchspec/CPU2006'
simpoints_path = gem5_path + '/riscv_simpoints'
if not os.path.exists(simpoints_path):
  os.mkdir(simpoints_path)

def change(start,end,new,path):
  with open(path,'r') as file:
    run_config = file.read()   
  start_data = run_config.find(str(start))
  end_data = run_config.find(str(end))
  new_data = ''
  new_data = run_config[:start_data]
  new_data += str(new)
  new_data += run_config[end_data:]
  with open(path,'w') as file:
    file.write(new_data)


checkpoints = ['gobmk_13x13','bzip2_program','bzip2_chicken','leslie3d','sjeng']
checkpoints += ['mcf','hmmer_retro','lbm','gcc_166','perlbench_diffmail','h264ref_sss']
checkpoints += ['gcc_200','gobmk_score2','gcc_typeck','povray','sphinx3','soplex_pds']
checkpoints += ['perlbench_splitmail','bwaves','gobmk_nngs','soplex_ref','omnet']
checkpoints += ['gcc_expr2','milc','h264ref_foreman_main','calculix','bzip2_html']
checkpoints += ['perlbench_checkspam','gcc_s04','zeusmp','gcc_g23','xalancbmk']
checkpoints += ['astar_rivers','bzip2_liberty','gromacs','bzip2_combined','tonto']
checkpoints += ['gobmk_trevorc','hmmer_nph3','GemsFDTD','dealII','gcc_scilab']
checkpoints += ['gcc_cpdecl','bzip2_source','namd','gobmk_trevord','cactusADM']
checkpoints += ['libquantum','h264ref_foreman-baseline','astar_biglakes','gcc_expr']
checkpoints += ['gamess_cytosine','gamess_gradient','gamess_triazolium']

benchs = os.listdir(bench_path)


for checkpoint in checkpoints:
    print(checkpoint)
    store_bench_path = path + f'/{checkpoint}'
    bench = checkpoint.split('_')[0] if '_' in checkpoint else checkpoint
    print(bench)
    
    items = os.listdir(bench_path)
    bench_items = []
    for item in items:
      item_path = bench_path + f'/{item}'
      if os.path.isdir(item_path):
        if bench in item:
          bench_items.append(item)
          break
          
    for bench_item in bench_items:      
      print(bench_item)
      print('\n')

      run_path = bench_path + f'/{bench_item}/run/run_base_ref_riscv.0000'
      shutil.copytree(run_path,store_bench_path)

      file1_path = path + '/riscv_se_simpoints.py'
      store_file1_path = simpoints_path + '/riscv_se_simpoints.py'
      shutil.copy(file1_path,store_file1_path)




