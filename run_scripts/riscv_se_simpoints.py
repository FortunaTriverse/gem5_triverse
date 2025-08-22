import os
import builtins
import argparse
import subprocess
import m5
from m5.objects import (
    System, SrcClockDomain, VoltageDomain,
    Cache, SystemXBar, L2XBar, MemCtrl, AddrRange, DDR3_1600_8x8,
    AtomicSimpleCPU, O3CPU, SEWorkload, Process, Root)


def print(*args, **kwargs):
    msg = ' '.join(str(arg) for arg in args)
    builtins.print('\033[93m' + msg + '\033[0m', **kwargs)


# Parse argument
parser = argparse.ArgumentParser()
parser.add_argument('action', choices=[
    'create_by_fixed_ticks',
    'create_by_fixed_insts',
    'restore',
    'restore_and_switch',
    'switch_repeatedly',
    'simpoint_profile',
    'take_simpoint_checkpoints',
    'restore_simpoint'])

parser.add_argument("--benchmark",type=str)

parser.add_argument(
    "--binary_path",
    action="store",
    type=str,
    default=None,
    help="base names for --take-checkpoint and --checkpoint-restore",
)

parser.add_argument(
    "--binary_cmd",
    action="store",
    type=str,
    default=None,
    help="base names for --take-checkpoint and --checkpoint-restore",
)
args = parser.parse_args()
action = args.action
interlnal_benchmark = args.benchmark
print(interlnal_benchmark)

# Compile helloworld executable

thispath = os.path.dirname(os.path.realpath(__file__))


#######################################
#          Cache Definitions          #
#######################################


class L1Cache(Cache):
    assoc = 4
    tag_latency = 1
    data_latency = 1
    response_latency = 1
    mshrs = 4
    tgts_per_mshr = 20


class L1ICache(L1Cache):
    size = '64kB'


class L1DCache(L1Cache):
    size = '64kB'


class L2Cache(Cache):
    size = '512kB'
    assoc = 8
    tag_latency = 10
    data_latency = 10
    response_latency = 10
    mshrs = 20
    tgts_per_mshr = 12


class PageTableWalkerCache(Cache):
    assoc = 2
    tag_latency = 1
    data_latency = 1
    response_latency = 1
    mshrs = 10
    size = '1kB'
    tgts_per_mshr = 12


#######################################
#         System Configuration        #
#######################################

system = System()

system.clk_domain = SrcClockDomain()
system.clk_domain.clock = '2GHz'
system.clk_domain.voltage_domain = VoltageDomain()

system.mem_mode = 'atomic'
system.mem_ranges = [AddrRange('4GB')]

# Use AtomicSimpleCPU initially (we will switch to O3CPU later)
system.cpu = AtomicSimpleCPU()

system.cpu.icache = L1ICache()
system.cpu.dcache = L1DCache()

system.cpu.icache.cpu_side = system.cpu.icache_port
system.cpu.dcache.cpu_side = system.cpu.dcache_port

# Note: TLB walker caches are necessary to RISC-V
system.cpu.itb_walker_cache = PageTableWalkerCache()
system.cpu.dtb_walker_cache = PageTableWalkerCache()
system.cpu.mmu.connectWalkerPorts(
    system.cpu.itb_walker_cache.cpu_side,
    system.cpu.dtb_walker_cache.cpu_side)

system.l2bus = L2XBar()

system.cpu.icache.mem_side = system.l2bus.cpu_side_ports
system.cpu.dcache.mem_side = system.l2bus.cpu_side_ports

system.cpu.itb_walker_cache.mem_side = system.l2bus.cpu_side_ports
system.cpu.dtb_walker_cache.mem_side = system.l2bus.cpu_side_ports

system.l2cache = L2Cache()
system.l2cache.cpu_side = system.l2bus.mem_side_ports

system.membus = SystemXBar()

system.l2cache.mem_side = system.membus.cpu_side_ports

system.cpu.createInterruptController()

system.system_port = system.membus.cpu_side_ports

system.mem_ctrl = MemCtrl()
system.mem_ctrl.dram = DDR3_1600_8x8()
system.mem_ctrl.dram.range = system.mem_ranges[0]
system.mem_ctrl.port = system.membus.mem_side_ports


