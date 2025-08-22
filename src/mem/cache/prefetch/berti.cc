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

#include "mem/cache/prefetch/berti.hh"
#include "mem/cache/base.hh"
#include "params/BertiPrefetcher.hh"
#include "mem/cache/prefetch/associative_set_impl.hh"
#include "debug/HWPrefetch.hh"
#include "debug/CacheMiss.hh"
#include "sim/cur_tick.hh"

namespace gem5
{
namespace prefetch
{

// BertiPrefetcher::BertiStats::BertiStats(statistics::Group *parent)
//     : statistics::Group(parent),
    // ADD_STAT(updateHistoryTableCycles, statistics::units::Count::get(),
    //          "Cycles spent in updateHistoryTable"),
    // ADD_STAT(searchTimelyDeltasCycles, statistics::units::Count::get(),
    //          "Cycles spent in searchTimelyDeltas"),
    // ADD_STAT(calculatePrefetchCycles, statistics::units::Count::get(),
    //          "Cycles spent in calculatePrefetch")
// {
// }
BertiPrefetcher::BertiPrefetcher(const BertiPrefetcherParams &params)
    : Queued(params),
        historyTable(params.history_table_assoc, params.history_table_entries,
                  params.history_table_indexing_policy,
                  params.history_table_replacement_policy,
                  HistoryTableEntry(maxDeltaListSize)),
      maxAddrListSize(params.addrlist_size),
      maxDeltaListSize(params.deltalist_size),
      maxDeltafound(params.max_deltafound),
      aggressivePF(params.aggressive_pf),
      useByteAddr(params.use_byte_addr),
      triggerPht(params.trigger_pht),
      miss_refill_cycles(params.miss_refill_cycles),
      hit_search_latency_cycles(params.hit_search_latency_cycles),
      trainBlockFilter(params.max_trainBlockFilter_size),
      filter(params.max_filter_size)
    //   statsBerti(this)
      
{
    // 注册退出回调（标准gem5方式）
}

BertiPrefetcher::HistoryTableEntry*
BertiPrefetcher::updateHistoryTable(const PrefetchInfo &pfi)
{
    // Tick start = curTick();
    //根据配置参数 useByteAddr 决定是否使用字节粒度的地址
    //（使用时直接获取地址 pfi.getAddr()），否则使用块粒度的地址（通过 blockIndex(pfi.getAddr()) 获取地址所在的块索引）。
    // 然后创建一个 HistoryInfo 对象 new_info，
    // 包含访问的虚拟地址 training_addr 和当前模拟周期 curCycle() 作为时间戳。
    Addr training_addr = useByteAddr ? pfi.getAddr() : blockIndex(pfi.getAddr());
    // 根据当前程序计数器（PC）的哈希值 pcHash(pfi.getPC()) 和是否为安全访问 pfi.isSecure() 在历史表中查找对应的条目。
    HistoryTableEntry *entry =
        historyTable.findEntry(pcHash(pfi.getPC()), pfi.isSecure());
    HistoryInfo new_info = {
        .vAddr = training_addr,
        .timestamp = curCycle()
    };
    // 如果在历史表中找到了对应的条目 entry
    // 则首先将该条目标记为已访问（historyTable.accessEntry(entry)）
    // 然后使用 std::find 函数在该条目的 history 列表中查找是否包含 new_info 这个地址访问信息。
    if (entry) {
        historyTable.accessEntry(entry);
        DPRINTF(HWPrefetch, "PC=%lx, history table hit, Addr=%lx\n", pfi.getPC(), training_addr);

        bool found_addr_in_hist =
            std::find(entry->history.begin(), entry->history.end(), new_info) != entry->history.end();
        // 如果 new_info 不在历史列表中，则首先检查历史列表的大小是否已达上限 maxAddrListSize。
        if (!found_addr_in_hist) {
            // 如果达到了上限，则从列表前端（FIFO 替换策略）移除最早的历史记录。
            if (entry->history.size() >= maxAddrListSize) {
                entry->history.erase(entry->history.begin());
            }
            // 然后将 new_info 添加到历史列表中，并设置 hysteresis 标志为 true。
            entry->history.push_back(new_info);
            entry->hysteresis = true;
            return entry;
        } else {
            // 如果 new_info 已经存在于历史列表中，则说明该地址是重复访问的，
            // 因此忽略此次访问（return nullptr），不进行任何更新操作。
            DPRINTF(HWPrefetch, "PC=%lx, addr %lx found in history table hit, ignore\n", pfi.getPC(),
                    training_addr);
            return nullptr;  // ignore redundant req
        }
    } else {
        // 如果在历史表中没有找到对应的条目 entry，则说明这是一次新的访问，
        // 因此需要在历史表中插入一个新的条目。
        DPRINTF(HWPrefetch, "PC=%lx, history table miss\n", pfi.getPC());
        entry = historyTable.findVictim(pcHash(pfi.getPC()));
        if (entry->hysteresis) {
            // 如果找到的条目具有 hysteresis 标志，则将其重置为 false，并重新插入历史表。
            entry->hysteresis = false;
            historyTable.insertEntry(pcHash(entry->pc), entry->isSecure(), entry);
        } else {
            // 这行代码判断在历史表的当前条目中，bestDelta 的状态是否不等于 NO_PREF。
            // bestDelta 通常包含了与最佳预取偏移量相关的信息。
            // 如果状态为 NO_PREF，表示没有可推荐的预取地址，后面的代码将不会执行。
            if (entry->bestDelta.status != NO_PREF) {
                // 这里计算了访问地址 pfi.getAddr() 经过 bestDelta.delta 偏移后的块级索引与当前地址块级索引之间的差值 blk_delta。
                // 这个计算旨在识别预期的预取地址在块中的位置变化。
                int64_t blk_delta =
                    (int64_t)blockIndex(pfi.getAddr() + entry->bestDelta.delta) - blockIndex(pfi.getAddr());
                // evictedBestDelta 用于跟踪最近被替换的最佳预取偏移。
                if (!useByteAddr) {
                    evictedBestDelta = entry->bestDelta.delta;
                } else {
                    evictedBestDelta = blk_delta;
                }
                //statsBerti.entryEvicts++;
                // 使用 evictedDeltas 计数器记录相同 blk_delta 偏移量的出现次数，
                // 若之前已经存在这个偏移值，则加1；否则初始化为1。
                // 这样做可以跟踪各种偏移量的使用情况。
                //evictedDeltas[blk_delta] = evictedDeltas.count(blk_delta) ? evictedDeltas[blk_delta] + 1 : 1;
            }
            // only when hysteresis is false
            entry->pc = pfi.getPC();
            entry->history.clear();
            entry->history.push_back(new_info);
            historyTable.insertEntry(pcHash(pfi.getPC()), pfi.isSecure(), entry);
        }
    }
    // funcStats.updateHistoryTableTime += curTick() - start;
    // statsBerti.updateHistoryTableCycles = funcStats.updateHistoryTableTime;
    return nullptr;
}


void BertiPrefetcher::searchTimelyDeltas(
    HistoryTableEntry &entry,
    const unsigned int &search_latency,
    const Cycles &demand_cycle,
    const Addr &trigger_addr)
{
    // Tick start = curTick();

    DPRINTF(HWPrefetch, "latency: %lu, demand_cycle: %lu, history count: %lu\n", search_latency, demand_cycle,
            entry.history.size());
    std::list<int64_t> new_deltas;
    int delta_thres = useByteAddr ? blkSize : 8;
    // 其主要目的是从历史访问记录中查找符合条件的地址偏移量（delta），
    // 并将这些偏移量添加到一个新的列表 new_deltas 中。
    // 这里使用了反向迭代器 rbegin() 和 rend() 来从历史记录列表的末尾开始向前遍历。
    // entry.history 是一个保存历史访问记录的列表，每个记录包括访问的虚拟地址 vAddr 和访问的时间戳 timestamp。
    for (auto it = entry.history.rbegin(); it != entry.history.rend(); it++) {
        // 对于每个历史访问记录，计算当前触发地址 trigger_addr 与历史访问地址 it->vAddr 之间的偏移量，
        // 并打印该偏移量。这个偏移量 delta 代表了从历史访问地址到触发地址的距离。
        int64_t delta = trigger_addr - it->vAddr;
        DPRINTF(HWPrefetch, "delta (%x - %x) = %ld\n", trigger_addr, it->vAddr, delta);

        // skip short deltas
        // 如果偏移量 delta 的绝对值小于或等于 delta_thres
        // （这个阈值根据是否使用字节粒度地址由 blkSize 或 8 确定），
        // 那么认为这个偏移量太短，不值得记录，直接跳过该历史记录，继续下一项。
        if (labs(delta) <= delta_thres) {
            continue;
        }

        // if not timely, skip and continue
        // 对于每个历史访问记录，除了检查偏移量长度外，
        // 还需要判断该记录的时间戳加上搜索延迟 search_latency 是否小于当前的周期 demand_cycle。
        // 如果这个条件不满足（意味着历史访问与当前访问间隔时间太短，预取可能不会产生效益），则跳过该历史记录，继续下一项
        if (it->timestamp + search_latency >= demand_cycle) {
            DPRINTF(HWPrefetch, "skip untimely delta: %lu + %lu <= %u : %ld\n", it->timestamp, search_latency,
                    demand_cycle, delta);
            continue;
        }
        assert(delta != 0);
        // 如果该历史访问记录满足上述两个条件（即偏移量足够长且访问间隔足够长），
        // 则将这个偏移量 delta 添加到新的偏移量列表 new_deltas 中，并打印该项。
        new_deltas.push_back(delta);
        DPRINTF(HWPrefetch, "Timely delta found: %d=(%x - %x)\n", delta, trigger_addr, it->vAddr);
        // 如果达到了这个上限，表示已经找到了足够的合格偏移量，因此跳出循环，不再继续查找更多的历史记录。
        if (new_deltas.size() >= maxDeltafound) {
            break;
        }
    }

    entry.counter++;
    // 遍历之前找到的新偏移量列表new_deltas。对于每个新找到的偏移量delta，执行以下处理。
    for (auto &delta : new_deltas) {
        // miss变量用于标记当前新发现的偏移量delta是否已经存在于历史表条目的偏移量列表entry.deltas中。
        bool miss = true;
        // 内层循环遍历entry.deltas列表，查找是否有与delta相同的偏移量。
        // 如果找到了相同的偏移量delta，
        // 则将对应的delta_info的覆盖计数coverageCounter加一，并将miss设为false，然后跳出内层循环。
        for (auto &delta_info : entry.deltas) {
            if (delta_info.coverageCounter != 0 && delta_info.delta == delta) {
                delta_info.coverageCounter++;
                DPRINTF(HWPrefetch, "Inc coverage for delta %d, cov = %d\n", delta, delta_info.coverageCounter);
                miss = false;
                break;
            }
        }
        // miss
        // 如果miss为true，意味着当前的新发现的偏移量delta在entry.deltas中不存在。
        if (miss) {
            // find the smallest coverage and replace
            int replace_idx = 0;
            // 为了容纳新的偏移量，需要查找entry.deltas中coverageCounter最小的偏移量，并将其替换为新的偏移量delta。
            for (auto i = 0; i < entry.deltas.size(); i++) {
                if (entry.deltas[replace_idx].coverageCounter >= entry.deltas[i].coverageCounter) {
                    replace_idx = i;
                }
            }
            entry.deltas[replace_idx].delta = delta;
            entry.deltas[replace_idx].coverageCounter = 1;
            entry.deltas[replace_idx].status = NO_PREF;
            DPRINTF(HWPrefetch, "Add new delta: %d with cov = 1\n", delta);
        }
    }

    if (entry.counter >= 6) {
        entry.updateStatus();
        if (entry.counter >= 16) {
            entry.resetConfidence(false);
        }
    }
    // funcStats.searchTimelyDeltasTime += curTick() - start;

    // statsBerti.searchTimelyDeltasCycles = funcStats.searchTimelyDeltasTime;
    //printDeltaTableEntry(entry);
}
void
BertiPrefetcher::calculatePrefetch(const PrefetchInfo &pfi, std::vector<AddrPriority> &addresses)
{
    if (!pfi.hasPC()) {
        return;
    }
    Addr pc = pfi.getPC();
    Addr addr = pfi.getAddr();
    bool cachemiss = pfi.isCacheMiss();
	if (cachemiss) DPRINTF(CacheMiss, "V02::pc:%0#x,addr:%0#x\n",pc,addr);

    // reset learned delta
    evictedBestDelta = 0;
    lastUsedBestDelta = 0;
    Addr local_delta_pf_addr = 0;
    //BaseCache* cache = this->cache;
    //CacheLatency = cache->getcacheLatency()/1000 + (cache->getcacheLatency()%1000 > 500);
    // Tick start = curTick();
    CacheLatency = 25;
    DPRINTF(HWPrefetch,
            "Train prefetcher, pc: %lx, addr: %lx miss: %d last lat: [%d]\n",
            pfi.getPC(), blockAddress(pfi.getAddr()),
            pfi.isCacheMiss(), hitSearchLatency);
    // printf("Train prefetcher, pc: %lx, addr: %lx miss: %d last lat: [%d]\n",
    //         pfi.getPC(), blockAddress(pfi.getAddr()),
    //         pfi.isCacheMiss(), hitSearchLatency);

    trainBlockFilter.insert(blockIndex(pfi.getAddr()), 0);
    //LRUFilter.insert(blockIndex(pfi.getAddr()), 0);

    if (!pfi.isCacheMiss()) {
        HistoryTableEntry *hist_entry = historyTable.findEntry(pcHash(pfi.getPC()), pfi.isSecure());
        if (hist_entry) {
            searchTimelyDeltas(*hist_entry, CacheLatency, curCycle(),
                               useByteAddr ? pfi.getAddr() : blockIndex(pfi.getAddr()));
            //statsBerti.trainOnHit++;
        }
    }

    /** 1.train: update history table and compute learned delta*/
    auto entry = updateHistoryTable(pfi);

    /** 2.prefetch: search table of deltas, issue prefetch request */
    if (entry) {
        DPRINTF(HWPrefetch, "Delta table hit, pc: %lx\n", pfi.getPC());
        if (aggressivePF) {
            // 启用了激进预取策略，代码会遍历entry->deltas列表中的每个delta_info。
            // 对于每个有效的偏移量（delta_info.status != NO_PREF），
            // 代码会计算预取地址pf_addr，并调用sendPFWithFilter函数发送预取请求。
            // 预取地址的计算方式取决于是否使用字节粒度地址useByteAddr。
            for (auto &delta_info : entry->deltas) {
                if (delta_info.status != NO_PREF) {
                    DPRINTF(HWPrefetch, "Using delta %d to prefetch\n", delta_info.delta);
                    int64_t delta = delta_info.delta;
                    Addr pf_addr =
                        useByteAddr ? pfi.getAddr() + delta : (blockIndex(pfi.getAddr()) + delta) << lBlkSize;
                    sendPFWithFilter(pfi, pf_addr, addresses, delta == entry->bestDelta.delta && entry->bestDelta.coverageCounter >= 8);
                }
            }
        } else {
            // 如果未启用激进预取策略，则仅使用bestDelta计算预取地址pf_addr。
            // 同样地，预取地址的计算方式取决于是否使用字节粒度地址useByteAddr。
            // 然后调用sendPFWithFilter函数发送预取请求。
            // 如果triggerPht标志为真且bestDelta的覆盖计数超过5，则将pf_addr赋值给local_delta_pf_addr。
            if (entry->bestDelta.status != NO_PREF) {
                DPRINTF(HWPrefetch, "Using best delta %d to prefetch\n", entry->bestDelta.delta);
                Addr pf_addr = useByteAddr ? pfi.getAddr() + entry->bestDelta.delta
                                           : (blockIndex(pfi.getAddr()) + entry->bestDelta.delta) << lBlkSize;
                sendPFWithFilter(pfi, pf_addr, addresses, entry->bestDelta.coverageCounter >= 8);
                if (triggerPht && entry->bestDelta.coverageCounter > 5) {
                    local_delta_pf_addr = pf_addr;
                }
            }
        }
    }
    // funcStats.calculatePrefetchTime += curTick() - start;
    // statsBerti.calculatePrefetchCycles = funcStats.calculatePrefetchTime;
    
}
// 负责根据预取算法生成的预取地址addr来决定是否发送预取请求，并对预取地址进行记录和过滤。
bool
BertiPrefetcher::sendPFWithFilter(const PrefetchInfo &pfi, Addr addr, std::vector<AddrPriority> &addresses,
                                    bool using_best_delta_and_confident)
{
    // 首先检查是否存在archDBer（一个架构相关的数据库或日志记录器）的对象，
    // 并且当前缓存级别是否为1级缓存。如果是，则调用archDBer的l1PFTraceWrite方法记录当前预取信息，包括当前模拟周期、程序计数器、触发地址、预取地址以及预取源类型。
    // if (archDBer && cache->level() == 1) {
    //     archDBer->l1PFTraceWrite(curTick(), pfi.getPC(), pfi.getAddr(), addr, src);
    // }
    DPRINTF(HWPrefetch, "Checking prefetch candidate %#lx for addr %#lx\n", 
            addr, pfi.getAddr());
    //如果参数using_best_delta_and_confident为真，
    // 表示当前使用的预取偏移量delta是来自最佳预取偏移量bestDelta且具有较高的置信度，
    // 则更新lastUsedBestDelta为当前预取地址与触发地址之间的块级偏移量。 
    if (using_best_delta_and_confident) {
        lastUsedBestDelta = blockIndex(addr) - blockIndex(pfi.getAddr());
    }
    // if (alreadyInQueue(addr, pfi,0)) { // 第二个参数表示是否检查MSHR
    //     DPRINTF(HWPrefetch, "Skipping duplicate prefetch: %#lx\n", addr);
    //     return false;
    // }
    // 地址过滤，用于避免对最近已经预取过的地址进行重复预取。
    // xsgem5采用指针形式实现filter 大小可变，但是gem5中filter的大小固定为16
    if (filter.contains(addr)) {
        DPRINTF(HWPrefetch, "Skip recently prefetched: %lx\n", addr);
        return false;
    } else {
        //int64_t blk_delta = (int64_t)blockIndex(addr) - blockIndex(pfi.getAddr());
        //topDeltas[blk_delta] = topDeltas.count(blk_delta) ? topDeltas[blk_delta] + 1 : 1;
        DPRINTF(HWPrefetch, "Send pf: %lx\n", addr);
        filter.insert(addr);
        addresses.push_back(AddrPriority(addr, 0));
        return true;
    }
}
void
BertiPrefetcher::notifyFill(const PacketPtr &pkt)
{
    if (pkt->req->isInstFetch() ||
        !pkt->req->hasVaddr() || !pkt->req->hasPC()) {
        DPRINTF(HWPrefetch, "Skip packet: %s\n", pkt->print());
        //statsBerti.notifySkippedCond1++;
        return;
    }

    DPRINTF(HWPrefetch,
            "Cache Fill: %s isPF: %d, pc: %lx\n",
            pkt->print(), pkt->req->isPrefetch(), pkt->req->getPC());

    if (pkt->req->isPrefetch()) {
        //tatsBerti.notifySkippedIsPF++;
        return;
    }

    // fill latency
    //Cycles miss_refill_search_lat = Cycles(miss_refill_cycles);
    hitSearchLatency = Cycles(hit_search_latency_cycles);
    // 根据程序计数器 (pkt->req->getPC()) 的哈希值和安全标志 (pkt->req->isSecure()) 在历史表中查找对应的条目。
    // 如果没有找到对应的条目，则跳过该填充请求。
    HistoryTableEntry *entry =
        historyTable.findEntry(pcHash(pkt->req->getPC()), pkt->req->isSecure());
    if (!entry) {
        //statsBerti.notifySkippedNoEntry++;
        return;
    }

    /** Search history table, find deltas. */
    // 将填充请求的时间戳从 ticks 转换为 Cycles，得到 demand_cycle。
    Cycles demand_cycle = ticksToCycles(pkt->req->time());

    DPRINTF(HWPrefetch, "Search delta for PC %lx\n", pkt->req->getPC());
    searchTimelyDeltas(*entry, CacheLatency, demand_cycle,
                       useByteAddr ? pkt->req->getVaddr() : blockIndex(pkt->req->getVaddr()));
    //statsBerti.trainOnMiss++;

    DPRINTF(HWPrefetch, "Updating table of deltas, latency [%d]\n",
            CacheLatency);

}

} // namespace prefetch
} // namespace gem5