/**
 * 점수 분해 시각화 컴포넌트
 * BM25 / Vector / Reranker 비율을 바 차트로 표시
 */
class ScoreBreakdown {
    constructor() {}

    render(container, result) {
        if (!container) return;

        const breakdown = result.score_breakdown || {};
        const components = breakdown.components || [];
        const rerankerScore = result.reranker_score || breakdown.reranker?.score;

        // 점수 구성 요소 추출
        let bm25Score = 0;
        let vectorScore = 0;

        for (const comp of components) {
            if (comp.type === 'bm25') bm25Score = comp.score || 0;
            if (comp.type === 'vector_text' || comp.type === 'vector_image') vectorScore += comp.score || 0;
        }

        // 점수가 없으면 전체 점수 기반으로 추정
        if (!bm25Score && !vectorScore && !rerankerScore) {
            container.innerHTML = '';
            return;
        }

        const maxScore = Math.max(bm25Score, vectorScore, rerankerScore || 0, 0.01);

        let html = '<div class="space-y-1">';

        if (bm25Score > 0) {
            const pct = (bm25Score / maxScore * 100).toFixed(0);
            html += `
                <div class="flex items-center gap-2">
                    <span class="w-12 text-[10px] text-surface-400">BM25</span>
                    <div class="score-bar-container flex-1">
                        <div class="score-bar bm25" style="width: ${pct}%"></div>
                    </div>
                    <span class="w-10 text-right text-[10px] font-mono text-surface-500">${bm25Score.toFixed(2)}</span>
                </div>
            `;
        }

        if (vectorScore > 0) {
            const pct = (vectorScore / maxScore * 100).toFixed(0);
            html += `
                <div class="flex items-center gap-2">
                    <span class="w-12 text-[10px] text-surface-400">Vector</span>
                    <div class="score-bar-container flex-1">
                        <div class="score-bar vector" style="width: ${pct}%"></div>
                    </div>
                    <span class="w-10 text-right text-[10px] font-mono text-surface-500">${vectorScore.toFixed(2)}</span>
                </div>
            `;
        }

        if (rerankerScore) {
            const pct = (rerankerScore / maxScore * 100).toFixed(0);
            html += `
                <div class="flex items-center gap-2">
                    <span class="w-12 text-[10px] text-surface-400">Rerank</span>
                    <div class="score-bar-container flex-1">
                        <div class="score-bar reranker" style="width: ${pct}%"></div>
                    </div>
                    <span class="w-10 text-right text-[10px] font-mono text-surface-500">${rerankerScore.toFixed(2)}</span>
                </div>
            `;
        }

        html += '</div>';
        container.innerHTML = html;
    }
}
