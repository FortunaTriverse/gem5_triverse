

#include "mem/cache/prefetch/ipcp.hh"

#include <cassert>
#include "debug/HWPrefetch.hh"
// #include "debug/IPCP.hh"

namespace gem5
{

namespace prefetch
{

IPCP::IPCP(const IPCPParams &p)
    : Queued(p),
      degree(p.degree),
      ipt_size(p.ipt_size),
      cspt_size(p.cspt_size)
      //ipcpStats(this)
{
    assert((ipt_size & (ipt_size - 1)) == 0);
    assert((cspt_size & (cspt_size - 1)) == 0);
    if (p.use_rrf) {
        rrf = new boost::compute::detail::lru_cache<Addr, Addr>(32);
    }

    ipt.resize(ipt_size);
    cspt.resize(cspt_size);

    lipt_size = floorLog2(ipt_size);
    for (auto &it : ipt) {
        it.hysteresis = false;
        it.last_addr = 0;
    }
    for (auto &it : cspt) {
        it.confidence = 0;
    }
}

// IPCP::StatGroup::StatGroup(statistics::Group *parent)
//     : statistics::Group(parent),
//       ADD_STAT(class_cs, statistics::units::Count::get(),
//             "demands not covered by prefetchs"),
//       ADD_STAT(class_cplx, statistics::units::Count::get(),
//             "demands not covered by prefetchs"),
//       ADD_STAT(cplx_issued, statistics::units::Count::get(),
//             "demands not covered by prefetchs")
// {

// }


// 主要功能是在内存访问时，根据最近请求过滤器rrf来决定是否发送预取请求。
// 如果目标地址已经在rrf中存在，则认为该地址已经被预取过，不会再次发送预取请求；
// 否则，将目标地址插入到rrf中，并将预取请求的信息添加到addresses向量中，表示成功发送了预取请求。
// 这样可以避免对同一个地址进行不必要的重复预取，提高预取的有效性和效率
bool
IPCP::sendPFWithFilter(const PrefetchInfo &pfi, Addr addr, std::vector<AddrPriority> &addresses, int prio
                    )
{
    assert(rrf);
    // 通过rrf->contains(addr)检查当前地址是否已经被预取过。
    if (rrf->contains(addr)) {
        DPRINTF(HWPrefetch, "IPCP PF filtered\n");
        // ipcpStats.pf_filtered++;
        return false;
    } else {
        // 如果地址不在rrf中，则将其插入rrf。
        // 同时，将预取请求的目标地址、优先级和来源类型以AddrPriority对象的形式添加到addresses向量中。
        // 返回true，表示成功发送预取请求。
        rrf->insert(addr, 0);
        addresses.push_back(AddrPriority(addr, prio));
        return true;
    }
    return false;
}


// 主要功能是在CSPTable中查找一个特定的条目，并根据传入的新的步长值new_stride来更新这个条目的置信度（confidence）。
// 如果新的步长值与现有条目的步长值相同，则置信度增加；
// 反之，置信度减少，如果置信度减少到0，则根据update参数的值决定是否将abort标志设置为true，并更新步长值。
// 这种机制是用于动态调整预取策略的有效性，避免对那些置信度低的内存访问模式进行无效的预取操作，提高缓存命中率和系统性能。
IPCP::CSPEntry*
IPCP::cspLookup(uint32_t signature, int new_stride, bool update)
{
    // 根据传入的signature，通过compressSignature函数将签名压缩到适合CSPTable大小的范围内，然后获取对应位置的CSPEntry。
    auto& csp = cspt[compressSignature(signature)];
    // 如果当前条目的步长值（csp.stride）与新的步长值（new_stride）相同，则增加该条目的置信度（csp.confidence）。
    if (csp.stride == new_stride) {
        csp.incConf();
    }
    else {
        // 否则减少置信度
        // 如果置信度减少到0，则根据update参数的值决定是否将abort标志设置为true，并更新步长值。
        csp.decConf();
        if (csp.confidence == 0) {
            // alloc new csp entry
            if (update) {
                csp.abort = false;
            }
            else {
                csp.abort = true;
            }
            csp.stride = new_stride;
        }
    }

    return &csp;
}

//**************************************************************************
// 主要功能是在内存访问时，根据程序计数器 pc 和预取地址 pf_addr，在 ipt 表中查找相应的条目。
// 如果找到匹配的条目，则根据访问模式更新步长信息和置信度，并决定是否进行复杂步长预取或连续步长预取，
// 同时更新相应的统计信息。
// 如果找不到匹配的条目，则在 ipt 表中为该访问模式分配一个新的条目，并进行初始化。
// 这个过程有助于动态调整预取策略的有效性，避免对无效的访问模式进行预取，从而提高缓存命中率和系统性能。
//**************************************************************************
IPCP::IPEntry *
IPCP::ipLookup(Addr pc, Addr pf_addr, Classifier &type, int &new_stride)
{
    auto &ip = ipt[getIndex(pc)];
    IPEntry *ret = nullptr;
    // 计算当前访问地址 pf_addr 与上一次访问地址 ip.last_addr 之间的步长
    new_stride = ((pf_addr - ip.last_addr) >> lBlkSize) & stride_mask;
    // 如果 pf_addr 大于 ip.last_addr 且步长在 stride_mask 范围内，则 update 为 true。
    // 前向预取
    bool update = (pf_addr > ip.last_addr) && (((pf_addr - ip.last_addr) >> lBlkSize) <= stride_mask);
    if (!update) {
        new_stride = 0;
    }

    DPRINTF(HWPrefetch, "IPCP cplx last_addr: %lx, cur_addr: %lx, stride: %d\n", ip.last_addr, pf_addr, new_stride);
    // 检查 ip 条目的 tag 是否与根据 pc 计算出的 tag 匹配。
    if (ip.tag == getTag(pc)) {
        
        // 如果 ip 条目的 hysteresis 标志为 false，则将其设置为 true。
        // hysteresis 可能是用来防止误判的机制。
        if (!ip.hysteresis) {
            ip.hysteresis = true;
        }

        CSPEntry* csp = nullptr;

        // cs class
        if (update) {
            // 连续步长信息的步长与当前步长相等，则增加置信度；
            // 否则减少置信度，并在置信度为 0 时更新步长信息。
            if (ip.cs_stride == new_stride) {
                ip.cs_incConf();
            } else {
                ip.cs_decConf();
                if (ip.cs_confidence == 0) {
                    ip.cs_stride = new_stride;
                }
            }
            // 置信度的值调整 cs_degree，即连续步长预取的深度
            if (ip.cs_confidence > cs_thre) {
                cs_degree = 4;
                if (ip.cs_confidence == 2) {
                    cs_degree = 2;
                }
                type = CLASS_CS;
            }
        }
        else {
            ip.cs_decConf();
        }

        // cplx class
        //  cspLookup 函数在 cspt 表中查找与当前 signature 和 new_stride 相关的条目。
        csp = cspLookup(ip.signature, new_stride, update);

        // select
        // 如果找到了相应的条目，则根据置信度决定是否将 type 设置为 CLASS_CPLX，即复杂步长类。
        if (csp) {
            if ((type == NO_PREFETCH) || (ip.cs_confidence < csp->confidence)) {
                type = CLASS_CPLX;
            }
        }
        // 如果 type 是 CLASS_CPLX 但置信度未超过 cplx_thre，则将 type 重新设置为 NO_PREFETCH。
        if (type == CLASS_CPLX && !(csp->confidence > cplx_thre)) {
            type = NO_PREFETCH;
        }

        if (type == CLASS_CS) {
            //ipcpStats.class_cs++;
        }
        else if (type == CLASS_CPLX) {
            //ipcpStats.class_cplx++;
        }
        // 调用 sign 函数更新 ip 条目的 signature
        sign(ip.signature, new_stride);

        ip.last_addr = pf_addr;

        ret = &ip;
    } else {  // not match
    // 不匹配且 ip 条目将 ip 条目重新初始化，并将 ret 指向 ip。
        if (ip.hysteresis) {
            ip.hysteresis = false;
        } else {
            // alloc new entry
            ip.tag = getTag(pc);
            ip.hysteresis = false;
            ip.signature = 0;
            ip.cs_stride = 0;
            ip.cs_confidence = 0;
            ip.last_addr = pf_addr;
            ret = &ip;
        }
    }
    DPRINTF(HWPrefetch,"IPCP IP lookup class: %d\n", (int)type);

    return ret;
}


// 主要功能是根据给定的内存访问信息查找相应的预取条目，并决定是否应该进行预取操作。
void
IPCP::doLookup(const PrefetchInfo &pfi)
{
    bool can_prefetch = !pfi.isWrite() && pfi.hasPC();
    if (!can_prefetch) {
        return;
    }
    DPRINTF(HWPrefetch, "IPCP lookup pc: %lx, vaddr: %lx\n", pfi.getPC(), pfi.getAddr());
    Addr pf_addr = blockAddress(pfi.getAddr());
    int new_stride = -1;

    Classifier type = NO_PREFETCH;
    IPEntry *ip = ipLookup(pfi.getPC(), pf_addr, type, new_stride);
    assert(new_stride != -1);

    saved_ip = ip;
    saved_type = type;
    saved_stride = new_stride;
    saved_pfAddr = pf_addr;
}

void
IPCP::sign(IPEntry &ipe, int stride)
{
    ipe.signature = ((ipe.signature << signature_shift) ^ stride) & (cspt_size - 1);
}

void
IPCP::sign(uint32_t &signature, int stride)
{
    signature = ((signature << signature_shift) ^ stride) & (cspt_size - 1);
}

bool
IPCP::doPrefetch(const PrefetchInfo &pfi, std::vector<AddrPriority> &addresses, Addr &best_block_offset)
{
    bool send_cplx_pf = false;
    if (saved_type == CLASS_CS) {
        assert(saved_ip);
        Addr base_addr = saved_pfAddr;
        for (int i = 1; i <= cs_degree; i++) {
            base_addr = base_addr + (saved_ip->cs_stride << lBlkSize);
            DPRINTF(HWPrefetch, "IPCP CS Send pf: %lx, cur stride: %d, conf: %d\n", base_addr, saved_ip->cs_stride, saved_ip->cs_confidence);
            sendPFWithFilter(pfi, base_addr, addresses, 1);
        }
    } else if (saved_type == CLASS_CPLX) {
        assert(saved_ip);
        uint32_t signature = saved_ip->signature;
        Addr base_addr = blockAddress(saved_pfAddr);
        int high_conf = 0;
        uint32_t init_signature = signature;
        Addr total_block_stride = 0;
        DPRINTF(HWPrefetch, "IPCP prefetching\n");
        for (int i = 1; i <= signature_width / signature_shift; i++) {
            auto &csp = cspt[compressSignature(signature)];
            if (csp.abort || !(csp.confidence > cplx_thre)) {
                DPRINTF(HWPrefetch, "IPCP CPLX forced abort\n");
                break;
            }
            base_addr = base_addr + (csp.stride << lBlkSize);
            total_block_stride += csp.stride;
            DPRINTF(HWPrefetch, "IPCP CPLX Send pf: %lx, cur stride: %d, conf: %d\n", base_addr, csp.stride, csp.confidence);
            if (sendPFWithFilter(pfi, base_addr, addresses, 0)) {
                // ipcpStats.cplx_issued++;
            }
            send_cplx_pf = true;
            if (csp.confidence == 3 && high_conf < 4) {
                high_conf++;
            }
            sign(signature, csp.stride);

            if ((signature & signMask) == (init_signature & signMask)) {
                DPRINTF(HWPrefetch, "IPCP CPLX init sign: %lx, current sign: %lx\n", init_signature, signature);
                best_block_offset = total_block_stride;
                DPRINTF(HWPrefetch, "CPLX found best blk offset: %u, best offset: %u\n", best_block_offset,
                        best_block_offset << lBlkSize);
            } else {
                DPRINTF(HWPrefetch, "IPCP CPLX init sign: %lx, current sign: %lx\n", init_signature, signature);
            }
        }
    }
    return send_cplx_pf;
}
void
IPCP::calculatePrefetch(const PrefetchInfo &pfi, std::vector<AddrPriority> &addresses)
{
    Addr cplx_best_offset = 0;
    doLookup(pfi);
    doPrefetch(pfi,addresses, cplx_best_offset);
}

uint16_t
IPCP::getIndex(Addr pc)
{
    return (pc >> 1) & (ipt_size - 1);
}
uint16_t
IPCP::getTag(Addr pc)
{
    return (pc >> (1 + lipt_size)) & ((1 << tag_width) - 1);
}

}

}
