from transformers import AutoTokenizer, AutoModelForSequenceClassification
import json

# 加载模型
model_path = "models/intent_model"
# model_path = "models/wechat_intent_model"
tokenizer = AutoTokenizer.from_pretrained(model_path)
model = AutoModelForSequenceClassification.from_pretrained(model_path)

# 加载意图映射
with open(f"{model_path}/intent_mapping.json", "r", encoding="utf-8") as f:
    mapping = json.load(f)
    id2intent = {int(k): v for k, v in mapping["id2intent"].items()}

# 预测
text = "专门飞去印度就为了吃咖喱？"
inputs = tokenizer(text, return_tensors="pt")
outputs = model(**inputs)
predicted_id = outputs.logits.argmax(-1).item()
intent = id2intent[predicted_id]

print(f"文本: {text}")
print(f"意图: {intent}")
