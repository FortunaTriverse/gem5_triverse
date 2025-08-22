import sys
import os
import shutil

core_numbers = int(sys.argv[1])
benchmark = sys.argv[2]

path = os.getcwd()
home_path = os.path.dirname(path)
check_path = home_path + f'/Checkpoints'
checkpoint_path = check_path + f'/{core_numbers}_core'

if not os.path.exists(check_path):
  os.mkdir(check_path)

if not os.path.exists(checkpoint_path):
  os.mkdir(checkpoint_path)

##### create the rcS file
print(f"input benchmark is {benchmark} with {core_numbers} of core")

#get command and bench name
if benchmark == "astar_biglakes":
    COMMAND="./astar_base.amd64-m64-gcc42-nn BigLakes2048.cfg"
    BENCH="473.astar"
elif benchmark == "astar_rivers":
    COMMAND="./astar_base.amd64-m64-gcc42-nn rivers.cfg"
    BENCH="473.astar"
elif benchmark == "bwaves":
    COMMAND="./bwaves_base.amd64-m64-gcc42-nn"
    BENCH="410.bwaves"
elif benchmark == "bzip2_chicken":
    COMMAND="./bzip2_base.amd64-m64-gcc42-nn chicken.jpg 30"
    BENCH="401.bzip2"
elif benchmark == "bzip2_combined":
    COMMAND="./bzip2_base.amd64-m64-gcc42-nn input.combined 200"
    BENCH="401.bzip2"
elif benchmark == "bzip2_html":
    COMMAND="./bzip2_base.amd64-m64-gcc42-nn text.html 280"
    BENCH="401.bzip2"
elif benchmark == "bzip2_liberty":
    COMMAND="./bzip2_base.amd64-m64-gcc42-nn liberty.jpg 30"
    BENCH="401.bzip2"
elif benchmark == "bzip2_program":
    COMMAND="./bzip2_base.amd64-m64-gcc42-nn input.program 280"
    BENCH="401.bzip2"
elif benchmark == "bzip2_source":
    COMMAND="./bzip2_base.amd64-m64-gcc42-nn input.source 280"
    BENCH="401.bzip2"
elif benchmark == "cactusADM":
    COMMAND="./cactusADM_base.amd64-m64-gcc42-nn benchADM.par"
    BENCH="436.cactusADM"
elif benchmark == "calculix":
    COMMAND="./calculix_base.amd64-m64-gcc42-nn -i hyperviscoplastic"
    BENCH="454.calculix"
elif benchmark == "dealII":
    COMMAND="./dealII_base.amd64-m64-gcc42-nn"
    BENCH="447.dealII"
elif benchmark == "gamess_cytosine":
    COMMAND="./gamess_base.amd64-m64-gcc42-nn < cytosine.2.config"
    BENCH="416.gamess"
elif benchmark == "gamess_gradient":
    COMMAND="./gamess_base.amd64-m64-gcc42-nn < h2ocu2+.gradient.config"
    BENCH="416.gamess"
elif benchmark == "gamess_triazolium":
    COMMAND="./gamess_base.amd64-m64-gcc42-nn < triazolium.config"
    BENCH="416.gamess"
elif benchmark == "gcc_166":
    COMMAND="./gcc_base.amd64-m64-gcc42-nn 166.in -o 166.s"
    BENCH="403.gcc"
elif benchmark == "gcc_200":
    COMMAND="./gcc_base.amd64-m64-gcc42-nn 200.in -o 200.s"
    BENCH="403.gcc"
elif benchmark == "gcc_cpdecl":
    COMMAND="./gcc_base.amd64-m64-gcc42-nn cp-decl.in -o cp-decl.s"
    BENCH="403.gcc"
elif benchmark == "gcc_expr":
    COMMAND="./gcc_base.amd64-m64-gcc42-nn expr.in -o expr.s"
    BENCH="403.gcc"
