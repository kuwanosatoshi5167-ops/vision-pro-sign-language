# Aoi ML Report — CNN and LSTM

## 日本語サマリー

Apple Vision Proで収集した手関節座標を用いて、1D-CNNと双方向LSTMを比較した。S07を含む6名、合計339ウィンドウを使用し、同一被験者が訓練とテストに混在しない6-fold Leave-One-Subject-Out（LOSO）で評価した。

3つの乱数seedの平均では、LSTMがAccuracy **80.9 ± 2.7%**、Macro F1 **80.1 ± 2.7%**となり、CNNのAccuracy **77.2 ± 2.4%**、Macro F1 **76.6 ± 2.4%**を上回った。S07単独のテストAccuracyも、LSTMは平均74.4%、CNNは平均59.8%だった。

## 1. Accuracy and per-class F1

Accuracy and Macro F1 are the mean ± population standard deviation over seeds 0, 1, and 2. Per-class F1 uses the same aggregation.

| Model | Accuracy | Macro F1 |
|---|---:|---:|
| 1D-CNN | 77.2 ± 2.4% | 76.6 ± 2.4% |
| BiLSTM | **80.9 ± 2.7%** | **80.1 ± 2.7%** |

| Class | CNN F1 | LSTM F1 |
|---|---:|---:|
| Hello | 87.5 ± 2.8% | **96.5 ± 0.7%** |
| ThankYou | 85.3 ± 4.5% | **87.9 ± 6.2%** |
| Yes | 59.9 ± 3.2% | **63.5 ± 6.0%** |
| No | 66.0 ± 2.2% | **72.7 ± 2.0%** |
| Help | 85.2 ± 4.0% | **93.1 ± 4.4%** |
| Rest | **75.7 ± 6.5%** | 67.0 ± 2.1% |

The representative run used for each confusion matrix is the seed whose overall Accuracy is closest to the three-seed mean:

| Model | Representative seed | Accuracy | Macro F1 |
|---|---:|---:|---:|
| 1D-CNN | 1 | 75.8% | 75.1% |
| BiLSTM | 2 | 81.7% | 80.5% |

## 2. Confusion matrices

### 1D-CNN

![CNN confusion matrix](results/aoi_ml/cnn_confusion_matrix.png)

### BiLSTM

![LSTM confusion matrix](results/aoi_ml/lstm_confusion_matrix.png)

The largest remaining errors are among `Yes`, `No`, and `Rest`. LSTM substantially improves `Hello`, `ThankYou`, and `Help`, but `Yes` and `Rest` remain difficult.

## 3. Steps done

1. Loaded every `Data/*.csv` file and retained only `is_warmup == 0` and `kept == 1` windows.
2. Used six subjects: S01, S02, S03, S04, S05, and S07.
3. Converted 54 hand joints from world coordinates to head-relative coordinates using the recorded head position and quaternion.
4. Sorted frames by `frame_index` and fixed each window at 90 frames by truncating or padding.
5. Interpolated temporary tracking gaps. Added left- and right-hand tracking flags as two explicit input channels, giving 164 features per frame.
6. Standardized coordinates using observed frames from the training subjects only. Validation and test data never contributed to normalization statistics.
7. Used six-fold LOSO. In each outer fold, one subject was held out for testing and a different subject was held out for validation and early stopping. The remaining four subjects were used for training.
8. Used class-weighted cross-entropy, AdamW, validation Macro F1 early stopping, and seeds 0, 1, and 2.
9. Evaluated a temporal 1D-CNN and a bidirectional LSTM under the same folds and preprocessing.
10. Saved fold metrics, seed metrics, per-class F1, confusion matrices, and an environment summary under `results/aoi_ml/`.

### Reproduction

On Windows PowerShell from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-ml.txt
.\.venv\Scripts\python.exe ml\aoi_lstm_cnn.py --output-dir results\aoi_ml --seeds 0 1 2 --max-epochs 80 --patience 12 --threads 4
```

S07 is intentionally not included in Git. To reproduce the exact reported numbers, its CSV must be provided privately and placed directly under `Data/` before running the command.

## 4. Limitations

- Only six subjects were evaluated, with one recording session per subject. Generalization across days, devices, environments, and a larger population remains unknown.
- S01–S05 contain 60 kept test windows each, while S07 contains 39. The final class supports are therefore 56–57 rather than perfectly balanced.
- S07 has substantially more tracking loss than the existing data: 28.1% of kept frames have an untracked left hand and 14.0% have an untracked right hand. Interpolation and tracking-mask channels reduce, but do not eliminate, this domain shift.
- Each fold uses only one validation subject. Results can depend on which subject is selected for early stopping, especially with the small dataset.
- Windows are fixed to the first 90 frames. Truncation or end padding may discard timing information.
- Hyperparameters were deliberately limited; a full nested search was not performed.
- `Yes`, `No`, and `Rest` remain confused, suggesting that additional motion features, more subjects, or more consistent recordings may be needed.
- Offline classification was evaluated; latency and accuracy in live Vision Pro inference were not measured.

## Output files

- `results/aoi_ml/fold_metrics.csv`: subject-level results for every seed and fold
- `results/aoi_ml/seed_metrics.csv`: overall LOSO results for each seed
- `results/aoi_ml/per_class_f1.csv`: per-class mean, standard deviation, and representative-run F1
- `results/aoi_ml/*_confusion_matrix.csv`: numeric confusion matrices
- `results/aoi_ml/*_confusion_matrix.png`: presentation-ready confusion matrices
- `results/aoi_ml/summary.json`: dataset, model, evaluation, and environment summary