process = Process()
#astar
if interlnal_benchmark == 'astar_biglakes':
  binary = os.path.join("./astar_base.riscv")
  process.cmd = [binary] + ['BigLakes2048.cfg']

elif interlnal_benchmark == 'astar_rivers':
  binary = os.path.join('./astar_base.riscv')
  process.cmd = [binary] + ['rivers.cfg']

#bwaves
elif interlnal_benchmark == 'bwaves':
  binary = os.path.join('./bwaves_base.riscv')
  process.cmd = [binary]

#bzip2
elif interlnal_benchmark == 'bzip2_chicken':
  binary = os.path.join('./bzip2_base.riscv')
  process.cmd = [binary] + ['chicken.jpg', '30']

elif interlnal_benchmark == 'bzip2_combined':
  binary = os.path.join('./bzip2_base.riscv')
  process.cmd = [binary] + ['input.combined', '200']

elif interlnal_benchmark == 'bzip2_html':
  binary = os.path.join('./bzip2_base.riscv')
  process.cmd = [binary] + ['text.html', '280']

elif interlnal_benchmark == 'bzip2_liberty':
  binary = os.path.join('./bzip2_base.riscv')
  process.cmd = [binary] + ['liberty.jpg', '30']


elif interlnal_benchmark == 'bzip2_program':
  binary = os.path.join('./bzip2_base.riscv')
  process.cmd = [binary] + ['input.program', '280']


elif interlnal_benchmark == 'bzip2_source':
  binary = os.path.join('./bzip2_base.riscv')
  process.cmd = [binary] + ['input.source', '280']


#cactusADM
elif interlnal_benchmark == 'cactusADM':
  binary = os.path.join('./cactusADM_base.riscv')
  process.cmd = [binary] + ['benchADM.par']


#calculix
elif interlnal_benchmark == 'calculix':
  binary = os.path.join('./calculix_base.riscv')
  process.cmd = [binary] + ['-i', 'hyperviscoplastic']


#dealII
elif interlnal_benchmark == 'dealII':
  binary = os.path.join('./dealII_base.riscv')
  process.cmd = [binary]


#gcc
elif interlnal_benchmark == 'gcc_166':
  binary = os.path.join('./gcc_base.riscv')
  process.cmd = [binary] + ['166.in', '-o', '166.s']

elif interlnal_benchmark == 'gcc_200':
  binary = os.path.join('./gcc_base.riscv')
  process.cmd = [binary] + ['200.in', '-o', '200.s']

elif interlnal_benchmark == 'gcc_cpdecl':
  binary = os.path.join('./gcc_base.riscv')
  process.cmd = [binary] + ['cp-decl.in', '-o', 'cp-decl.s']


elif interlnal_benchmark == 'gcc_expr':
  binary = os.path.join('./gcc_base.riscv')
  process.cmd = [binary] + ['expr.in', '-o', 'expr.s']


elif interlnal_benchmark == 'gcc_expr2':
  binary = os.path.join('./gcc_base.riscv')
  process.cmd = [binary] + ['expr2.in', '-o', 'expr2.s']


elif interlnal_benchmark == 'gcc_g23':
  binary = os.path.join('./gcc_base.riscv')
  process.cmd = [binary] + ['g23.in', '-o', 'g23.s']


elif interlnal_benchmark == 'gcc_s04':
  binary = os.path.join('./gcc_base.riscv')
  process.cmd = [binary] + ['s04.in', '-o', 's04.s']


elif interlnal_benchmark == 'gcc_scilab':
  binary = os.path.join('./gcc_base.riscv')
  process.cmd = [binary] + ['scilab.in', '-o', 'scilab.s']


elif interlnal_benchmark == 'gcc_typeck':
  binary = os.path.join('./gcc_base.riscv')
  process.cmd = [binary] + ['c-typeck.in', '-o', 'c-typeck.s']


#GemsFDTD
elif interlnal_benchmark == 'GemsFDTD':
  binary = os.path.join('./GemsFDTD_base.riscv')
  process.cmd = [binary]


#gobmk
elif interlnal_benchmark == 'gobmk_13x13':
  binary = os.path.join('./gobmk_base.riscv')
  process.cmd = [binary] + ['--quiet','--mode', 'gtp']
  process.input = '13x13.tst'


