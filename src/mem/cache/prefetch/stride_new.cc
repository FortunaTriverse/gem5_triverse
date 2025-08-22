/*
 * Copyright (c) 2018 Inria
 * Copyright (c) 2012-2013, 2015 ARM Limited
 * All rights reserved
 *
 * The license below extends only to copyright in the software and shall
 * not be construed as granting a license to any other intellectual
 * property including but not limited to intellectual property relating
 * to a hardware implementation of the functionality of the software
 * licensed hereunder.  You may use the software subject to the license
 * terms below provided that you ensure that this notice is replicated
 * unmodified and in its entirety in all distributions of the software,
 * modified or unmodified, in source code or in binary form.
 *
 * Copyright (c) 2005 The Regents of The University of Michigan
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are
 * met: redistributions of source code must retain the above copyright
 * notice, this list of conditions and the following disclaimer;
 * redistributions in binary form must reproduce the above copyright
 * notice, this list of conditions and the following disclaimer in the
 * documentation and/or other materials provided with the distribution;
 * neither the name of the copyright holders nor the names of its
 * contributors may be used to endorse or promote products derived from
 * this software without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
 * "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
 * LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
 * A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
 * OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
 * SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
 * LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
 * DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
 * THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 * (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
 * OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 */

/**
 * @file
 * StrideNew Prefetcher template instantiations.
 */

#include "mem/cache/prefetch/stride_new.hh"

#include <cassert>

#include "base/intmath.hh"
#include "base/logging.hh"
#include "base/random.hh"
#include "base/trace.hh"
#include "debug/HWPrefetch.hh"
#include "mem/cache/prefetch/associative_set_impl.hh"
#include "mem/cache/replacement_policies/base.hh"
#include "params/StrideNewPrefetcher.hh"
#include "debug/CacheMiss.hh"

