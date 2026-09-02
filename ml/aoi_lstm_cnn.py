"""Subject-independent CNN/LSTM evaluation for Vision Pro sign-language data.

The script loads kept, non-warm-up windows directly from Data/*.csv. Raw and
intermediate arrays are never written to disk; only aggregate metrics and plots
are saved. Evaluation uses leave-one-subject-out (LOSO) splits with a separate
validation subject for early stopping.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import platform
import random
from pathlib import Path

os.environ.setdefault(
    "MPLCONFIGDIR", str(Path(__file__).resolve().parents[1] / ".matplotlib")
)

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset


SIGNS = ["Hello", "ThankYou", "Yes", "No", "Help", "Rest"]
HEAD_POS = ["head_x", "head_y", "head_z"]
HEAD_QUAT = ["head_qx", "head_qy", "head_qz", "head_qw"]
TARGET_FRAMES = 90


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=Path("Data"))
    parser.add_argument("--output-dir", type=Path, default=Path("results/aoi_ml"))
    parser.add_argument("--models", nargs="+", choices=["cnn", "lstm"], default=["cnn", "lstm"])
    parser.add_argument("--seeds", nargs="+", type=int, default=[0, 1, 2])
    parser.add_argument("--max-epochs", type=int, default=80)
    parser.add_argument("--patience", type=int, default=12)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--threads", type=int, default=min(4, os.cpu_count() or 1))
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    return parser.parse_args()


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def classification_metrics(
    true: np.ndarray, predicted: np.ndarray, classes: int = len(SIGNS)
) -> tuple[float, float, np.ndarray, np.ndarray]:
    """Return accuracy, macro F1, per-class F1, and confusion matrix."""
    matrix = np.zeros((classes, classes), dtype=np.int64)
    np.add.at(matrix, (true.astype(int), predicted.astype(int)), 1)
    true_support = matrix.sum(axis=1)
    predicted_support = matrix.sum(axis=0)
    true_positive = np.diag(matrix).astype(np.float64)
    precision = np.divide(
        true_positive,
        predicted_support,
        out=np.zeros(classes, dtype=np.float64),
        where=predicted_support > 0,
    )
    recall = np.divide(
        true_positive,
        true_support,
        out=np.zeros(classes, dtype=np.float64),
        where=true_support > 0,
    )
    per_class_f1 = np.divide(
        2 * precision * recall,
        precision + recall,
        out=np.zeros(classes, dtype=np.float64),
        where=(precision + recall) > 0,
    )
    accuracy = float((true == predicted).mean())
    macro_f1 = float(per_class_f1.mean())
    return accuracy, macro_f1, per_class_f1, matrix


def quaternion_to_rotation(q: np.ndarray) -> np.ndarray:
    """Return head-to-world rotation matrices for (x, y, z, w) quaternions."""
    norm = np.linalg.norm(q, axis=1, keepdims=True)
    q = q / np.where(norm > 0, norm, 1.0)
    x, y, z, w = q.T
    rotation = np.empty((len(q), 3, 3), dtype=np.float64)
    rotation[:, 0, 0] = 1 - 2 * (y * y + z * z)
    rotation[:, 0, 1] = 2 * (x * y - w * z)
    rotation[:, 0, 2] = 2 * (x * z + w * y)
    rotation[:, 1, 0] = 2 * (x * y + w * z)
    rotation[:, 1, 1] = 1 - 2 * (x * x + z * z)
    rotation[:, 1, 2] = 2 * (y * z - w * x)
    rotation[:, 2, 0] = 2 * (x * z - w * y)
    rotation[:, 2, 1] = 2 * (y * z + w * x)
    rotation[:, 2, 2] = 1 - 2 * (x * x + y * y)
    return rotation


def to_head_frame(joints: np.ndarray, head_pos: np.ndarray, head_quat: np.ndarray) -> np.ndarray:
    frames = joints.shape[0]
    points = joints.reshape(frames, -1, 3)
    centered = points - head_pos[:, None, :]
    rotation = quaternion_to_rotation(head_quat)
    return np.einsum("fpc,fcd->fpd", centered, rotation).reshape(frames, -1)


def fix_length(values: np.ndarray, target: int, pad_value: np.ndarray | None = None) -> np.ndarray:
    if len(values) >= target:
        return values[:target]
    if len(values) == 0:
        raise ValueError("A recording window contains no frames")
    pad = values[-1] if pad_value is None else pad_value
    return np.concatenate([values, np.repeat(pad[None, ...], target - len(values), axis=0)], axis=0)


def interpolate_coordinates(values: np.ndarray) -> np.ndarray:
    """Interpolate short tracking gaps; all-missing channels remain NaN."""
    return pd.DataFrame(values).interpolate(limit_direction="both").to_numpy(dtype=np.float64)


def load_dataset(data_dir: Path) -> dict[str, np.ndarray | list[str]]:
    files = sorted(data_dir.glob("*.csv"))
    if not files:
        raise FileNotFoundError(f"No CSV files found in {data_dir}")

    expected_header: list[str] | None = None
    coord_cols: list[str] | None = None
    all_coords: list[np.ndarray] = []
    all_tracking: list[np.ndarray] = []
    labels: list[int] = []
    subjects: list[str] = []
    sample_keys: list[str] = []
    source_files: list[str] = []

    for path in files:
        frame = pd.read_csv(path)
        header = frame.columns.tolist()
        if expected_header is None:
            expected_header = header
            coord_cols = [
                name
                for name in header
                if (name.startswith("L_") or name.startswith("R_"))
                and name.endswith(("_x", "_y", "_z"))
            ]
            if len(coord_cols) != 162:
                raise ValueError(f"Expected 162 coordinate columns, found {len(coord_cols)}")
        elif header != expected_header:
            raise ValueError(f"CSV header does not match the reference: {path}")

        kept = frame[(frame["is_warmup"] == 0) & (frame["kept"] == 1)].copy()
        grouped = kept.groupby(["subject_id", "session_id", "window_id"], sort=True)
        for (subject, session, window), group in grouped:
            group = group.sort_values("frame_index")
            label = str(group["sign_label"].iloc[0])
            if label not in SIGNS:
                raise ValueError(f"Unknown label {label!r} in {path}")

            joints = group[coord_cols].to_numpy(dtype=np.float64)
            head_pos = group[HEAD_POS].to_numpy(dtype=np.float64)
            head_quat = group[HEAD_QUAT].to_numpy(dtype=np.float64)
            coords = interpolate_coordinates(to_head_frame(joints, head_pos, head_quat))
            tracking = group[["left_hand_tracked", "right_hand_tracked"]].to_numpy(dtype=np.float32)

            all_coords.append(fix_length(coords, TARGET_FRAMES))
            all_tracking.append(fix_length(tracking, TARGET_FRAMES, pad_value=np.zeros(2, dtype=np.float32)))
            labels.append(SIGNS.index(label))
            subjects.append(str(subject))
            sample_keys.append(f"{subject}/{session}/{window}")
            source_files.append(path.name)

    return {
        "coords": np.stack(all_coords),
        "tracking": np.stack(all_tracking),
        "labels": np.asarray(labels, dtype=np.int64),
        "subjects": np.asarray(subjects),
        "sample_keys": sample_keys,
        "source_files": sorted(set(source_files)),
        "coord_cols": coord_cols or [],
    }


def normalize_fold(
    coords: np.ndarray,
    tracking: np.ndarray,
    train_index: np.ndarray,
) -> np.ndarray:
    """Normalize using observed training frames only and append two tracking masks."""
    observed = np.concatenate(
        [
            np.repeat(tracking[:, :, 0:1] > 0.5, 81, axis=2),
            np.repeat(tracking[:, :, 1:2] > 0.5, 81, axis=2),
        ],
        axis=2,
    )
    train_values = np.where(observed[train_index], coords[train_index], np.nan)
    mean = np.nanmean(train_values, axis=(0, 1), keepdims=True)
    std = np.nanstd(train_values, axis=(0, 1), keepdims=True)
    mean = np.nan_to_num(mean, nan=0.0)
    std = np.where(np.isfinite(std) & (std > 1e-6), std, 1.0)

    scaled = (coords - mean) / std
    scaled = np.nan_to_num(scaled, nan=0.0, posinf=0.0, neginf=0.0)
    return np.concatenate([scaled, tracking.astype(np.float64)], axis=2).astype(np.float32)


class TemporalCNN(nn.Module):
    def __init__(self, features: int, classes: int) -> None:
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv1d(features, 64, kernel_size=5, padding=2),
            nn.ReLU(),
            nn.MaxPool1d(2),
            nn.Conv1d(64, 128, kernel_size=5, padding=2),
            nn.ReLU(),
            nn.AdaptiveAvgPool1d(1),
        )
        self.classifier = nn.Sequential(nn.Dropout(0.30), nn.Linear(128, classes))

    def forward(self, values: torch.Tensor) -> torch.Tensor:
        encoded = self.features(values.transpose(1, 2)).squeeze(-1)
        return self.classifier(encoded)


class TemporalLSTM(nn.Module):
    def __init__(self, features: int, classes: int) -> None:
        super().__init__()
        self.projection = nn.Sequential(nn.Linear(features, 128), nn.LayerNorm(128), nn.ReLU())
        self.lstm = nn.LSTM(
            input_size=128,
            hidden_size=64,
            num_layers=1,
            batch_first=True,
            bidirectional=True,
        )
        self.classifier = nn.Sequential(nn.Dropout(0.30), nn.Linear(128, classes))

    def forward(self, values: torch.Tensor) -> torch.Tensor:
        projected = self.projection(values)
        encoded, _ = self.lstm(projected)
        return self.classifier(encoded.mean(dim=1))


def make_model(name: str, features: int, classes: int) -> nn.Module:
    if name == "cnn":
        return TemporalCNN(features, classes)
    if name == "lstm":
        return TemporalLSTM(features, classes)
    raise ValueError(name)


def predict(model: nn.Module, values: np.ndarray, device: torch.device, batch_size: int) -> np.ndarray:
    loader = DataLoader(TensorDataset(torch.from_numpy(values)), batch_size=batch_size, shuffle=False)
    predictions: list[np.ndarray] = []
    model.eval()
    with torch.no_grad():
        for (batch,) in loader:
            logits = model(batch.to(device))
            predictions.append(logits.argmax(dim=1).cpu().numpy())
    return np.concatenate(predictions)


def train_fold(
    model_name: str,
    values: np.ndarray,
    labels: np.ndarray,
    train_index: np.ndarray,
    validation_index: np.ndarray,
    test_index: np.ndarray,
    seed: int,
    args: argparse.Namespace,
    device: torch.device,
) -> tuple[np.ndarray, int, float]:
    set_seed(seed)
    model = make_model(model_name, values.shape[2], len(SIGNS)).to(device)
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=args.learning_rate, weight_decay=args.weight_decay
    )
    counts = np.bincount(labels[train_index], minlength=len(SIGNS)).astype(np.float32)
    weights = counts.sum() / (len(SIGNS) * np.maximum(counts, 1.0))
    criterion = nn.CrossEntropyLoss(weight=torch.tensor(weights, device=device))

    generator = torch.Generator().manual_seed(seed)
    dataset = TensorDataset(torch.from_numpy(values[train_index]), torch.from_numpy(labels[train_index]))
    loader = DataLoader(
        dataset,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=0,
        generator=generator,
    )

    best_state: dict[str, torch.Tensor] | None = None
    best_score = -1.0
    best_epoch = 0
    stale_epochs = 0

    for epoch in range(1, args.max_epochs + 1):
        model.train()
        for batch_values, batch_labels in loader:
            batch_values = batch_values.to(device)
            batch_labels = batch_labels.to(device)
            optimizer.zero_grad(set_to_none=True)
            loss = criterion(model(batch_values), batch_labels)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
            optimizer.step()

        validation_predictions = predict(
            model, values[validation_index], device=device, batch_size=args.batch_size
        )
        _, validation_score, _, _ = classification_metrics(
            labels[validation_index], validation_predictions
        )
        if validation_score > best_score + 1e-6:
            best_score = float(validation_score)
            best_epoch = epoch
            best_state = copy.deepcopy(model.state_dict())
            stale_epochs = 0
        else:
            stale_epochs += 1
        if stale_epochs >= args.patience:
            break

    if best_state is None:
        raise RuntimeError("Training did not produce a model state")
    model.load_state_dict(best_state)
    return (
        predict(model, values[test_index], device=device, batch_size=args.batch_size),
        best_epoch,
        best_score,
    )


def save_confusion_matrix(matrix: np.ndarray, model_name: str, output_dir: Path) -> None:
    pd.DataFrame(matrix, index=SIGNS, columns=SIGNS).to_csv(
        output_dir / f"{model_name}_confusion_matrix.csv", index_label="true_label"
    )
    plt.figure(figsize=(7, 6))
    sns.heatmap(matrix, annot=True, fmt="d", cmap="Blues", xticklabels=SIGNS, yticklabels=SIGNS)
    plt.title(f"{model_name.upper()} LOSO confusion matrix")
    plt.xlabel("Predicted")
    plt.ylabel("True")
    plt.tight_layout()
    plt.savefig(output_dir / f"{model_name}_confusion_matrix.png", dpi=180)
    plt.close()


def resolve_device(requested: str) -> torch.device:
    if requested == "cuda":
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA was requested but is not available")
        return torch.device("cuda")
    if requested == "auto" and torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def main() -> None:
    args = parse_args()
    torch.set_num_threads(args.threads)
    device = resolve_device(args.device)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    dataset = load_dataset(args.data_dir)
    coords = dataset["coords"]
    tracking = dataset["tracking"]
    labels = dataset["labels"]
    subjects = dataset["subjects"]
    if not isinstance(coords, np.ndarray) or not isinstance(tracking, np.ndarray):
        raise TypeError("Unexpected dataset representation")
    if not isinstance(labels, np.ndarray) or not isinstance(subjects, np.ndarray):
        raise TypeError("Unexpected label representation")

    unique_subjects = sorted(np.unique(subjects).tolist())
    if len(unique_subjects) < 3:
        raise ValueError("At least three subjects are required for train/validation/test splits")

    print(
        f"Loaded {len(labels)} windows from {len(unique_subjects)} subjects: "
        f"{', '.join(unique_subjects)} | device={device}"
    )
    print("Class counts:", {SIGNS[i]: int((labels == i).sum()) for i in range(len(SIGNS))})

    fold_rows: list[dict[str, object]] = []
    seed_rows: list[dict[str, object]] = []
    per_class_rows: list[dict[str, object]] = []
    model_summaries: dict[str, object] = {}

    for model_name in args.models:
        predictions_by_seed: list[np.ndarray] = []
        class_f1_by_seed: list[np.ndarray] = []
        for seed in args.seeds:
            out_of_fold = np.full(len(labels), -1, dtype=np.int64)
            for fold_number, test_subject in enumerate(unique_subjects):
                validation_subject = unique_subjects[(fold_number + 1) % len(unique_subjects)]
                test_index = np.flatnonzero(subjects == test_subject)
                validation_index = np.flatnonzero(subjects == validation_subject)
                train_index = np.flatnonzero(
                    (subjects != test_subject) & (subjects != validation_subject)
                )
                normalized = normalize_fold(coords, tracking, train_index)
                test_predictions, best_epoch, best_validation_f1 = train_fold(
                    model_name,
                    normalized,
                    labels,
                    train_index,
                    validation_index,
                    test_index,
                    seed,
                    args,
                    device,
                )
                out_of_fold[test_index] = test_predictions
                fold_accuracy, fold_macro_f1, _, _ = classification_metrics(
                    labels[test_index], test_predictions
                )
                fold_rows.append(
                    {
                        "model": model_name,
                        "seed": seed,
                        "test_subject": test_subject,
                        "validation_subject": validation_subject,
                        "test_windows": len(test_index),
                        "best_epoch": best_epoch,
                        "validation_macro_f1": best_validation_f1,
                        "accuracy": fold_accuracy,
                        "macro_f1": fold_macro_f1,
                    }
                )
                print(
                    f"{model_name} seed={seed} test={test_subject} val={validation_subject} "
                    f"accuracy={fold_accuracy:.3f} macro_f1={fold_macro_f1:.3f} epoch={best_epoch}"
                )

            if np.any(out_of_fold < 0):
                raise RuntimeError("Some samples did not receive an out-of-fold prediction")
            predictions_by_seed.append(out_of_fold)
            seed_accuracy, seed_macro_f1, seed_class_f1, _ = classification_metrics(
                labels, out_of_fold
            )
            class_f1_by_seed.append(seed_class_f1)
            seed_rows.append(
                {
                    "model": model_name,
                    "seed": seed,
                    "accuracy": seed_accuracy,
                    "macro_f1": seed_macro_f1,
                }
            )

        seed_accuracies = np.asarray(
            [row["accuracy"] for row in seed_rows if row["model"] == model_name], dtype=float
        )
        seed_macro_f1s = np.asarray(
            [row["macro_f1"] for row in seed_rows if row["model"] == model_name], dtype=float
        )
        representative_index = int(np.argmin(np.abs(seed_accuracies - seed_accuracies.mean())))
        representative_seed = args.seeds[representative_index]
        representative = predictions_by_seed[representative_index]
        representative_accuracy, representative_macro_f1, representative_class_f1, matrix = (
            classification_metrics(labels, representative)
        )
        save_confusion_matrix(matrix, model_name, args.output_dir)
        class_f1_values = np.stack(class_f1_by_seed)
        for index, score in enumerate(representative_class_f1):
            per_class_rows.append(
                {
                    "model": model_name,
                    "class": SIGNS[index],
                    "support": int((labels == index).sum()),
                    "f1_mean": float(class_f1_values[:, index].mean()),
                    "f1_std": float(class_f1_values[:, index].std(ddof=0)),
                    "representative_seed": representative_seed,
                    "representative_f1": float(score),
                }
            )

        model_summaries[model_name] = {
            "accuracy_mean": float(seed_accuracies.mean()),
            "accuracy_std": float(seed_accuracies.std(ddof=0)),
            "macro_f1_mean": float(seed_macro_f1s.mean()),
            "macro_f1_std": float(seed_macro_f1s.std(ddof=0)),
            "representative_seed": representative_seed,
            "representative_accuracy": representative_accuracy,
            "representative_macro_f1": representative_macro_f1,
        }

    pd.DataFrame(fold_rows).to_csv(args.output_dir / "fold_metrics.csv", index=False)
    pd.DataFrame(seed_rows).to_csv(args.output_dir / "seed_metrics.csv", index=False)
    pd.DataFrame(per_class_rows).to_csv(args.output_dir / "per_class_f1.csv", index=False)

    summary = {
        "evaluation": {
            "method": "six-fold leave-one-subject-out",
            "validation": "next subject in sorted order; excluded from training",
            "early_stopping_metric": "validation macro F1",
            "seeds": args.seeds,
            "target_frames": TARGET_FRAMES,
            "tracking_handling": "temporal interpolation plus left/right tracking-mask channels",
        },
        "dataset": {
            "windows": len(labels),
            "subjects": unique_subjects,
            "class_counts": {SIGNS[i]: int((labels == i).sum()) for i in range(len(SIGNS))},
            "source_files": dataset["source_files"],
        },
        "models": model_summaries,
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "torch": torch.__version__,
            "device": str(device),
        },
    }
    (args.output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(model_summaries, indent=2))
    print(f"Saved aggregate outputs to {args.output_dir}")


if __name__ == "__main__":
    main()
