//
//  RecordingSession.swift
//  SignLanguageRecorder
//

import Foundation
import Observation

/// Drives the guided collection loop from SCHEMA.md Part A: one warm-up pass
/// followed by `attemptCount` passes through the sign set, each sign recorded
/// in its own fixed window with a Keep/Redo review.
///
/// Holds no ARKit state. The recorder buffers frames while `phase == .recording`
/// and writes them when `onCommit` fires.
@MainActor
@Observable
final class RecordingSession {

    enum Sign: String, CaseIterable {
        case hello = "Hello"
        case thankYou = "ThankYou"
        case yes = "Yes"
        case no = "No"
        case help = "Help"
        case rest = "Rest"
    }

    enum Phase {
        case idle
        case getReady
        case recording
        case review
        case finished
    }

    static let getReadyDuration: Duration = .seconds(2)
    static let recordingDuration: Duration = .seconds(3)

    private(set) var phase: Phase = .idle
    private(set) var currentWindow: WindowMetadata?

    /// Attempt 0 is the warm-up pass; 1...attemptCount are recorded attempts.
    private(set) var attemptID = 0
    private(set) var signIndex = 0

    /// Called on Keep (`true`) or Redo (`false`) so the recorder can write the
    /// buffered window. Rejected windows are still written, flagged `kept = 0`.
    var onCommit: ((Bool) -> Void)?

    let subjectID: String
    let sessionID: String
    let dominantHand: String

    private let attemptCount: Int
    private var windowCounter = 0
    private var task: Task<Void, Never>?

    init(
        subjectID: String,
        sessionID: String,
        dominantHand: String,
        attemptCount: Int = 10
    ) {
        self.subjectID = subjectID
        self.sessionID = sessionID
        self.dominantHand = dominantHand
        self.attemptCount = attemptCount
    }

    // MARK: - Prompts

    var currentSign: Sign {
        Sign.allCases[signIndex]
    }

    var isWarmup: Bool {
        attemptID == 0
    }

    var promptText: String {
        switch phase {
        case .idle:
            return "Ready to start."

        case .getReady:
            return "Get ready… \(currentSign.rawValue)"

        case .recording:
            return "GO — \(currentSign.rawValue)"

        case .review:
            return "Keep this take?"

        case .finished:
            return "Session complete."
        }
    }

    var progressText: String {
        let attempt = isWarmup
            ? "Warm-up"
            : "Attempt \(attemptID)/\(attemptCount)"

        return "\(attempt) · sign \(signIndex + 1)/\(Sign.allCases.count)"
    }

    // MARK: - Control

    func start() {
        guard phase == .idle else {
            return
        }

        runCurrentSign()
    }

    func keep() {
        commit(kept: true)
        advance()
    }

    func redo() {
        commit(kept: false)
        runCurrentSign()
    }

    func stop() {
        task?.cancel()
        task = nil

        currentWindow = nil
        phase = .finished
    }

    // MARK: - Window lifecycle

    private func runCurrentSign() {
        guard phase != .finished else {
            return
        }

        windowCounter += 1

        currentWindow = WindowMetadata(
            subjectID: subjectID,
            sessionID: sessionID,
            dominantHand: dominantHand,
            attemptID: attemptID,
            signLabel: currentSign.rawValue,
            windowID: windowCounter,
            isWarmup: isWarmup
        )

        task?.cancel()
        task = Task { [weak self] in
            guard let self else {
                return
            }

            phase = .getReady

            guard await sleep(Self.getReadyDuration) else {
                return
            }

            phase = .recording

            guard await sleep(Self.recordingDuration) else {
                return
            }

            phase = .review
        }
    }

    private func commit(kept: Bool) {
        guard phase == .review else {
            return
        }

        onCommit?(kept)
        currentWindow = nil
    }

    private func advance() {
        signIndex += 1

        if signIndex == Sign.allCases.count {
            signIndex = 0
            attemptID += 1
        }

        if attemptID > attemptCount {
            phase = .finished
            return
        }

        runCurrentSign()
    }

    private func sleep(_ duration: Duration) async -> Bool {
        do {
            try await Task.sleep(for: duration)
            return !Task.isCancelled
        } catch {
            return false
        }
    }
}
