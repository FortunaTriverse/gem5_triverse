
/*
 * Copyright (c) 2025
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
 * Stride Prefetcher template instantiations.
 */
#include "mem/cache/prefetch/triverse.hh"

#include "debug/HWPrefetch.hh"
#include "mem/cache/prefetch/associative_set_impl.hh"
#include "params/TriversePrefetcher.hh"
#include <cmath>


namespace gem5
{

GEM5_DEPRECATED_NAMESPACE(Prefetcher, prefetch);
namespace prefetch
{

int Triverse::target_size=0;
int Triverse::current_size=0;
int64_t Triverse::global_timestamp=0;
AssociativeSet<Triverse::MarkovMapping>* Triverse::markovTablePtr=NULL;
std::vector<uint32_t> Triverse::setPrefetch(17,0);
Triverse::SizeDuel* Triverse::sizeDuelPtr=nullptr;
bloom* Triverse::blptr = nullptr;


Triverse::Triverse(
    const TriversePrefetcherParams &p)
  : Queued(p),
    degree(p.degree),
    cachetags(p.cachetags),
    cacheDelay(p.cache_delay),
    should_lookahead(p.should_lookahead),
    should_rearrange(p.should_rearrange),
    use_bloom(p.use_bloom),
    perfbias(p.perfbias),
    timed_scs(p.timed_scs),    
    sctags(p.sctags),
    max_size(p.address_map_actual_entries),
    size_increment(p.address_map_actual_entries/p.address_map_max_ways),
    second_chance_timestamp(0),
    //global_timestamp(0),
    //current_size(0),
    //target_size(0),
    maxWays(p.address_map_max_ways),    
    bl(),
    bloomset(-1),
    way_idx(p.address_map_actual_entries/(p.address_map_max_ways*p.address_map_actual_cache_assoc),0),
    globalReuseConfidence(7,64),
    globalPatternConfidence(7,64),
    globalHighPatternConfidence(7,64),
    trainingUnit(p.training_unit_assoc, p.training_unit_entries,
                 p.training_unit_indexing_policy,
                 p.training_unit_replacement_policy),
    lookupAssoc(p.lookup_assoc),
    lookupOffset(p.lookup_offset),        
    //setPrefetch(cachetags->getWayAllocationMax()+1,0),      
    useHawkeye(p.use_hawkeye),
    historySampler(p.sample_assoc,
    		  p.sample_entries,
    		  p.sample_indexing_policy,
    		  p.sample_replacement_policy),
    secondChanceUnit(p.secondchance_assoc,
    		  p.secondchance_entries,
    		  p.secondchance_indexing_policy,
    		  p.secondchance_replacement_policy),
    markovTable(p.address_map_rounded_cache_assoc,
                          p.address_map_rounded_entries,
                          p.address_map_cache_indexing_policy,
                          p.address_map_cache_replacement_policy,
                          MarkovMapping()),                   
    metadataReuseBuffer(p.metadata_reuse_assoc,
                          p.metadata_reuse_entries,
                          p.metadata_reuse_indexing_policy,
                          p.metadata_reuse_replacement_policy,
                          MarkovMapping()),
    lastAccessFromPFCache(false),

	// stride prefetcher
	strideTable(p.stride_table_assoc,
				p.stride_table_entries,
				p.stride_table_indexing_policy,
				p.stride_table_replacement_policy),
	use_stride(p.use_stride),
	max_stride(p.maxstride),
	replace_threshold(p.re_thre/100.0),
	prefetch_threshold(p.pre_threshold/100.0),
	dynamic_stride_degree(p.dynamic_stride_degree),
	stride_degree(p.stride_degree),	
	increase_stride_threshold(p.inc_stride_thre/100.0),
	decrease_stride_threshold(p.dec_stride_thre/100.0),
	max_degree(p.max_degree),
	min_degree(p.min_degree),
	stream_degree(p.stream_degree),

	//LRU filter
	filterTable(p.filter_assoc,
	 		    p.filter_entries,
	 			p.filter_indexing_policy,
	 			p.filter_replacement_policy),
    use_filter(p.use_filter),