namespace gem5
{

namespace prefetch
{

StrideNew::StrideNewEntry::StrideNewEntry(const SatCounter8& init_confidence)
  : TaggedEntry(), confidence(init_confidence)
{
    invalidate();
}

void
StrideNew::StrideNewEntry::invalidate()
{
    TaggedEntry::invalidate();
    lastAddr = 0;
    stride = 0;
    confidence.reset();
}

StrideNew::StrideNew(const StrideNewPrefetcherParams &p)
  : Queued(p),
    initConfidence(p.confidence_counter_bits, p.initial_confidence),
    threshConf(p.confidence_threshold/100.0),
    useRequestorId(p.use_requestor_id),
    degree(p.degree),
    pcTableInfo(p.table_assoc, 
                p.table_entries, 
                p.table_indexing_policy,
                p.table_replacement_policy),
    filterTable(p.filter_assoc,
	 		    p.filter_entries,
	 			p.filter_indexing_policy,
	 			p.filter_replacement_policy),
    use_filter(p.use_filter)
{
}

StrideNew::PCTable*
StrideNew::findTable(int context)
{
    // Check if table for given context exists
    auto it = pcTables.find(context);
    if (it != pcTables.end())
        return &it->second;

    // If table does not exist yet, create one
    return allocateNewContext(context);
}

StrideNew::PCTable*
StrideNew::allocateNewContext(int context)
{
    // Create new table
    auto insertion_result = pcTables.insert(std::make_pair(context,
        PCTable(pcTableInfo.assoc, pcTableInfo.numEntries,
        pcTableInfo.indexingPolicy, pcTableInfo.replacementPolicy,
        StrideNewEntry(initConfidence))));

    DPRINTF(HWPrefetch, "Adding context %i with stride entries\n", context);

    // Get iterator to new pc table, and then return a pointer to the new table
    return &(insertion_result.first->second);
}

void
StrideNew::calculatePrefetch(const PrefetchInfo &pfi,
                                    std::vector<AddrPriority> &addresses)
{
    if (!pfi.hasPC()) {
        DPRINTF(HWPrefetch, "Ignoring request with no PC.\n");
        return;
    }

    // Get required packet info
    Addr pf_addr = pfi.getAddr();
    Addr pc = pfi.getPC();
    bool is_secure = pfi.isSecure();
    RequestorID requestor_id = useRequestorId ? pfi.getRequestorId() : 0;

    bool cachemiss = pfi.isCacheMiss();
	if (cachemiss) DPRINTF(CacheMiss, "V02::pc:%0#x,addr:%0#x\n",pc,pf_addr);

    // Get corresponding pc table
    PCTable* pcTable = findTable(requestor_id);

    // Search for entry in the pc table
    StrideNewEntry *entry = pcTable->findEntry(pc, is_secure);

    if (entry != nullptr) {
        pcTable->accessEntry(entry);

        // Hit in table
        int new_stride = pf_addr - entry->lastAddr;
        bool stride_match = (new_stride == entry->stride);

        // Adjust confidence for stride entry
        if (stride_match && new_stride != 0) {
            entry->confidence++;
        } else {
            entry->confidence--;
            // If confidence has dropped below the threshold, train new stride
            if (entry->confidence.calcSaturation() < threshConf) {
                entry->stride = new_stride;
            }
        }

        DPRINTF(HWPrefetch, "Hit: PC %x pkt_addr %x (%s) stride %d (%s), "
                "conf %d\n", pc, pf_addr, is_secure ? "s" : "ns",
                new_stride, stride_match ? "match" : "change",
                (int)entry->confidence);

        entry->lastAddr = pf_addr;

        // Abort prefetch generation if below confidence threshold
        if (entry->confidence.calcSaturation() < threshConf) {
            return;
        }

        // Generate up to degree prefetches
        for (int d = 1; d <= degree; d++) {
            // Round strides up to atleast 1 cacheline
            int prefetch_stride = new_stride;
            if (abs(new_stride) < blkSize) {
                prefetch_stride = (new_stride < 0) ? -blkSize : blkSize;
            }

            Addr new_addr = pf_addr + d * prefetch_stride;
            sendPFWithFilter(pfi,new_addr,addresses,0);
            //addresses.push_back(AddrPriority(new_addr, 0));
        }
    } else {
        // Miss in table
        DPRINTF(HWPrefetch, "Miss: PC %x pkt_addr %x (%s)\n", pc, pf_addr,
                is_secure ? "s" : "ns");

        StrideNewEntry* entry = pcTable->findVictim(pc);

        // Insert new entry's data
        entry->lastAddr = pf_addr;
        pcTable->insertEntry(pc, is_secure, entry);
    }
}

uint32_t
StrideNewPrefetcherHashedSetAssociative::extractSet(const Addr pc) const
{
    const Addr hash1 = pc >> 1;
    const Addr hash2 = hash1 >> tagShift;
    return (hash1 ^ hash2) & setMask;
}

Addr
StrideNewPrefetcherHashedSetAssociative::extractTag(const Addr addr) const
{
    uint64_t low = addr & 0x1FFFFF;
    uint64_t mid = (addr >> 21) & 0x1FFFFF;
    uint64_t hig = (addr >> 43) & 0x1FFFFF;
    constexpr uint64_t M = 0x9E3779B97F4A7C15ULL;
    return (low ^ mid ^ hig) * M & 0x1FFFFF;
}

bool
StrideNew::sendPFWithFilter(const PrefetchInfo &pfi, Addr addr, 
									std::vector<AddrPriority> &addresses,unsigned delay)
{
    if (!use_filter){
        addresses.push_back(AddrPriority(addr, delay));
        return true;
    } else {
        FilterEntry *entry = filterTable.findEntry(addr,true);
        if (entry != nullptr) {
            return false;
        } else {
            entry = filterTable.findVictim(addr);
            filterTable.insertEntry(addr,true,entry);
            //printf("pfi address is %ld, prefetch address is %ld\n",pfi.getAddr(),addr);
            addresses.push_back(AddrPriority(addr, delay));
            return true;
        }
    } 
}

} // namespace prefetch
} // namespace gem5
