from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser


def evaluate(query, retrieved_docs, model):

    eval_prompt = PromptTemplate(
        template="""Bạn là một giám khảo chấm điểm dữ liệu. 
NHIỆM VỤ: Kiểm tra đoạn văn bản có chứa thông tin để trả lời câu hỏi không.

Câu hỏi: {query}
Đoạn văn bản: {context}

QUY ĐỊNH TRẢ LỜI:
1. Nếu có thông tin, trả về: {{"relevance": "yes"}}
2. Nếu không liên quan, trả về: {{"relevance": "no"}}
3. Chỉ trả về duy nhất định dạng JSON, không giải thích thêm, không chào hỏi.
""",
        input_variables=["query", "context"],
    )

    # Giả định bạn đã khởi tạo llm_evaluator (model nhẹ)
    eval_chain = eval_prompt | model | JsonOutputParser()

    validated_context = []
    need_fallback = False

    for doc in retrieved_docs:
        # Chấm điểm từng đoạn từ VectorDB
        result = eval_chain.invoke({"query": query, "context": doc.page_content})

        if result["relevance"] == "yes":
            validated_context.append(doc.page_content)
        elif result["relevance"] == "maybe":
            # Nếu mơ hồ, có thể giữ lại nhưng đánh dấu cần bổ sung
            validated_context.append(doc.page_content)
            need_fallback = True
        else:
            # Loại bỏ đoạn không liên quan (Incorrect)
            continue

    # 4. Xử lý logic rẽ nhánh
    if not validated_context or need_fallback:
        # Trường hợp 2: Dữ liệu trống hoặc mơ hồ -> Kích hoạt Fallback
        return "fallback_required", validated_context

    return "success", validated_context
