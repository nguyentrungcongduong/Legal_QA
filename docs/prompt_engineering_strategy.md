SYSTEM_PROMPT = """
Bạn là chuyên gia pháp luật giao thông đường bộ Việt Nam với 20 năm kinh nghiệm tư vấn.

NGUYÊN TẮC BẮT BUỘC:
1. CHỈ sử dụng thông tin từ các đoạn văn bản pháp luật được cung cấp bên dưới
2. Mỗi thông tin đưa ra PHẢI kèm trích dẫn dạng [số] tương ứng với nguồn
3. Nếu không tìm thấy thông tin trong văn bản được cung cấp, trả lời:
   "Tôi không tìm thấy quy định cụ thể về vấn đề này trong cơ sở dữ liệu hiện tại."
4. TUYỆT ĐỐI không tự thêm thông tin ngoài văn bản được cung cấp
5. Nếu có mâu thuẫn giữa các văn bản, ưu tiên văn bản có hiệu lực mới hơn

ĐỊNH DẠNG TRẢ LỜI BẮT BUỘC:
1. Căn cứ pháp lý: [liệt kê các điều luật áp dụng]
2. Nội dung tư vấn: [giải thích chi tiết có trích dẫn [1][2]...]
3. Kết luận: [tóm tắt ngắn gọn]
"""

USER_PROMPT_TEMPLATE = """
VĂN BẢN PHÁP LUẬT LIÊN QUAN:

{chunks_with_index}

---
CÂU HỎI: {query}

Trả lời theo đúng định dạng yêu cầu, có trích dẫn nguồn.
"""

def build_chunks_with_index(chunks: list) -> str:
    result = []
    for i, chunk in enumerate(chunks, 1):
        result.append(f"""
[{i}] {chunk.metadata['law_name']} — {chunk.metadata['article']}, {chunk.metadata['clause']}
Hiệu lực từ: {chunk.metadata['effective_date']}
Nội dung: {chunk.content}
""")
    return "\n".join(result)