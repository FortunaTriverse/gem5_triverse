# Copyright (c) 2012-2013, 2015-2016 ARM Limited
# Copyright (c) 2020 Barkhausen Institut
# All rights reserved
#
# The license below extends only to copyright in the software and shall
# not be construed as granting a license to any other intellectual
# property including but not limited to intellectual property relating
# to a hardware implementation of the functionality of the software
# licensed hereunder.  You may use the software subject to the license
# terms below provided that you ensure that this notice is replicated
# unmodified and in its entirety in all distributions of the software,
# modified or unmodified, in source code or in binary form.
#
# Copyright (c) 2010 Advanced Micro Devices, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met: redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer;
# redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution;
# neither the name of the copyright holders nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

# Configure the M5 cache hierarchy config in one place
#

import m5
from m5.objects import *
from gem5.isas import ISA
from gem5.runtime import get_runtime_isa

from common.Caches import *
from common import ObjectList


def _get_hwp(hwp_option):
    if hwp_option == None:
        return NULL

    hwpClass = ObjectList.hwp_list.get(hwp_option)
    return hwpClass()


def _get_cache_opts(level, options):
    opts = {}

    size_attr = f"{level}_size"
    if hasattr(options, size_attr):
        opts["size"] = getattr(options, size_attr)

    assoc_attr = f"{level}_assoc"
    if hasattr(options, assoc_attr):
        opts["assoc"] = getattr(options, assoc_attr)

    prefetcher_attr = f"{level}_hwp_type"
    if hasattr(options, prefetcher_attr):
        opts["prefetcher"] = _get_hwp(getattr(options, prefetcher_attr))

    return opts


