//
//  HandJointRecord.swift
//  SignLanguageRecorder
//
//  Created by satoshi kuwano on 2026/07/10.
//

import Foundation

/// CSVの1行に対応するデータ
struct HandJointRecord {
    let frame: Int
    let time: TimeInterval
    let hand: String
    let joint: String
    let x: Float
    let y: Float
    let z: Float
    let isTracked: Bool

    /// CSVの1行へ変換する
    var csvRow: String {
        [
            String(frame),
            String(format: "%.6f", time),
            hand,
            joint,
            String(format: "%.6f", x),
            String(format: "%.6f", y),
            String(format: "%.6f", z),
            String(isTracked)
        ].joined(separator: ",")
    }
}
