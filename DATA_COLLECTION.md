# Data Collection — Implementation Notes / データ収集 実装メモ

Hand-joint recording on Apple Vision Pro. Bilingual reference (EN / 日本語).
Apple Vision Pro の手関節記録。英語・日本語の対訳リファレンス。

---

## 1. Changes & Why / 変更点と理由

- **Info.plist file-sharing keys** (`UIFileSharingEnabled`, `LSSupportsOpeningDocumentsInPlace`) → CSVs become visible in the Files app / iCloud, no Mac needed.
  **Info.plist のファイル共有キー** → CSV が Files アプリ・iCloud に表示され、Mac 不要で取り出せる。

- **Long → wide format** (was 54 rows/frame; now 1 row/frame) → maps directly to ML features, easy to inspect.
  **縦持ち → 横持ち形式**（1フレーム54行 → 1フレーム1行）→ 機械学習の特徴量に直結し、確認も容易。

- **Added head pose** (`WorldTrackingProvider`) → signs are body-relative; head position/orientation lets features be head-relative.
  **頭部姿勢を追加** → 手話は身体基準のため、頭の位置・向きで頭部基準の特徴量を作れる。

- **Guided collection loop** (warm-up → 2s ready → 3s record → Keep/Redo) → auto-labeled, cleanly segmented, no manual labeling.
  **ガイド付き収集ループ** → 自動ラベル付け・区切り済みで、手動ラベリング不要。

- **Skeleton visualizer** (cyan = left, green = right) → subject sees tracking quality live and self-corrects.
  **骨格ビジュアライザ**（水色=左、緑=右）→ 被験者が追跡品質をその場で確認し自己修正できる。

- **Session lifecycle fix** → `isSessionRunning` resets when the immersive space closes (old bug left it stuck "running").
  **セッション状態の修正** → 没入空間を閉じると `isSessionRunning` がリセット（旧バグは「実行中」のままだった）。

- **Deadline-based sampling** → holds a steady 30 fps instead of drifting.
  **締め切りベースのサンプリング** → ずれずに安定した 30 fps を維持。

- **Booleans as `1`/`0`** → pandas reads them as numbers, not always-truthy strings.
  **真偽値を `1`/`0` で出力** → pandas が文字列でなく数値として読み込む。

- **Untracked hand → empty fields (NaN)**, never zero → zeros would look like a real position at the origin.
  **未追跡の手は空欄（NaN）**、ゼロにしない → ゼロは原点の実座標に見えてしまうため。

- **One CSV per subject/session, flush per kept window** → crash costs at most one window; file always valid.
  **被験者・セッション単位で1 CSV、ウィンドウごとに書き込み** → クラッシュしても最大1ウィンドウのみ損失。

---

## 2. Files Created / 作成ファイル

| File / ファイル | Purpose / 目的 |
|---|---|
| `JointDefinitions.swift` | Canonical 27-joint order + all column names. Single source of truth for the header. / 27関節の正準順序と全列名。ヘッダーの唯一の基準。 |
| `FrameSample.swift` | One frame (both hands + head) and its CSV row; window metadata. / 1フレーム（両手＋頭）とその CSV 行、ウィンドウのメタデータ。 |
| `SessionCSVWriter.swift` | Opens one CSV, appends a window, flushes to disk. / CSV を開き、ウィンドウを追記しディスクへ書き込む。 |
| `RecordingSession.swift` | Guided-loop state machine (warm-up, timing, Keep/Redo, `window_id`). / ガイドループの状態機械（ウォームアップ、タイミング、Keep/Redo、`window_id`）。 |
| `HandSkeletonVisualizer.swift` | 54 pre-allocated spheres; transforms updated per frame. / 事前確保した54個の球、毎フレーム位置を更新。 |

**Rewritten / 書き換え:** `HandTrackingRecorder.swift`, `ContentView.swift`, `ImmersiveView.swift`
**Deleted / 削除:** `HandJointRecord.swift`

---

## 3. Output / 実行結果

Verified on device from `session_S01_*.csv`:
実機の `session_S01_*.csv` で検証:

- **182 columns**, header exact. / **182列**、ヘッダー完全一致。
- **30.0 fps**, 90–91 frames per 3 s window. / **30.0 fps**、3秒ウィンドウあたり90〜91フレーム。
- **Head pose populated** every frame (0% NaN) → world tracking authorized. / **頭部姿勢が毎フレーム**記録（NaN 0%）→ ワールド追跡が許可済み。
- **Flags read as `int64`** (`1`/`0`) → boolean handling correct. / **フラグが `int64`** で読める → 真偽値処理が正しい。
- **Keep/Redo & warm-up flags** written correctly (`kept=0` redos, `is_warmup=1`). / **Keep/Redo・ウォームアップのフラグ**が正しく記録。
- **Part D reconstruction** groups by `window_id` cleanly with correct labels. / **Part D の再構成**が `window_id` で正しく分割・ラベル付け。