elif benchmark == "gcc_expr2":
    COMMAND="./gcc_base.amd64-m64-gcc42-nn expr2.in -o expr2.s"
    BENCH="403.gcc"
elif benchmark == "gcc_g23":
    COMMAND="./gcc_base.amd64-m64-gcc42-nn g23.in -o g23.s"
    BENCH="403.gcc"
elif benchmark == "gcc_s04":
    COMMAND="./gcc_base.amd64-m64-gcc42-nn s04.in -o s04.s"
    BENCH="403.gcc"
elif benchmark == "gcc_scilab":
    COMMAND="./gcc_base.amd64-m64-gcc42-nn scilab.in -o scilab.s"
    BENCH="403.gcc"
elif benchmark == "gcc_typeck":
    COMMAND="./gcc_base.amd64-m64-gcc42-nn c-typeck.in -o c-typeck.s"
    BENCH="403.gcc"
elif benchmark == "GemsFDTD":
    COMMAND="./GemsFDTD_base.amd64-m64-gcc42-nn"
    BENCH="459.GemsFDTD"
elif benchmark == "gobmk_13x13":
    COMMAND="./gobmk_base.amd64-m64-gcc42-nn --quiet --mode gtp < 13x13.tst"
    BENCH="403.gcc"
elif benchmark == "gobmk_nngs":
    COMMAND="./gobmk_base.amd64-m64-gcc42-nn --quiet --mode gtp < nngs.tst"
    BENCH="445.gobmk"
elif benchmark == "gobmk_score2":
    COMMAND="./gobmk_base.amd64-m64-gcc42-nn --quiet --mode gtp < score2.tst"
    BENCH="445.gobmk"
elif benchmark == "gobmk_trevorc":
    COMMAND="./gobmk_base.amd64-m64-gcc42-nn --quiet --mode gtp < trevorc.tst"
    BENCH="445.gobmk"
elif benchmark == "gobmk_trevord":
    COMMAND="./gobmk_base.amd64-m64-gcc42-nn --quiet --mode gtp < trevord.tst"
    BENCH="445.gobmk"
elif benchmark == "gromacs":
    COMMAND="./gromacs_base.amd64-m64-gcc42-nn -silent -deffnm gromacs.tpr -nice 0"
    BENCH="435.gromacs"
elif benchmark == "h264ref_foreman_baseline":
    COMMAND="./h264ref_base.amd64-m64-gcc42-nn -d foreman_ref_encoder_baseline.cfg"
    BENCH="464.h264ref"
elif benchmark == "h264ref_foreman_main":
    COMMAND="./h264ref_base.amd64-m64-gcc42-nn -d foreman_ref_encoder_main.cfg"
    BENCH="464.h264ref"
elif benchmark == "h264ref_sss":
    COMMAND="./h264ref_base.amd64-m64-gcc42-nn -d sss_encoder_main.cfg"
    BENCH="464.h264ref"
elif benchmark == "hmmer_nph3":
    COMMAND="./hmmer_base.amd64-m64-gcc42-nn nph3.hmm swiss41"
    BENCH="456.hmmer"
elif benchmark == "hmmer_retro":
    COMMAND="./hmmer_base.amd64-m64-gcc42-nn --fixed 0 --mean 500 --num 500000 --sd 350"
    BENCH="456.hmmer"
elif benchmark == "lbm":
    COMMAND="./lbm_base.amd64-m64-gcc42-nn 3000 reference.dat 0 0 100_100_130_ldc.of"
    BENCH="470.lbm"
elif benchmark == "leslie3d":
    COMMAND="./leslie3d_base.amd64-m64-gcc42-nn < leslie3d.in"
    BENCH="437.leslie3d"
elif benchmark == "libquantum":
    COMMAND="./libquantum_base.amd64-m64-gcc42-nn 1397 8"
    BENCH="462.libquantum"
elif benchmark == "mcf":
    COMMAND="./mcf_base.amd64-m64-gcc42-nn inp.in"
    BENCH="429.mcf"
