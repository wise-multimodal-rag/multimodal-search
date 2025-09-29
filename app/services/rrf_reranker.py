"""RRF (Reciprocal Rank Fusion) reranking implementation"""

from typing import Dict, List, Any
from loguru import logger


class RRFReranker:
    """Handles RRF reranking of search results from multiple queries"""
    
    def __init__(self, k: int = 60):
        """Initialize RRF reranker with fusion constant k"""
        self.k = k
    
    def rerank_results(
        self, 
        all_results: List[Dict], 
        size: int, 
        from_: int,
        total_took: int = 0
    ) -> Dict[str, Any]:
        """Aggregate results from multiple queries and rerank using RRF"""
        
        if not all_results:
            return self._empty_response(total_took)
        
        # Step 1: Group results by query type
        query_results = self._group_by_query_type(all_results)
        
        # Step 2: Calculate ranks for each query
        query_ranks = self._calculate_query_ranks(query_results)
        
        # Step 3: Calculate RRF scores
        rrf_scores = self._calculate_rrf_scores(query_ranks)
        
        # Step 4: Create final ranked results
        final_results = self._create_final_results(rrf_scores)
        
        # Step 5: Apply pagination
        paginated_results = final_results[from_:from_ + size]
        
        return self._build_response(final_results, paginated_results, total_took)
    
    def _group_by_query_type(self, all_results: List[Dict]) -> Dict[str, List[Dict]]:
        """Group results by query type (element_type_query)"""
        query_results = {}
        for hit in all_results:
            query_type = hit.get("_element_type_query", "unknown")
            if query_type not in query_results:
                query_results[query_type] = []
            query_results[query_type].append(hit)
        return query_results
    
    def _calculate_query_ranks(self, query_results: Dict[str, List[Dict]]) -> Dict[str, Dict[str, Dict]]:
        """Sort each query's results by score and assign ranks"""
        query_ranks = {}
        for query_type, hits in query_results.items():
            # Sort by score descending
            sorted_hits = sorted(hits, key=lambda x: x["_score"], reverse=True)
            
            # Assign ranks (1-based)
            ranks = {}
            for rank, hit in enumerate(sorted_hits, 1):
                element_id = hit["_source"]["element_id"]
                ranks[element_id] = {
                    "rank": rank,
                    "score": hit["_score"],
                    "hit": hit
                }
            query_ranks[query_type] = ranks
        
        return query_ranks
    
    def _calculate_rrf_scores(self, query_ranks: Dict[str, Dict[str, Dict]]) -> Dict[str, Dict]:
        """Calculate RRF scores for each element"""
        rrf_scores = {}
        
        for query_type, ranks in query_ranks.items():
            for element_id, rank_info in ranks.items():
                if element_id not in rrf_scores:
                    rrf_scores[element_id] = {
                        "rrf_score": 0.0,
                        "query_details": {},
                        "hit": rank_info["hit"]
                    }
                
                # RRF formula: 1 / (k + rank)
                rrf_contribution = 1.0 / (self.k + rank_info["rank"])
                rrf_scores[element_id]["rrf_score"] += rrf_contribution
                
                # Store query details for debugging
                rrf_scores[element_id]["query_details"][query_type] = {
                    "rank": rank_info["rank"],
                    "original_score": rank_info["score"],
                    "rrf_contribution": rrf_contribution
                }
                
                # Keep the hit with highest original score
                if rank_info["score"] > rrf_scores[element_id]["hit"]["_score"]:
                    rrf_scores[element_id]["hit"] = rank_info["hit"]
        
        return rrf_scores
    
    def _create_final_results(self, rrf_scores: Dict[str, Dict]) -> List[Dict]:
        """Create final ranked results list"""
        final_results = []
        for element_id, rrf_data in rrf_scores.items():
            hit = rrf_data["hit"].copy()
            hit["_score"] = rrf_data["rrf_score"]
            hit["_rrf_details"] = {
                "queries_matched": len(rrf_data["query_details"]),
                "query_breakdown": rrf_data["query_details"]
            }
            final_results.append(hit)
        
        # Sort by RRF score
        final_results.sort(key=lambda x: x["_score"], reverse=True)
        return final_results
    
    def _build_response(
        self, 
        final_results: List[Dict], 
        paginated_results: List[Dict], 
        total_took: int
    ) -> Dict[str, Any]:
        """Build OpenSearch format response"""
        return {
            "took": total_took,
            "timed_out": False,
            "hits": {
                "total": {"value": len(final_results), "relation": "eq"},
                "max_score": final_results[0]["_score"] if final_results else 0.0,
                "hits": paginated_results
            }
        }
    
    def _empty_response(self, total_took: int) -> Dict[str, Any]:
        """Return empty response"""
        return {
            "took": total_took,
            "timed_out": False,
            "hits": {
                "total": {"value": 0, "relation": "eq"},
                "max_score": 0.0,
                "hits": []
            }
        }
    
    def log_reranking_summary(self, response: Dict[str, Any]) -> None:
        """Log compact reranking summary"""
        final_hits = response["hits"]["hits"]
        total_hits = response["hits"]["total"]["value"]
        final_max_score = response["hits"]["max_score"]
        
        # Create compact final results summary
        final_summary = []
        for i, hit in enumerate(final_hits[:5], 1):
            element_id = hit["_source"].get("element_id", "unknown")
            rrf_score = hit["_score"]
            queries_matched = hit.get("_rrf_details", {}).get("queries_matched", 0)
            final_summary.append(f"#{i}:{element_id}(rrf:{rrf_score:.4f},q:{queries_matched})")
        
        results_text = " | ".join(final_summary) if final_summary else "no results"
        logger.info(f"RRF reranking: {total_hits} unique elements → final_max: {final_max_score:.4f} → {results_text}")