from datasets import load_dataset
from sklearn.model_selection import train_test_split
import torch

from transformers import TrainingArguments, default_data_collator
from datasets import load_dataset
import wandb
from transformers import AutoTokenizer, MT5Tokenizer
from multi_model import *
from data_processing import Build_Dataset,DataCollatorForTranslation
from trainer import *
import os

    
    
def preprocess_function(examples):
    inputs = examples['query']  # Truy cập trực tiếp các danh sách cột
    targets = examples['positive']  # Truy cập trực tiếp các danh sách cột

    model_inputs = tokenizer(inputs, max_length=512, padding='max_length', truncation=True, return_tensors="pt")
    labels = tokenizer(text_target=targets, max_length=512, padding='max_length', truncation=True, return_tensors="pt")

    model_inputs["labels"] = labels["input_ids"]
    return model_inputs

if __name__ == "__main__":
    os.environ["CUDA_VISIBLE_DEVICES"] = "0,1"
    
    set_seed(42)


    custom_model = SMT5Model()

    # if torch.cuda.device_count() > 1:
    #     print("Let's use", torch.cuda.device_count(), "GPUs!")
    #     custom_model = nn.DataParallel(custom_model)

    tokenizer = MT5Tokenizer.from_pretrained('google/mt5-base')

    # Load dataset và chọn 240 samples cho việc train
    datasets = load_dataset('wanhin/luat-translate', split='train')

    column_names = datasets.column_names

    # Chia dataset thành train và test sets
    split_dataset = datasets.train_test_split(test_size=0.0001)

    # Truy cập train và test sets
    train_dataset = split_dataset['train']
    eval_dataset = split_dataset['test']

    # Áp dụng preprocess_function vào datasets
    train_dataset = train_dataset.map(
                    preprocess_function,
                    batched=True,
                    num_proc=16,
                    batch_size=2,
                    remove_columns=column_names
                )

    eval_dataset = eval_dataset.map(
                    preprocess_function,
                    batched=True,
                    num_proc=16,
                    batch_size=2,
                    remove_columns=column_names
                )

    data_collator = default_data_collator
    
    training_args = TrainingArguments(
        output_dir='./translation-v0-3e',
        run_name='translation-v0',
        evaluation_strategy="epoch",  # Đánh giá mỗi epoch
        save_strategy="epoch",
        learning_rate=3e-5,
        per_device_train_batch_size=6,  # Batch size
        per_device_eval_batch_size=6,   # Batch size
        num_train_epochs=3,  # Số lượng epoch
        save_total_limit=3,
        bf16=True,
        gradient_accumulation_steps=128, 
        logging_dir='./logs',
        logging_steps=8,
        report_to="wandb",  # Báo cáo kết quả lên wandb
        load_best_model_at_end=True,  # Load model tốt nhất vào cuối quá trình huấn luyện
        remove_unused_columns=False,
        deepspeed="ds_config.json",
        # save_steps = 100,
        # eval_steps = 100
    )

    trainer = TranslationTrainer(
        model=custom_model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        tokenizer=tokenizer,
        data_collator=data_collator,
    )

    # Đăng nhập vào wandb
    wandb.login(key='7ac28caf9e3dc3e0685c97df182d52e13a81e311')

    # Đăng ký wandb
    wandb.init(project="se-form-model")

    try:
        # Train the model
        trainer.train()
    finally:
        # Kết thúc phiên làm việc với wandb
        wandb.finish()