elif interlnal_benchmark == 'gobmk_nngs':
  binary = os.path.join('./gobmk_base.riscv')
  process.cmd = [binary] + ['--quiet','--mode', 'gtp']
  process.input = 'nngs.tst'


elif interlnal_benchmark == 'gobmk_score2':
  binary = os.path.join('./gobmk_base.riscv')
  process.cmd = [binary] + ['--quiet','--mode', 'gtp']
  process.input = 'score2.tst'


elif interlnal_benchmark == 'gobmk_trevorc':
  binary = os.path.join('./gobmk_base.riscv')
  system.workload = SEWorkload.init_compatible(binary)
  process.cmd = [binary] + ['--quiet','--mode', 'gtp']
  process.input = 'trevorc.tst'

elif interlnal_benchmark == 'gobmk_trevord':
  binary = os.path.join('./gobmk_base.riscv')
  process.cmd = [binary] + ['--quiet','--mode', 'gtp']
  process.input = 'trevord.tst'


#gromacs
elif interlnal_benchmark == 'gromacs':
  binary = os.path.join('./gromacs_base.riscv')
  process.cmd = [binary] + ['-silent','-deffnm', 'gromacs', '-nice','0']


#h264ref
elif interlnal_benchmark == 'h264ref_foreman-baseline':
  binary = os.path.join('./h264ref_base.riscv')
  process.cmd = [binary] + ['-d', 'foreman_ref_encoder_baseline.cfg']

elif interlnal_benchmark == 'h264ref_foreman_main':
  binary = os.path.join('./h264ref_base.riscv')
  process.cmd = [binary] + ['-d', 'foreman_ref_encoder_main.cfg']


elif interlnal_benchmark == 'h264ref_sss':
  binary = os.path.join('./h264ref_base.riscv')
  process.cmd = [binary] + ['-d', 'sss_encoder_main.cfg']


#hmmer
elif interlnal_benchmark == 'hmmer_nph3':
  binary = os.path.join('./hmmer_base.riscv')
  process.cmd = [binary] + ['nph3.hmm', 'swiss41']


elif interlnal_benchmark == 'hmmer_retro':
  binary = os.path.join('./hmmer_base.riscv')
  process.cmd = [binary] + ['--fixed', '0', '--mean', '500', '--num', '500000', '--sd', '350', '--seed', '0', 'retro.hmm']


#lbm
elif interlnal_benchmark == 'lbm':
  binary = os.path.join('./lbm_base.riscv')
  process.cmd = [binary] + ['300', 'reference.dat', '0', '0', '100_100_130_ldc.of']

#leslie3d
elif interlnal_benchmark == 'leslie3d':
  binary = os.path.join('./leslie3d_base.riscv')
  process.cmd = [binary]
  process.input = 'leslie3d.in'


#libquantum
elif interlnal_benchmark == 'libquantum':
  binary = os.path.join('./libquantum_base.riscv')
  process.cmd = [binary] + ['1397','8']


#mcf
elif interlnal_benchmark == 'mcf':
  binary = os.path.join('./mcf_base.riscv')
  process.cmd = [binary] + ['inp.in']

#milc
elif interlnal_benchmark == 'milc':
  binary = os.path.join('./milc_base.riscv')
  process.cmd = [binary]
  process.input = 'su3imp.in'


#namd
elif interlnal_benchmark == 'namd':
  binary = os.path.join('./namd_base.riscv')
  process.cmd = [binary] + ['--input', 'namd.input', '--output', 'namd.out', '--iterations', '38']

#omnet
elif interlnal_benchmark == 'omnet':
  binary = os.path.join('./omnetpp_base.riscv')
  process.cmd = [binary] + ['omnetpp.ini']


#perlbench
elif interlnal_benchmark == 'perlbench_checkspam':
  binary = os.path.join('./perlbench_base.riscv')
  process.cmd = [binary] + ['-I./lib', 'checkspam.pl', '2500', '5', '25', '11', '150', '1', '1', '1', '1']


elif interlnal_benchmark == 'perlbench_diffmail':
  binary = os.path.join('./perlbench_base.riscv')
  process.cmd = [binary] + ['-I./lib', 'diffmail.pl', '4', '800', '10', '17', '19', '300']


