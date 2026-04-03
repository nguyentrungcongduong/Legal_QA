from datetime import date

class ConflictDetector:

    def detect_and_resolve(self, chunks: list) -> dict:
        conflicts = []
        resolved_chunks = list(chunks)

        # Group chunks nói về cùng chủ đề
        # (similarity > 0.85 với nhau nhưng từ nguồn khác nhau)
        groups = self._group_by_topic(chunks)

        for group in groups:
            if len(group) < 2:
                continue

            sources = set(c.metadata['document_code'] for c in group)
            if len(sources) < 2:
                continue  # cùng nguồn, không conflict

            # Verify conflict bằng LLM judge
            if self._is_conflicting(group):

                # Resolve: ưu tiên effective_date mới hơn
                newest = max(
                    group,
                    key=lambda c: date.fromisoformat(c.metadata['effective_date'])
                )
                outdated = [c for c in group if c != newest]

                # Loại chunks cũ khỏi kết quả
                for old in outdated:
                    if old in resolved_chunks:
                        resolved_chunks.remove(old)

                conflicts.append({
                    "type": "version_conflict",
                    "description": f"Phát hiện mâu thuẫn giữa {len(group)} văn bản",
                    "outdated_sources": [c.metadata['law_name'] for c in outdated],
                    "applied_source": newest.metadata['law_name'],
                    "reason": f"Ưu tiên văn bản hiệu lực từ {newest.metadata['effective_date']}"
                })

        return {
            "resolved_chunks": resolved_chunks,
            "conflicts": conflicts,
            "has_conflict": len(conflicts) > 0
        }

    def _is_conflicting(self, chunks: list) -> bool:
        # Dùng LLM judge để verify
        prompt = f"""
        Hai đoạn văn bản pháp luật sau có mâu thuẫn nhau không?
        Chỉ trả lời YES hoặc NO.

        Đoạn 1: {chunks[0].content}
        Đoạn 2: {chunks[1].content}
        """
        result = self.llm.complete(prompt).strip()
        return result == "YES"

    def _group_by_topic(self, chunks: list) -> list:
        # Dùng cosine similarity giữa các chunks
        # Threshold 0.85: cùng chủ đề nhưng khác nguồn
        groups = []
        used = set()

        for i, chunk_a in enumerate(chunks):
            if i in used:
                continue
            group = [chunk_a]
            for j, chunk_b in enumerate(chunks):
                if i == j or j in used:
                    continue
                if self._cosine_sim(chunk_a.vector, chunk_b.vector) > 0.85:
                    group.append(chunk_b)
                    used.add(j)
            used.add(i)
            groups.append(group)

        return groups