def config_cache(options, system):
    if options.external_memory_system and (options.caches or options.l2cache):
        print("External caches and internal caches are exclusive options.\n")
        sys.exit(1)

    if options.external_memory_system:
        ExternalCache = ExternalCacheFactory(options.external_memory_system)

    if options.cpu_type == "O3_ARM_v7a_3":
        try:
            import cores.arm.O3_ARM_v7a as core
        except:
            print("O3_ARM_v7a_3 is unavailable. Did you compile the O3 model?")
            sys.exit(1)

        dcache_class, icache_class, l2_cache_class, walk_cache_class = (
            core.O3_ARM_v7a_DCache,
            core.O3_ARM_v7a_ICache,
            core.O3_ARM_v7aL2,
            None,
        )
    elif options.cpu_type == "HPI":
        try:
            import cores.arm.HPI as core
        except:
            print("HPI is unavailable.")
            sys.exit(1)

        dcache_class, icache_class, l2_cache_class, walk_cache_class = (
            core.HPI_DCache,
            core.HPI_ICache,
            core.HPI_L2,
            None,
        )
    elif options.cpu_type == "A510":
        try:
            import cores.arm.A510 as core
        except:
            print("A510 is unavailable.")
            sys.exit(1)

        dcache_class, icache_class, l2_cache_class, walk_cache_class = (
            core.A510_DCache,
            core.A510_ICache,
            core.A510_L2,
            None,
        )
    # elif options.cpu_type == "X2":
    #    try:
    #        import cores.arm.X2 as core
    #    except:
    #        print("X2 is unavailable.")
    #        sys.exit(1)

    #   dcache_class, icache_class, l2_cache_class, walk_cache_class = (
    #       core.X2_DCache,
    #       core.X2_ICache,
    #       core.X2_L2,
    #       None,
    #   )
    else:
        dcache_class, icache_class, l2_cache_class, walk_cache_class = (
            L1_DCache,
            L1_ICache,
            L2Cache,
            None,
        )

        if get_runtime_isa() in [ISA.X86, ISA.RISCV]:
            walk_cache_class = PageTableWalkerCache
    # For L3
    if options.pl2sl3cache:
        l3_cache_class = L3Cache

    # Set the cache line size of the system
    system.cache_line_size = options.cacheline_size

    # If elastic trace generation is enabled, make sure the memory system is
    # minimal so that compute delays do not include memory access latencies.
    # Configure the compulsory L1 caches for the O3CPU, do not configure
    # any more caches.
    if options.l2cache and options.elastic_trace_en:
        fatal("When elastic trace is enabled, do not configure L2 caches.")

    if options.l2cache:
        # Provide a clock for the L2 and the L1-to-L2 bus here as they
        # are not connected using addTwoLevelCacheHierarchy. Use the
        # same clock as the CPUs.
        system.l2 = l2_cache_class(clk_domain=system.cpu_clk_domain)

        system.tol2bus = L2XBar(clk_domain=system.cpu_clk_domain)
        system.l2.cpu_side = system.tol2bus.mem_side_ports
        system.l2.mem_side = system.membus.cpu_side_ports

    if options.pl2sl3cache:
        # Provide a clock for the L3 and the L2-to-L3 bus here as they
        # are not connected using addTwoLevelCacheHierarchy. Use the
        # same clock as the CPUs.
        system.l3 = l3_cache_class(
            clk_domain=system.cpu_clk_domain, **_get_cache_opts("l3", options)
        )

        # TODO: config for L3 croassbar?
        system.tol3bus = L2XBar(clk_domain=system.cpu_clk_domain)
        system.l3.cpu_side = system.tol3bus.mem_side_ports
        system.l3.mem_side = system.membus.cpu_side_ports

    if options.memchecker:
        system.memchecker = MemChecker()

    for i in range(options.num_cpus):
        if options.caches:
            icache = icache_class(**_get_cache_opts("l1i", options))
            dcache = dcache_class(**_get_cache_opts("l1d", options))

            # If we have a walker cache specified, instantiate two
            # instances here
            if walk_cache_class:
                iwalkcache = walk_cache_class()
                dwalkcache = walk_cache_class()
            else:
                iwalkcache = None
                dwalkcache = None

            if options.memchecker:
                dcache_mon = MemCheckerMonitor(warn_only=True)
                dcache_real = dcache

                # Do not pass the memchecker into the constructor of
                # MemCheckerMonitor, as it would create a copy; we require
                # exactly one MemChecker instance.
                dcache_mon.memchecker = system.memchecker

                # Connect monitor
                dcache_mon.mem_side = dcache.cpu_side

                # Let CPU connect to monitors
                dcache = dcache_mon

            # When connecting the caches, the clock is also inherited
            # from the CPU in question
            system.cpu[i].addPrivateSplitL1Caches(
                icache, dcache, iwalkcache, dwalkcache
            )

            if options.memchecker:
                # The mem_side ports of the caches haven't been connected yet.
                # Make sure connectAllPorts connects the right objects.
                system.cpu[i].dcache = dcache_real
                system.cpu[i].dcache_mon = dcache_mon

        elif options.external_memory_system:
            # These port names are presented to whatever 'external' system
            # gem5 is connecting to.  Its configuration will likely depend
            # on these names.  For simplicity, we would advise configuring
            # it to use this naming scheme; if this isn't possible, change
            # the names below.
            if get_runtime_isa() in [ISA.X86, ISA.ARM, ISA.RISCV]:
                system.cpu[i].addPrivateSplitL1Caches(
                    ExternalCache("cpu%d.icache" % i),
                    ExternalCache("cpu%d.dcache" % i),
                    ExternalCache("cpu%d.itb_walker_cache" % i),
                    ExternalCache("cpu%d.dtb_walker_cache" % i),
                )
            else:
                system.cpu[i].addPrivateSplitL1Caches(
                    ExternalCache("cpu%d.icache" % i),
                    ExternalCache("cpu%d.dcache" % i),
                )
        elif options.pl2sl3cache:
            icache = icache_class()
            dcache = dcache_class()
            if options.triangel:
                l2_cache = l2_cache_class(
                    prefetcher=TriangelPrefetcher(
                        cachetags=system.l3.tags,#To take a partition of for the Markov table.
                        cache_delay=25, #5 cycles more than the L3 cache itself
                        degree=4,
                        address_map_max_ways=8,
                        #The below params assume 1MiB partition max of a 2MiB 16-way cache (So 8 max_ways).
                        #The density is 12 entries per cache line (actual_cache_assoc) unlike Triage's 16
                        #And the rounded version sets everything to a power of two -- with the difference between
                        #actual and rounded based on that ratio between 12 and 16 here.
                        address_map_actual_entries="196608",
                        address_map_actual_cache_assoc=12,
                        address_map_rounded_entries="262144",
                        address_map_rounded_cache_assoc=16,
                        #ablation study to disable/retune features
                        use_bloom=options.triangelbloom,
                        use_scs= not options.triangelnoscs,
                        timed_scs=True,
                        use_pattern= not options.triangelnopattern,
                        use_pattern2= not options.triangelnopattern2,
                        use_reuse= not options.triangelnoreuse,
                        perfbias = options.triangelperfbias, #Adjusts tuning params to make it more aggressive and less DRAM/L3-partition friendly.
                        should_rearrange = not options.triangelnorearr,
                        use_mrb = not options.triangelnomrb
                        
                        
                    )
                )     
            elif options.triangeldual: 
                #two-core setup. Assumes 4M 16-way L3.
                #Note that the size doubles and the number of ways stays the same
                #As in the 1-core version, unlike Triage which does the opposite.
                #This is because Triangel's L3 Markov table is shared, whereas
                #Triage has private partitions in the L3.
                l2_cache = l2_cache_class(
                    prefetcher=TriangelPrefetcher(
                        cachetags=system.l3.tags,
                        cache_delay=25,
                        address_map_actual_entries="393216",
                        address_map_rounded_entries="524288",
                        use_bloom=options.triangelbloom,
                        use_scs= not options.triangelnoscs,
                        use_pattern= not options.triangelnopattern,
                        use_pattern2= not options.triangelnopattern2,
                        use_reuse= not options.triangelnoreuse,
                        perfbias = options.triangelperfbias,
                        should_rearrange = not options.triangelnorearr,
                        use_mrb = not options.triangelnomrb
                    )
                )     
            #The following cases could be rolled together if better parameterised...  sorry!
            elif options.triangelhawk:
                l2_cache = l2_cache_class(
                    prefetcher=TriangelPrefetcher(
                        cachetags=system.l3.tags,
                        use_hawkeye=True,
                        address_map_cache_replacement_policy=WeightedLRURP()
                    )
                )                
            elif options.triangeldeg1:
                l2_cache = l2_cache_class(
                    prefetcher=TriangelPrefetcher(
                        cachetags=system.l3.tags,
                        degree=1,
                    )
                )
            elif options.triangeldeg1off1:
                l2_cache = l2_cache_class(
                    prefetcher=TriangelPrefetcher(
                        cachetags=system.l3.tags,
                        degree=1,
                        should_lookahead=False,                        
                    )
                )                
            elif options.triangeloff1:
                l2_cache = l2_cache_class(
                    prefetcher=TriangelPrefetcher(
                        cachetags=system.l3.tags,
                        should_lookahead=False,
                    )
                )
            elif options.triangel256luthawk:
                l2_cache = l2_cache_class(
                    prefetcher=TriangelPrefetcher(
                        cachetags=system.l3.tags,
                        address_map_max_ways=2,
                        address_map_actual_entries="65536",
                        address_map_actual_cache_assoc=16,
                        address_map_rounded_entries="65536",
                        address_map_rounded_cache_assoc=16,
                        lookup_assoc=16,
                        use_hawkeye=True,
                        address_map_cache_replacement_policy=WeightedLRURP(),
                    )
                )
            elif options.triangel256lutlru:
                l2_cache = l2_cache_class(
                    prefetcher=TriangelPrefetcher(
                        cachetags=system.l3.tags,
                        address_map_max_ways=2,
                        address_map_actual_entries="65536",
                        address_map_actual_cache_assoc=16,
                        address_map_rounded_entries="65536",
                        address_map_rounded_cache_assoc=16,
                        lookup_assoc=16,
                        address_map_cache_replacement_policy=LRURP(),
                    )
                )
            elif options.triangel256lutrrip:
                l2_cache = l2_cache_class(
                    prefetcher=TriangelPrefetcher(
                        cachetags=system.l3.tags,
                        address_map_max_ways=2,
                        address_map_actual_entries="65536",
                        address_map_actual_cache_assoc=16,
                        address_map_rounded_entries="65536",
                        address_map_rounded_cache_assoc=16,
                        secondchance_entries="64",
                        sample_entries="512",
                        lookup_assoc=16,
                        address_map_cache_replacement_policy=RRIPRP(),
                    )
                )
            elif options.triangelsmall:
                l2_cache = l2_cache_class(
                    prefetcher=TriangelPrefetcher(
                        cachetags=system.l3.tags,
                        metadata_reuse_entries="128",
                        secondchance_entries="16",
                        sample_entries="128",
                        training_unit_entries="128",
                        smallduel=True
                    )
                )
            elif options.triage:
                l2_cache = l2_cache_class(
                    prefetcher=TriagePrefetcher(
                        cachetags=system.l3.tags,
                        cache_delay=25,
                        address_map_max_ways=8,
                        address_map_actual_entries="262144",
                        address_map_actual_cache_assoc=16,
                        address_map_rounded_entries="262144",
                        address_map_rounded_cache_assoc=16,
                    )
                )
            elif options.triagedeg4:
                l2_cache = l2_cache_class(
                    prefetcher=TriagePrefetcher(
                        cachetags=system.l3.tags,
                        degree=4,
                        lookahead_two=options.triagelookaheadtwo
                    )
                )
            elif options.triagedual:
                l2_cache = l2_cache_class(
                    prefetcher=TriagePrefetcher(
                        cachetags=system.l3.tags,
                        address_map_max_ways=4, #This halves assuming 4M cache -- as each core's Triage gets own partition.
                    )
                )
            elif options.triagedeg4dual:
                l2_cache = l2_cache_class(
                    prefetcher=TriagePrefetcher(
                        cachetags=system.l3.tags,
                        degree=4,
                        address_map_max_ways=4,
                    )
                )                                
            elif options.triagenorearr:
                l2_cache = l2_cache_class(
                    prefetcher=TriagePrefetcher(
                        cachetags=system.l3.tags,
                        should_rearrange=False,
                        lookahead_two=options.triagelookaheadtwo
                    )
                )
            elif options.triageideal:
                l2_cache = l2_cache_class(
                    prefetcher=TriagePrefetcher(
                        cachetags=system.l3.tags,
                        lookup_assoc=0,
                        lookahead_two=options.triagelookaheadtwo
                    )
                )
            elif options.triagefalut:
                l2_cache = l2_cache_class(
                    prefetcher=TriagePrefetcher(
                        cachetags=system.l3.tags,
                        lookup_assoc=1024,
                        lookahead_two=options.triagelookaheadtwo
                    )
                )
            elif options.triage12:
                l2_cache = l2_cache_class(
                    prefetcher=TriagePrefetcher(
                        cachetags=system.l3.tags,
                        address_map_max_ways=8,
                        address_map_actual_entries="196608",
                        address_map_actual_cache_assoc=12,
                        address_map_rounded_entries="262144",
                        address_map_rounded_cache_assoc=16,
                        lookup_assoc=0,
                        lookahead_two=options.triagelookaheadtwo
                    )
                )
            elif options.triage10boff:
                l2_cache = l2_cache_class(
                    prefetcher=TriagePrefetcher(
                        cachetags=system.l3.tags,
                        lookup_offset=10,
                        lookahead_two=options.triagelookaheadtwo
                    )
                )
            elif options.triagenounrel:
                l2_cache = l2_cache_class(
                    prefetcher=TriagePrefetcher(
                        cachetags=system.l3.tags,
                        store_unreliable=False,
                        lookahead_two=options.triagelookaheadtwo
                    )
                )
            elif options.triagelru:
                l2_cache = l2_cache_class(
                    prefetcher=TriagePrefetcher(
                        cachetags=system.l3.tags,
                        address_map_cache_replacement_policy=LRURP(),
                        lookahead_two=options.triagelookaheadtwo
                    )
                )
            elif options.triage256:
                l2_cache = l2_cache_class(
                    prefetcher=TriagePrefetcher(
                        cachetags=system.l3.tags,
                        address_map_max_ways=2,
                        address_map_actual_entries="65536",
                        address_map_actual_cache_assoc=16,
                        address_map_rounded_entries="65536",
                        address_map_rounded_cache_assoc=16,
                        lookahead_two=options.triagelookaheadtwo
                    )
                )
            elif options.triage256rrip:
                l2_cache = l2_cache_class(
                    prefetcher=TriagePrefetcher(
                        cachetags=system.l3.tags,
                        address_map_max_ways=2,
                        address_map_actual_entries="65536",
                        address_map_actual_cache_assoc=16,
                        address_map_rounded_entries="65536",
                        address_map_rounded_cache_assoc=16,
                        address_map_cache_replacement_policy=RRIPRP(),
                        lookahead_two=options.triagelookaheadtwo
                    )
                )
            elif options.triagelru256:
                l2_cache = l2_cache_class(
                    prefetcher=TriagePrefetcher(
                        cachetags=system.l3.tags,
                        address_map_max_ways=2,
                        address_map_actual_entries="65536",
                        address_map_actual_cache_assoc=16,
                        address_map_rounded_entries="65536",
                        address_map_rounded_cache_assoc=16,
                        address_map_cache_replacement_policy=LRURP(),
                        lookahead_two=options.triagelookaheadtwo
                    )
                )

            elif options.l2triangelbloom:
                l2_cache = l2_cache_class(
                    prefetcher=TriangelBloomPrefetcher()
                )

            elif options.ampm:
                l2_cache = l2_cache_class(
                    prefetcher=AMPMPrefetcher()
                )
            elif options.bop:
                l2_cache = l2_cache_class(
                    prefetcher=BOPPrefetcher()
                )
            elif options.dcpt:
                l2_cache = l2_cache_class(
                    prefetcher=DCPTPrefetcher()
                )
            elif options.imp:
                l2_cache = l2_cache_class(
                    prefetcher=IndirectMemoryPrefether()
                )
            elif options.isb:
                l2_cache = l2_cache_class(
                    prefetcher=IrregularStreamBufferPrefetcher()
                )
            elif options.multi:
                l2_cache = l2_cache_class(
                    prefetcher=MultiPrefetcher()
                )
            elif options.sbooe:
                l2_cache = l2_cache_class(
                    prefetcher=SBOOEPrefetcher()
                )
            elif options.stems:
                l2_cache = l2_cache_class(
                    prefetcher=STeMSPrefetcher()
                )
            elif options.spp:
                l2_cache = l2_cache_class(
                    prefetcher=SignaturePathPrefetcher()
                )
            elif options.slim:
                l2_cache = l2_cache_class(
                    prefetcher=SlimAMPMPrefetcher()
                )
            elif options.stride:
                l2_cache = l2_cache_class(
                    prefetcher=StridePrefetcher()
                )
            elif options.tagged:
                l2_cache = l2_cache_class(
                    prefetcher=TaggedPrefetcher()
                )

            elif options.xsberti:
                l2_cache = l2_cache_class(
                    prefetcher=BertiPrefetcher()
                )

            elif options.xsbop:
                l2_cache = l2_cache_class(
                    prefetcher=XSBOPPrefetcher()
                )

            elif options.xsopt:
                l2_cache = l2_cache_class(
                    prefetcher=OptPrefetcher()
                )

            elif options.xsstream:
                l2_cache = l2_cache_class(
                    prefetcher=XsStreamPrefetcher()
                )

            elif options.tkV10:
                l2_cache = l2_cache_class(
                    prefetcher=TkV10Prefetcher(
                        max_filter_size = options.filter_size,
                        degree = options.degree,
                        training_unit_assoc = options.tu_assoc,
                        training_unit_entries = options.tu_entries,
                        training_unit_replacement_policy = options.tu_replace,
                        address_map_actual_entries = options.ama_entries,
                        address_map_actual_cache_assoc = options.ama_assoc,
                        address_map_rounded_entries = options.amr_entries,
                        address_map_rounded_cache_assoc = options.amr_assoc,
                        address_map_cache_replacement_policy = options.am_replace,
                        sample_assoc = options.sample_assoc,
                        sample_entries = options.sample_entries,
                        sample_replacement_policy = options.sample_replacement_policy,
                        metadata_reuse_assoc = options.reuse_assoc,
                        metadata_reuse_entries = options.reuse_entries,
                        metadata_reuse_replacement_policy = options.reuse_replace,
                        secondchance_assoc = options.second_assoc,
                        secondchance_entries = options.second_entries,
                        secondchance_replacement_policy = options.second_replace,
                        re_thre = options.re_thre,
                        pre_threshold = options.pre_threshold,
                        maxstride = options.maxstride,
                        dynamic_stride_degree = options.dynamic_mode,
                        stride_degree = options.stride_degree,
                        inc_stride_thre = options.inc_stride_thre,
                        dec_stride_thre = options.dec_stride_thre,
                        max_degree = options.max_degree,
                        min_degree = options.min_degree,
                        stride_table_assoc = options.st_assoc,
                        stride_table_entries = options.st_entries,
                        stride_table_replacement_policy = options.st_replace
                    )
                )
            
            elif options.tkV11:
                l2_cache = l2_cache_class(
                    prefetcher=TkV11Prefetcher(
                        use_stride = options.stride_mode,
                        dynamic_stride_degree = options.dynamic_mode,
                        max_filter_size = options.filter_size,
                        degree = options.degree,
                        training_unit_assoc = options.tu_assoc,
                        training_unit_entries = options.tu_entries,
                        training_unit_replacement_policy = options.tu_replace,
                        address_map_actual_entries = options.ama_entries,
                        address_map_actual_cache_assoc = options.ama_assoc,
                        address_map_rounded_entries = options.amr_entries,
                        address_map_rounded_cache_assoc = options.amr_assoc,
                        address_map_cache_replacement_policy = options.am_replace,
                        sample_assoc = options.sample_assoc,
                        sample_entries = options.sample_entries,
                        sample_replacement_policy = options.sample_replacement_policy,
                        metadata_reuse_assoc = options.reuse_entries,
                        metadata_reuse_entries = options.reuse_assoc,
                        metadata_reuse_replacement_policy = options.reuse_replace,
                        secondchance_assoc = options.second_assoc,
                        secondchance_entries = options.second_entries,
                        secondchance_replacement_policy = options.second_replace,
                        re_thre = options.re_thre,
                        pre_threshold = options.pre_threshold,
                        maxstride = options.maxstride,
                        stride_degree = options.stride_degree,
                        inc_stride_thre = options.inc_stride_thre,
                        dec_stride_thre = options.dec_stride_thre,
                        max_degree = options.max_degree,
                        min_degree = options.min_degree,
                        stride_table_assoc = options.st_assoc,
                        stride_table_entries = options.st_entries,
                        stride_table_replacement_policy = options.st_replace
                    )
                )

            elif options.tkV12:
                l2_cache = l2_cache_class(
                    prefetcher=TkV12Prefetcher(
                        max_filter_size = options.filter_size,
                        degree = options.degree,
                        training_unit_assoc = options.tu_assoc,
                        training_unit_entries = options.tu_entries,
                        training_unit_replacement_policy = options.tu_replace,
                        address_map_actual_entries = options.ama_entries,
                        address_map_actual_cache_assoc = options.ama_assoc,
                        address_map_rounded_entries = options.amr_entries,
                        address_map_rounded_cache_assoc = options.amr_assoc,
                        address_map_cache_replacement_policy = options.am_replace,
                        sample_assoc = options.sample_assoc,
                        sample_entries = options.sample_entries,
                        sample_replacement_policy = options.sample_replacement_policy,
                        metadata_reuse_assoc = options.reuse_assoc,
                        metadata_reuse_entries = options.reuse_entries,
                        metadata_reuse_replacement_policy = options.reuse_replace,
                        secondchance_assoc = options.second_assoc,
                        secondchance_entries = options.second_entries,
                        secondchance_replacement_policy = options.second_replace,
                        re_thre = options.re_thre,
                        pre_threshold = options.pre_threshold,
                        maxstride = options.maxstride,
                        dynamic_stride_degree = options.dynamic_mode,
                        stride_degree = options.stride_degree,
                        inc_stride_thre = options.inc_stride_thre,
                        dec_stride_thre = options.dec_stride_thre,
                        max_degree = options.max_degree,
                        min_degree = options.min_degree,
                        stride_table_assoc = options.st_assoc,
                        stride_table_entries = options.st_entries,
                        stride_table_replacement_policy = options.st_replace
                    )
                )

            elif options.tkV13:
                l2_cache = l2_cache_class(
                    prefetcher=TkV13Prefetcher(
                        max_filter_size = options.filter_size,
                        degree = options.degree,
                        training_unit_assoc = options.tu_assoc,
                        training_unit_entries = options.tu_entries,
                        training_unit_replacement_policy = options.tu_replace,
                        address_map_actual_entries = options.ama_entries,
                        address_map_actual_cache_assoc = options.ama_assoc,
                        address_map_rounded_entries = options.amr_entries,
                        address_map_rounded_cache_assoc = options.amr_assoc,
                        address_map_cache_replacement_policy = options.am_replace,
                        sample_assoc = options.sample_assoc,
                        sample_entries = options.sample_entries,
                        sample_replacement_policy = options.sample_replacement_policy,
                        metadata_reuse_assoc = options.reuse_assoc,
                        metadata_reuse_entries = options.reuse_entries,
                        metadata_reuse_replacement_policy = options.reuse_replace,
                        secondchance_assoc = options.second_assoc,
                        secondchance_entries = options.second_entries,
                        secondchance_replacement_policy = options.second_replace,
                        re_thre = options.re_thre,
                        pre_threshold = options.pre_threshold,
                        maxstride = options.maxstride,
                        dynamic_stride_degree = options.dynamic_mode,
                        stride_degree = options.stride_degree,
                        inc_stride_thre = options.inc_stride_thre,
                        dec_stride_thre = options.dec_stride_thre,
                        max_degree = options.max_degree,
                        min_degree = options.min_degree,
                        stride_table_assoc = options.st_assoc,
                        stride_table_entries = options.st_entries,
                        stride_table_replacement_policy = options.st_replace,
                        stream_degree=options.stream_degree
                    )
                )

            elif options.tkV14:
                l2_cache = l2_cache_class(
                    CleanCacheMissThreshold = options.CleanCacheMissThreshold,
                    prefetcher=TkV14Prefetcher(
                        max_filter_size = options.filter_size,
                        degree = options.degree,
                        training_unit_assoc = options.tu_assoc,
                        training_unit_entries = options.tu_entries,
                        training_unit_replacement_policy = options.tu_replace,
                        address_map_actual_entries = options.ama_entries,
                        address_map_actual_cache_assoc = options.ama_assoc,
                        address_map_rounded_entries = options.amr_entries,
                        address_map_rounded_cache_assoc = options.amr_assoc,
                        address_map_cache_replacement_policy = options.am_replace,
                        sample_assoc = options.sample_assoc,
                        sample_entries = options.sample_entries,
                        sample_replacement_policy = options.sample_replacement_policy,
                        metadata_reuse_assoc = options.reuse_assoc,
                        metadata_reuse_entries = options.reuse_entries,
                        metadata_reuse_replacement_policy = options.reuse_replace,
                        secondchance_assoc = options.second_assoc,
                        secondchance_entries = options.second_entries,
                        secondchance_replacement_policy = options.second_replace,
                        re_thre = options.re_thre,
                        pre_threshold = options.pre_threshold,
                        maxstride = options.maxstride,
                        dynamic_stride_degree = options.dynamic_mode,
                        stride_degree = options.stride_degree,
                        inc_stride_thre = options.inc_stride_thre,
                        dec_stride_thre = options.dec_stride_thre,
                        max_degree = options.max_degree,
                        min_degree = options.min_degree,
                        stride_table_assoc = options.st_assoc,
                        stride_table_entries = options.st_entries,
                        stride_table_replacement_policy = options.st_replace,
                        stream_degree = options.stream_degree,
                        monitor_accuracy = options.monitor_accuracy,
                        CleanAccuracyThreshold = options.CleanAccuracyThreshold,
                        global_accuracy_increase_threshold = options.global_accuracy_increase_threshold,
                        global_accuracy_decrease_threshold = options.global_accuracy_decrease_threshold,
                        high_accuracy_degree_coefficient = options.high_accuracy_degree_coefficient,
                        normal_accuracy_degree_coefficient = options.normal_accuracy_degree_coefficient,
                        low_accuracy_degree_coefficient = options.low_accuracy_degree_coefficient,
                        monitor_cache_miss = options.monitor_cache_miss,
                        global_cache_miss_increase_threshold = options.global_cache_miss_increase_threshold,
                        global_cache_miss_decrease_threshold = options.global_cache_miss_decrease_threshold,
                        high_cache_miss_degree_coefficient = options.high_cache_miss_degree_coefficient,
                        normal_cache_miss_degree_coefficient = options.normal_cache_miss_degree_coefficient,
                        low_cache_miss_degree_coefficient = options.low_cache_miss_degree_coefficient, 
                        CleanCacheMissThreshold = options.CleanCacheMissThreshold                       
                    )
                )

            elif options.tkV15:
                l2_cache = l2_cache_class(
                    prefetcher=TkV15Prefetcher(
                        max_filter_size = options.filter_size,
                        degree = options.degree,
                        training_unit_assoc = options.tu_assoc,
                        training_unit_entries = options.tu_entries,
                        training_unit_replacement_policy = options.tu_replace,
                        address_map_actual_entries = options.ama_entries,
                        address_map_actual_cache_assoc = options.ama_assoc,
                        address_map_rounded_entries = options.amr_entries,
                        address_map_rounded_cache_assoc = options.amr_assoc,
                        address_map_cache_replacement_policy = options.am_replace,
                        sample_assoc = options.sample_assoc,
                        sample_entries = options.sample_entries,
                        sample_replacement_policy = options.sample_replacement_policy,
                        metadata_reuse_assoc = options.reuse_assoc,
                        metadata_reuse_entries = options.reuse_entries,
                        metadata_reuse_replacement_policy = options.reuse_replace,
                        secondchance_assoc = options.second_assoc,
                        secondchance_entries = options.second_entries,
                        secondchance_replacement_policy = options.second_replace,
                        re_thre = options.re_thre,
                        pre_threshold = options.pre_threshold,
                        maxstride = options.maxstride,
                        dynamic_stride_degree = options.dynamic_mode,
                        stride_degree = options.stride_degree,
                        inc_stride_thre = options.inc_stride_thre,
                        dec_stride_thre = options.dec_stride_thre,
                        max_degree = options.max_degree,
                        min_degree = options.min_degree,
                        stride_table_assoc = options.st_assoc,
                        stride_table_entries = options.st_entries,
                        stride_table_replacement_policy = options.st_replace,
                        stream_degree=options.stream_degree,
                        monitor_accuracy = options.monitor_accuracy,
                        CleanAccuracyThreshold = options.CleanAccuracyThreshold,
                        global_accuracy_increase_threshold = options.global_accuracy_increase_threshold,
                        global_accuracy_decrease_threshold = options.global_accuracy_decrease_threshold,
                        high_accuracy_degree_coefficient = options.high_accuracy_degree_coefficient,
                        normal_accuracy_degree_coefficient = options.normal_accuracy_degree_coefficient,
                        low_accuracy_degree_coefficient = options.low_accuracy_degree_coefficient                     
                    )
                )
            
            elif options.l2triangelbase:
                l2_cache = l2_cache_class(
                    prefetcher = TriangelBasePrefetcher(
                        degree = options.degree,
                        training_unit_assoc = options.tu_assoc,
                        training_unit_entries = options.tu_entries,
                        training_unit_replacement_policy = options.tu_replace,
                        address_map_actual_entries = options.ama_entries,
                        address_map_actual_cache_assoc = options.ama_assoc,
                        address_map_rounded_entries = options.amr_entries,
                        address_map_rounded_cache_assoc = options.amr_assoc,
                        address_map_cache_replacement_policy = options.am_replace,
                        sample_assoc = options.sample_assoc,
                        sample_entries = options.sample_entries,
                        sample_replacement_policy = options.sample_replacement_policy,
                        metadata_reuse_assoc = options.reuse_assoc,
                        metadata_reuse_entries = options.reuse_entries,
                        metadata_reuse_replacement_policy = options.reuse_replace,
                        secondchance_assoc = options.second_assoc,
                        secondchance_entries = options.second_entries,
                        secondchance_replacement_policy = options.second_replace                       
                    )
                )

            elif options.t1:
                l2_cache = l2_cache_class(
                    prefetcher=T1Prefetcher(
                        cachetags=system.l3.tags,#To take a partition of for the Markov table.
                        cache_delay=25, #5 cycles more than the L3 cache itself
                        degree=4,
                        address_map_max_ways=8,
                        #The below params assume 1MiB partition max of a 2MiB 16-way cache (So 8 max_ways).
                        #The density is 12 entries per cache line (actual_cache_assoc) unlike Triage's 16
                        #And the rounded version sets everything to a power of two -- with the difference between
                        #actual and rounded based on that ratio between 12 and 16 here.
                        address_map_actual_entries="196608",
                        address_map_actual_cache_assoc=12,
                        address_map_rounded_entries="262144",
                        address_map_rounded_cache_assoc=16,
                        #ablation study to disable/retune features
                        use_bloom=False,
                        use_scs= not options.triangelnoscs,
                        timed_scs=True,
                        use_pattern= not options.triangelnopattern,
                        use_pattern2= not options.triangelnopattern2,
                        use_reuse= not options.triangelnoreuse,
                        perfbias = options.triangelperfbias, #Adjusts tuning params to make it more aggressive and less DRAM/L3-partition friendly.
                        should_rearrange = not options.triangelnorearr,
                        use_mrb = not options.triangelnomrb,
                        re_thre = options.re_thre,
                        pre_threshold = options.pre_threshold,
                        maxstride = options.maxstride,
                        use_stride=options.stride_mode,
                        max_filter_size=options.filter_size,
                        dynamic_stride_degree = options.dynamic_mode,
                        stride_degree = options.stride_degree,
                        inc_stride_thre = options.inc_stride_thre,
                        dec_stride_thre = options.dec_stride_thre,
                        max_degree = options.max_degree,
                        min_degree = options.min_degree,
                        stride_table_assoc = options.st_assoc,
                        stride_table_entries = options.st_entries,
                        stride_table_replacement_policy = options.st_replace,
                        stream_degree=options.stream_degree,
                        monitor_accuracy = options.monitor_accuracy,
                        CleanAccuracyThreshold = options.CleanAccuracyThreshold,
                        global_accuracy_increase_threshold = options.global_accuracy_increase_threshold,
                        global_accuracy_decrease_threshold = options.global_accuracy_decrease_threshold,
                        high_accuracy_degree_coefficient = options.high_accuracy_degree_coefficient,
                        normal_accuracy_degree_coefficient = options.normal_accuracy_degree_coefficient,
                        low_accuracy_degree_coefficient = options.low_accuracy_degree_coefficient    
                    )
                )
            
            elif options.t1_bloom:
                l2_cache = l2_cache_class(
                     prefetcher=T1Prefetcher(
                        cachetags=system.l3.tags,
                        cache_delay=25, 
                        degree=4,
                        address_map_max_ways=8,
                        address_map_actual_entries="196608",
                        address_map_actual_cache_assoc=12,
                        address_map_rounded_entries="262144",
                        address_map_rounded_cache_assoc=16,
                        use_bloom=True,
                        use_scs= not options.triangelnoscs,
                        timed_scs=True,
                        use_pattern= not options.triangelnopattern,
                        use_pattern2= not options.triangelnopattern2,
                        use_reuse= not options.triangelnoreuse,
                        perfbias = options.triangelperfbias, #Adjusts tuning params to make it more aggressive and less DRAM/L3-partition friendly.
                        should_rearrange = not options.triangelnorearr,
                        use_mrb = not options.triangelnomrb,
                        re_thre = options.re_thre,
                        pre_threshold = options.pre_threshold,
                        maxstride = options.maxstride,
                        use_stride=options.stride_mode,
                        max_filter_size=options.filter_size,
                        dynamic_stride_degree = options.dynamic_mode,
                        stride_degree = options.stride_degree,
                        inc_stride_thre = options.inc_stride_thre,
                        dec_stride_thre = options.dec_stride_thre,
                        max_degree = options.max_degree,
                        min_degree = options.min_degree,
                        stride_table_assoc = options.st_assoc,
                        stride_table_entries = options.st_entries,
                        stride_table_replacement_policy = options.st_replace,
                        stream_degree=options.stream_degree,
                        monitor_accuracy = options.monitor_accuracy,
                        CleanAccuracyThreshold = options.CleanAccuracyThreshold,
                        global_accuracy_increase_threshold = options.global_accuracy_increase_threshold,
                        global_accuracy_decrease_threshold = options.global_accuracy_decrease_threshold,
                        high_accuracy_degree_coefficient = options.high_accuracy_degree_coefficient,
                        normal_accuracy_degree_coefficient = options.normal_accuracy_degree_coefficient,
                        low_accuracy_degree_coefficient = options.low_accuracy_degree_coefficient    
                    )
                )
                   
            #The following cases could be rolled together if better parameterised...  sorry!
            elif options.t1_hawk:
                l2_cache = l2_cache_class(
                    prefetcher=T1Prefetcher(
                        cachetags=system.l3.tags,
                        use_hawkeye=True,
                        address_map_cache_replacement_policy=WeightedLRURP(),
                        re_thre = options.re_thre,
                        pre_threshold = options.pre_threshold,
                        maxstride = options.maxstride,
                        dynamic_stride_degree = options.dynamic_mode,
                        stride_degree = options.stride_degree,
                        inc_stride_thre = options.inc_stride_thre,
                        dec_stride_thre = options.dec_stride_thre,
                        max_degree = options.max_degree,
                        min_degree = options.min_degree,
                        stride_table_assoc = options.st_assoc,
                        stride_table_entries = options.st_entries,
                        stride_table_replacement_policy = options.st_replace,
                        stream_degree=options.stream_degree,
                        monitor_accuracy = options.monitor_accuracy,
                        CleanAccuracyThreshold = options.CleanAccuracyThreshold,
                        global_accuracy_increase_threshold = options.global_accuracy_increase_threshold,
                        global_accuracy_decrease_threshold = options.global_accuracy_decrease_threshold,
                        high_accuracy_degree_coefficient = options.high_accuracy_degree_coefficient,
                        normal_accuracy_degree_coefficient = options.normal_accuracy_degree_coefficient,
                        low_accuracy_degree_coefficient = options.low_accuracy_degree_coefficient
                    )
                )                               
            elif options.t1_off1:
                l2_cache = l2_cache_class(
                    prefetcher=T1Prefetcher(
                        cachetags=system.l3.tags,
                        should_lookahead=False,
                        re_thre = options.re_thre,
                        pre_threshold = options.pre_threshold,
                        maxstride = options.maxstride,
                        dynamic_stride_degree = options.dynamic_mode,
                        stride_degree = options.stride_degree,
                        inc_stride_thre = options.inc_stride_thre,
                        dec_stride_thre = options.dec_stride_thre,
                        max_degree = options.max_degree,
                        min_degree = options.min_degree,
                        stride_table_assoc = options.st_assoc,
                        stride_table_entries = options.st_entries,
                        stride_table_replacement_policy = options.st_replace,
                        stream_degree=options.stream_degree,
                        monitor_accuracy = options.monitor_accuracy,
                        CleanAccuracyThreshold = options.CleanAccuracyThreshold,
                        global_accuracy_increase_threshold = options.global_accuracy_increase_threshold,
                        global_accuracy_decrease_threshold = options.global_accuracy_decrease_threshold,
                        high_accuracy_degree_coefficient = options.high_accuracy_degree_coefficient,
                        normal_accuracy_degree_coefficient = options.normal_accuracy_degree_coefficient,
                        low_accuracy_degree_coefficient = options.low_accuracy_degree_coefficient
                    )
                )
            elif options.t1_256luthawk:
                l2_cache = l2_cache_class(
                    prefetcher=T1Prefetcher(
                        cachetags=system.l3.tags,
                        address_map_max_ways=2,
                        address_map_actual_entries="196608",
                        address_map_actual_cache_assoc=12,
                        address_map_rounded_entries="262144",
                        address_map_rounded_cache_assoc=16,
                        lookup_assoc=16,
                        use_hawkeye=True,
                        address_map_cache_replacement_policy=WeightedLRURP(),
                        re_thre = options.re_thre,
                        pre_threshold = options.pre_threshold,
                        maxstride = options.maxstride,
                        dynamic_stride_degree = options.dynamic_mode,
                        stride_degree = options.stride_degree,
                        inc_stride_thre = options.inc_stride_thre,
                        dec_stride_thre = options.dec_stride_thre,
                        max_degree = options.max_degree,
                        min_degree = options.min_degree,
                        stride_table_assoc = options.st_assoc,
                        stride_table_entries = options.st_entries,
                        stride_table_replacement_policy = options.st_replace,
                        stream_degree=options.stream_degree,
                        monitor_accuracy = options.monitor_accuracy,
                        CleanAccuracyThreshold = options.CleanAccuracyThreshold,
                        global_accuracy_increase_threshold = options.global_accuracy_increase_threshold,
                        global_accuracy_decrease_threshold = options.global_accuracy_decrease_threshold,
                        high_accuracy_degree_coefficient = options.high_accuracy_degree_coefficient,
                        normal_accuracy_degree_coefficient = options.normal_accuracy_degree_coefficient,
                        low_accuracy_degree_coefficient = options.low_accuracy_degree_coefficient
                    )
                )
            elif options.t1_256lutlru:
                l2_cache = l2_cache_class(
                    prefetcher=T1Prefetcher(
                        cachetags=system.l3.tags,
                        address_map_max_ways=2,
                        address_map_actual_entries="65536",
                        address_map_actual_cache_assoc=16,
                        address_map_rounded_entries="65536",
                        address_map_rounded_cache_assoc=16,
                        lookup_assoc=16,
                        address_map_cache_replacement_policy=LRURP(),
                        re_thre = options.re_thre,
                        pre_threshold = options.pre_threshold,
                        maxstride = options.maxstride,
                        dynamic_stride_degree = options.dynamic_mode,
                        stride_degree = options.stride_degree,
                        inc_stride_thre = options.inc_stride_thre,
                        dec_stride_thre = options.dec_stride_thre,
                        max_degree = options.max_degree,
                        min_degree = options.min_degree,
                        stride_table_assoc = options.st_assoc,
                        stride_table_entries = options.st_entries,
                        stride_table_replacement_policy = options.st_replace,
                        stream_degree=options.stream_degree,
                        monitor_accuracy = options.monitor_accuracy,
                        CleanAccuracyThreshold = options.CleanAccuracyThreshold,
                        global_accuracy_increase_threshold = options.global_accuracy_increase_threshold,
                        global_accuracy_decrease_threshold = options.global_accuracy_decrease_threshold,
                        high_accuracy_degree_coefficient = options.high_accuracy_degree_coefficient,
                        normal_accuracy_degree_coefficient = options.normal_accuracy_degree_coefficient,
                        low_accuracy_degree_coefficient = options.low_accuracy_degree_coefficient
                    )
                )
            elif options.t1_256lutrrip:
                l2_cache = l2_cache_class(
                    prefetcher=T1Prefetcher(
                        cachetags=system.l3.tags,
                        address_map_max_ways=2,
                        address_map_actual_entries="65536",
                        address_map_actual_cache_assoc=16,
                        address_map_rounded_entries="65536",
                        address_map_rounded_cache_assoc=16,
                        secondchance_entries="64",
                        sample_entries="512",
                        lookup_assoc=16,
                        address_map_cache_replacement_policy=RRIPRP(),
                        re_thre = options.re_thre,
                        pre_threshold = options.pre_threshold,
                        maxstride = options.maxstride,
                        dynamic_stride_degree = options.dynamic_mode,
                        stride_degree = options.stride_degree,
                        inc_stride_thre = options.inc_stride_thre,
                        dec_stride_thre = options.dec_stride_thre,
                        max_degree = options.max_degree,
                        min_degree = options.min_degree,
                        stride_table_assoc = options.st_assoc,
                        stride_table_entries = options.st_entries,
                        stride_table_replacement_policy = options.st_replace,
                        stream_degree=options.stream_degree,
                        monitor_accuracy = options.monitor_accuracy,
                        CleanAccuracyThreshold = options.CleanAccuracyThreshold,
                        global_accuracy_increase_threshold = options.global_accuracy_increase_threshold,
                        global_accuracy_decrease_threshold = options.global_accuracy_decrease_threshold,
                        high_accuracy_degree_coefficient = options.high_accuracy_degree_coefficient,
                        normal_accuracy_degree_coefficient = options.normal_accuracy_degree_coefficient,
                        low_accuracy_degree_coefficient = options.low_accuracy_degree_coefficient
                    )
                )
            elif options.t1_small:
                l2_cache = l2_cache_class(
                    prefetcher=T1Prefetcher(
                        cachetags=system.l3.tags,
                        metadata_reuse_entries="128",
                        secondchance_entries="16",
                        sample_entries="128",
                        training_unit_entries="128",
                        smallduel=True,
                        re_thre = options.re_thre,
                        pre_threshold = options.pre_threshold,
                        maxstride = options.maxstride,
                        dynamic_stride_degree = options.dynamic_mode,
                        stride_degree = options.stride_degree,
                        inc_stride_thre = options.inc_stride_thre,
                        dec_stride_thre = options.dec_stride_thre,
                        max_degree = options.max_degree,
                        min_degree = options.min_degree,
                        stride_table_assoc = options.st_assoc,
                        stride_table_entries = options.st_entries,
                        stride_table_replacement_policy = options.st_replace,
                        stream_degree=options.stream_degree,
                        monitor_accuracy = options.monitor_accuracy,
                        CleanAccuracyThreshold = options.CleanAccuracyThreshold,
                        global_accuracy_increase_threshold = options.global_accuracy_increase_threshold,
                        global_accuracy_decrease_threshold = options.global_accuracy_decrease_threshold,
                        high_accuracy_degree_coefficient = options.high_accuracy_degree_coefficient,
                        normal_accuracy_degree_coefficient = options.normal_accuracy_degree_coefficient,
                        low_accuracy_degree_coefficient = options.low_accuracy_degree_coefficient
                    )
                )
            elif options.t1_bloom_v2:
                l2_cache = l2_cache_class(
                    prefetcher=T1Prefetcher(
                        cachetags=system.l3.tags,
                        cache_delay=25, 
                        degree=4,
                        address_map_max_ways=8,
                        address_map_actual_entries="196608",
                        address_map_actual_cache_assoc=12,
                        address_map_rounded_entries="262144",
                        address_map_rounded_cache_assoc=16,
                        use_bloom=True,
                        use_scs=True,
                        use_pattern=True,
                        use_pattern2=True,
                        use_reuse=True,
                        perfbias=False,
                        should_rearrange=True,
                        use_mrb=True,
                        dynamic_stride_degree=2,
                        stream_degree=3,
                        stride_degree=4,
                        use_stride=options.stride_mode,
                        max_filter_size=options.filter_size,
                        maxstride=options.maxstride,
                        monitor_accuracy=options.monitor_accuracy,
                        re_thre = options.re_thre,
                        pre_threshold = options.pre_threshold,
                        inc_stride_thre = options.inc_stride_thre,
                        dec_stride_thre = options.dec_stride_thre,
                        max_degree = options.max_degree,
                        min_degree = options.min_degree,
                        stride_table_assoc = options.st_assoc,
                        stride_table_entries = options.st_entries,
                        stride_table_replacement_policy = options.st_replace,
                        CleanAccuracyThreshold = options.CleanAccuracyThreshold,
                        global_accuracy_increase_threshold = options.global_accuracy_increase_threshold,
                        global_accuracy_decrease_threshold = options.global_accuracy_decrease_threshold,
                        high_accuracy_degree_coefficient = options.high_accuracy_degree_coefficient,
                        normal_accuracy_degree_coefficient = options.normal_accuracy_degree_coefficient,
                        low_accuracy_degree_coefficient = options.low_accuracy_degree_coefficient 
                    )
                )

            else:
                l2_cache = l2_cache_class()
            # If we have a walker cache specified, instantiate two
            # instances here
            if walk_cache_class:
                iwalkcache = walk_cache_class()
                dwalkcache = walk_cache_class()
            else:
                iwalkcache = None
                dwalkcache = None
            if options.memchecker:
                dcache_mon = MemCheckerMonitor(warn_only=True)
                dcache_real = dcache

                # Do not pass the memchecker into the constructor of
                # MemCheckerMonitor, as it would create a copy; we require
                # exactly one MemChecker instance.
                dcache_mon.memchecker = system.memchecker

                # Connect monitor
                dcache_mon.mem_side = dcache.cpu_side

                # Let CPU connect to monitors
                dcache = dcache_mon
            # When connecting the caches, the clock is also inherited
            # from the CPU in question
            system.cpu[i].addTwoLevelCacheHierarchy(
                icache, dcache, l2_cache, iwalkcache, dwalkcache
            )

            if options.memchecker:
                # The mem_side ports of the caches haven't been connected yet.
                # Make sure connectAllPorts connects the right objects.
                system.cpu[i].dcache = dcache_real
                system.cpu[i].dcache_mon = dcache_mon

        system.cpu[i].createInterruptController()
        if options.l2cache:
            system.cpu[i].connectAllPorts(
                system.tol2bus.cpu_side_ports,
                system.membus.cpu_side_ports,
                system.membus.mem_side_ports,
            )
        elif options.pl2sl3cache:
            system.cpu[i].connectAllPorts(
                system.tol3bus.cpu_side_ports,
                system.membus.cpu_side_ports,
                system.membus.mem_side_ports,
            )
        elif options.external_memory_system:
            system.cpu[i].connectUncachedPorts(
                system.membus.cpu_side_ports, system.membus.mem_side_ports
            )
        else:
            system.cpu[i].connectBus(system.membus)

    return system


# ExternalSlave provides a "port", but when that port connects to a cache,
# the connecting CPU SimObject wants to refer to its "cpu_side".
# The 'ExternalCache' class provides this adaptation by rewriting the name,
# eliminating distracting changes elsewhere in the config code.
class ExternalCache(ExternalSlave):
    def __getattr__(cls, attr):
        if attr == "cpu_side":
            attr = "port"
        return super(ExternalSlave, cls).__getattr__(attr)

    def __setattr__(cls, attr, value):
        if attr == "cpu_side":
            attr = "port"
        return super(ExternalSlave, cls).__setattr__(attr, value)


def ExternalCacheFactory(port_type):
    def make(name):
        return ExternalCache(
            port_data=name, port_type=port_type, addr_ranges=[AllMemory]
        )

    return make