	//monitor
    monitor_accuracy(p.monitor_accuracy),
	global_accuracy_increase_threshold(p.global_accuracy_increase_threshold/100.0),
	global_accuracy_decrease_threshold(p.global_accuracy_decrease_threshold/100.0),
	high_accuracy_degree_coefficient(p.high_accuracy_degree_coefficient/100.0),
	low_accuracy_degree_coefficient(p.low_accuracy_degree_coefficient/100.0),
	normal_accuracy_degree_coefficient(p.normal_accuracy_degree_coefficient/100.0),
	update_accuracy_threshold(p.CleanAccuracyThreshold)	

{	
	markovTablePtr = &markovTable;

	setPrefetch.resize(cachetags->getWayAllocationMax()+1,0);
	assert(p.address_map_rounded_entries / p.address_map_rounded_cache_assoc == p.address_map_actual_entries / p.address_map_actual_cache_assoc);
	markovTable.setWayAllocationMax(p.address_map_actual_cache_assoc);
	assert(cachetags->getWayAllocationMax()> maxWays);
	int bloom_size = p.address_map_actual_entries/128 < 1024? 1024: p.address_map_actual_entries/128;
	assert(bloom_init2(&bl,bloom_size, 0.01)==0);
	blptr = &bl;
	for(int x=0;x<64;x++) {
		hawksets[x].setMask = p.address_map_actual_entries/ hawksets[x].maxElems;
		hawksets[x].reset();
	}
		sizeDuelPtr= sizeDuels;	
	for(int x=0;x<64;x++) {
		sizeDuelPtr[x].reset(size_increment/p.address_map_actual_cache_assoc - 1 ,p.address_map_actual_cache_assoc,cachetags->getWayAllocationMax());
	}

	for(int x=0;x<1024;x++) {
		lookupTable[x]=0;
    		lookupTick[x]=0;
	}	
	current_size = 0;
	target_size=0;
}


bool
Triverse::randomChance(int reuseConf, int replaceRate) {
	replaceRate -=8;

	uint64_t baseChance = 1000000000l * historySampler.numEntries / markovTable.numEntries;
	baseChance = replaceRate>0? (baseChance << replaceRate) : (baseChance >> (-replaceRate));
	baseChance = reuseConf < 3 ? baseChance / 16 : baseChance;
	uint64_t chance = random_mt.random<uint64_t>(0,1000000000ul);

	return baseChance >= chance;
}

void
Triverse::calculatePrefetch(const PrefetchInfo &pfi,
    std::vector<AddrPriority> &addresses)
{

    Addr addr = blockIndex(pfi.getAddr());
    second_chance_timestamp++;
    
    // This prefetcher requires a PC
    if (!pfi.hasPC() || pfi.isWrite()) {
		if(!use_bloom) {
	    	for(int x=0;x<64;x++) {
			int res = sizeDuelPtr[x].checkAndInsert(addr,false);
			if(res==0)continue;
			int cache_hit = res%128;
			int cache_set = cache_hit-1;
			assert(!cache_hit || (cache_set<setPrefetch.size()-1 && cache_set>=0));
			if(cache_hit) for(int y= setPrefetch.size()-2-cache_set; y>=0; y--) setPrefetch[y]++; 
	    	}
		}
        return;
    }

    bool is_secure = pfi.isSecure();
    Addr pc = pfi.getPC()>>2; //Shifted by 2 to help Arm indexing. Bit fake; really should xor in these bits with upper bits.

	if (monitor_accuracy && timelyissuedPrefetches >= update_accuracy_threshold){
		double timelyAccuracy = double(timelyusefulPrefetches / timelyissuedPrefetches);
		if (timelyAccuracy > global_accuracy_increase_threshold){
			global_accuracy_degree_coefficient = high_accuracy_degree_coefficient;
		} else if (timelyAccuracy < global_accuracy_decrease_threshold){
			global_accuracy_degree_coefficient = low_accuracy_degree_coefficient;
		} else {
			global_accuracy_degree_coefficient = normal_accuracy_degree_coefficient;
		}
	}

    // Looks up the last address at this PC
    TrainingUnitEntry *entry = trainingUnit.findEntry(pc, is_secure);
    bool correlated_addr_found = false;
    Addr index = 0;
    Addr target = 0;
    
    const int upperHistory=globalPatternConfidence>64?7:8;
    const int highUpperHistory=globalHighPatternConfidence>64?7:8;
    const int superHistory=14;
    
    const int upperReuse=globalReuseConfidence>64?7:8;
    
    //const int globalThreshold = 9;
    
    bool should_pf=false;
    bool should_hawk=false;
    bool should_sample = false;
    if (entry != nullptr) { //This accesses the training table at this PC.
        trainingUnit.accessEntry(entry);
        correlated_addr_found = true;
        index = entry->lastAddress;

        if(addr == entry->lastAddress) return; // to avoid repeat trainings on sequence.
		if(entry->highPatternConfidence >= superHistory) entry->currently_twodist_pf=true;
		if(entry->patternConfidence < upperHistory) entry->currently_twodist_pf=false; 
        //if very sure, index should be lastLastAddress. TODO: We could also try to learn timeliness here, by tracking PCs at the MSHRs.
        if(entry->currently_twodist_pf && should_lookahead) index = entry->lastLastAddress;
        target = addr;
        should_pf = (entry->reuseConfidence > upperReuse) && (entry->patternConfidence > upperHistory); //8 is the reset point.

        global_timestamp++;

		//if use modified stride prefetcher

		if (use_stride){
						
			int stride = addr - entry->lastAddress;
			StrideEntry *rentry = strideTable.findEntry(pc, is_secure);

			//assert(rentry != nullptr);
			if (rentry != nullptr){
					
				bool stride_match = (stride == rentry->stride_1);

				if (stride_match) { 
					rentry->confidence_1++; 
				} else { 
					rentry->confidence_1--; 
				}

        		if (rentry->confidence_1.calcSaturation() < replace_threshold) {
        	    	    rentry->stride_1 = stride;
        		}

                bool increase_degree = rentry->confidence_1.calcSaturation() > increase_stride_threshold;
				bool decrease_degree = rentry->confidence_1.calcSaturation() < decrease_stride_threshold;

				// dynamic change stride prefetcher degree
				if (!dynamic_stride_degree){
					real_degree = stride_degree;
				}else if (dynamic_stride_degree == 1){
            		if (stride_match && increase_degree && (stride_degree < max_degree)) {
						stride_degree ++;
						DPRINTF(HWPrefetch, "increase the stride degree to %d with confidence_1 of %f\n"
							,stride_degree,rentry->confidence_1.calcSaturation());
					} else if (stride_match && decrease_degree && stride_degree > min_degree) {
						stride_degree --;
						DPRINTF(HWPrefetch, "decrease the stride degree to %d with confidence_1 of %f\n"
							,stride_degree,rentry->confidence_1.calcSaturation());	
					}					
					real_degree = stride_degree;	
				} else if (dynamic_stride_degree == 2){
            		if (stride_match && increase_degree && (rentry->degree < max_degree)) {
						rentry->degree ++;
						DPRINTF(HWPrefetch, "increase the stride degree to %d with confidence_1 of %f\n"
							,rentry->degree,rentry->confidence_1.calcSaturation());
					} else if (stride_match && decrease_degree && rentry->degree > min_degree) {
						rentry->degree --;
						DPRINTF(HWPrefetch, "decrease the stride degree to %d with confidence_1 of %f\n"
							,rentry->degree,rentry->confidence_1.calcSaturation());						
					}
					real_degree = rentry->degree;
				} else if (dynamic_stride_degree == 3){
					if (stride_match){
						if (increase_degree) {
							real_degree = max_degree;
							DPRINTF(HWPrefetch, "increase the stride degree to %d with confidence_1 of %f\n"
								,real_degree,rentry->confidence_1.calcSaturation());
						}else if (decrease_degree){
							real_degree = min_degree;;
							DPRINTF(HWPrefetch, "decrease the stride degree to %d with confidence_1 of %f\n"
								,rentry->degree,rentry->confidence_1.calcSaturation());
						} else {
							real_degree = stride_degree;
						}
					}							
				}

				// when triangel bloom prefetcher cannot send, use stride to help it
				if (should_pf == 0){
					DPRINTF(HWPrefetch, "Not match triangel bloom prefetcher %x\n",pc);
					if (stride_match && (rentry->confidence_1.calcSaturation() >= prefetch_threshold)){
						//printf("real_degree_1 = %d\n",real_degree);
						real_degree = monitor_accuracy ? global_accuracy_degree_coefficient*real_degree:real_degree;
						real_degree = real_degree == 0 ? 1 : real_degree;
						//real_degree = 0;
						//printf("real_degree_2 = %d\n",real_degree);
						stridePrefetch(addr,stride,addresses,real_degree,pfi);
					}else if (stream_degree && stride == 1){
						streamPrefetch(addr,addresses,stream_degree,pfi);
					}
				}

			} else {
				rentry = strideTable.findVictim(pc);
				assert(rentry != nullptr);
				assert(!rentry->isValid());
				strideTable.insertEntry(pc,is_secure,rentry);
				rentry->stride_1 = stride;
				rentry->stride_2 = 0;
			}			
		}			
    }

    if(entry==nullptr && (randomChance(8,8) || ((globalReuseConfidence > 64) && (globalHighPatternConfidence > 64) && (globalPatternConfidence > 64)))){
    	if(!((globalReuseConfidence > 64) && (globalHighPatternConfidence > 64)  && (globalPatternConfidence > 64)))should_sample = true;
        entry = trainingUnit.findVictim(pc);
        DPRINTF(HWPrefetch, "Replacing Training Entry %x\n",pc);
        assert(entry != nullptr);
        assert(!entry->isValid());
        trainingUnit.insertEntry(pc, is_secure, entry);
        //printf("local timestamp %ld\n", entry->local_timestamp);
        if(globalHighPatternConfidence>96) entry->currently_twodist_pf=true;
    }

    if(correlated_addr_found) {
    	//Check second-chance sampler for a recent history. If so, update pattern confidence accordingly.
    	SecondChanceEntry* tentry = secondChanceUnit.findEntry(addr, is_secure);
    	if(tentry!= nullptr && !tentry->used) {
    		tentry->used=true;
    		TrainingUnitEntry *pentry = trainingUnit.findEntry(tentry->pc, is_secure);
    		if((!timed_scs || (tentry->global_timestamp + 512 > second_chance_timestamp)) && pentry != nullptr) {  
  				if(tentry->pc==pc) {
	  				pentry->patternConfidence++;
	    			pentry->highPatternConfidence++;
	    			globalPatternConfidence++;
	    			globalHighPatternConfidence++;
    			}
			} else if(pentry!=nullptr) {
				pentry->patternConfidence--;
			    globalPatternConfidence--;
			    if(!perfbias) { pentry->patternConfidence--; globalPatternConfidence--;} //bias 
			    for(int x=0;x<(perfbias? 2 : 5);x++) {pentry->highPatternConfidence--;  globalHighPatternConfidence--;}
			}
    	}
    	
    	//Check history sampler for entry.
    	SampleEntry *sentry = historySampler.findEntry(entry->lastAddress, is_secure);
    	if(sentry != nullptr && sentry->entry == entry) {    		
    		
			int64_t distance = sentry->entry->local_timestamp - sentry->local_timestamp;
			if(distance > 0 && distance < max_size) { 
				entry->reuseConfidence++;globalReuseConfidence++;
			} else if(!sentry->reused){ 
				entry->reuseConfidence--;globalReuseConfidence--;
			}
    		sentry->reused = true;

     	    DPRINTF(HWPrefetch, "Found reuse for addr %x, PC %x, distance %ld (train %ld vs sample %ld) confidence %d\n",addr, pc, distance, entry->local_timestamp, sentry->local_timestamp, entry->reuseConfidence+0);
     	    	
			bool willBeConfident = addr == sentry->next;
    		
    		if(addr == sentry->next || (sctags->findBlock(sentry->next<<lBlkSize,is_secure) && !sctags->findBlock(sentry->next<<lBlkSize,is_secure)->wasPrefetched())) {
    			if(addr == sentry->next) {
    				entry->patternConfidence++;
    				entry->highPatternConfidence++;
    				globalPatternConfidence++;
	    			globalHighPatternConfidence++;
    			}
    			//if(entry->replaceRate < 8) entry->replaceRate.reset();
    		} else {
    			//We haven't spotted the (x,y) pattern we expect, on seeing y. So put x in the SCS.
				SecondChanceEntry* tentry = secondChanceUnit.findVictim(sentry->next);
				if(tentry->pc !=0 && !tentry->used) {
    			   	TrainingUnitEntry *pentry = trainingUnit.findEntry(tentry->pc, is_secure);	
    			   	if(pentry != nullptr) {
			    		pentry->patternConfidence--;
			    		globalPatternConfidence--;
			    		if(!perfbias) { pentry->patternConfidence--; globalPatternConfidence--;} //bias 
			    		for(int x=0;x<(perfbias? 2 : 5);x++) {pentry->highPatternConfidence--;  globalHighPatternConfidence--;}		   		
    			   	}			
				}
	    			secondChanceUnit.insertEntry(sentry->next, is_secure, tentry);
	    			tentry->pc = pc;
	    			tentry->global_timestamp = second_chance_timestamp;
	    			tentry->used = false;
    		}
    		
        	if(addr == sentry->next) DPRINTF(HWPrefetch, "Match for address %x confidence %d\n",addr, entry->patternConfidence+0);
    		if(sentry->entry == entry) sentry->next=addr;
    		sentry->confident = willBeConfident;
    	} else if(should_sample || randomChance(entry->reuseConfidence,entry->replaceRate)) {
    		//Fill sample table, as we're taking a sample at this PC. Should_sample also set by randomChance earlier, on first insert of PC intro training table.
    		sentry = historySampler.findVictim(entry->lastAddress);
    		assert(sentry != nullptr);
    		if(sentry->entry !=nullptr) {
    			TrainingUnitEntry *pentry = sentry->entry;
    			if(pentry != nullptr) {
    			    int64_t distance = pentry->local_timestamp - sentry->local_timestamp;
    			    DPRINTF(HWPrefetch, "Replacing Entry %x with PC %x, old distance %d\n",sentry->entry, pc, distance);
    			    if(distance > max_size) {
    			        trainingUnit.accessEntry(pentry);
    			        if(!sentry->reused) { 
    			            pentry->reuseConfidence--;
							globalReuseConfidence--;
    			        }
    			        entry->replaceRate++; //only replacing oldies -- can afford to be more aggressive.
    			    } else if(distance > 0 && !sentry->reused) { //distance goes -ve due to lack of training-entry space
    			        entry->replaceRate--;
    			    }
    			} else entry->replaceRate++;
    		}
    		assert(!sentry->isValid());
    		sentry->clear();
    		historySampler.insertEntry(entry->lastAddress, is_secure, sentry);
    		sentry->entry = entry;
    		sentry->reused = false;
    		sentry->local_timestamp = entry->local_timestamp+1;
    		sentry->next = addr;
    		sentry->confident=false;
    	}
    }
    
    if(!use_bloom) {
	    for(int x=0;x<64;x++) {
	    	//Here we update the size duellers, to work out for each cache set whether it is better to be markov table or L3 cache.
			int res =  sizeDuelPtr[x].checkAndInsert(addr,should_pf); //TODO: combine with hawk?
			if(res==0)continue;
			const int ratioNumer=(perfbias?4:2);
			const int ratioDenom=4;//should_pf && entry->highPatternConfidence >=upperHistory? 4 : 8;
			int cache_hit = res%128; //This is just bit encoding of cache hits.
			int pref_hit = res/128; //This is just bit encoding of prefetch hits.
			int cache_set = cache_hit-1; //Encodes which nth most used replacement-state we hit at, if any.
			int pref_set = pref_hit-1; //Encodes which nth most used replacement-state we hit at, if any.
			assert(!cache_hit || (cache_set<setPrefetch.size()-1 && cache_set>=0));
			assert(!pref_hit || (pref_set<setPrefetch.size()-1 && pref_set>=0));
			if(cache_hit) for(int y= setPrefetch.size()-2-cache_set; y>=0; y--) setPrefetch[y]++; 
			// cache partition hit at this size or bigger. So hit in way 14 = y=17-2-14=1 and 0: would hit with 0 ways reserved or 1, not 2.
			if(pref_hit)for(int y=pref_set+1;y<setPrefetch.size();y++) setPrefetch[y]+=(ratioNumer*sizeDuelPtr[x].temporalModMax)/ratioDenom; 
			// ^ pf hit at this size or bigger. one-indexed (since 0 is an alloc on 0 ways). So hit in way 0 = y=1--16 ways reserved, not 0.
		
			//if(cache_hit) printf("Cache hit\n");
			//else printf("Prefetch hit\n");
	    }
	    

	    if(global_timestamp > 500000) {
	    //Here we choose the size of the Markov table based on the optimum for the last epoch
	    	int counterSizeSeen = 0;

	    	for(int x=0;x<setPrefetch.size() && x*size_increment <= max_size;x++) {
	    		if(setPrefetch[x]>counterSizeSeen) {
	    		 	target_size= size_increment*x;
	    		 	counterSizeSeen = setPrefetch[x];
	    		}
	    	}

	    	int currentscore = setPrefetch[current_size/size_increment];
	    	currentscore = currentscore + (currentscore>>4); //Slight bias against changing for minimal benefit.
	    	int targetscore = setPrefetch[target_size/size_increment];

	    	if(target_size != current_size && targetscore>currentscore) {
	    		current_size = target_size;
				assert(current_size >= 0);
		
	
				for(int x=0;x<64;x++) {
					hawksets[x].setMask = current_size / hawksets[x].maxElems;
					hawksets[x].reset();
				}
				std::vector<MarkovMapping> ams;
			    if(should_rearrange) {		    	
					for(MarkovMapping am: *markovTablePtr) {
					    		if(am.isValid()) ams.push_back(am);
					}
					for(MarkovMapping& am: *markovTablePtr) {
				    		am.invalidate(); //for RRIP's sake
				    }
			    }

			    TriverseHashedSetAssociative* thsa = dynamic_cast<TriverseHashedSetAssociative*>(markovTablePtr->indexingPolicy);
		  		if(thsa) { thsa->ways = current_size/size_increment; thsa->max_ways = maxWays; assert(thsa->ways <= thsa->max_ways);}
		  		else assert(0);

			    //rearrange conditionally
				if(should_rearrange) {        	
				    if(current_size >0) {
					    for(MarkovMapping am: ams) {
					    	MarkovMapping *mapping = getHistoryEntry(am.index, am.isSecure(),true,false,true,true);
					    	mapping->address = am.address;
					    	mapping->index=am.index;
					    	mapping->confident = am.confident;
					    	mapping->lookupIndex=am.lookupIndex;
					    	markovTablePtr->weightedAccessEntry(mapping,1,false); //For RRIP, touch
					    }    	
				    }
			    }
			    	
			    for(MarkovMapping& am: *markovTablePtr) {
				    if(thsa->ways==0 || (thsa->extractSet(am.index) % maxWays)>=thsa->ways)  am.invalidate();
				}
			    cachetags->setWayAllocationMax(setPrefetch.size()-1-thsa->ways);  	
	    	} 


	    	global_timestamp=0;
			for(int x=0;x<setPrefetch.size();x++) {
		    	setPrefetch[x]=0;
			}
	    	//Reset after 2 million prefetch accesses -- not quite the same as after 30 million insts but close enough
	    }
    }


    if(useHawkeye && correlated_addr_found && should_pf) {
        // If a correlation was found, update the Markov table accordingly
        for(int x=0; x<64; x++)hawksets[x].add(addr,pc,&trainingUnit);
        should_hawk = entry->hawkConfidence>7;
    }
    
    if(use_bloom) {
	    if(correlated_addr_found && should_pf) {
	    	if(bloomset==-1) bloomset = index&127;
	    	if((index&127)==bloomset) {
				int add = bloom_add(blptr, &index, sizeof(Addr));
				if(!add) target_size+=192;
			}
	    }
	    
	    while(target_size > current_size && target_size > size_increment / 8 && current_size < max_size) {
		    //check for size_increment to leave empty if unlikely to be useful.
		    current_size += size_increment;
		    //printf("size: %d, tick %ld \n",current_size,curTick());
		    assert(current_size <= max_size);
		    assert(cachetags->getWayAllocationMax()>1);
		    cachetags->setWayAllocationMax(cachetags->getWayAllocationMax()-1);

		    std::vector<MarkovMapping> ams;
		    if(should_rearrange) {        	
			    for(MarkovMapping am: *markovTablePtr) {
			    	if(am.isValid()) ams.push_back(am);
			    }
				for(MarkovMapping& am: *markovTablePtr) {
			    	am.invalidate(); //for RRIP's sake
			    }
			}
		    
			TriverseHashedSetAssociative* thsa = dynamic_cast<TriverseHashedSetAssociative*>(markovTablePtr->indexingPolicy);
	  		if(thsa) { thsa->ways++; thsa->max_ways = maxWays; assert(thsa->ways <= thsa->max_ways);}
	  		else assert(0);

		    //TODO: rearrange conditionally
		    if(should_rearrange) {        	            	
				for(MarkovMapping am: ams) {
					MarkovMapping *mapping = getHistoryEntry(am.index, am.isSecure(),true,false, true, true);
					mapping->address = am.address;
					mapping->index=am.index;
					mapping->confident = am.confident;
					mapping->lookupIndex=am.lookupIndex;
					markovTablePtr->weightedAccessEntry(mapping,1,false); //For RRIP, touch
				} 
			}  
		    //increase associativity of the set structure by 1!
		    //Also, decrease LLC cache associativity by 1.
	    }

		if(global_timestamp > 2000000) {
	    	//Reset after 2 million prefetch accesses -- not quite the same as after 30 million insts but close enough

	    	while((target_size <= current_size - size_increment  || target_size < size_increment / 8)  && current_size >=size_increment) {
	    		//reduce the assoc by 1.
	    		//Also, increase LLC cache associativity by 1.
	    		current_size -= size_increment;
	    		//printf("size: %d, tick %ld \n",current_size,curTick());
		    	assert(current_size >= 0);
		    	std::vector<MarkovMapping> ams;
		     	if(should_rearrange) {		    	
					for(MarkovMapping am: *markovTablePtr) {
				    	if(am.isValid()) ams.push_back(am);
					}
					for(MarkovMapping& am: *markovTablePtr) {
			    		am.invalidate(); //for RRIP's sake
			    	}
		    	}

		    	TriverseHashedSetAssociative* thsa = dynamic_cast<TriverseHashedSetAssociative*>(markovTablePtr->indexingPolicy);
	  			if(thsa) { assert(thsa->ways >0); thsa->ways--; }
	  			else assert(0);

		    	//rearrange conditionally
		        if(should_rearrange) {        	
			    	if(current_size >0) {
				      	for(MarkovMapping am: ams) {
				    		MarkovMapping *mapping = getHistoryEntry(am.index, am.isSecure(),true,false,true,true);
				    		mapping->address = am.address;
				    		mapping->index=am.index;
				    		mapping->confident = am.confident;
				    		mapping->lookupIndex=am.lookupIndex;
				    		markovTablePtr->weightedAccessEntry(mapping,1,false); //For RRIP, touch
				    	}    	
			    	}
		    	}
		    	
		    	for(MarkovMapping& am: *markovTablePtr) {
			    	if(thsa->ways==0 || (thsa->extractSet(am.index) % maxWays)>=thsa->ways)  am.invalidate();
				}

	    		cachetags->setWayAllocationMax(cachetags->getWayAllocationMax()+1);
	    	}
	    	target_size = 0;
	    	global_timestamp=0;
	    	bloom_reset(blptr);
	    	bloomset=-1;
	    }
    }
    
    
    if (correlated_addr_found && should_pf && (current_size>0)) {
        // If a correlation was found, update the Markov table accordingly
		//DPRINTF(HWPrefetch, "Tabling correlation %x to %x, PC %x\n", index << lBlkSize, target << lBlkSize, pc);
		MarkovMapping *mapping = getHistoryEntry(index, is_secure,false,false,false, should_hawk);
		if(mapping == nullptr) {
        	mapping = getHistoryEntry(index, is_secure,true,false,false, should_hawk);
        	mapping->address = target;
        	mapping->index=index; //for HawkEye
        	mapping->confident = false;
        }
        assert(mapping != nullptr);
        bool confident = mapping->address == target; 
        bool wasConfident = mapping->confident;
        mapping->confident = confident; //Confidence is just used for replacement. I haven't tested how important it is for performance to use it; this is inherited from Triage.
        if(!wasConfident) {
        	mapping->address = target;
        }
        if(wasConfident && confident) {
        	MarkovMapping *cached_entry =
        		metadataReuseBuffer.findEntry(index, is_secure);
        	if(cached_entry != nullptr) {
        		prefetchStats.metadataAccesses--;
        		//No need to access L3 again, as no updates to be done.
        	}
        }
        
        int index=0;
        uint64_t time = -1;
        if(lookupAssoc>0){
			int lookupMask = (1024/lookupAssoc)-1;
			int set = (target>>lookupOffset)&lookupMask;
			for(int x=lookupAssoc*set;x<lookupAssoc*(set+1);x++) {
				if(target>>lookupOffset == lookupTable[x]) {
					index=x;
					break;
				}
				if(time > lookupTick[x]) {
					time = lookupTick[x];
					index=x;
				}
			}
		
			lookupTable[index]=target>>lookupOffset;
			lookupTick[index]=curTick();
			mapping->lookupIndex=index;
        }
    }

    if(target != 0 && should_pf && (current_size>0)) {
  	 	MarkovMapping *pf_target = getHistoryEntry(target, is_secure,false,true,false, should_hawk);
   	 	unsigned deg = 0;
  	 	unsigned delay = cacheDelay;
  		bool high_degree_pf = pf_target != nullptr && (entry->highPatternConfidence>highUpperHistory);
   	 	unsigned max = high_degree_pf? degree : (should_pf? 1 : 0);
	 	max = monitor_accuracy ? max * global_accuracy_degree_coefficient:max;
	 	max = max == 0 ? 1 : max;
   	 	//if(pf_target == nullptr && should_pf) DPRINTF(HWPrefetch, "Target not found for %x, PC %x\n", target << lBlkSize, pc);
   	 	while (pf_target != nullptr && deg < max) { 
    		DPRINTF(HWPrefetch, "Prefetching %x on miss at %x, PC \n", pf_target->address << lBlkSize, addr << lBlkSize, pc);
    		int extraDelay = cacheDelay;
    		if(lastAccessFromPFCache) {
    			Cycles time = curCycle() - pf_target->cycle_issued;
    			if(time >= cacheDelay) extraDelay = 0;
    			else if (time < cacheDelay) extraDelay = cacheDelay-time;
    		}
    		
    		Addr lookup = pf_target->address;
   	        if(lookupAssoc>0){
	   	 		int index=pf_target->lookupIndex;
	   	 		int lookupMask = (1<<lookupOffset)-1;
	   	 		lookup = (lookupTable[index]<<lookupOffset) + ((pf_target->address)&lookupMask);
	   	 		lookupTick[index]=curTick();
	   	 		if(lookup == pf_target->address)prefetchStats.lookupCorrect++;
	    		else prefetchStats.lookupWrong++;
    		}
    		
    		if(extraDelay == cacheDelay) {
				sendPFWithFilter(pfi,lookup << lBlkSize,addresses,delay);
				//printf("send temporal prefetcher %ld\n",lookup << lBlkSize);
			}
			//addresses.push_back(AddrPriority(lookup << lBlkSize, delay));
    		delay += extraDelay;
    		deg++;
    		
    		if(deg<max /*&& pf_target->confident*/) pf_target = getHistoryEntry(lookup, is_secure,false,true,false, should_hawk);
    		else pf_target = nullptr;
   	 	}
    }

    // Update the entry
    if(entry != nullptr) {
    	entry->lastLastAddress = entry->lastAddress;
    	entry->lastLastAddressSecure = entry->lastAddressSecure;
    	entry->lastAddress = addr;
    	entry->lastAddressSecure = is_secure;
    	entry->local_timestamp ++;
    }
}

Triverse::MarkovMapping*
Triverse::getHistoryEntry(Addr paddr, bool is_secure, bool add, bool readonly, bool clearing, bool hawk)
{
	//The weird parameters above control whether we replace entries, and how the number of metadata accesses are updated, for instance. They're basically a simulation thing.
  	TriverseHashedSetAssociative* thsa = dynamic_cast<TriverseHashedSetAssociative*>(markovTablePtr->indexingPolicy);
	if(!thsa)  assert(0);  

    cachetags->clearSetWay(thsa->extractSet(paddr)/maxWays, thsa->extractSet(paddr)%maxWays); 

    if(should_rearrange) {    
	    int index= paddr % (way_idx.size()); //Not quite the same indexing strategy, but close enough.
	    if(way_idx[index] != thsa->ways) {
	    	if(way_idx[index] !=0) prefetchStats.metadataAccesses+= thsa->ways + way_idx[index];
	    	way_idx[index]=thsa->ways;
	    }
    }

    if(readonly) { //check the cache first.
        MarkovMapping *pf_entry = metadataReuseBuffer.findEntry(paddr, is_secure);
        if (pf_entry != nullptr) {
        	lastAccessFromPFCache = true;
        	return pf_entry;
        }
        lastAccessFromPFCache = false;
    }

    MarkovMapping *ps_entry = markovTablePtr->findEntry(paddr, is_secure);
    if(readonly || !add) prefetchStats.metadataAccesses++;
    if (ps_entry != nullptr) {
        // A PS-AMC line already exists
        markovTablePtr->weightedAccessEntry(ps_entry,hawk?1:0,false);
    } else {
        if(!add) return nullptr;
        ps_entry = markovTablePtr->findVictim(paddr);
        assert(ps_entry != nullptr);
        if(useHawkeye && !clearing) for(int x=0;x<64;x++) hawksets[x].decrementOnLRU(ps_entry->index,&trainingUnit);
		assert(!ps_entry->isValid());
        markovTablePtr->insertEntry(paddr, is_secure, ps_entry);
        markovTablePtr->weightedAccessEntry(ps_entry,hawk?1:0,true);
    }

    if(readonly) {
    	MarkovMapping *pf_entry = metadataReuseBuffer.findVictim(paddr);
    	metadataReuseBuffer.insertEntry(paddr, is_secure, pf_entry);
    	pf_entry->address = ps_entry->address;
    	pf_entry->confident = ps_entry->confident;
    	pf_entry->cycle_issued = curCycle();
    	//This adds access time, to set delay appropriately.
    }

    return ps_entry;
}


uint32_t
TriverseHashedSetAssociative::extractSet(const Addr addr) const
{
	//Input is already blockIndex so no need to remove block again.
    Addr offset = addr;
    
   /* const Addr hash1 = offset & ((1<<16)-1);
    const Addr hash2 = (offset >> 16) & ((1<<16)-1);
        const Addr hash3 = (offset >> 32) & ((1<<16)-1);
    */
    offset = ((offset) * max_ways) + (extractTag(addr) % ways);
    return offset & setMask;   //setMask is numSets-1

}


Addr
TriverseHashedSetAssociative::extractTag(const Addr addr) const
{
    //Input is already blockIndex so no need to remove block again.

    //Description in Triage-ISR confuses whether the index is just the 16 least significant bits,
    //or the weird index above. The tag can't be the remaining bits if we use the literal representation!

    Addr offset = addr / (numSets/max_ways); 
    int result = 0;
    
    //This is a tag# as described in the Triverse paper.
    const int shiftwidth=10;

    for(int x=0; x<64; x+=shiftwidth) {
       result ^= (offset & ((1<<shiftwidth)-1));
       offset = offset >> shiftwidth;
    }
    return result;
}

void
Triverse::streamPrefetch(Addr pf_addr, std::vector<AddrPriority> &addresses,
						int degree,const PrefetchInfo &pfi)
{
    // Generate up to degree prefetches
    for (int d = 1; d <= degree; d++) {
		// Addr new_addr = (pf_addr + d)*(blkSize);
        pf_addr += 1;
		Addr new_addr = pf_addr << lBlkSize;
		//printf("send stream prefetcher %ld\n",new_addr);
		DPRINTF(HWPrefetch, "send stream prefetcher %x\n",new_addr);
        sendPFWithFilter(pfi,new_addr,addresses,0);
    }
}


void
Triverse::stridePrefetch(Addr pf_addr,int new_stride, 
                        std::vector<AddrPriority> &addresses,int stride_degree,
                        const PrefetchInfo &pfi)
{
    // Round strides up to atleast 1 cacheline
	//printf("stride_degree = %d\n",stride_degree);
    int prefetch_stride = new_stride;

    // Generate up to degree prefetches
    for (int d = 1; d <= stride_degree; d++) {
        pf_addr += prefetch_stride;
		Addr new_addr = pf_addr << lBlkSize;
		//("send stride prefetcher %ld\n",new_addr);
        sendPFWithFilter(pfi,new_addr,addresses,0);
    }
}

bool
Triverse::sendPFWithFilter(const PrefetchInfo &pfi, Addr addr, 
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
            addresses.push_back(AddrPriority(addr, delay));
            return true;
        }
    } 
}


} // namespace prefetch
} // namespace gem5
