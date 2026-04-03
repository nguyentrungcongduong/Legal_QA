GOLDEN_DATASET = [

    # LOẠI 1: Factual — có số cụ thể, dễ verify (8 câu)
    {
        "id": "F001",
        "question": "Vượt đèn đỏ xe máy bị phạt bao nhiêu tiền?",
        "ground_truth": "Phạt tiền từ 600.000đ đến 1.000.000đ",
        "expected_article": "Điều 6, Khoản 1, NĐ 100/2019",
        "type": "factual", "difficulty": "easy"
    },
    {
        "id": "F002",
        "question": "Lái xe ô tô có nồng độ cồn vượt mức tối đa bị phạt thế nào?",
        "ground_truth": "Phạt từ 30-40 triệu, tước GPLX 22-24 tháng",
        "expected_article": "Điều 5, Khoản 8, NĐ 100/2019",
        "type": "factual", "difficulty": "medium"
    },
    {
        "id": "F003",
        "question": "Xe máy không có gương chiếu hậu bị xử phạt bao nhiêu?",
        "ground_truth": "Phạt tiền từ 100.000đ đến 200.000đ",
        "expected_article": "Điều 17, Khoản 1, NĐ 100/2019",
        "type": "factual", "difficulty": "easy"
    },

    # LOẠI 2: Temporal — luật cũ vs luật mới (5 câu)
    {
        "id": "T001",
        "question": "Mức phạt uống rượu lái xe hiện hành là bao nhiêu?",
        "ground_truth": "Theo NĐ 123/2021 sửa đổi NĐ 100/2019...",
        "expected_article": "Điều 3, NĐ 123/2021",
        "type": "temporal", "difficulty": "hard",
        "trap": "NĐ 100/2019 có mức phạt cũ hơn, phải lấy NĐ 123/2021"
    },
    {
        "id": "T002",
        "question": "Quy định về nồng độ cồn bằng 0 áp dụng từ khi nào?",
        "ground_truth": "Từ 01/01/2020 theo NĐ 100/2019",
        "expected_article": "Điều 5, NĐ 100/2019",
        "type": "temporal", "difficulty": "medium"
    },

    # LOẠI 3: Conflict — nhiều văn bản liên quan (4 câu)
    {
        "id": "C001",
        "question": "Xe tải quá tải bị xử phạt theo quy định nào?",
        "ground_truth": "Kết hợp NĐ 100/2019 và Thông tư hướng dẫn...",
        "expected_article": "Điều 24, NĐ 100/2019 + Thông tư 46/2015",
        "type": "conflict", "difficulty": "hard",
        "trap": "Cần tổng hợp cả Nghị định lẫn Thông tư"
    },

    # LOẠI 4: Out of domain — phải từ chối (3 câu)
    {
        "id": "O001",
        "question": "Thủ tục đăng ký kết hôn cần giấy tờ gì?",
        "ground_truth": "OUT_OF_DOMAIN",
        "type": "out_of_domain", "difficulty": "easy",
        "expected_behavior": "Từ chối, không hallucinate"
    },
    {
        "id": "O002",
        "question": "Luật thuế thu nhập cá nhân quy định thế nào?",
        "ground_truth": "OUT_OF_DOMAIN",
        "type": "out_of_domain", "difficulty": "easy"
    }
]