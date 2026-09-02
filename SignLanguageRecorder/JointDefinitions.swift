//
//  JointDefinitions.swift
//  SignLanguageRecorder
//

import ARKit

/// Single source of truth for the CSV layout (SCHEMA.md Part B).
/// The header is derived from these arrays, never written by hand.
enum JointDefinitions {

    static let schemaVersion = 1

    /// Canonical joint order. Changing this order invalidates existing CSVs.
    static let joints: [HandSkeleton.JointName] = [
        .wrist,
        .forearmWrist,
        .forearmArm,

        .thumbKnuckle,
        .thumbIntermediateBase,
        .thumbIntermediateTip,
        .thumbTip,

        .indexFingerMetacarpal,
        .indexFingerKnuckle,
        .indexFingerIntermediateBase,
        .indexFingerIntermediateTip,
        .indexFingerTip,

        .middleFingerMetacarpal,
        .middleFingerKnuckle,
        .middleFingerIntermediateBase,
        .middleFingerIntermediateTip,
        .middleFingerTip,

        .ringFingerMetacarpal,
        .ringFingerKnuckle,
        .ringFingerIntermediateBase,
        .ringFingerIntermediateTip,
        .ringFingerTip,

        .littleFingerMetacarpal,
        .littleFingerKnuckle,
        .littleFingerIntermediateBase,
        .littleFingerIntermediateTip,
        .littleFingerTip
    ]

    /// Constant within a window, then per-frame.
    static let metadataColumns = [
        "schema_version",
        "subject_id",
        "session_id",
        "dominant_hand",
        "attempt_id",
        "sign_label",
        "window_id",
        "is_warmup",
        "kept",
        "frame_index",
        "timestamp",
        "left_hand_tracked",
        "right_hand_tracked"
    ]

    static let headColumns = [
        "head_x", "head_y", "head_z",
        "head_qx", "head_qy", "head_qz", "head_qw"
    ]

    /// 2 hands x 27 joints x 3 axes = 162 columns.
    static let jointColumns: [String] = ["L", "R"].flatMap { hand in
        joints.flatMap { joint in
            ["x", "y", "z"].map { axis in
                "\(hand)_\(joint.csvName)_\(axis)"
            }
        }
    }

    static let allColumns = metadataColumns + headColumns + jointColumns

    static let header = allColumns.joined(separator: ",")

    /// Empty fields for one untracked hand (27 joints x 3 axes).
    static let emptyHandFields = [String](
        repeating: "",
        count: joints.count * 3
    )
}
