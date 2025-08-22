// berti.hh
#ifndef __MEM_CACHE_PREFETCH_BERTI_HH__
#define __MEM_CACHE_PREFETCH_BERTI_HH__

#include <list>
#include <unordered_map>
#include <vector>
#include <boost/compute/detail/lru_cache.hpp>
#include "base/statistics.hh"
#include "base/types.hh"
#include "mem/cache/prefetch/associative_set.hh"
#include "mem/cache/prefetch/queued.hh"
#include "mem/packet.hh"
#include "params/BertiPrefetcher.hh"
#include "debug/HWPrefetch.hh"
namespace gem5
{
namespace prefetch
{

class BertiPrefetcher : public Queued
{
    unsigned int CacheLatency;
    protected:
    struct HistoryInfo {
        Addr vAddr{0};
        Cycles timestamp{0};

        bool operator==(const HistoryInfo &rhs) const {
            return vAddr == rhs.vAddr;
        }
    };

    enum DeltaStatus { L1_PREF, L2_PREF, NO_PREF };
    struct DeltaInfo {
        uint8_t coverageCounter = 0;
        int delta = 0;
        DeltaStatus status = NO_PREF;
    };
    class TableOfDeltasEntry
    {
        public:
        std::vector<DeltaInfo> deltas;
        uint8_t counter = 0;
        DeltaInfo bestDelta;

        void resetConfidence(bool reset_status)
        {
            counter = 0;
            for (auto &info : deltas) {
                info.coverageCounter = 0;
                if (reset_status) {
                    info.status = NO_PREF;
                }
            }
            if (reset_status) {
                bestDelta.delta = 0;
                bestDelta.status = NO_PREF;
            }
        }

        void updateStatus()
        {
            uint8_t max_cov = 0;
            for (auto &info : deltas) {
                info.status = (info.coverageCounter >= 2) ? L2_PREF : NO_PREF;
                info.status = (info.coverageCounter >= 4) ? L1_PREF : info.status;
                if (info.status != NO_PREF && info.coverageCounter > max_cov) {
                    max_cov = info.coverageCounter;
                    bestDelta = info;
                }
            }
            if (max_cov == 0) {
                bestDelta.delta = 0;
                bestDelta.status = NO_PREF;
            }
        }

        TableOfDeltasEntry(int size) {
            deltas.resize(size);
        }
    };

    class HistoryTableEntry : public TableOfDeltasEntry, public TaggedEntry
    {
        public:
            bool hysteresis = false;
            Addr pc = ~(0UL);
            /** FIFO of demand miss history. */
            std::list<HistoryInfo> history;
        HistoryTableEntry(int deltaTableSize) : TableOfDeltasEntry(deltaTableSize) {}
    };


    AssociativeSet<HistoryTableEntry> historyTable;

    // Parameters
    Cycles hitSearchLatency;
    int lastUsedBestDelta;
    int evictedBestDelta;
    const unsigned maxAddrListSize;
    const unsigned maxDeltaListSize;
    const unsigned maxDeltafound;
    const bool aggressivePF;
    const bool useByteAddr;
    const bool triggerPht;
    const int miss_refill_cycles;
    const int hit_search_latency_cycles;
    // const Cycles hitSearchLatency;
    // const Cycles miss_refill_search_lat;
    // const bool max_filter_size;

    
    

    
    // Helper methods
    Addr pcHash(Addr pc) const { return pc >> 1 ^ (pc >> 4); }
    
    HistoryTableEntry* updateHistoryTable(const PrefetchInfo &pfi);
    void printDeltaTableEntry(const TableOfDeltasEntry &entry) {
        DPRINTF(HWPrefetch, "Entry Counter: %d\n", entry.counter);
        for (auto &info : entry.deltas) {
            DPRINTF(HWPrefetch,
                    "=>[delta: %d coverage: %d status: %d]\n",
                    info.delta, info.coverageCounter, info.status);
        }
    }


    boost::compute::detail::lru_cache<Addr, Addr> trainBlockFilter;
    


    std::unordered_map<int64_t, uint64_t> topDeltas;

    std::unordered_map<int64_t, uint64_t> evictedtrainBlockFilterDeltas;


    // LRU filter (替换boost的lru_cache)
    class LRUFilter {
        std::list<Addr> entries;
        std::unordered_map<Addr, std::list<Addr>::iterator> cacheMap;
        size_t capacity;
      public:
        LRUFilter(size_t size) : capacity(size) {}
        bool contains(Addr addr) const { return cacheMap.count(addr); }
        void insert(Addr addr) {
            if (contains(addr)) entries.erase(cacheMap[addr]);
            else if (entries.size() >= capacity) {
                cacheMap.erase(entries.back());
                entries.pop_back();
            }
            entries.push_front(addr);
            cacheMap[addr] = entries.begin();
        }
    }filter;
    // struct BertiStats : public statistics::Group
    // {
    //     BertiStats(statistics::Group *parent);
    //     // STATS
    //     statistics::Scalar updateHistoryTableCycles;
    //     statistics::Scalar searchTimelyDeltasCycles;
    //     statistics::Scalar calculatePrefetchCycles;
    // } statsBerti;
    struct FunctionStats {
        Tick updateHistoryTableTime = 0;
        Tick searchTimelyDeltasTime = 0;
        Tick calculatePrefetchTime = 0;
        // 添加其他需要统计的函数...
    } funcStats;

  public:
     //LRUFilter filter;
  
    //boost::compute::detail::lru_cache<Addr, Addr> *filter;
    BertiPrefetcher(const BertiPrefetcherParams &params);
    // ~BertiPrefetcher()
    // {
    //     delete filter; // 释放filter占用的内存
    // }
    void searchTimelyDeltas(HistoryTableEntry &entry,
                            const unsigned int  &latency,
                            const Cycles &demand_cycle,
                            const Addr &blk_addr);
    bool sendPFWithFilter(const PrefetchInfo &pfi, Addr addr, std::vector<AddrPriority> &addresses, bool using_best_delta_and_confident);
    void calculatePrefetch(const PrefetchInfo &pfi,
                          std::vector<AddrPriority> &addresses) override;
    void notifyFill(const PacketPtr &pkt) override;
};

} // namespace prefetch
} // namespace gem5

#endif