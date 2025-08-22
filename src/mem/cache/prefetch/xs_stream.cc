#include "mem/cache/prefetch/xs_stream.hh"

#include "debug/HWPrefetch.hh"
#include "mem/cache/prefetch/associative_set_impl.hh"
#include "debug/CacheMiss.hh"

namespace gem5
{
namespace prefetch
{

XsStreamPrefetcher::XsStreamPrefetcher(const XsStreamPrefetcherParams &p)
    : Queued(p),
      depth(p.xs_stream_depth),
      badPreNum(0),
      enableAutoDepth(p.enable_auto_depth),
      enableL3StreamPre(p.enable_l3_stream_pre),
      stream_array(p.xs_stream_entries, p.xs_stream_entries, p.xs_stream_indexing_policy,
                   p.xs_stream_replacement_policy, STREAMEntry()),
      streamBlkFilter(pfFilterSize),
      filter(p.max_filter_size)
{
}
void
XsStreamPrefetcher::calculatePrefetch(const PrefetchInfo &pfi, std::vector<AddrPriority> &addresses)
{
    if (!pfi.hasPC()) {
        DPRINTF(HWPrefetch, "Ignoring request with no PC.\n");
        return;
    }
    Addr pc = pfi.getPC();
    Addr vaddr = pfi.getAddr();
    Addr block_addr = blockAddress(vaddr);
    //PrefetchSourceType stream_type = PrefetchSourceType::SStream;
    bool in_active_page = false;
    bool decr = false;
    //if (pfi.isStore()) {
    //    stream_type = PrefetchSourceType::StoreStream;
    //    DPRINTF(XsStreamPrefetcher, "prefetch trigger come from store unit\n");
    //}
    if (pfi.isCacheMiss() && (streamBlkFilter.contains(block_addr))) {
        badPreNum++;
    }

    bool cachemiss = pfi.isCacheMiss();
	if (cachemiss) DPRINTF(CacheMiss, "V02::pc:%0#x,addr:%0#x\n",pc,vaddr);

    STREAMEntry *entry = streamLookup(pfi, in_active_page, decr);
    if ((issuedPrefetches >= VALIDITYCHECKINTERVAL) && (enableAutoDepth)) {
        //if ((double)late_num / issuedPrefetches >= LATECOVERAGE) {
        //    if (depth != DEPTHRIGHT)
        //        depth = depth << DEPTHSTEP;
        //}
        if (badPreNum > LATEMISSTHRESHOLD) {
            badPreNum = 0;
            if (depth != DEPTHLEFT) {
                depth = depth >> DEPTHSTEP;
            }
        }
        issuedPrefetches = 0;
    }

    if (in_active_page) {
        Addr pf_stream_l1 = decr ? block_addr - depth * blkSize : block_addr + depth * blkSize;
        sendPFWithFilter(pfi, pf_stream_l1, addresses);
        Addr pf_stream_l2 =
            decr ? block_addr - (depth << l2Ratio) * blkSize : block_addr + (depth << l2Ratio) * blkSize;
        sendPFWithFilter(pfi, pf_stream_l2, addresses);
        //if (enableL3StreamPre) {
        //    Addr pf_stream_l3 =
        //        decr ? block_addr - (depth << l3Ratio) * blkSize : block_addr + (depth << l3Ratio) * blkSize;
        //    sendPFWithFilter(pfi, pf_stream_l3, addresses);
        //}
    }
}

XsStreamPrefetcher::STREAMEntry *
XsStreamPrefetcher::streamLookup(const PrefetchInfo &pfi, bool &in_active_page, bool &decr)
{
    Addr pc = pfi.getPC();
    Addr vaddr = pfi.getAddr();
    Addr vaddr_tag_num = tagAddress(vaddr);
    Addr vaddr_offset = tagOffset(vaddr);
    bool secure = pfi.isSecure();

    STREAMEntry *entry = stream_array.findEntry(regionHashTag(vaddr_tag_num), pfi.isSecure());
    STREAMEntry *entry_plus = stream_array.findEntry(regionHashTag(vaddr_tag_num + 1), pfi.isSecure());
    STREAMEntry *entry_min = stream_array.findEntry(regionHashTag(vaddr_tag_num - 1), pfi.isSecure());

    if (entry) {
        stream_array.accessEntry(entry);
        uint64_t region_bit_accessed = 1UL << vaddr_offset;
        if (entry_plus)
            entry->decrMode = true;
        if ((entry_plus || entry_min) || (entry->cnt > ACTIVETHRESHOLD))
            entry->active = true;
        in_active_page = entry->active;
        decr = entry->decrMode;
        if (!(entry->bitVec & region_bit_accessed)) {
            entry->cnt += 1;
        }
        return entry;
    }
    entry = stream_array.findVictim(0);

    in_active_page = (entry_plus || entry_min);
    decr = entry_plus != nullptr;
    entry->tag = regionHashTag(vaddr_tag_num);
    entry->decrMode = entry_plus != nullptr;
    entry->bitVec = 1UL << vaddr_offset;
    entry->cnt = 1;
    entry->active = (entry_plus != nullptr) || (entry_min != nullptr);
    stream_array.insertEntry(regionHashTag(vaddr_tag_num), secure, entry);
    return entry;
}
bool
XsStreamPrefetcher::sendPFWithFilter(const PrefetchInfo &pfi, Addr addr, std::vector<AddrPriority> &addresses)
{
    if (filter.contains(addr)) {
        return false;
    } else {
        filter.insert(addr);
        addresses.push_back(std::make_pair(static_cast<long unsigned int>(addr), 0));
        streamBlkFilter.insert(addr, 0);
        return true;
    }
}

}
}