elif interlnal_benchmark == 'perlbench_splitmail':
  binary = os.path.join('./perlbench_base.riscv')
  process.cmd = [binary] + ['-I./lib', 'splitmail.pl', '1600', '12', '26', '16', '4500']


#povray
elif interlnal_benchmark == 'povray':
  binary = os.path.join('./povray_base.riscv')
  process.cmd = [binary] + ['SPEC-benchmark-ref.ini']

#sjeng
elif interlnal_benchmark == 'sjeng':
  binary = os.path.join('./sjeng_base.riscv')
  process.cmd = [binary] + ['ref.txt']

#soplex
elif interlnal_benchmark == 'soplex_pds':
  binary = os.path.join('./soplex_base.riscv')
  process.cmd = [binary] + ['-m45000', 'pds-50.mps']

elif interlnal_benchmark == 'soplex_ref':
  binary = os.path.join('./soplex_base.riscv')
  process.cmd = [binary] + ['-m3500', 'ref.mps']

#sphinx3
elif interlnal_benchmark == 'sphinx3':
  binary = os.path.join('./sphinx_livepretend_base.riscv')
  process.cmd = [binary] + ['ctlfile', '.', 'args.an4']

#tonto
elif interlnal_benchmark == 'tonto':
  binary = os.path.join('./tonto_base.riscv')
  process.cmd = [binary]


#Xalan
elif interlnal_benchmark == 'xalancbmk':
  binary = os.path.join('./Xalan_base.riscv')
  process.cmd = [binary] + ['t5.xml','xalanc.xsl']

#zeusmp
elif interlnal_benchmark == 'zeusmp':
  binary = os.path.join('./zeusmp_base.riscv')
  process.cmd = [binary]

#gamess
elif interlnal_benchmark == 'gamess_cytosine':
  binary = os.path.join('./gamess_base.riscv')
  process.cmd = [binary] + ['< cytosine.2.config']

elif interlnal_benchmark == 'gamess_gradient':
  binary = os.path.join('./gamess_base.riscv')
  process.cmd = [binary] + ['< h2ocu2+.gradient.config']

elif interlnal_benchmark == 'gamess_triazolium':
  binary = os.path.join('./gamess_base.riscv')
  process.cmd = [binary] + ['< h2ocu2+.gradient.config']

#wrf
elif interlnal_benchmark == 'wrf':
  binary = os.path.join('./wrf_base.riscv')


else:
  print('\033[31m###########\nerror input benchmark name\n###########\n\033[0m')

system.workload = SEWorkload.init_compatible(binary)
system.cpu.workload = process
system.cpu.createThreads()

#######################################
#         System Instantiation        #
#######################################

# Before system instantiation, add an O3CPU as switch_cpu to system if we
# will switch. It should copy key settings from the original cpu
if 'switch' in action:
    switch_cpu = O3CPU(switched_out=True, cpu_id=0)
    switch_cpu.workload = system.cpu.workload
    switch_cpu.clk_domain = system.cpu.clk_domain
    switch_cpu.progress_interval = system.cpu.progress_interval
    switch_cpu.isa = system.cpu.isa

    switch_cpu.createThreads()
    system.switch_cpu = switch_cpu

# Set ckpt_dir if we are restoring from some checkpoint
ckpt_dir = None
m5out = m5.options.outdir
if 'restore' in action:
    ckpt_dir = os.path.join(m5out, 'ckpt.001')
    if not os.path.exists(ckpt_dir):
        print("You haven't create any checkpoint yet! Abort")
        exit(-1)

simpoint_interval = 5000000

# Add SimPoint probe to cpu if we will profile for SimPoint
if action == 'simpoint_profile':
    system.cpu.addSimPointProbe(simpoint_interval)

# Add breakpoints if we will create SimPoint checkpoints
if action == 'take_simpoint_checkpoints':
    try:
        with open('m5out/simpoints.txt') as f:
            ss = f.readlines()
        with open('m5out/weights.txt') as f:
            ws = f.readlines()
    except FileNotFoundError:
        print("Either 'm5out/simpoints.txt' or 'm5out/weights.txt' not found")
        exit(-1)

    # Read simpoints and weights
    print('Read simpoints and weights')
    simpoints = []
    for sl, wl in zip(ss, ws):
        s = int(sl.split()[0])
        w = float(wl.split()[0])
        simpoints.append((s, w))

    # Compute start insts
    simpoints.sort()
    simpoint_start_insts = []
    warmup_length = 50000000
    for s, _ in simpoints:
        insts = s * simpoint_interval - warmup_length
        if insts <0:
          print(f'warn:insts={insts}<0,ID={s}')
          continue
        simpoint_start_insts.append(insts)
    system.cpu.simpoint_start_insts = simpoint_start_insts

