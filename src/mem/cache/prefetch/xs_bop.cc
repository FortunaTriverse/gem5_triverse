/**
 * Copyright (c) 2018 Metempsy Technology Consulting
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

#include "mem/cache/prefetch/xs_bop.hh"
#include "debug/HWPrefetch.hh"
#include "base/stats/group.hh"
#include "mem/cache/base.hh"
#include "params/XSBOPPrefetcher.hh"
#include "mem/cache/prefetch/associative_set_impl.hh"
#include "debug/CacheMiss.hh"

namespace gem5
{

GEM5_DEPRECATED_NAMESPACE(Prefetcher, prefetch);
namespace prefetch
{

XSBOP::XSBOP(const XSBOPPrefetcherParams &p)
    : Queued(p),
      scoreMax(p.score_max), roundMax(p.round_max),
      badScore(p.bad_score), rrEntries(p.rr_size),
      tagMask((1 << p.tag_bits) - 1),
      delayQueueEnabled(p.delay_queue_enable),
      delayQueueSize(p.delay_queue_size),
      delayTicks(cyclesToTicks(p.delay_queue_cycles)),
      victimListSize(p.victimOffsetsListSize),
      restoreCycle(p.restoreCycle),
      delayQueueEvent([this]{ delayQueueEventWrapper(); }, name()),
      issuePrefetchRequests(false), bestOffset(1), phaseBestOffset(0),
      bestScore(0), round(0), stats(this),
      filter(p.max_filter_size)
{
    if (!isPowerOf2(rrEntries)) {
        fatal("%s: number of RR entries is not power of 2\n", name());
    }
    if (!isPowerOf2(blkSize)) {
        fatal("%s: cache line size is not power of 2\n", name());
    }

    rrLeft.resize(rrEntries);
    rrRight.resize(rrEntries);

    int offset_count = p.offsets.size();
    maxOffsetCount = p.negative_offsets_enable ? 2*p.offsets.size() : p.offsets.size();
    if (p.autoLearning) {
        maxOffsetCount = 32;
    }


    for (int i = 0; i < offset_count; i++) {
        offsetsList.emplace_back(p.offsets[i], (uint8_t) 0);
        originOffsets.push_back(p.offsets[i]);
        if (p.negative_offsets_enable) {
            offsetsList.emplace_back(-p.offsets[i], (uint8_t) 0);
            originOffsets.push_back(-p.offsets[i]);
        }
    }

    bestOffset = offsetsList.back().calcOffset();

    offsetsListIterator = offsetsList.begin();
    bestoffsetsListIterator = offsetsListIterator;

    restore_event = new EventFunctionWrapper([this](){
        assert(victimOffsetsList.size() > 0);
        int offset = victimOffsetsList.front();
        victimOffsetsList.pop_front();
        tryAddOffset(offset);
        if (victimOffsetsList.size() > 0) {
            schedule(restore_event, cyclesToTicks(curCycle() + Cycles(restoreCycle)));
        }
        else {
            victimRestoreScheduled = false;
        }
    },name(),false);
}

void
XSBOP::delayQueueEventWrapper()
{
    while (!delayQueue.empty() &&
            delayQueue.front().processTick <= curTick())
    {
        insertIntoRR(delayQueue.front().rrEntry, RRWay::Left);
        delayQueue.pop_front();
    }

    // Schedule an event for the next element if there is one
    if (!delayQueue.empty()) {
        schedule(delayQueueEvent, delayQueue.front().processTick);
    }
}

unsigned int
XSBOP::hash(Addr addr, unsigned int way) const
{
    Addr hash1 = addr >> way;
    Addr hash2 = hash1 >> floorLog2(rrEntries);
    return (hash1 ^ hash2) & (Addr)(rrEntries - 1);
}

void
XSBOP::insertIntoRR(Addr full_addr, Addr tag, unsigned int way)
{
    insertIntoRR(RREntryDebug(full_addr, tag), way);
}

void
XSBOP::insertIntoRR(RREntryDebug rr_entry, unsigned int way)
{
    switch (way) {
        case RRWay::Left:
            rrLeft[hash(rr_entry.hashAddr, RRWay::Left)] = rr_entry;
            break;
        case RRWay::Right:
            rrRight[hash(rr_entry.hashAddr, RRWay::Right)] = rr_entry;
            break;
    }
}

void
XSBOP::insertIntoDelayQueue(Addr full_addr, Addr tag)
{
    if (delayQueue.size() == delayQueueSize) {
        return;
    }

    // Add the address to the delay queue and schedule an event to process
    // it after the specified delay cycles
    Tick process_tick = curTick() + delayTicks;

    delayQueue.push_back(DelayQueueEntry({full_addr, tag}, process_tick));

    if (!delayQueueEvent.scheduled()) {
        schedule(delayQueueEvent, process_tick);
    }
}

void
XSBOP::resetScores()
{
    for (auto& it : offsetsList) {
        it.score = 0;
    }
}

inline Addr
XSBOP::tag(Addr addr) const
{
    return (addr >> lBlkSize) & tagMask;
}

std::pair<bool, XSBOP::RREntryDebug>
XSBOP::testRR(Addr tag) const
{
    if (rrLeft[hash(tag, RRWay::Left)].hashAddr == tag) {
        return std::make_pair(true, rrLeft[hash(tag, RRWay::Left)]);
    }
    if (rrRight[hash(tag, RRWay::Right)].hashAddr == tag) {
        return std::make_pair(true, rrRight[hash(tag, RRWay::Right)]);
    }

    return std::make_pair(false, RREntryDebug());
}

bool
//BOP::tryAddOffset(int64_t offset, bool late)
XSBOP::tryAddOffset(int64_t offset)
{
    assert(offset != 0);
    bool find_it = std::find(offsetsList.begin(), offsetsList.end(), offset) != offsetsList.end();
    if (find_it) {
        return false;
    }
    if (victimOffsetsList.size() >= victimListSize) {
        return false;
    }

    if (offsetsList.size() >= maxOffsetCount) {
        int evict_offset = 0;
        auto it = offsetsList.begin();
        while (it != offsetsList.end()) {
            if (it->score <= badScore) {
                break;
            }
            it++;
        }
        if (it == offsetsList.end()) {
            // all offsets are good, erase the one before the iterator
            if (offsetsListIterator == offsetsList.begin()) {
                // the iterator is the first element, erase the last one
                auto end_offset = --offsetsList.end();
                evict_offset = end_offset->offset;
                offsetsList.erase(end_offset);
            } else {
                auto temp = --offsetsListIterator;
                evict_offset = temp->offset;
                offsetsListIterator = offsetsList.erase(temp);
            }
        } else {
            // erase it from set and list
            evict_offset = it->offset;
            if (it == offsetsListIterator) {
                offsetsListIterator = offsetsList.erase(it);  // update iterator
                if (offsetsListIterator == offsetsList.end()) {
                    offsetsListIterator = offsetsList.begin();
                }
            } else {
                offsetsList.erase(it);
            }
        }
        assert(evict_offset != 0);
        if (std::find(originOffsets.begin(), originOffsets.end(), evict_offset) != originOffsets.end()) {
            victimOffsetsList.push_back(evict_offset);
        }
    }

    auto best_it = getBestOffsetIter();

    auto offset_it = std::find(offsetsList.begin(), offsetsList.end(), offset);
    if (offset_it == offsetsList.end()) {
        bool found = false;
        for (auto it = offsetsList.begin(); it != offsetsList.end(); it++) {
            if (it == offsetsListIterator) {
                found = true;
            }
        }
        assert(found);
        // insert it next to the offsetsListIterator
        auto next_it = std::next(offsetsListIterator);
        offsetsList.emplace(next_it, (int32_t) offset, (uint8_t) 0);
        stats.learnOffsetCount++;

    } else {
        bool found = false;
        for (auto it = offsetsList.begin(); it != offsetsList.end(); it++) {
            if (it->offset == offset) {
                found = true;
                break;
            } 
        }
        assert(found);
    }
    return true;
}

std::list<XSBOP::OffsetListEntry>::iterator
XSBOP::getBestOffsetIter()
{
    return std::find(offsetsList.begin(), offsetsList.end(), bestOffset);
}

bool
//BOP::bestOffsetLearning(Addr x, bool late, const PrefetchInfo &pfi)
XSBOP::bestOffsetLearning(Addr x, const PrefetchInfo &pfi)
{
    Addr offset = offsetsListIterator->calcOffset();
    Addr lookup_addr = x - offset;
    // There was a hit in the RR table, increment the score for this offset
    auto [exist, rr_entry] = testRR(lookup_addr);
    if (exist) {
        //if (archDBer) {
        //    archDBer->xsbopTrainTraceWrite(curTick(), rr_entry.fullAddr, pfi.getAddr(), offset,
        //                                offsetsListIterator->score + 1, pfi.isCacheMiss());
        //}

        offsetsListIterator->score++;

        if (offsetsListIterator->score >= round / 2) {
            // if (late) {
            //     offsetsListIterator->late += 2;
            // } else {
            //     offsetsListIterator->late--;
            // }

            auto best_it = getBestOffsetIter();
            bool update_depth = false;
            // if (offsetsListIterator->late > (uint8_t)42) {
            //     offsetsListIterator->depth++;
            //     update_depth = true;
            // }
            // if (offsetsListIterator->late < (uint8_t)4) {
            //     offsetsListIterator->depth = std::max(1, offsetsListIterator->depth - 1);
            //     update_depth = true;
            // }

            if (update_depth) {
                if (best_it == offsetsListIterator) {
                    bestOffset = best_it->calcOffset();
                }
                //offsetsListIterator->late.reset();
            }
        }

        if (offsetsListIterator->score > bestScore) {
            bestoffsetsListIterator = offsetsListIterator;
            bestScore = (*offsetsListIterator).score;
            phaseBestOffset = offsetsListIterator->calcOffset();
        }
    }

    offsetsListIterator++;

    // All the offsets in the list were visited meaning that a learning
    // phase finished. Check if
    if (offsetsListIterator == offsetsList.end()) {
        offsetsListIterator = offsetsList.begin();
        round++;

        // Check if the best offset must be updated if:
        // (1) One of the scores equals SCORE_MAX
        // (2) The number of rounds equals ROUND_MAX
        if ((bestScore >= scoreMax) || (round == roundMax)) {
            if (bestScore > badScore) {
                issuePrefetchRequests = true;
            } else {
                issuePrefetchRequests = false;
            }

            bestOffset = phaseBestOffset;
            round = 0;
            bestScore = 0;
            phaseBestOffset = 0;
            resetScores();
            //issuePrefetchRequests = true;
            return true;
        } else if ((round >= roundMax/2) && (bestOffset != phaseBestOffset) && (bestScore <= badScore)) {
            issuePrefetchRequests = false;
        }
    }
    return false;
}

void
XSBOP::calculatePrefetch(const PrefetchInfo &pfi,
        std::vector<AddrPriority> &addresses)
{
    if (!pfi.hasPC()) {
        DPRINTF(HWPrefetch, "Ignoring request with no PC.\n");
        return;
    }
    Addr pc = pfi.getPC();
    Addr addr = blockAddress(pfi.getAddr());
    Addr tag_x = tag(addr);

    bool cachemiss = pfi.isCacheMiss();
	if (cachemiss) DPRINTF(CacheMiss, "V02::pc:%0#x,addr:%0#x\n",pc,addr);

    if (delayQueueEnabled) {
        insertIntoDelayQueue(addr, tag_x);
    } else {
        insertIntoRR(addr, tag_x, RRWay::Left);
    }

    // Go through the nth offset and update the score, the best score and the
    // current best offset if a better one is found
    bestOffsetLearning(tag_x, pfi);

    // This prefetcher is a degree 1 prefetch, so it will only generate one
    // prefetch at most per access
    if (issuePrefetchRequests) {
        Addr prefetch_addr = addr + (bestOffset << lBlkSize);
        stats.issuedOffsetDist.sample(bestOffset);
        sendPFWithFilter(pfi, prefetch_addr,addresses);

    } else {
        stats.throttledCount++;
    }

    if (!victimRestoreScheduled && victimOffsetsList.size() > 0) {
        victimRestoreScheduled = true;
        schedule(restore_event, cyclesToTicks(curCycle() + Cycles(restoreCycle)));
    }

}

bool
XSBOP::sendPFWithFilter(const PrefetchInfo &pfi, Addr addr, std::vector<AddrPriority> &addresses)
{
    if (filter.contains(addr)) {
        return false;
    } else {
        filter.insert(addr);
        addresses.push_back(std::make_pair(static_cast<long unsigned int>(addr), 0));
        return true;
    }
}


void
XSBOP::notifyFill(const PacketPtr& pkt)
{

}

XSBOP::XSBopStats::XSBopStats(statistics::Group *parent)
    : statistics::Group(parent),
      ADD_STAT(issuedOffsetDist, statistics::units::Count::get(), "Distribution of issued offsets"),
      ADD_STAT(learnOffsetCount, statistics::units::Count::get(), "Number of learning offsets"),
      ADD_STAT(throttledCount, statistics::units::Count::get(), "Number of throttled prefetches")
{
    issuedOffsetDist.init(-64, 256, 1).prereq(issuedOffsetDist);
}

} // namespace prefetch
} // namespace gem5