elif benchmark == "milc":
    COMMAND="./milc_base.amd64-m64-gcc42-nn < su3imp.in"
    BENCH="433.milc"
elif benchmark == "namd":
    COMMAND="./namd_base.amd64-m64-gcc42-nn  --input namd.input --iterations 38 --output namd.out"
    BENCH="444.namd"
elif benchmark == "omnet":
    COMMAND="./omnetpp_base.amd64-m64-gcc42-nn omnetpp.ini"
    BENCH="471.omnetpp"
elif benchmark == "perlbench_checkspam":
    COMMAND="./perlbench_base.amd64-m64-gcc42-nn -I./lib checkspam.pl 2500 5 25 11 150 1 1 1 1"
    BENCH="400.perlbench"
elif benchmark == "perlbench_diffmail":
    COMMAND="./perlbench_base.amd64-m64-gcc42-nn -I./lib diffmail.pl 4 800 10 17 19 300"
    BENCH="400.perlbench"
elif benchmark == "perlbench_splitmail":
    COMMAND="./perlbench_base.amd64-m64-gcc42-nn -I./lib splitmail.pl 1600 12 26 16 4500"
    BENCH="400.perlbench"
elif benchmark == "povray":
    COMMAND="./povray_base.amd64-m64-gcc42-nn SPEC-benchmark-ref.ini"
    BENCH="453.povray"
elif benchmark == "sjeng":
    COMMAND="./sjeng_base.amd64-m64-gcc42-nn ref.txt "
    BENCH="458.sjeng"
elif benchmark == "soplex_pds":
    COMMAND="./soplex_base.amd64-m64-gcc42-nn -s1 -e -m45000 pds-50.mps"
    BENCH="450.soplex"
elif benchmark == "soplex_ref":
    COMMAND="./soplex_base.amd64-m64-gcc42-nn -m3500 ref.mps"
    BENCH="450.soplex"
elif benchmark == "sphinx3":
    COMMAND="./sphinx_livepretend_base.amd64-m64-gcc42-nn ctlfile . args.an4"
    BENCH="482.sphinx3"
elif benchmark == "tonto":
    COMMAND="./tonto_base.amd64-m64-gcc42-nn"
    BENCH="465.tonto"
elif benchmark == "wrf":
    COMMAND="./wrf_base.amd64-m64-gcc42-nn"
    BENCH="481.wrf"
elif benchmark == "xalan":
    COMMAND="./Xalan_base.amd64-m64-gcc42-nn  -v t5.xml xalanc.xsl"
    BENCH="483.xalancbmk"
elif benchmark == "zeusmp":
    COMMAND="./zeusmp_base.amd64-m64-gcc42-nn"
    BENCH="434.zeusmp"
else:
    print("input wrong args")

print(f'{BENCH} command is {COMMAND}')

bench_path = checkpoint_path + f'/{benchmark}'
if not os.path.exists(bench_path):
    os.mkdir(bench_path)
else:
    shutil.rmtree(bench_path)
    os.mkdir(bench_path)

rcS_path = bench_path + '/run.rcS'
f = open(rcS_path,'w')
data = r'''#!/bin/sh

# Checkpoint the first execution
echo "Checkpointing simulation..."
/sbin/m5 checkpoint

'''
for i in range(core_numbers):
    j = i + 1
    data += rf'  cd /home/gem5/SPEC/benchspec/CPU2006/{BENCH}/run/run_base_ref_amd64-m64-gcc42-nn.000{i}'
    data += '\n'
    data += f'  echo \"{benchmark} {j} time...\"\n'
    data += rf'  taskset {j} {COMMAND} &'
    data += '\n'

data += '\nwait\necho "done"\n'
data += r'/sbin/m5 exit'
f.write(data)
f.close()

###### run 
os.system(f"./create_checkpoints.sh {core_numbers} {benchmark}")
