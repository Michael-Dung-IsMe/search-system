# Quy ước cấu trúc mã nguồn

```text
backend/
├── core/
│   ├── detector.py
│   ├── embedder.py
│   ├── extractor.py
│   ├── normalizer.py
│   ├── retriever.py
│   ├── reranker.py
│   ├── search_audit.py
│   └── transcriber.py
├── db/
├── domain/
├── routes/
├── schemas/
└── main.py

web/src/
├── app/
├── components/
├── lib/
└── types/
```

## Hướng phụ thuộc

- Route điều phối core services và schema.
- Retriever truy cập database thông qua `backend/db`.
- Frontend chỉ giao tiếp backend qua `web/src/lib/api.ts`.
- Pydantic schema và TypeScript interface phải đồng bộ.
- Mỗi `/api/search` request tạo `SearchState` mới; không có singleton lưu session tìm kiếm.

## Quy tắc thay đổi

- Đổi embedding model phải index lại vector cùng loại.
- Đổi API response phải cập nhật Pydantic, TypeScript và API tests.
- Đổi taxonomy phải cập nhật normalizer, retriever và test mapping.
- Logic retrieval và reranking không đặt trong React component.