# Add breakpoints if we will restore SimPoint checkpoints
if action == 'restore_simpoint':
    system.cpu.simpoint_start_insts = [simpoint_interval]

# Instantiate system
root = Root(full_system=False, system=system)
if ckpt_dir is None:
    print('Instantiate')
    m5.instantiate()
else:
    print('Restore checkpoint', repr(ckpt_dir))
    m5.instantiate(ckpt_dir)


#######################################
#           Real Simulation           #
#######################################

if action == 'create_by_fixed_ticks':
    interval_ticks = 20000000
    i = 1

    while True:
        print('Simulate for %d ticks' % interval_ticks)
        exit_event = m5.simulate(interval_ticks)
        if exit_event.getCause() != 'simulate() limit reached':
            break

        print('Pause @ tick', m5.curTick())
        print('Create checkpoint', i)
        m5.checkpoint(os.path.join(m5out, 'ckpt.%03d' % i))
        i += 1

elif action == 'create_by_fixed_insts':
    interval_insts = 20000
    tid = 0  # thread id, should be 0 since we have only one thread
    event_str = 'inst stop'  # any unique string is fine
    i = 1

    while True:
        print('Simulate for %d insts' % interval_insts)
        system.cpu.scheduleInstStop(tid, interval_insts, event_str)
        exit_event = m5.simulate()
        if exit_event.getCause() != event_str:
            break

        print('Pause @ tick', m5.curTick())
        print('Create checkpoint', i)
        m5.checkpoint(os.path.join(m5out, 'ckpt.%03d' % i))
        i += 1

elif action == 'restore':
    print('Resume simulation')
    exit_event = m5.simulate()

elif action == 'restore_and_switch':
    print('Warmup for 10000 ticks')
    m5.simulate(10000)

    print('Switch @ tick', m5.curTick())
    switch_cpu_list = [(system.cpu, system.switch_cpu)]
    m5.switchCpus(system, switch_cpu_list)

    print('Simulate on switch_cpu')
    exit_event = m5.simulate()

elif action == 'switch_repeatedly':
    interval_insts = 10000
    switch_cpu_list = [(system.cpu, system.switch_cpu)]
    tid = 0
    event_str = 'inst stop'

    while True:
        print('Simulate for %d insts' % interval_insts)
        curr_cpu = switch_cpu_list[0][0]
        curr_cpu.scheduleInstStop(tid, interval_insts, event_str)
        exit_event = m5.simulate()
        if exit_event.getCause() != event_str:
            break

        print('Pause @ tick', m5.curTick())
        print('Switch %s -> %s' % (switch_cpu_list[0]))
        m5.switchCpus(system, switch_cpu_list)

        # Reverse each CPU pair in switch_cpu_list
        switch_cpu_list = [(p[1], p[0]) for p in switch_cpu_list]

elif action == 'simpoint_profile':
    print('Simulate and profile for SimPoint')
    exit_event = m5.simulate()

elif action == 'take_simpoint_checkpoints':
    for i, (s, w) in enumerate(simpoints, 1):
        print('Simulate until next simpoint entry')
        exit_event = m5.simulate()

        if exit_event.getCause() == 'simpoint starting point found':
            print('Take simpoint %d @ tick %d' % (s, m5.curTick()))
            ckpt_dir = os.path.join(m5out, 'ckpt.%03d' % i)
            m5.checkpoint(ckpt_dir)
            with open(os.path.join(ckpt_dir, 'weight.txt'), 'w') as f:
                f.write(str(w))

    print('Simulate to end')
    exit_event = m5.simulate()

elif action == 'restore_simpoint':
    print('Simulate simpoint for %d insts' % simpoint_interval)
    exit_event = m5.simulate()

print('Exiting @ tick %d because %s' % (m5.curTick(), exit_event.getCause()))
