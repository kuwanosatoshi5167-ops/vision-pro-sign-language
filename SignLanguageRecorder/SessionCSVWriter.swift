//
//  SessionCSVWriter.swift
//  SignLanguageRecorder
//

import Foundation

/// One CSV per subject per session, appended one window at a time.
/// Each kept window is flushed to disk immediately so a crash costs at most
/// the window in progress (SCHEMA.md Part A).
@MainActor
final class SessionCSVWriter {

    let fileURL: URL

    private let handle: FileHandle

    init(subjectID: String, sessionID: String) throws {
        guard let documentsDirectory =
            FileManager.default.urls(
                for: .documentDirectory,
                in: .userDomainMask
            ).first
        else {
            throw RecorderError.documentsDirectoryNotFound
        }

        fileURL = documentsDirectory
            .appendingPathComponent(
                "session_\(subjectID)_\(sessionID).csv"
            )

        FileManager.default.createFile(
            atPath: fileURL.path,
            contents: nil
        )

        handle = try FileHandle(forWritingTo: fileURL)

        try write(JointDefinitions.header)
        try handle.synchronize()
    }

    /// Appends every frame of one window, then flushes.
    func append(
        frames: [FrameSample],
        metadata: WindowMetadata,
        kept: Bool
    ) throws {
        guard !frames.isEmpty else {
            return
        }

        let prefix = metadata.csvPrefix(kept: kept)
        let rows = frames.map { $0.csvRow(prefix: prefix) }

        try write(rows.joined(separator: "\n"))
        try handle.synchronize()
    }

    func close() {
        try? handle.close()
    }

    private func write(_ line: String) throws {
        guard let data = (line + "\n").data(using: .utf8) else {
            return
        }

        try handle.write(contentsOf: data)
    }
}

enum RecorderError: LocalizedError {
    case documentsDirectoryNotFound

    var errorDescription: String? {
        switch self {
        case .documentsDirectoryNotFound:
            return "The app Documents directory was not found."
        }
    }
}