Not yet exercised / 未検証:
- Untracked-hand NaN path (both hands were tracked 100%). / 未追跡時の NaN 経路（今回は両手100%追跡）。
- Real attempts (all data was warm-up, `attempt_id=0`). / 本番アテンプト（今回は全てウォームアップ `attempt_id=0`）。

---

## 4. CSV Structure / CSV 構造

**182 columns = 13 metadata + 7 head + 162 joints.**
**182列 = メタデータ13 + 頭部7 + 関節162。**

### Metadata (13) / メタデータ

| Column | Type | Meaning / 意味 |
|---|---|---|
| `schema_version` | int | Schema version, for future format changes. / スキーマ版数、将来の形式変更用。 |
| `subject_id` | str | Subject code (e.g. `S01`); leave-one-person-out split key. / 被験者コード。人単位分割のキー。 |
| `session_id` | str | Recording session (date+time). / 記録セッション（日時）。 |
| `dominant_hand` | str | `right` / `left`; lets code canonicalize one-handed signs. / 利き手。片手手話の正規化に使用。 |
| `attempt_id` | int | Pass number; `0` = warm-up, `1..10` = real. / パス番号。`0`＝ウォームアップ、`1..10`＝本番。 |
| `sign_label` | str | Target sign (Hello / ThankYou / Yes / No / Help / Rest). / 対象サイン。 |
| `window_id` | int | Unique per recorded window. **The true delimiter.** / ウィンドウ固有ID。**真の区切り。** |
| `is_warmup` | 0/1 | Warm-up window flag. / ウォームアップの印。 |
| `kept` | 0/1 | `1` = kept, `0` = rejected (Redo). / `1`＝採用、`0`＝やり直し。 |
| `frame_index` | int | 0…N within the window (N varies). / ウィンドウ内の連番（Nは可変）。 |
| `timestamp` | float | Device time in seconds; gives real frame rate. / デバイス時刻（秒）。実フレームレート算出用。 |
| `left_hand_tracked` | 0/1 | Left hand tracked this frame. / このフレームで左手を追跡。 |
| `right_hand_tracked` | 0/1 | Right hand tracked this frame. / このフレームで右手を追跡。 |

### Head pose (7) / 頭部姿勢

| Column | Meaning / 意味 |
|---|---|
| `head_x`, `head_y`, `head_z` | Head position in ARKit world space (meters). / ARKit ワールド座標系での頭の位置（メートル）。 |
| `head_qx`, `head_qy`, `head_qz`, `head_qw` | Head orientation as a quaternion. / 頭の向き（クォータニオン）。 |

### Joint coordinates (162) / 関節座標

- Naming: **`{hand}_{joint}_{axis}`** — hand ∈ {`L`, `R`}, 27 joints, axis ∈ {`x`, `y`, `z`}.
  命名: **`{手}_{関節}_{軸}`** — 手 ∈ {`L`, `R`}、27関節、軸 ∈ {`x`, `y`, `z`}。
- Values: **ARKit world-space position in meters** (`originFromAnchorTransform × anchorFromJointTransform`), raw — normalize in code, not here.
  値: **ARKit ワールド座標系の位置（メートル）**、生データ。正規化はコード側で行う。
- Range: `L_wrist_x` … `R_littleFingerTip_z`. Untracked hand → all 81 of its columns empty (NaN).
  範囲: `L_wrist_x`〜`R_littleFingerTip_z`。未追跡の手は81列すべて空欄（NaN）。

**27 joints per hand (order) / 片手27関節（順序）:**

```
wrist, forearmWrist, forearmArm,
thumbKnuckle, thumbIntermediateBase, thumbIntermediateTip, thumbTip,
indexFingerMetacarpal, indexFingerKnuckle, indexFingerIntermediateBase, indexFingerIntermediateTip, indexFingerTip,
middleFingerMetacarpal, middleFingerKnuckle, middleFingerIntermediateBase, middleFingerIntermediateTip, middleFingerTip,
ringFingerMetacarpal, ringFingerKnuckle, ringFingerIntermediateBase, ringFingerIntermediateTip, ringFingerTip,
littleFingerMetacarpal, littleFingerKnuckle, littleFingerIntermediateBase, littleFingerIntermediateTip, littleFingerTip
```

---

## Reconstruct a window / ウィンドウの再構成

```python
import pandas as pd
df = pd.read_csv("session_S01_20260724_132649.csv")
for wid, w in df.groupby("window_id"):
    w = w.sort_values("frame_index")
    label = w["sign_label"].iloc[0]
    # w is now a clean (frames × 162) block → feature extraction
    # w は (フレーム数 × 162) の1ウィンドウ → 特徴抽出へ
```
